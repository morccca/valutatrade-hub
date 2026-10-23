"""Пользователи, кошельки и валютные портфели."""

import hashlib
import hmac
import secrets

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.utils import parse_time, utc_now, validate_amount


class User:
    """Учебная модель пользователя с солёным SHA-256 по заданию."""

    def __init__(self, user_id, username, hashed_password, salt, registration_date):
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("Некорректный ID пользователя")
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = parse_time(registration_date)

    @classmethod
    def create(cls, user_id, username, password):
        """Создать пользователя с новой солью и текущей датой."""
        user = cls(user_id, username, "", "", utc_now())
        user.change_password(password)
        return user

    @property
    def user_id(self):
        return self._user_id

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не должно быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self):
        return self._hashed_password

    @property
    def salt(self):
        return self._salt

    @property
    def registration_date(self):
        return self._registration_date

    def get_user_info(self):
        """Вернуть публичные поля без хеша и соли."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "registration_date": self.registration_date.isoformat(),
        }

    def change_password(self, new_password):
        """Обновить соль и хеш пароля."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._salt = secrets.token_hex(16)
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode()
        ).hexdigest()

    def verify_password(self, password):
        """Сравнить хеш введённого пароля с сохранённым."""
        if not isinstance(password, str):
            return False
        candidate = hashlib.sha256((password + self._salt).encode()).hexdigest()
        return hmac.compare_digest(candidate, self._hashed_password)

    def to_dict(self):
        """Подготовить запись для users.json."""
        return {
            **self.get_user_info(),
            "hashed_password": self._hashed_password,
            "salt": self._salt,
        }


class Wallet:
    """Баланс одной валюты."""

    def __init__(self, currency_code, balance=0.0):
        self.currency_code = get_currency(currency_code).code
        self.balance = balance

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        self._balance = validate_amount(value, allow_zero=True)

    def deposit(self, amount):
        """Увеличить баланс на положительную сумму."""
        self.balance += validate_amount(amount)

    def withdraw(self, amount):
        """Снять валюту, не допуская отрицательного остатка."""
        amount = validate_amount(amount)
        if amount > self.balance:
            raise InsufficientFundsError(self.balance, amount, self.currency_code)
        self.balance -= amount

    def get_balance_info(self):
        """Вернуть строку с текущим балансом."""
        return f"{self.currency_code}: {self.balance:.4f}"


class Portfolio:
    """Все кошельки одного пользователя."""

    def __init__(self, user, wallets=None, rate_provider=None):
        self._user = user
        self._user_id = user.user_id
        self._wallets = dict(wallets or {})
        self._rate_provider = rate_provider

    @property
    def user(self):
        return self._user

    @property
    def wallets(self):
        return self._wallets.copy()

    def add_currency(self, currency_code):
        """Создать кошелёк один раз и вернуть его."""
        get_currency(currency_code)
        if currency_code not in self._wallets:
            self._wallets[currency_code] = Wallet(currency_code)
        return self._wallets[currency_code]

    def get_wallet(self, currency_code):
        """Получить существующий кошелёк."""
        if currency_code not in self._wallets:
            raise ValueError(f"У вас нет кошелька '{currency_code}'")
        return self._wallets[currency_code]

    def get_total_value(self, base_currency="USD"):
        """Суммировать стоимость через переданный поставщик курсов."""
        get_currency(base_currency)
        total = 0.0
        for code, wallet in self._wallets.items():
            if wallet.balance == 0:
                continue
            if code == base_currency:
                rate = 1.0
            elif self._rate_provider:
                rate = self._rate_provider(code, base_currency)["rate"]
            else:
                raise ValueError("Не задан источник курсов")
            total += wallet.balance * rate
        return total

    def to_dict(self):
        """Подготовить портфель для JSON."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: {"balance": wallet.balance}
                for code, wallet in self._wallets.items()
            },
        }
