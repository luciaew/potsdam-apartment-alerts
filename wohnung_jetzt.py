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


# =========================================================
# GET INDIVIDUAL LISTING PAGE
# =========================================================

def get_detail_text(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        print(
            "Detail status:",
            response.status_code,
            url
        )

        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        return soup.get_text(
            " ",
            strip=True
        ).lower()

    except Exception as e:

        print(
            "Detail error:",
            e
        )

        return ""


# =========================================================
# EXTRACT AVAILABILITY
# =========================================================

def extract_availability(text):

    if not text:
        return None

    # -----------------------------------------------------
    # Explicitly unavailable immediately
    # -----------------------------------------------------

    if re.search(
        r"\b(?:ab\s+sofort|sofort\s+frei|sofort\s+verfügbar)\b",
        text,
        re.IGNORECASE
    ):
        return None

    # -----------------------------------------------------
    # Month names
    # -----------------------------------------------------

    months = {
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

    month_names = (
        "januar|jan|"
        "februar|feb|"
        "märz|maerz|mär|"
        "april|"
        "mai|"
        "juni|jun|"
        "juli|jul|"
        "august|aug|"
        "september|sep|"
        "oktober|okt|"
        "november|nov|"
        "dezember|dez"
    )

    # -----------------------------------------------------
    # "frei ab November 2026"
    # "verfügbar ab November 2026"
    # "Bezugsfrei ab November 2026"
    # "Bezug ab November 2026"
    # -----------------------------------------------------

    month_pattern = re.compile(
        r"(?:"
        r"frei\s+ab|"
        r"verfügbar\s+ab|"
        r"bezugsfrei\s+ab|"
        r"bezug\s+ab|"
        r"mietbeginn\s+ab|"
        r"ab"
        r")"
        r"\s+"
        r"("
        + month_names +
        r")"
        r"(?:\s+(\d{4}))?",
        re.IGNORECASE
    )

    match = month_pattern.search(text)

    if match:

        month_name = (
            match.group(1)
            .lower()
        )

        month = months.get(
            month_name
        )

        if month is None:
            return None

        year_text = match.group(2)

        if year_text:
            year = int(year_text)
        else:
            # Month without year:
            # assume the current relevant year.
            year = 2026

        return {
            "month": month,
            "year": year,
            "text": match.group(0)
        }

    # -----------------------------------------------------
    # Numeric date
    #
    # 01.11.2026
    # 01/11/2026
    # 01-11-2026
    # -----------------------------------------------------

    date_pattern = re.compile(
        r"(?:"
        r"frei\s+ab|"
        r"verfügbar\s+ab|"
        r"bezugsfrei\s+ab|"
        r"bezug\s+ab|"
        r"mietbeginn\s+ab|"
        r"ab"
        r")"
        r"\s+"
        r"(\d{1,2})"
        r"[./-]"
        r"(\d{1,2})"
        r"[./-]"
        r"(\d{2,4})",
        re.IGNORECASE
    )

    date_match = date_pattern.search(
        text
    )

    if date_match:

        day = int(
            date_match.group(1)
        )

        month = int(
            date_match.group(2)
        )

        year = int(
            date_match.group(3)
        )

        if year < 100:
            year += 2000

        return {
            "day": day,
            "month": month,
            "year": year,
            "text": date_match.group(0)
        }

    return None


# =========================================================
# CHECK NOVEMBER 2026 OR LATER
# =========================================================

def availability_is_valid(availability):

    if not availability:
        return False

    year = availability.get(
        "year"
    )

    month = availability.get(
        "month"
    )

    if year is None or month is None:
        return False

    # Before 2026
    if year < 2026:
        return False

    # November 2026 or later
    if year == 2026 and month < 11:
        return False

    return True


# =========================================================
# SEARCH PAGE
# =========================================================

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

    # Wohnung-jetzt uses /exposee/
    # URLs for individual listings.
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

        # Remove fragments
        url = url.split("#")[0]

        if url in seen_urls:
            continue

        seen_urls.add(url)

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        title = link.get_text(
            " ",
            strip=True
        )

        if not title:

            title = (
                "Wohnung in Potsdam"
            )

        # -------------------------------------------------
        # CARD TEXT
        # -------------------------------------------------

        parent = link.parent

        card_text = ""

        if parent:

            card_text = (
                parent.get_text(
                    " ",
                    strip=True
                )
            )

        # Sometimes card is one level higher
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


# =========================================================
# FILTER
# =========================================================

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

    # =====================================================
    # POTSDAM ONLY
    # =====================================================

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

    # =====================================================
    # EXCLUDE WG / SHARED ROOMS
    # =====================================================

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

    # =====================================================
    # EXCLUDE WANTED / EXCHANGE
    # =====================================================

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

    # =====================================================
    # ROOMS
    #
    # >2 rooms = EXCLUDE
    # 1-2 rooms = KEEP
    # unknown = KEEP
    # =====================================================

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

    # =====================================================
    # WARM RENT
    #
    # unknown = KEEP
    # <=900 = KEEP
    # >900 = EXCLUDE
    # =====================================================

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

    # =====================================================
    # EXPLICIT NO ANMELDUNG
    #
    # Unknown = KEEP
    # =====================================================

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

    # =====================================================
    # AVAILABILITY
    #
    # IMPORTANT:
    # First check card text.
    # If no date is found, open the individual listing.
    # =====================================================

    availability = extract_availability(
        full_text
    )

    # -----------------------------------------------------
    # If card has no date, open the detail page.
    # -----------------------------------------------------

    if not availability:

        print(
            "Checking detail page for availability:",
            listing.get("title")
        )

        detail_text = get_detail_text(
            listing["url"]
        )

        if not detail_text:

            print(
                "No detail text -> False"
            )

            return False

        availability = extract_availability(
            detail_text
        )

        if not availability:

            print(
                "No availability found -> False"
            )

            return False

        # Save it for possible use by bot.py
        listing["availability"] = (
            availability.get("text")
        )

    # =====================================================
    # NOVEMBER 2026 OR LATER
    # =====================================================

    if not availability_is_valid(
        availability
    ):

        print(
            "Availability rejected:",
            availability
        )

        return False

    print(
        "Availability accepted:",
        availability
    )

    # Save readable availability
    listing["availability"] = (
        availability.get("text")
    )

    # =====================================================
    # PASSED ALL FILTERS
    # =====================================================

    return True
