"""Последовательное обновление курсов с частичным успехом."""

import logging

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.utils import current_time
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Объединение ответов API без потери старых данных при сбое."""

    def __init__(self, clients=None, storage=None):
        self.clients = (
            clients
            if clients is not None
            else [CoinGeckoClient(), ExchangeRateApiClient()]
        )
        self.storage = storage or RatesStorage()

    def run_update(self):
        """Опросить все источники, сохранить успехи, вернуть ошибки отдельно."""
        logger = logging.getLogger("valutatrade.parser")
        logger.info("%s Начало обновления", current_time())
        updates = {}
        errors = []
        for client in self.clients:
            try:
                rates = client.fetch_rates()
                timestamp = current_time()
                for pair, rate in rates.items():
                    updates[pair] = {
                        "rate": rate,
                        "updated_at": timestamp,
                        "source": client.source,
                    }
                logger.info("%s %s: %s курсов", timestamp, client.source, len(rates))
            except ApiRequestError as error:
                errors.append(str(error))
                logger.warning("%s %s", current_time(), error)
        if not updates:
            raise ApiRequestError("; ".join(errors) or "Источники не вернули курсы")
        count = self.storage.save(updates)
        logger.info("%s Завершено: %s курсов", current_time(), count)
        return {"updated": count, "errors": errors}
