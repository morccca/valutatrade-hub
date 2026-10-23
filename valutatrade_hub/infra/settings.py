"""Общая конфигурация приложения."""

import os


class SettingsLoader:
    """Один набор настроек; __new__ проще отдельного метакласса."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.reload()
        return cls._instance

    def reload(self):
        """Загрузить настройки из переменных окружения."""
        self._settings = {
            "data_dir": "data",
            "logs_dir": "logs",
            "rates_ttl_seconds": 300,
            "base_currency": "USD",
        }
        self._settings["rates_ttl_seconds"] = int(
            os.environ.get("VALUTATRADE_RATES_TTL_SECONDS", "300")
        )
        for key in ("data_dir", "logs_dir"):
            value = os.environ.get("VALUTATRADE_" + key.upper())
            if value:
                self._settings[key] = value
        if self.get("rates_ttl_seconds") <= 0:
            raise ValueError("TTL должен быть положительным")

    def get(self, key, default=None):
        """Прочитать настройку с запасным значением."""
        return self._settings.get(key, default)
