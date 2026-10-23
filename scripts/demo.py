"""Воспроизводимое демо с явно обозначенными тестовыми ответами API."""

import os
import tempfile
from unittest.mock import Mock, patch


def fake_response(url, **kwargs):
    response = Mock(status_code=200)
    if "coingecko" in url:
        response.json.return_value = {
            "bitcoin": {"usd": 60000},
            "ethereum": {"usd": 3000},
            "solana": {"usd": 150},
        }
    else:
        response.json.return_value = {
            "result": "success",
            "conversion_rates": {
                "USD": 1,
                "EUR": 0.8,
                "GBP": 0.75,
                "RUB": 100,
            },
        }
    return response


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ["VALUTATRADE_DATA_DIR"] = directory
        os.environ["VALUTATRADE_LOGS_DIR"] = directory + "/logs"
        os.environ["EXCHANGERATE_API_KEY"] = "demo-not-a-real-key"
        from valutatrade_hub.cli.interface import execute
        from valutatrade_hub.core.usecases import TradingService
        from valutatrade_hub.logging_config import setup_logging

        setup_logging()
        service = TradingService()
        print("ДЕМО: ответы API подменены тестовыми, курсы не рыночные.")
        print("Остальной код — реальные команды, модели, JSON и журналы проекта.")
        commands = [
            "update-rates",
            "show-rates --top 2",
            "register --username student --password demo1234",
            "login --username student --password demo1234",
            "show-portfolio",
            "buy --currency BTC --amount 0.05",
            "buy --currency EUR --amount 100",
            "sell --currency BTC --amount 0.01",
            "show-portfolio",
            "get-rate --from USD --to BTC",
            "show-rates --currency EUR",
            "sell --currency BTC --amount 10",
            "buy --currency ABC --amount 1",
        ]
        with patch("requests.get", side_effect=fake_response):
            for command in commands:
                print("\n> " + command, flush=True)
                execute(command, service)


if __name__ == "__main__":
    main()
