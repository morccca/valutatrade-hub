# ValutaTrade Hub

Консольный симулятор валютного портфеля. Требуется Python 3.12+.

## Запуск

```bash
python3 -m pip install "prettytable>=3.12,<4" "requests>=2.32,<3"
python3 main.py
```

## Ввод и вывод

Введите команды:

```text
register --username student --password example1234
login --username student --password example1234
buy --currency USD --amount 100
show-portfolio
```

Результат просмотра портфеля:

```text
Портфель пользователя 'student' (база: USD):
+--------+----------+----------------+
| Валюта |  Баланс  | Стоимость, USD |
+--------+----------+----------------+
|  USD   | 100.0000 |     100.00     |
+--------+----------+----------------+
ИТОГО: 100.00 USD
```

Для криптовалют сначала загрузите курсы:

```text
update-rates --source coingecko
buy --currency BTC --amount 0.05
sell --currency BTC --amount 0.01
get-rate --from USD --to BTC
show-rates --top 2
help
exit
```

Покупка пополняет выбранную валюту, продажа списывает её.
Стоимость в USD справочная; автоматического обмена с USD-кошельком нет.

## Курсы и файлы

Для фиатных курсов задайте `EXCHANGERATE_API_KEY` в окружении перед запуском.
Необязательный ключ CoinGecko: `COINGECKO_DEMO_API_KEY`.
`update-rates` обновляет оба источника, `show-rates` показывает курсы.
Ключи не нужно записывать в код.

`main.py` — запуск. В `valutatrade_hub/`: `core/` — модели и операции,
`commands.py` — команды, `infra/` — настройки и JSON, `parser_service/` — API.
Данные — в `data/`, логи — в `logs/`.
`rates.json` содержит кэш, `exchange_rates.json` — историю курсов.
TTL — 300 секунд; после истечения выполните `update-rates`.
Изменить TTL можно через `VALUTATRADE_RATES_TTL_SECONDS`.

Время регистрации, обновления курсов и записей в логах — UTC+3.
