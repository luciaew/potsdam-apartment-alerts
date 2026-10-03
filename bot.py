import os
import re
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"


def send_message(chat_id, message):
    requests.post(
        f"{TELEGRAM_URL}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": False,
        },
    )


def is_valid_apartment(title, description="", price=None):
    text = f"{title} {description}".lower()

    # Must be Potsdam
    if "potsdam" not in text:
        return False

    # Exclude obvious WG/shared-room listings
    excluded = [
        "wg-zimmer",
        "wg zimmer",
        "wohngemeinschaft",
        "mitbewohner",
        "mitbewohnerin",
        "mitbewohner gesucht",
        "shared room",
        "shared apartment",
        "gemeinschaftszimmer",
        "zimmer in wg",
        "room in shared",
    ]

    for word in excluded:
        if word in text:
            return False

    # Price filter
    if price is not None and price > 900:
        return False

    # We want a whole apartment
    apartment_terms = [
        "wohnung",
        "apartment",
        "studio",
        "1-zimmer-wohnung",
        "1 zimmer wohnung",
        "2-zimmer-wohnung",
        "2 zimmer wohnung",
    ]

    if not any(term in text for term in apartment_terms):
        return False

    return True


def format_alert(title, price, url):
    return f"""🏠 NEUE WOHNUNG IN POTSDAM

{title}

💶 {price} € warm

🔗 {url}
"""
