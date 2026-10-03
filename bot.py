import os
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"


def send_message(message):
    response = requests.post(
        f"{TELEGRAM_URL}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message,
        },
    )

    print(response.text)


send_message(
    "🤖 Potsdam Apartment Alerts\n\n"
    "Bot conectado correctamente.\n\n"
    "Próximo paso: conectar las páginas de apartamentos."
)
