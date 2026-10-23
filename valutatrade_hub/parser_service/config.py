"""Параметры API; ключи читаются из окружения."""

import os
from dataclasses import dataclass, field


@dataclass
class ParserConfig:
    """Конфигурация клиентов курсов."""

    exchangerate_key: str = field(
        default_factory=lambda: os.environ.get("EXCHANGERATE_API_KEY", "")
    )
    coingecko_key: str = field(
        default_factory=lambda: os.environ.get("COINGECKO_DEMO_API_KEY", "")
    )
    coingecko_url: str = "https://api.coingecko.com/api/v3/simple/price"
    exchangerate_url: str = "https://v6.exchangerate-api.com/v6"
    fiat_currencies: tuple = ("EUR", "GBP", "RUB")
    crypto_id_map: dict = field(
        default_factory=lambda: {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
    )
    base_currency: str = "USD"
    timeout: int = 10
