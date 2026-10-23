"""Логирование сделок без паролей и API-ключей."""

import json
import logging
from functools import wraps

from valutatrade_hub.core.utils import utc_now


def log_action(action, verbose=False):
    """Записать результат операции и сохранить поведение исключений."""

    def decorate(function):
        @wraps(function)
        def wrapper(self, currency_code, amount):
            record = {
                "timestamp": utc_now(),
                "action": action,
                "user_id": self.user.user_id if self.user else None,
                "currency_code": currency_code,
                "amount": amount,
                "base": "USD",
            }
            try:
                result = function(self, currency_code, amount)
            except Exception as error:
                record.update(
                    result="ERROR",
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
                logging.getLogger("valutatrade.actions").info(
                    json.dumps(record, ensure_ascii=False)
                )
                raise
            record.update(result="OK", rate=result["rate"])
            if verbose:
                record.update(before=result["before"], after=result["after"])
            logging.getLogger("valutatrade.actions").info(
                json.dumps(record, ensure_ascii=False)
            )
            return result

        return wrapper

    return decorate
