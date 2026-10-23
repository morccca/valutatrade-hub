"""Необязательный запуск обновлений с заданным интервалом."""

import argparse
import logging
import time

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.updater import RatesUpdater


def main():
    """Обновлять курсы до Ctrl+C; автоматически не запускается."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=300)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("Интервал должен быть положительным")
    setup_logging()
    try:
        while True:
            try:
                RatesUpdater().run_update()
            except ApiRequestError as error:
                logging.getLogger("valutatrade.parser").warning("%s", error)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Обновление остановлено.")


if __name__ == "__main__":
    main()
