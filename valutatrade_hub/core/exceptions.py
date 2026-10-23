"""Ошибки, которые консоль показывает пользователю."""


class InsufficientFundsError(ValueError):
    """На кошельке недостаточно валюты."""

    def __init__(self, available, required, code):
        super().__init__(
            f"Недостаточно средств: доступно {available} {code}, "
            f"требуется {required} {code}"
        )


class CurrencyNotFoundError(ValueError):
    """Код отсутствует в реестре валют."""

    def __init__(self, code):
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(Exception):
    """Курсы нельзя получить или использовать."""

    def __init__(self, reason):
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
