import os
import json
import requests

from kleinanzeigen import get_search_listings, filter_listing


TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"

SEEN_FILE = "seen.json"


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()

    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return set(data)

    except Exception:
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as file:
        json.dump(
            sorted(seen),
            file,
            ensure_ascii=False,
            indent=2
        )


def send_message(message):
    response = requests.post(
        f"{TELEGRAM_URL}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    print("Telegram:", response.status_code)

    if response.status_code != 200:
        print(response.text)

    return response.status_code == 200


def format_listing(listing):
    warm = listing["warm_rent"]

    if warm is None:
        warm_text = "Warmmiete: nicht angegeben"
    else:
        warm_text = f"Warmmiete: €{warm:.0f}"

    anmeldung = listing["anmeldung"]

    if anmeldung == "YES":
        anmeldung_text = "Anmeldung: ✅"
    elif anmeldung == "NO":
        anmeldung_text = "Anmeldung: ❌"
    else:
        anmeldung_text = "Anmeldung: ⚠️ nicht angegeben"

    return (
        "🏠 NUEVO DEPARTAMENTO EN POTSDAM\n\n"
        f"{listing['title']}\n\n"
        f"{warm_text}\n"
        f"{anmeldung_text}\n\n"
        f"{listing['url']}"
    )


def main():

    print("Buscando nuevos departamentos...")

    listings = get_search_listings()

    print(
        "Listings found:",
        len(listings)
    )

    seen = load_seen()

    new_matches = []

    for listing in listings:

        url = listing["url"]

        if url in seen:
            continue

        result, reason = filter_listing(
            listing
        )

        print(
            listing["title"],
            "->",
            reason
        )

        if result:
            new_matches.append(result)

    print()
    print(
        "NEW MATCHES:",
        len(new_matches)
    )

    # Send only new listings
    successfully_sent = []

    for listing in new_matches:

        message = format_listing(
            listing
        )

        success = send_message(
            message
        )

        if success:
            successfully_sent.append(
                listing["url"]
            )

    # Save only listings that were
    # successfully sent to Telegram
    seen.update(successfully_sent)

    save_seen(seen)

    print(
        "Saved seen listings:",
        len(seen)
    )


if __name__ == "__main__":
    main()
