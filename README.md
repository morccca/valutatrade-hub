# ValutaTrade Hub

Автор: Naumov Pavel. Python 3.12+, uv.

```bash
uv sync
uv run valutatrade
```

Команды: `register`, `login`, `buy`, `sell`, `show-portfolio`,
`get-rate`, `update-rates`, `show-rates`. Справка: `help`, выход: `exit`.

Для фиатных курсов нужна переменная `EXCHANGERATE_API_KEY`.
Для криптовалют: `update-rates --source coingecko`.
Покупка пополняет выбранную валюту, продажа списывает её;
стоимость в USD показывается справочно.
