# ValutaTrade Hub

Автор: Naumov Pavel. Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/).

Консольный симулятор валютного портфеля с регистрацией, покупкой,
продажей и получением курсов CoinGecko и ExchangeRate-API.

## Запуск

В каталоге проекта:

```bash
uv sync
uv run valutatrade
```

Для фиатных курсов перед запуском задайте ключ ExchangeRate-API:

```bash
export EXCHANGERATE_API_KEY="ваш_ключ"
```

Необязательный ключ CoinGecko задаётся через `COINGECKO_DEMO_API_KEY`.
Ключи хранятся в переменных окружения, в файлы проекта их добавлять не нужно.

## Команды

```text
update-rates
register --username student --password example1234
login --username student --password example1234
buy --currency BTC --amount 0.05
sell --currency BTC --amount 0.01
show-portfolio
show-portfolio --base EUR
get-rate --from USD --to BTC
show-rates --top 2
show-rates --currency EUR
help
exit
```

`amount` — количество валюты. Покупка увеличивает её баланс, продажа
уменьшает. Стоимость в USD справочная: USD-кошелёк автоматически не меняется.

## Структура и курсы

В `valutatrade_hub/`: `core/` — модели и операции, `cli/` — команды,
`infra/` — настройки и хранилище, `parser_service/` — загрузка курсов.
Данные находятся в `data/`, журналы операций — в `logs/`.

Parser Service запускается командой `update-rates` внутри приложения.
Только криптовалюты: `update-rates --source coingecko`;
только фиатные валюты: `update-rates --source exchangerate`.
Для обновления по расписанию в отдельном терминале:

```bash
uv run python -m valutatrade_hub.parser_service.scheduler --interval 300
```

`data/rates.json` — кэш курсов, `data/exchange_rates.json` — история.
TTL по умолчанию — 300 секунд. Просроченные курсы нужно обновить через
`update-rates`. TTL и пути задаются в `[tool.valutatrade]` файла
`pyproject.toml`, параметры API — в `parser_service/config.py`.

Проверка стиля: `uv run ruff check .`. Сборка пакета: `uv build`.
