"""Файловые журналы с ограничением размера."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging():
    """Настроить раздельные журналы сделок и получения курсов."""
    directory = Path(SettingsLoader().get("logs_dir"))
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("actions", "parser"):
        logger = logging.getLogger("valutatrade." + name)
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        handler = RotatingFileHandler(
            directory / (name + ".log"),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
