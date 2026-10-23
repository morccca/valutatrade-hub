"""Простое JSON-хранилище для последовательного запуска CLI."""

import json
import os
import tempfile
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Единый доступ к файлам, без повторной инициализации при импортах."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def read(self, filename, default):
        """Прочитать JSON; повреждённый файл не считать пустым."""
        path = Path(SettingsLoader().get("data_dir")) / filename
        try:
            with path.open(encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return default
        except json.JSONDecodeError:
            raise ValueError(f"Повреждён файл {filename}; данные не перезаписаны")

    def write(self, filename, data):
        """Атомарно заменить файл после сериализации."""
        directory = Path(SettingsLoader().get("data_dir"))
        directory.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=directory, delete=False
            ) as file:
                temporary = file.name
                json.dump(data, file, ensure_ascii=False, indent=2, allow_nan=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, directory / filename)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
