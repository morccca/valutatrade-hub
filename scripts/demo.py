"""Воспроизводимое демо с явно обозначенными тестовыми ответами API."""

import argparse
import os
import tempfile
from contextlib import nullcontext
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Получить курсы CoinGecko")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        os.environ["VALUTATRADE_DATA_DIR"] = directory
        os.environ["VALUTATRADE_LOGS_DIR"] = directory + "/logs"
        if not args.live:
            os.environ["EXCHANGERATE_API_KEY"] = "demo-not-a-real-key"
        from valutatrade_hub.cli.interface import execute
        from valutatrade_hub.core.usecases import TradingService
        from valutatrade_hub.logging_config import setup_logging

        setup_logging()
        service = TradingService()
        print("Курсы CoinGecko из API." if args.live else "Тестовые курсы, без сети.")
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
        if args.live:
            commands[0] = "update-rates --source coingecko"
            commands = [command for command in commands if "EUR" not in command]
        responses = nullcontext() if args.live else patch(
            "requests.get", side_effect=fake_response
        )
        with responses:
            for command in commands:
                print("\n> " + command, flush=True)
                execute(command, service)


if __name__ == "__main__":
    main()
