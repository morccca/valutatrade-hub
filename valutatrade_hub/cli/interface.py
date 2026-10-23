"""Разбор команд и вывод результатов без логики сделок."""

import argparse
import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import CURRENCIES
from valutatrade_hub.core.exceptions import ApiRequestError, CurrencyNotFoundError
from valutatrade_hub.core.usecases import TradingService
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.updater import RatesUpdater


def create_parser():
    """Описать команды и обязательные аргументы."""
    parser = argparse.ArgumentParser(prog="valutatrade")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("register", "login"):
        command = commands.add_parser(name)
        command.add_argument("--username", required=True)
        command.add_argument("--password", required=True)
    command = commands.add_parser("show-portfolio")
    command.add_argument("--base", default="USD")
    for name in ("buy", "sell"):
        command = commands.add_parser(name)
        command.add_argument("--currency", required=True)
        command.add_argument("--amount", required=True, type=float)
    command = commands.add_parser("get-rate")
    command.add_argument("--from", dest="from_code", required=True)
    command.add_argument("--to", dest="to_code", required=True)
    command = commands.add_parser("update-rates")
    command.add_argument("--source", choices=("coingecko", "exchangerate"))
    command = commands.add_parser("show-rates")
    command.add_argument("--currency")
    command.add_argument("--top", type=int)
    command.add_argument("--base", default="USD")
    command = commands.add_parser("help")
    command.add_argument("topic", nargs="?")
    commands.add_parser("exit")
    return parser


def execute(command, service, parser=None):
    """Выполнить одну команду и сохранить интерактивную сессию."""
    parser = parser or create_parser()
    try:
        tokens = shlex.split(command)
        if not tokens:
            return True
        args = parser.parse_args(tokens)
        if args.command == "exit":
            return False
        if args.command == "help":
            if args.topic:
                parser.parse_args([args.topic, "--help"])
            else:
                parser.print_help()
        elif args.command == "register":
            result = service.register(args.username, args.password)
            print(
                f"Пользователь '{result['username']}' зарегистрирован "
                f"(id={result['user_id']}). Выполните login."
            )
        elif args.command == "login":
            result = service.login(args.username, args.password)
            print(f"Вы вошли как '{result['username']}'")
        elif args.command == "show-portfolio":
            result = service.show_portfolio(args.base)
            print(f"Портфель пользователя '{result['username']}' (база: {args.base}):")
            if not result["rows"]:
                print("Портфель пуст.")
            table = PrettyTable(["Валюта", "Баланс", f"Стоимость, {args.base}"])
            for code, balance, value in result["rows"]:
                table.add_row([code, f"{balance:.4f}", f"{value:.2f}"])
            print(table)
            print(f"ИТОГО: {result['total']:,.2f} {args.base}")
        elif args.command in ("buy", "sell"):
            operation = service.buy if args.command == "buy" else service.sell
            result = operation(args.currency, args.amount)
            label = "Покупка" if args.command == "buy" else "Продажа"
            print(
                f"{label} выполнена: {args.amount:.4f} {args.currency} "
                f"по курсу {result['rate']:.4f} USD/{args.currency}"
            )
            print(f"Баланс: {result['before']:.4f} → {result['after']:.4f}")
            print(f"Оценочная стоимость: {result['value']:.2f} USD")
        elif args.command == "get-rate":
            result = service.get_rate(args.from_code, args.to_code)
            print(
                f"Курс {args.from_code}→{args.to_code}: {result['rate']:.8f} "
                f"(обновлено: {result['updated_at']})"
            )
            print(f"Обратный курс: {1 / result['rate']:.8f}")
        elif args.command == "update-rates":
            clients = {
                "coingecko": CoinGeckoClient,
                "exchangerate": ExchangeRateApiClient,
            }
            selected = [clients[args.source]()] if args.source else None
            result = RatesUpdater(clients=selected).run_update()
            print(f"Обновлено курсов: {result['updated']}")
            for error in result["errors"]:
                print(f"Частичное обновление: {error}")
        elif args.command == "show-rates":
            rows = service.show_rates(args.currency, args.top, args.base)
            table = PrettyTable(["Пара", "Курс", "Обновлено (UTC)"])
            for code, rate, timestamp in rows:
                table.add_row([f"{code}_{args.base}", f"{rate:.8f}", timestamp])
            print(table)
    except CurrencyNotFoundError as error:
        print(error)
        print("Поддерживаются: " + ", ".join(CURRENCIES))
    except ApiRequestError as error:
        print(error)
        print("Проверьте сеть и настройки API, затем выполните update-rates.")
    except (ValueError, OSError) as error:
        print(f"Ошибка: {error}")
    except SystemExit:
        # argparse завершает разбор после --help или ошибки, но не всю сессию.
        pass
    return True


def main():
    """Запустить интерактивный режим; пароль не сохраняется в истории команд."""
    setup_logging()
    service = TradingService()
    parser = create_parser()
    print("ValutaTrade Hub. Учебный симулятор. help — команды, exit — выход.")
    while True:
        try:
            if not execute(input("> "), service, parser):
                break
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break


if __name__ == "__main__":
    main()
