"""Актуальный снимок и история измерений курсов."""

from valutatrade_hub.core.utils import parse_time, utc_now, validate_amount
from valutatrade_hub.infra.database import DatabaseManager


class RatesStorage:
    """Обновлять только успешно полученные пары."""

    def __init__(self, database=None):
        self.database = database or DatabaseManager()

    def save(self, updates):
        """Сохранить историю без повторов и последний снимок."""
        snapshot = self.database.read("rates.json", {"pairs": {}})
        history = self.database.read("exchange_rates.json", [])
        known = {row["id"] for row in history}
        count = 0
        for pair, item in updates.items():
            validate_amount(item["rate"])
            timestamp = parse_time(item["updated_at"])
            previous = snapshot["pairs"].get(pair)
            if previous and timestamp <= parse_time(previous["updated_at"]):
                continue
            from_code, to_code = pair.split("_")
            identifier = pair + "_" + item["updated_at"]
            if identifier not in known:
                history.append(
                    {
                        "id": identifier,
                        "from_currency": from_code,
                        "to_currency": to_code,
                        "rate": item["rate"],
                        "timestamp": item["updated_at"],
                        "source": item["source"],
                    }
                )
                known.add(identifier)
            snapshot["pairs"][pair] = item
            count += 1
        if count:
            snapshot["last_refresh"] = utc_now()
            self.database.write("exchange_rates.json", history)
            self.database.write("rates.json", snapshot)
        return count
