"""Валидация чисел и работа со временем."""

import math
from datetime import datetime, timezone


def validate_amount(amount, allow_zero=False):
    """Не пропускать bool, NaN, бесконечности и отрицательные суммы."""
    if type(amount) not in (int, float) or not math.isfinite(amount):
        raise ValueError("'amount' должен быть конечным числом")
    if amount < 0 or (amount == 0 and not allow_zero):
        raise ValueError("'amount' должен быть положительным числом")
    return float(amount)


def utc_now():
    """Текущее время в ISO UTC."""
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    """Прочитать ISO-время, включая UTC с суффиксом Z."""
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result
