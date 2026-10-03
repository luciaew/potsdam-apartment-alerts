import requests
from bs4 import BeautifulSoup
import re


SEARCH_URL = (
    "https://www.wohnung-jetzt.de/"
    "suche/potsdam/mieten/wohnung/"
)


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

        print(
            "Wohnung-jetzt status:",
            response.status_code
        )

        if response.status_code != 200:
            print(
                "Wohnung-jetzt could not be accessed."
            )
            return []

    except Exception as e:

        print(
            "Wohnung-jetzt error:",
            e
        )

        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    listings = []
    seen_urls = set()

    # Wohnung-jetzt uses /exposee/ URLs
    # for individual property listings.
    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href",
            ""
        ).strip()

        if "/exposee/" not in href:
            continue

        # Build absolute URL
        if href.startswith("/"):
            url = (
                "https://www.wohnung-jetzt.de"
                + href
            )

        elif href.startswith("http"):
            url = href

        else:
            continue

        # Remove possible URL fragments
        url = url.split("#")[0]

        if url in seen_urls:
            continue

        seen_urls.add(url)

        # Listing title
        title = link.get_text(
            " ",
            strip=True
        )

        if not title:
            title = "Wohnung in Potsdam"

        # Get the text belonging to the
        # listing card.
        parent = link.parent

        card_text = ""

        if parent:
            card_text = parent.get_text(
                " ",
                strip=True
            )

        # Sometimes the card is one level higher.
        if len(card_text) < len(title) + 20:

            grandparent = (
                parent.parent
                if parent
                else None
            )

            if grandparent:

                card_text = (
                    grandparent.get_text(
                        " ",
                        strip=True
                    )
                )

        listings.append({
            "url": url,
            "title": title,
            "description": card_text,
            "source": "Wohnung-jetzt"
        })

    print(
        "Wohnung-jetzt raw listings:",
        len(listings)
    )

    return listings


