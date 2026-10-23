"""Получение курсов из двух источников в едином формате XXX_USD."""

from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.utils import validate_amount
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Общий контракт поставщика курсов."""

    source = ""

    def __init__(self, config=None):
        self.config = config or ParserConfig()

    def request_json(self, url, **kwargs):
        """Получить JSON без раскрытия URL с ключом в тексте ошибок."""
        try:
            response = requests.get(url, timeout=self.config.timeout, **kwargs)
            if response.status_code != 200:
                raise ApiRequestError(f"{self.source}: HTTP {response.status_code}")
            return response.json()
        except requests.exceptions.RequestException:
            raise ApiRequestError(f"{self.source}: ошибка сети или ответа") from None
        except ValueError:
            raise ApiRequestError(f"{self.source}: некорректный JSON") from None

    @abstractmethod
    def fetch_rates(self):
        """Вернуть словарь вида BTC_USD: стоимость одного BTC в USD."""


class CoinGeckoClient(BaseApiClient):
    """Криптовалютные котировки."""

    source = "CoinGecko"

    def fetch_rates(self):
        """Получить несколько валют одним запросом."""
        headers = {}
        if self.config.coingecko_key:
            headers["x-cg-demo-api-key"] = self.config.coingecko_key
        data = self.request_json(
            self.config.coingecko_url,
            headers=headers,
            params={
                "ids": ",".join(self.config.crypto_id_map.values()),
                "vs_currencies": "usd",
            },
        )
        try:
            return {
                f"{code}_USD": validate_amount(data[coin_id]["usd"])
                for code, coin_id in self.config.crypto_id_map.items()
            }
        except (KeyError, TypeError, ValueError):
            raise ApiRequestError("CoinGecko: некорректные котировки") from None


class ExchangeRateApiClient(BaseApiClient):
    """Фиатные котировки с пересчётом обратного курса."""

    source = "ExchangeRate-API"

    def fetch_rates(self):
        """Привести ответ conversion_rates к стоимости валюты в USD."""
        if not self.config.exchangerate_key:
            raise ApiRequestError("Не задан EXCHANGERATE_API_KEY")
        url = (
            f"{self.config.exchangerate_url}/{self.config.exchangerate_key}"
            f"/latest/{self.config.base_currency}"
        )
        data = self.request_json(url)
        if not isinstance(data, dict) or data.get("result") != "success":
            raise ApiRequestError("ExchangeRate-API: проверьте ключ и лимит запросов")
        try:
            rates = data["conversion_rates"]
            usd_rate = validate_amount(rates["USD"])
            return {
                f"{code}_USD": usd_rate / validate_amount(rates[code])
                for code in self.config.fiat_currencies
            }
        except (KeyError, TypeError, ValueError):
            raise ApiRequestError("ExchangeRate-API: некорректные котировки") from None
