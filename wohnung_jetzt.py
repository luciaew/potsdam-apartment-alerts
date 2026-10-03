import requests
from bs4 import BeautifulSoup
import re


SEARCH_URL = "https://www.wohnung-jetzt.de/suche/potsdam/mieten/wohnung/"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    )
}


def get_search_listings():
    print("Checking Wohnung-jetzt...")

    try:
        response = requests.get(
            SEARCH_URL,
            headers=HEADERS,
            timeout=30
        )

        print("Wohnung-jetzt status:", response.status_code)

        if response.status_code != 200:
            print("Wohnung-jetzt could not be accessed.")
            return []

    except Exception as e:
        print("Wohnung-jetzt error:", e)
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    listings = []
    seen_urls = set()

    # Wohnung-jetzt currently uses /exposee/ URLs for property listings.
    for link in soup.find_all("a", href=True):

        href = link.get("href", "").strip()

        if "/exposee/" not in href:
            continue

        if href.startswith("/"):
            url = "https://www.wohnung-jetzt.de" + href
        elif href.startswith("http"):
            url = href
        else:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        title = link.get_text(" ", strip=True)

        if not title:
            title = "Wohnung in Potsdam"

        # The search result card itself contains useful information:
        # title, postcode, rooms, area and cold rent.
        parent = link.parent

        card_text = ""
        if parent:
            card_text = parent.get_text(" ", strip=True)

        # Sometimes the useful text is one or more levels higher.
        if len(card_text) < len(title) + 20:
            grandparent = parent.parent if parent else None
            if grandparent:
                card_text = grandparent.get_text(" ", strip=True)

        listings.append({
            "url": url,
            "title": title,
            "description": card_text,
            "source": "Wohnung-jetzt"
        })

    print("Wohnung-jetzt raw listings:", len(listings))

    return listings


def filter_listing(listing):
    text = (
        listing.get("title", "") + " " +
        listing.get("description", "")
    ).lower()

    # ---------------------------------------------------------
    # POTSDAM ONLY
    # ---------------------------------------------------------

    potsdam_terms = [
        "potsdam",
        "14467",
        "14469",
        "14471",
        "14473",
        "14476",
        "14478",
        "14480",
        "14482"
    ]

    if not any(term in text for term in potsdam_terms):
        return False

    # ---------------------------------------------------------
    # EXCLUDE WG / SHARED ROOMS
    # ---------------------------------------------------------

    if re.search(r"\bwg\b", text):
        return False

    wg_terms = [
        "wg-zimmer",
        "wohngemeinschaft",
        "mitbewohner",
        "mitbewohnerin",
        "mitbewohner gesucht",
        "shared room",
        "shared flat",
        "gemeinschaftszimmer"
    ]

    for term in wg_terms:
        if term in text:
            return False

    # ---------------------------------------------------------
    # EXCLUDE WANTED / EXCHANGE LISTINGS
    # ---------------------------------------------------------

    excluded_terms = [
        "tauschangebot",
        "wohnungstausch",
        "tauschwohnung",
        "gesuch",
        "wohnung gesucht",
        "mietgesuch"
    ]

    for term in excluded_terms:
        if term in text:
            return False

    # ---------------------------------------------------------
    # EXCLUDE MORE THAN 2 ROOMS
    # ---------------------------------------------------------

    room_matches = re.findall(
        r"(\d+(?:[.,]\d+)?)\s*(?:-|–)?\s*zimmer",
        text
    )

    for match in room_matches:
        try:
            rooms = float(match.replace(",", "."))

            if rooms > 2:
                return False

        except ValueError:
            pass

    # ---------------------------------------------------------
    # WARM RENT
    # ---------------------------------------------------------
    #
    # IMPORTANT:
    # If Warmmiete is unknown, KEEP the listing.
    # If Warmmiete is explicitly > €900, exclude it.
    #

    warm_patterns = [
        r"warmmiete\s*:?\s*(\d[\d.]*)\s*€?",
        r"warm\s*:?\s*(\d[\d.]*)\s*€",
        r"\bwm\s*:?\s*(\d[\d.]*)\s*€"
    ]

    for pattern in warm_patterns:

        matches = re.findall(pattern, text)

        for match in matches:

            try:
                warm = float(match.replace(".", "").replace(",", "."))

                if warm > 900:
                    return False

            except ValueError:
                pass

    # ---------------------------------------------------------
    # EXPLICIT "NO ANMELDUNG"
    # ---------------------------------------------------------

    anmeldung_no = [
        "anmeldung nicht möglich",
        "anmeldung nicht moglich",
        "keine anmeldung möglich",
        "keine anmeldung moglich",
        "no registration possible"
    ]

    for term in anmeldung_no:
        if term in text:
            return False

    return True
