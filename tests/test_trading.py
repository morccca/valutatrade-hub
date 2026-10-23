"""Проверки портфеля, хранения, API и поведения при ошибках."""

import io
import json
import logging
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from valutatrade_hub.cli.interface import execute
from valutatrade_hub.core.currencies import Currency, get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, InsufficientFundsError
from valutatrade_hub.core.models import User, Wallet
from valutatrade_hub.core.usecases import TradingService
from valutatrade_hub.core.utils import utc_now
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


class TradingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "VALUTATRADE_DATA_DIR": self.directory.name,
                "VALUTATRADE_LOGS_DIR": self.directory.name + "/logs",
            },
        )
        self.env.start()
        SettingsLoader().reload()
        setup_logging()
        self.database = DatabaseManager()
        self.service = TradingService()
        self.seed_rates()

    def tearDown(self):
        for name in ("actions", "parser"):
            logger = logging.getLogger("valutatrade." + name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        self.env.stop()
        SettingsLoader().reload()
        self.directory.cleanup()

    def seed_rates(self):
        RatesStorage().save(
            {
                pair: {"rate": rate, "updated_at": utc_now(), "source": "Test fixture"}
                for pair, rate in {"BTC_USD": 60000, "EUR_USD": 1.2}.items()
            }
        )

    def login(self):
        self.service.register("anna", "secret")
        self.service.login("anna", "secret")

    def test_registration_hash_and_unique_name(self):
        info = self.service.register("anna", "secret")
        self.assertNotIn("hashed_password", info)
        stored = self.database.read("users.json", [])[0]
        self.assertNotEqual(stored["hashed_password"], "secret")
        self.assertTrue(User(**stored).verify_password("secret"))
        with self.assertRaises(ValueError):
            self.service.register(" anna ", "secret")
        with self.assertRaises(ValueError):
            self.service.login("anna", "wrong")
        self.assertIsNone(self.service.user)

    def test_wallet_rejects_invalid_values(self):
        wallet = Wallet("USD", 20)
        for value in (0, -1, True, float("inf"), float("nan"), "5"):
            with self.assertRaises(ValueError):
                wallet.deposit(value)
        with self.assertRaises(InsufficientFundsError):
            wallet.withdraw(21)
        self.assertEqual(wallet.balance, 20)

    def test_currency_abstract_class_and_display(self):
        with self.assertRaises(TypeError):
            Currency("Test", "TT")
        self.assertIn("[FIAT]", get_currency("USD").get_display_info())
        self.assertIn("[CRYPTO]", get_currency("BTC").get_display_info())

    def test_trades_persist_and_portfolio_conversion(self):
        self.login()
        self.service.buy("BTC", 0.05)
        self.service.sell("BTC", 0.01)
        result = self.service.show_portfolio("EUR")
        self.assertAlmostEqual(result["total"], 2000)
        restored = TradingService()
        restored.login("anna", "secret")
        self.assertAlmostEqual(
            restored.load_portfolio().get_wallet("BTC").balance, 0.04
        )
        with self.assertRaises(InsufficientFundsError):
            restored.sell("BTC", 1)
        self.assertAlmostEqual(
            restored.load_portfolio().get_wallet("BTC").balance, 0.04
        )
        portfolio = restored.load_portfolio()
        copy = portfolio.wallets
        copy.clear()
        self.assertIn("BTC", portfolio.wallets)

    def test_login_required_and_user_isolation(self):
        with self.assertRaises(ValueError):
            self.service.buy("BTC", 1)
        self.login()
        self.service.buy("USD", 100)
        self.service.register("other", "pass")
        self.service.login("other", "pass")
        self.assertEqual(self.service.show_portfolio()["total"], 0)

    def test_cross_rate_and_ttl(self):
        self.assertAlmostEqual(self.service.get_rate("EUR", "BTC")["rate"], 0.00002)
        self.assertEqual(self.service.get_rate("EUR", "EUR")["rate"], 1)
        snapshot = self.database.read("rates.json", {})
        snapshot["pairs"]["BTC_USD"]["updated_at"] = "2000-01-01T00:00:00Z"
        self.database.write("rates.json", snapshot)
        with self.assertRaises(ApiRequestError):
            self.service.get_rate("BTC", "USD")

    def test_failed_trade_does_not_change_storage(self):
        self.login()
        self.service.buy("BTC", 0.05)
        before = self.database.read("portfolios.json", [])
        self.database.write("rates.json", {"pairs": {}})
        with self.assertRaises(ApiRequestError):
            self.service.sell("BTC", 0.01)
        self.assertEqual(self.database.read("portfolios.json", []), before)

    def test_api_contracts_and_inverse_fiat_rate(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "result": "success",
            "conversion_rates": {"USD": 1, "EUR": 0.8},
        }
        config = ParserConfig(exchangerate_key="test-only", fiat_currencies=("EUR",))
        with patch("requests.get", return_value=response) as get:
            rates = ExchangeRateApiClient(config).fetch_rates()
            self.assertEqual(rates, {"EUR_USD": 1.25})
            self.assertEqual(get.call_args.kwargs["timeout"], 10)
        response.json.return_value = {"bitcoin": {"usd": 60000}}
        config.crypto_id_map = {"BTC": "bitcoin"}
        with patch("requests.get", return_value=response):
            self.assertEqual(CoinGeckoClient(config).fetch_rates(), {"BTC_USD": 60000})

    def test_api_errors_do_not_reveal_key(self):
        client = ExchangeRateApiClient(ParserConfig(exchangerate_key="PRIVATE_KEY"))
        with patch("requests.get", side_effect=requests.Timeout("PRIVATE_KEY")):
            with self.assertRaises(ApiRequestError) as raised:
                client.fetch_rates()
        self.assertNotIn("PRIVATE_KEY", str(raised.exception))
        with patch("requests.get", return_value=Mock(status_code=429)):
            with self.assertRaises(ApiRequestError):
                client.fetch_rates()

    def test_partial_update_preserves_other_source(self):
        broken = Mock(source="Broken")
        broken.fetch_rates.side_effect = ApiRequestError("offline")
        working = Mock(source="Working")
        working.fetch_rates.return_value = {"EUR_USD": 1.3}
        old = self.database.read("rates.json", {})["pairs"]["BTC_USD"]
        result = RatesUpdater([broken, working]).run_update()
        self.assertEqual(result["updated"], 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(self.database.read("rates.json", {})["pairs"]["BTC_USD"], old)

    def test_history_deduplication_and_atomic_write(self):
        update = {"BTC_USD": {"rate": 61000, "updated_at": utc_now(), "source": "Test"}}
        storage = RatesStorage()
        storage.save(update)
        count = len(self.database.read("exchange_rates.json", []))
        storage.save(update)
        self.assertEqual(len(self.database.read("exchange_rates.json", [])), count)
        before = self.database.read("rates.json", {})
        with self.assertRaises(ValueError):
            self.database.write("rates.json", {"bad": float("nan")})
        self.assertEqual(self.database.read("rates.json", {}), before)

    def test_corrupt_json_not_silently_replaced(self):
        path = Path(self.directory.name) / "users.json"
        path.write_text("broken")
        with self.assertRaises(ValueError):
            self.service.register("anna", "pass")
        self.assertEqual(path.read_text(), "broken")

    def test_singletons(self):
        self.assertIs(SettingsLoader(), SettingsLoader())
        self.assertIs(DatabaseManager(), DatabaseManager())

    def test_cli_happy_path_and_errors(self):
        output = io.StringIO()
        with redirect_stdout(output):
            for command in [
                "register --username anna --password pass",
                "login --username anna --password pass",
                "buy --currency BTC --amount 0.05",
                "sell --currency BTC --amount 0.01",
                "show-portfolio",
                "get-rate --from EUR --to BTC",
                "show-rates --top 1",
                "buy --currency ABC --amount 1",
                "sell --currency BTC --amount 5",
            ]:
                self.assertTrue(execute(command, self.service))
        text = output.getvalue()
        self.assertIn("Покупка выполнена", text)
        self.assertIn("Продажа выполнена", text)
        self.assertIn("Недостаточно средств", text)
        self.assertIn("Неизвестная валюта", text)

    def test_logs_include_success_and_failure_without_password(self):
        self.login()
        self.service.buy("USD", 10)
        with self.assertRaises(InsufficientFundsError):
            self.service.sell("USD", 11)
        text = (Path(self.directory.name) / "logs/actions.log").read_text()
        records = [json.loads(line.split(" ", 1)[1]) for line in text.splitlines()]
        self.assertEqual([row["result"] for row in records], ["OK", "ERROR"])
        self.assertNotIn("secret", text)


if __name__ == "__main__":
    unittest.main()
