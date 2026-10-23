"""Общий интерфейс валют и небольшой реестр."""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.utils import validate_amount


class Currency(ABC):
    """Валюта с именем и кодом."""

    def __init__(self, name, code):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не должно быть пустым")
        if (
            not isinstance(code, str)
            or not 2 <= len(code) <= 5
            or not code.isascii()
            or not code.isalpha()
            or code != code.upper()
        ):
            raise ValueError("Код валюты: 2–5 заглавных латинских букв")
        self.name = name
        self.code = code

    @abstractmethod
    def get_display_info(self):
        """Вернуть описание валюты для консоли."""


class FiatCurrency(Currency):
    """Государственная валюта."""

    def __init__(self, name, code, issuing_country):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self):
        """Показать страну или зону эмиссии."""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта с алгоритмом и капитализацией."""

    def __init__(self, name, code, algorithm, market_cap=0.0):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = validate_amount(market_cap, allow_zero=True)

    def get_display_info(self):
        """Показать алгоритм и известную капитализацию."""
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


CURRENCIES = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("Pound Sterling", "GBP", "United Kingdom"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256"),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Proof of Stake"),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof of Stake"),
}


def get_currency(code):
    """Вернуть валюту по коду без неявной смены регистра."""
    if not isinstance(code, str) or code not in CURRENCIES:
        raise CurrencyNotFoundError(code)
    return CURRENCIES[code]
