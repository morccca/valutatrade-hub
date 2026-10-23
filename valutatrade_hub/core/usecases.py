"""Операции приложения, не зависящие от ввода и печати в консоли."""

from datetime import datetime, timezone

from valutatrade_hub.core.currencies import CURRENCIES, CryptoCurrency, get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import parse_time, utc_now, validate_amount
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


class TradingService:
    """Учебный учёт валют: покупка пополняет валюту, продажа списывает её."""

    def __init__(self, database=None):
        self.database = database or DatabaseManager()
        self.user = None

    def register(self, username, password):
        """Добавить пользователя и пустой портфель."""
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не должно быть пустым")
        username = username.strip()
        users = self.database.read("users.json", [])
        if any(item["username"] == username for item in users):
            raise ValueError(f"Имя пользователя '{username}' уже занято")
        identifier = max((item["user_id"] for item in users), default=0) + 1
        user = User.create(identifier, username, password)
        portfolios = self.database.read("portfolios.json", [])
        portfolios.append(Portfolio(user).to_dict())
        self.database.write("portfolios.json", portfolios)
        self.database.write("users.json", users + [user.to_dict()])
        return user.get_user_info()

    def login(self, username, password):
        """Проверить пароль и сохранить пользователя текущей сессии."""
        self.user = None
        for item in self.database.read("users.json", []):
            if item["username"] == username:
                user = User(**item)
                if not user.verify_password(password):
                    raise ValueError("Неверный пароль")
                self.user = user
                return user.get_user_info()
        raise ValueError(f"Пользователь '{username}' не найден")

    def require_login(self):
        """Ограничить доступ к портфелю текущей сессией."""
        if self.user is None:
            raise ValueError("Сначала выполните login")

    def load_portfolio(self):
        """Восстановить кошельки только текущего пользователя."""
        self.require_login()
        for item in self.database.read("portfolios.json", []):
            if item["user_id"] == self.user.user_id:
                wallets = {
                    code: Wallet(code, data["balance"])
                    for code, data in item["wallets"].items()
                }
                return Portfolio(self.user, wallets, self.get_rate)
        return Portfolio(self.user, rate_provider=self.get_rate)

    def save_portfolio(self, portfolio):
        """Заменить портфель текущего пользователя, сохранив остальные."""
        portfolios = self.database.read("portfolios.json", [])
        portfolios = [
            item for item in portfolios if item["user_id"] != self.user.user_id
        ]
        portfolios.append(portfolio.to_dict())
        self.database.write("portfolios.json", portfolios)

    def get_rate(self, from_code, to_code):
        """Рассчитать прямой или кросс-курс через USD и проверить TTL."""
        get_currency(from_code)
        get_currency(to_code)
        if from_code == to_code:
            return {"rate": 1.0, "updated_at": utc_now()}
        pairs = self.database.read("rates.json", {"pairs": {}})["pairs"]
        rates = {}
        timestamps = []
        now = datetime.now(timezone.utc)
        ttl = SettingsLoader().get("rates_ttl_seconds")
        for code in (from_code, to_code):
            if code == "USD":
                rates[code] = 1.0
                continue
            item = pairs.get(f"{code}_USD")
            if item is None:
                raise ApiRequestError(f"Нет курса {code}→USD. Выполните update-rates")
            try:
                timestamp = parse_time(item["updated_at"])
                rates[code] = validate_amount(item["rate"])
            except (ValueError, TypeError, KeyError):
                raise ApiRequestError("Повреждён кэш курсов. Выполните update-rates")
            age = (now - timestamp).total_seconds()
            if age < -60 or age > ttl:
                raise ApiRequestError(f"Курс {code} устарел. Выполните update-rates")
            timestamps.append(timestamp)
        return {
            "rate": rates[from_code] / rates[to_code],
            "updated_at": min(timestamps).isoformat(),
        }

    def show_portfolio(self, base="USD"):
        """Получить строки портфеля и сумму в базовой валюте."""
        portfolio = self.load_portfolio()
        get_currency(base)
        rows = []
        for code, wallet in sorted(portfolio.wallets.items()):
            value = 0.0
            if wallet.balance:
                value = wallet.balance * self.get_rate(code, base)["rate"]
            rows.append((code, wallet.balance, value))
        return {
            "username": self.user.username,
            "rows": rows,
            "total": portfolio.get_total_value(base),
            "base": base,
        }

    def show_rates(self, currency=None, top=None, base="USD"):
        """Подготовить отфильтрованные курсы для вывода в таблицу."""
        get_currency(base)
        if currency:
            get_currency(currency)
        if top is not None and top <= 0:
            raise ValueError("--top должен быть положительным")
        pairs = self.database.read("rates.json", {"pairs": {}})["pairs"]
        if not pairs:
            raise ValueError("Локальный кеш курсов пуст. Выполните update-rates")
        codes = (
            [currency] if currency else sorted({pair.split("_")[0] for pair in pairs})
        )
        rows = []
        for code in codes:
            if top and not isinstance(CURRENCIES.get(code), CryptoCurrency):
                continue
            item = self.get_rate(code, base)
            rows.append((code, item["rate"], item["updated_at"]))
        if top:
            rows = sorted(rows, key=lambda row: row[1], reverse=True)[:top]
        return rows

    @log_action("BUY", verbose=True)
    def buy(self, currency_code, amount):
        """Добавить виртуальную валюту и вывести её оценочную стоимость."""
        self.require_login()
        amount = validate_amount(amount)
        rate = self.get_rate(currency_code, "USD")["rate"]
        portfolio = self.load_portfolio()
        wallet = portfolio.add_currency(currency_code)
        before = wallet.balance
        wallet.deposit(amount)
        self.save_portfolio(portfolio)
        return {
            "currency": currency_code,
            "amount": amount,
            "rate": rate,
            "before": before,
            "after": wallet.balance,
            "value": amount * rate,
        }

    @log_action("SELL", verbose=True)
    def sell(self, currency_code, amount):
        """Списать виртуальную валюту после проверки остатка."""
        self.require_login()
        amount = validate_amount(amount)
        get_currency(currency_code)
        portfolio = self.load_portfolio()
        wallet = portfolio.get_wallet(currency_code)
        before = wallet.balance
        wallet.withdraw(amount)
        rate = self.get_rate(currency_code, "USD")["rate"]
        self.save_portfolio(portfolio)
        return {
            "currency": currency_code,
            "amount": amount,
            "rate": rate,
            "before": before,
            "after": wallet.balance,
            "value": amount * rate,
        }
