import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# ============================================================
# CONFIGURATION
# ============================================================

SEARCH_URL = (
    "https://www.kleinanzeigen.de/"
    "s-wohnung-mieten/potsdam/wohnung-mieten/k0c203l7958"
)

BASE_URL = "https://www.kleinanzeigen.de"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0 Safari/537.36"
    )
}

MAX_WARM_RENT = 900


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


# ============================================================
# WG FILTER
# ============================================================

def is_wg(text):
    text_lower = text.lower()

    excluded_phrases = [
        "wg-zimmer",
        "wg zimmer",
        "wohngemeinschaft",
        "zimmer in wg",
        "zimmer frei in wg",
        "zimmer in einer wg",
        "mitbewohner gesucht",
        "mitbewohnerin gesucht",
        "wg gesucht",
        "wg-wohnung",
    ]

    return any(
        phrase in text_lower
        for phrase in excluded_phrases
    )


# ============================================================
# TAUSCH / GESUCH FILTER
# ============================================================

def is_exchange_or_wanted(text):
    text_lower = text.lower()

    excluded_phrases = [
        "tauschangebot",
        "tauschwohnung",
        "wohnungstausch",
        "wohnungsswap",
        "swapwohnung",
        "gesuch",
        "wohnung gesucht",
        "suche wohnung",
        "suche eine wohnung",
        "nachmieter gesucht",
    ]

    return any(
        phrase in text_lower
        for phrase in excluded_phrases
    )


# ============================================================
# EXPLICIT ROOM COUNT
# ============================================================

def explicit_room_count(text):
    """
    Returns the room count if the title explicitly contains it.

    Examples:
    1-Zimmer -> 1
    2-Zimmer -> 2
    3-Zimmer -> 3
    2-Zi. -> 2

    Returns None if the number of rooms is not clear.
    """

    text_lower = text.lower()

    patterns = [
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*zimmer\b",
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*zi\.",
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*z\.",
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*zkb\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text_lower
        )

        if match:

            value = match.group(1)

            value = value.replace(",", ".")

            try:
                return float(value)
            except ValueError:
                pass

    return None


# ============================================================
# WARM RENT
# ============================================================

def extract_warm_rent(text):

    patterns = [
        r"warmmiete\s*:?\s*(\d[\d\.\s]*)\s*€",
        r"warmmiete\s*:?\s*€\s*(\d[\d\.\s]*)",

        r"gesamtmiete\s*:?\s*(\d[\d\.\s]*)\s*€",
        r"gesamtmiete\s*:?\s*€\s*(\d[\d\.\s]*)",

        r"warm\s*:?\s*(\d[\d\.\s]*)\s*€",
        r"warm\s*:?\s*€\s*(\d[\d\.\s]*)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        value = match.group(1)

        value = (
            value
            .replace(".", "")
            .replace(" ", "")
            .replace(",", ".")
        )

        try:
            return float(value)
        except ValueError:
            continue

    return None


# ============================================================
# SEARCH RESULTS
# ============================================================

def get_search_listings():

    response = requests.get(
        SEARCH_URL,
        headers=HEADERS,
        timeout=30,
    )

    print(
        "HTTP status:",
        response.status_code
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    listings = []

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link["href"]

        if "/s-anzeige/" not in href:
            continue

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        if not title:
            continue

        full_url = urljoin(
            BASE_URL,
            href
        )

        listings.append({
            "title": title,
            "url": full_url,
        })

    # Remove duplicate URLs
    unique = {}

    for listing in listings:
        unique[listing["url"]] = listing

    return list(unique.values())


# ============================================================
# INDIVIDUAL LISTING
# ============================================================

def get_listing_details(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        return clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )

    except requests.RequestException:
        return ""


# ============================================================
# BROAD FILTER
# ============================================================

def filter_listing(listing):

    title = listing["title"]

    # --------------------------------------------------------
    # 1. TAUSCH / GESUCH
    # HARD FILTER
    # --------------------------------------------------------

    if is_exchange_or_wanted(title):
        return None, "TAUSCH/GESUCH"

    # --------------------------------------------------------
    # 2. WG / SHARED ROOM
    # HARD FILTER
    # --------------------------------------------------------

    if is_wg(title):
        return None, "WG"

    # --------------------------------------------------------
    # 3. ROOM COUNT
    #
    # We only reject if the title explicitly says 3+ rooms.
    # If the number is unknown, KEEP the listing.
    # --------------------------------------------------------

    rooms = explicit_room_count(title)

    if rooms is not None and rooms > 2:
        return None, f"MORE THAN 2 ROOMS ({rooms})"

    # --------------------------------------------------------
    # 4. GET INDIVIDUAL LISTING
    # --------------------------------------------------------

    details = get_listing_details(
        listing["url"]
    )

    if not details:
        return {
            "title": title,
            "url": listing["url"],
            "warm_rent": None,
            "anmeldung": "UNKNOWN",
        }, "MATCH - NO DETAILS"

    combined_text = (
        title
        + " "
        + details
    )

    # --------------------------------------------------------
    # 5. WARM RENT
    #
    # If explicitly above €900 -> reject.
    # If unknown -> KEEP.
    # --------------------------------------------------------

    warm_rent = extract_warm_rent(
        combined_text
    )

    if warm_rent is not None:

        if warm_rent > MAX_WARM_RENT:

            return None, (
                f"WARM > 900 ({warm_rent} EUR)"
            )

    # --------------------------------------------------------
    # 6. ANMELDUNG
    #
    # We DO NOT filter by Anmeldung.
    # We simply report it if detectable.
    # --------------------------------------------------------

    anmeldung = "UNKNOWN"

    text_lower = combined_text.lower()

    if (
        "anmeldung nicht möglich" in text_lower
        or "anmeldung nicht moglich" in text_lower
        or "keine anmeldung" in text_lower
        or "ohne anmeldung" in text_lower
    ):

        anmeldung = "NO"

    elif (
        "anmeldung möglich" in text_lower
        or "anmeldung moglich" in text_lower
        or "anmeldung erlaubt" in text_lower
        or "wohnungsgeberbestätigung" in text_lower
        or "wohnungsgeberbescheinigung" in text_lower
    ):

        anmeldung = "YES"

    # --------------------------------------------------------
    # 7. MATCH
    # --------------------------------------------------------

    return {
        "title": title,
        "url": listing["url"],
        "warm_rent": warm_rent,
        "anmeldung": anmeldung,
    }, "MATCH"


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    listings = get_search_listings()

    print(
        "Listings found:",
        len(listings)
    )

    print()

    reasons = {}
    matches = []

    for listing in listings:

        result, reason = filter_listing(
            listing
        )

        reasons[reason] = (
            reasons.get(reason, 0) + 1
        )

        if result:
            matches.append(result)

    print(
        "========== FILTER RESULTS =========="
    )

    for reason, count in reasons.items():

        print(
            reason,
            ":",
            count
        )

    print()

    print(
        "MATCHING LISTINGS:",
        len(matches)
    )

    print()

    for result in matches:

        print(
            "TITLE:",
            result["title"]
        )

        if result["warm_rent"] is not None:

            print(
                "WARM:",
                result["warm_rent"],
                "EUR"
            )

        else:

            print(
                "WARM: UNKNOWN"
            )

        print(
            "ANMELDUNG:",
            result["anmeldung"]
        )

        print(
            "URL:",
            result["url"]
        )

        print()
