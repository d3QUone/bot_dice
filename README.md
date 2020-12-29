# Telegram Dice Bot

Small telegram bot to roll dices with leader board.


## Install instructions

We use Python 3.8.

1. Install [poetry](https://github.com/python-poetry/poetry) and project dependencies:
```bash
python3 -m pip install poetry==1.1.4
poetry env use 3.8
poetry install
```

2. Run bot locally:
```bash
poetry run python src/bot.py
```


## CI config

You need the following `secrets` in your repository settings:

- `TG_TOKEN` -- bot token from BotFather.
- `SERVER_HOSTNAME` -- your server host name or IP address.
- `SERVER_USERNAME` -- your server user name.
- `ID_RSA_PRIVATE` -- your `~/.ssh/id_rsa` file contents to access server under provided user name.
