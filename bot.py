import json
import os
import requests

from kleinanzeigen import get_search_listings as get_kleinanzeigen_listings
from kleinanzeigen import filter_listing as filter_kleinanzeigen

from immoscout import get_search_listings as get_immoscout_listings

from wohnung_jetzt import (
    get_search_listings as get_wohnung_jetzt_listings,
    filter_listing as filter_wohnung_jetzt
)


SEEN_FILE = "seen.json"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def load_seen():
    try:
        with open(
            SEEN_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return set(json.load(file))

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


def send_telegram(message):

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    print(
        "Telegram status:",
        response.status_code
    )

    if response.status_code != 200:
        print(response.text)
        return False

    return True


def format_distance(value):

    if value is None:
        return "nicht verfügbar"

    return f"{value:.1f} km"


# ==========================================================
# IMMOSCOUT24
# ==========================================================

def format_immoscout_listing(listing):

    message = "🏠 NEUE WOHNUNG – ImmoScout24\n\n"

    message += (
        f"📌 {listing.get('title', 'Wohnung in Potsdam')}\n"
    )

    warm_rent = listing.get("warm_rent")

    if warm_rent is not None:
        message += (
            f"💶 Warmmiete: {warm_rent:.0f} €\n"
        )
    else:
        message += (
            "💶 Warmmiete: nicht angegeben\n"
        )

    area = listing.get("area")

    if area is not None:
        message += (
            f"📐 Wohnfläche: {area:g} m²\n"
        )
    else:
        message += (
            "📐 Wohnfläche: nicht angegeben\n"
        )

    rooms = listing.get("rooms")

    if rooms is not None:
        message += (
            f"🛏️ Zimmer: {rooms:g}\n"
        )
    else:
        message += (
            "🛏️ Zimmer: nicht angegeben\n"
        )

    available_from = listing.get(
        "available_from"
    )

    if available_from:
        message += (
            f"📅 Disponible desde: "
            f"{available_from}\n"
        )
    else:
        message += (
            "📅 Disponible desde: "
            "no indicado\n"
        )

    address = listing.get("address")

    if address:
        message += (
            f"📍 {address}\n"
        )

    elif listing.get("postcode"):
        message += (
            f"📍 ~{listing['postcode']} Potsdam\n"
        )

    else:
        message += (
            "📍 Dirección no indicada\n"
        )

    hbf = listing.get("hbf_distance")
    fh = listing.get("fh_distance")

    message += (
        f"🚉 Potsdam Hbf: "
        f"{format_distance(hbf)}\n"
    )

    message += (
        f"🎓 FH Potsdam: "
        f"{format_distance(fh)}\n"
    )

    message += "\n"

    message += (
        f"🔗 {listing['url']}"
    )

    return message


# ==========================================================
# KLEINANZEIGEN
# ==========================================================

def format_kleinanzeigen_listing(listing):

    message = "🏠 NUEVA VIVIENDA – Kleinanzeigen\n\n"

    message += (
        f"📌 {listing.get('title', 'Wohnung in Potsdam')}\n"
    )

    warm_rent = listing.get("warm_rent")

    if warm_rent is not None:
        message += (
            f"💶 Warmmiete: {warm_rent:.0f} €\n"
        )
    else:
        message += (
            "💶 Warmmiete: no indicada\n"
        )

    rooms = listing.get("rooms")

    if rooms is not None:
        message += (
            f"🛏️ Zimmer: {rooms:g}\n"
        )

    available_from = listing.get(
        "available_from"
    )

    if available_from:
        message += (
            f"📅 Disponible desde: "
            f"{available_from}\n"
        )

    address = listing.get("address")

    if address:
        message += (
            f"📍 {address}\n"
        )

    elif listing.get("postcode"):
        message += (
            f"📍 ~{listing['postcode']} Potsdam\n"
        )

    else:
        message += (
            "📍 Dirección no indicada\n"
        )

    hbf = listing.get("hbf_distance")
    fh = listing.get("fh_distance")

    message += (
        f"🚉 Potsdam Hbf: "
        f"{format_distance(hbf)}\n"
    )

    message += (
        f"🎓 FH Potsdam: "
        f"{format_distance(fh)}\n"
    )

    message += "\n"

    message += (
        f"🔗 {listing['url']}"
    )

    return message


# ==========================================================
# WOHNUNG-JETZT
# ==========================================================

def format_wohnung_jetzt_listing(listing):

    message = "🏠 NUEVA VIVIENDA – Wohnung-jetzt\n\n"

    message += (
        f"📌 {listing.get('title', 'Wohnung in Potsdam')}\n"
    )

    description = listing.get(
        "description",
        ""
    )

    import re

    # ----------------------------------------------
    # Wohnfläche / m²
    # ----------------------------------------------

    area_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*m²",
        description,
        re.IGNORECASE
    )

    if area_match:

        area = area_match.group(1)

        message += (
            f"📐 Wohnfläche: {area} m²\n"
        )

    else:

        message += (
            "📐 Wohnfläche: nicht angegeben\n"
        )

    # ----------------------------------------------
    # Zimmer
    # ----------------------------------------------

    room_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(?:-|–)?\s*Zimmer",
        description,
        re.IGNORECASE
    )

    if room_match:

        rooms = room_match.group(1)

        message += (
            f"🛏️ Zimmer: {rooms}\n"
        )

    else:

        message += (
            "🛏️ Zimmer: nicht angegeben\n"
        )

    # ----------------------------------------------
    # Warmmiete
    # ----------------------------------------------

    warm_match = re.search(
        r"(?:Warmmiete|Warm|WM)\s*:?\s*"
        r"(\d[\d.]*)\s*€",
        description,
        re.IGNORECASE
    )

    if warm_match:

        warm = warm_match.group(1)

        message += (
            f"💶 Warmmiete: {warm} €\n"
        )

    else:

        message += (
            "💶 Warmmiete: nicht angegeben\n"
        )

    # ----------------------------------------------
    # Adresse / PLZ
    # ----------------------------------------------

    postcode_match = re.search(
        r"\b(144(?:67|69|71|73|76|78|80|82))\b",
        description
    )

    if postcode_match:

        postcode = postcode_match.group(1)

        message += (
            f"📍 ~{postcode} Potsdam\n"
        )

    else:

        message += (
            "📍 Dirección no indicada\n"
        )

    # ----------------------------------------------
    # Distancias
    # ----------------------------------------------

    message += (
        "🚉 Potsdam Hbf: nicht verfügbar\n"
    )

    message += (
        "🎓 FH Potsdam: nicht verfügbar\n"
    )

    message += "\n"

    message += (
        f"🔗 {listing['url']}"
    )

    return message


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("================================")
    print("POTSDAM APARTMENT BOT")
    print("================================")

    seen = load_seen()


    # ==================================================
    # ONE-TIME NOVEMBER RESET
    #
    # Re-check old Wohnung-jetzt listings once.
    # Kleinanzeigen is NOT touched.
    # ==================================================

    reset_marker = (
        "__wohnung_jetzt_november_reset_done__"
    )

    if reset_marker not in seen:

        print(
            "Resetting old Wohnung-jetzt listings "
            "for November filter..."
        )

        seen = {
            item
            for item in seen
            if not item.startswith(
                "wohnung-jetzt:"
            )
        }

        seen.add(reset_marker)


    # ==================================================
    # KLEINANZEIGEN
    # ==================================================

    print()
    print("Checking Kleinanzeigen...")

    kleinanzeigen_listings = (
        get_kleinanzeigen_listings()
    )

    print(
        "Kleinanzeigen listings:",
        len(kleinanzeigen_listings)
    )

    for listing in kleinanzeigen_listings:

        url = listing["url"]

        seen_key = (
            f"kleinanzeigen:{url}"
        )

        if seen_key in seen:
            continue

        result, reason = (
            filter_kleinanzeigen(listing)
        )

        print(
            "Kleinanzeigen:",
            listing["title"],
            "->",
            reason
        )

        if result:

            success = send_telegram(
                format_kleinanzeigen_listing(
                    result
                )
            )

            if success:
                seen.add(seen_key)

        else:

            seen.add(seen_key)


    # ==================================================
    # IMMOSCOUT24
    # ==================================================

    print()
    print("Checking ImmoScout24...")

    immoscout_listings = (
        get_immoscout_listings()
    )

    print(
        "ImmoScout24 listings:",
        len(immoscout_listings)
    )

    for listing in immoscout_listings:

        url = listing["url"]

        seen_key = (
            f"immoscout24:{url}"
        )

        if seen_key in seen:
            continue

        print(
            "ImmoScout24:",
            listing.get("title")
        )

        success = send_telegram(
            format_immoscout_listing(
                listing
            )
        )

        if success:
            seen.add(seen_key)


    # ==================================================
    # WOHNUNG-JETZT
    # ==================================================

    print()
    print("Checking Wohnung-jetzt...")

    wohnung_jetzt_listings = (
        get_wohnung_jetzt_listings()
    )

    print(
        "Wohnung-jetzt listings:",
        len(wohnung_jetzt_listings)
    )

    for listing in wohnung_jetzt_listings:

        url = listing["url"]

        seen_key = (
            f"wohnung-jetzt:{url}"
        )

        if seen_key in seen:
            continue

        result = filter_wohnung_jetzt(
            listing
        )

        print(
            "Wohnung-jetzt:",
            listing.get("title"),
            "->",
            result
        )

        if result:

            success = send_telegram(
                format_wohnung_jetzt_listing(
                    listing
                )
            )

            if success:
                seen.add(seen_key)

        else:

            seen.add(seen_key)


    # ==================================================
    # SAVE
    # ==================================================

    save_seen(seen)

    print()
    print("Done.")

    print(
        "Total seen listings:",
        len(seen)
    )


if __name__ == "__main__":
    main()