def filter_listing(listing):

    title = listing.get(
        "title",
        ""
    ).lower()

    description = listing.get(
        "description",
        ""
    ).lower()

    full_text = (
        title
        + " "
        + description
    )

    # =========================================================
    # POTSDAM ONLY
    # =========================================================

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

    if not any(
        term in full_text
        for term in potsdam_terms
    ):
        return False

    # =========================================================
    # EXCLUDE WG / SHARED ROOMS
    #
    # We check the TITLE primarily.
    # This prevents unrelated WG text elsewhere
    # on the page from killing a normal apartment.
    # =========================================================

    if re.search(
        r"\bwg\b",
        title
    ):
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

        if term in title:
            return False

    # =========================================================
    # EXCLUDE WANTED / EXCHANGE LISTINGS
    # =========================================================

    excluded_terms = [
        "tauschangebot",
        "wohnungstausch",
        "tauschwohnung",
        "wohnung gesucht",
        "mietgesuch"
    ]

    for term in excluded_terms:

        if term in title:
            return False

    # IMPORTANT:
    # We do NOT exclude the generic word "gesuch".
    # It may appear elsewhere on the website/card.

    # =========================================================
    # ROOMS
    #
    # >2 rooms  -> EXCLUDE
    # 1-2 rooms -> KEEP
    # unknown    -> KEEP
    # =========================================================

    room_matches = re.findall(
        r"(\d+(?:[.,]\d+)?)"
        r"\s*(?:-|–)?\s*zimmer",
        title,
        re.IGNORECASE
    )

    for match in room_matches:

        try:

            rooms = float(
                match.replace(
                    ",",
                    "."
                )
            )

            if rooms > 2:
                return False

        except ValueError:
            pass

    # =========================================================
    # WARM RENT
    #
    # Warmmiete unknown -> KEEP
    # Warmmiete <= 900  -> KEEP
    # Warmmiete > 900   -> EXCLUDE
    #
    # Kaltmiete alone does NOT exclude the listing.
    # =========================================================

    warm_patterns = [

        r"warmmiete\s*:?\s*"
        r"(\d[\d.]*)\s*€?",

        r"\bwarm\s*:?\s*"
        r"(\d[\d.]*)\s*€",

        r"\bwm\s*:?\s*"
        r"(\d[\d.]*)\s*€"
    ]

    for pattern in warm_patterns:

        matches = re.findall(
            pattern,
            full_text,
            re.IGNORECASE
        )

        for match in matches:

            try:

                warm = float(
                    match
                    .replace(".", "")
                    .replace(",", ".")
                )

                if warm > 900:
                    return False

            except ValueError:
                pass

    # =========================================================
    # EXPLICIT "NO ANMELDUNG"
    #
    # Unknown Anmeldung -> KEEP
    # =========================================================

    anmeldung_no = [

        "anmeldung nicht möglich",
        "anmeldung nicht moglich",

        "keine anmeldung möglich",
        "keine anmeldung moglich",

        "no registration possible"
    ]

    for term in anmeldung_no:

        if term in full_text:
            return False

    # =========================================================
    # AVAILABILITY
    #
    # ONLY NOVEMBER 2026 OR LATER
    #
    # Examples accepted:
    #   frei ab November
    #   frei ab November 2026
    #   verfügbar ab November
    #   ab November 2026
    #   frei ab 01.11.2026
    #   verfügbar ab 15.12.2026
    #
    # Examples rejected:
    #   ab sofort
    #   ab Oktober
    #   ab September
    #   ab 01.10.2026
    #   no availability information
    # =========================================================

    availability_patterns = [

        # Month names
        r"(?:frei\s+ab|verfügbar\s+ab|ab)"
        r"\s+"
        r"(januar|jan|februar|feb|märz|maerz|mär|"
        r"april|mai|juni|jun|juli|jul|august|aug|"
        r"september|sep|oktober|okt|november|nov|"
        r"dezember|dez)"
        r"(?:\s+\d{4})?",

        # Numeric dates:
        # 01.11.2026
        # 01/11/2026
        # 01-11-2026
        r"(?:frei\s+ab|verfügbar\s+ab|ab)"
        r"\s+"
        r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})"
    ]

    availability_found = False
    availability_month = None
    availability_year = None

    # ---------------------------------------------------------
    # Check month names
    # ---------------------------------------------------------

    month_names = {
        "januar": 1,
        "jan": 1,

        "februar": 2,
        "feb": 2,

        "märz": 3,
        "maerz": 3,
        "mär": 3,

        "april": 4,

        "mai": 5,

        "juni": 6,
        "jun": 6,

        "juli": 7,
        "jul": 7,

        "august": 8,
        "aug": 8,

        "september": 9,
        "sep": 9,

        "oktober": 10,
        "okt": 10,

        "november": 11,
        "nov": 11,

        "dezember": 12,
        "dez": 12
    }

    month_pattern = re.compile(
        r"(?:frei\s+ab|verfügbar\s+ab|ab)"
        r"\s+"
        r"(januar|jan|februar|feb|märz|maerz|mär|"
        r"april|mai|juni|jun|juli|jul|august|aug|"
        r"september|sep|oktober|okt|november|nov|"
        r"dezember|dez)"
        r"(?:\s+(\d{4}))?",
        re.IGNORECASE
    )

    month_match = month_pattern.search(
        full_text
    )

    if month_match:

        availability_found = True

        month_name = (
            month_match.group(1)
            .lower()
        )

        availability_month = (
            month_names.get(month_name)
        )

        year_text = month_match.group(2)

        if year_text:
            availability_year = int(
                year_text
            )
        else:
            # If no year is written,
            # assume the upcoming 2026 period.
            availability_year = 2026

    # ---------------------------------------------------------
    # Check numeric date
    # ---------------------------------------------------------

    if not availability_found:

        date_pattern = re.compile(
            r"(?:frei\s+ab|verfügbar\s+ab|ab)"
            r"\s+"
            r"(\d{1,2})[./-]"
            r"(\d{1,2})[./-]"
            r"(\d{2,4})",
            re.IGNORECASE
        )

        date_match = date_pattern.search(
            full_text
        )

        if date_match:

            availability_found = True

            availability_month = int(
                date_match.group(2)
            )

            availability_year = int(
                date_match.group(3)
            )

            if availability_year < 100:
                availability_year += 2000

    # ---------------------------------------------------------
    # No availability information
    # ---------------------------------------------------------

    if not availability_found:
        return False

    if availability_month is None:
        return False

    if availability_year is None:
        return False

    # ---------------------------------------------------------
    # Accept November 2026 or later
    # ---------------------------------------------------------

    if availability_year < 2026:
        return False

    if (
        availability_year == 2026
        and availability_month < 11
    ):
        return False

    # =========================================================
    # PASSED ALL FILTERS
    # =========================================================

    return True
