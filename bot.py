import os
import json
import requests

from kleinanzeigen import (
    get_search_listings,
    filter_listing,
)


TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"

SEEN_FILE = "seen.json"


def load_seen():

    if not os.path.exists(SEEN_FILE):
        return set()

    try:

        with open(
            SEEN_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return set(data)

    except Exception:

        return set()


def save_seen(seen):

    with open(
        SEEN_FILE,
        "w",
        encoding="utf-8"
    ) as file:

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

    print(
        "Telegram:",
        response.status_code
    )

    if response.status_code != 200:
        print(response.text)

    return response.status_code == 200


def format_distance(
    distance,
    approximate=False
):

    if distance is None:
        return "—"

    if approximate:
        return f"~{distance:.1f} km"

    return f"{distance:.1f} km"


def format_listing(listing):

    # =========================================
    # Warmmiete
    # =========================================

    warm = listing.get(
        "warm_rent"
    )

    if warm is None:

        warm_text = (
            "Warmmiete: nicht angegeben"
        )

    else:

        warm_text = (
            f"Warmmiete: €{warm:.0f}"
        )


    # =========================================
    # Anmeldung
    # =========================================

    anmeldung = listing.get(
        "anmeldung"
    )

    if anmeldung == "YES":

        anmeldung_text = (
            "Anmeldung: ✅"
        )

    elif anmeldung == "NO":

        anmeldung_text = (
            "Anmeldung: ❌"
        )

    else:

        anmeldung_text = (
            "Anmeldung: ⚠️ "
            "nicht angegeben"
        )


    # =========================================
    # Disponible desde
    # =========================================

    available_from = listing.get(
        "available_from"
    )

    if available_from:

        available_text = (
            f"📅 Disponible desde: "
            f"{available_from}"
        )

    else:

        available_text = (
            "📅 Disponible desde: "
            "no indicado"
        )


    # =========================================
    # Dirección / PLZ
    # =========================================

    address = listing.get(
        "address"
    )

    postcode = listing.get(
        "postcode"
    )

    location_type = listing.get(
        "location_type"
    )


    if (
        address
        and location_type == "EXACT"
    ):

        address_text = (
            f"📍 Adresse:\n"
            f"{address}"
        )

    elif (
        postcode
        and location_type == "PLZ"
    ):

        address_text = (
            "📍 Adresse: "
            "nicht veröffentlicht\n"
            f"📌 PLZ aproximado: "
            f"{postcode}"
        )

    else:

        address_text = (
            "📍 Adresse: "
            "nicht veröffentlicht"
        )


    # =========================================
    # Distancias
    # =========================================

    approximate = (
        location_type == "PLZ"
    )

    hbf = format_distance(
        listing.get(
            "hbf_distance"
        ),
        approximate
    )

    fh = format_distance(
        listing.get(
            "fh_distance"
        ),
        approximate
    )


    # =========================================
    # Telegram message
    # =========================================

    return (
        f"{listing['title']}\n\n"

        f"{warm_text}\n"
        f"{anmeldung_text}\n"
        f"{available_text}\n\n"

        f"{address_text}\n\n"

        f"🚉 Potsdam Hbf: {hbf}\n"
        f"🎓 FH Potsdam: {fh}\n\n"

        f"🔗 {listing['url']}"
    )


def main():

    print(
        "Buscando nuevos departamentos..."
    )

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

            new_matches.append(
                result
            )


    print()

    print(
        "NEW MATCHES:",
        len(new_matches)
    )


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


    seen.update(
        successfully_sent
    )

    save_seen(
        seen
    )

    print(
        "Saved seen listings:",
        len(seen)
    )


if __name__ == "__main__":
    main()
