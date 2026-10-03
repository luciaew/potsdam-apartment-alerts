import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


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

# Para esta primera prueba queremos que Anmeldung
# aparezca explícitamente en el anuncio.
REQUIRE_ANMELDUNG = True


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def is_valid_room_count(text):
    """
    Accept only 1 or 2 rooms.
    Allows:
      1 Zi.
      1 Zimmer
      1-Zimmer-Wohnung
      2 Zi.
      2 Zimmer
      2-Zimmer-Wohnung

    Rejects:
      1,5 Zi.
      2,5 Zi.
      3 Zi.
    """

    matches = re.findall(
        r"(\d+(?:[.,]\d+)?)\s*(?:-|–)?\s*(?:Zimmer|Zi\.?)",
        text,
        flags=re.IGNORECASE,
    )

    if not matches:
        return False

    for value in matches:
        value = value.replace(",", ".")

        try:
            rooms = float(value)
        except ValueError:
            continue

        if rooms in (1.0, 2.0):
            return True

    return False


def is_wg(text):
    text_lower = text.lower()

    excluded_phrases = [
        "wg-zimmer",
        "wg zimmer",
        "wohngemeinschaft",
        "mitbewohner gesucht",
        "mitbewohnerin gesucht",
        "mitbewohner gesucht",
        "zimmer in wg",
        "zimmer frei in wg",
        "zimmer in einer wg",
        "wg gesucht",
        "wg-wohnung",
    ]

    return any(phrase in text_lower for phrase in excluded_phrases)


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

    return any(phrase in text_lower for phrase in excluded_phrases)


def extract_warm_rent(text):
    """
    Try to find an explicitly stated Warmmiete.
    """

    patterns = [
        r"warmmiete\s*:?\s*(\d[\d\.\s]*)\s*€",
        r"warmmiete\s*:?\s*€\s*(\d[\d\.\s]*)",
        r"warm\s*:?\s*(\d[\d\.\s]*)\s*€",
        r"warm\s*:?\s*€\s*(\d[\d\.\s]*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            value = match.group(1)

            value = (
                value.replace(".", "")
                .replace(" ", "")
                .replace(",", ".")
            )

            try:
                return float(value)
            except ValueError:
                pass

    return None


def anmeldung_status(text):
    text_lower = text.lower()

    negative = [
        "anmeldung nicht möglich",
        "anmeldung nicht moglich",
        "keine anmeldung",
        "ohne anmeldung",
        "keine wohnungsgeberbestätigung",
        "wohnungsgeberbestätigung nicht möglich",
        "wohnungsgeberbescheinigung nicht möglich",
    ]

    positive = [
        "anmeldung möglich",
        "anmeldung moglich",
        "anmeldung erlaubt",
        "wohnungsgeberbestätigung",
        "wohnungsgeberbescheinigung",
    ]

    if any(phrase in text_lower for phrase in negative):
        return "NO"

    if any(phrase in text_lower for phrase in positive):
        return "YES"

    return "UNKNOWN"


def get_search_listings():
    response = requests.get(
        SEARCH_URL,
        headers=HEADERS,
        timeout=30,
    )

    print("HTTP status:", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    listings = []

    for link in soup.find_all("a", href=True):

        href = link["href"]

        if "/s-anzeige/" not in href:
            continue

        title = clean_text(link.get_text(" ", strip=True))

        if not title:
            continue

        full_url = urljoin(BASE_URL, href)

        listings.append({
            "title": title,
            "url": full_url,
        })

    unique = {}

    for listing in listings:
        unique[listing["url"]] = listing

    return list(unique.values())


def get_listing_details(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(response.text, "html.parser")

        return clean_text(soup.get_text(" ", strip=True))

    except requests.RequestException:
        return ""


def filter_listing(listing):
    title = listing["title"]

    if not is_valid_room_count(title):
        return None, "NO 1-2 ZIMMER"

    if is_wg(title):
        return None, "WG"

    if is_exchange_or_wanted(title):
        return None, "TAUSCH/GESUCH"

    details = get_listing_details(listing["url"])

    if not details:
        return None, "NO DETAILS"

    combined_text = title + " " + details

    if is_wg(combined_text):
        return None, "WG"

    if is_exchange_or_wanted(combined_text):
        return None, "TAUSCH/GESUCH"

    warm_rent = extract_warm_rent(combined_text)

    if warm_rent is None:
        return None, "NO WARMMIETE"

    if warm_rent > MAX_WARM_RENT:
        return None, f"WARM > 900 ({warm_rent} EUR)"

    anmeldung = anmeldung_status(combined_text)

    if anmeldung == "NO":
        return None, "ANMELDUNG NO"

    if REQUIRE_ANMELDUNG and anmeldung != "YES":
        return None, "ANMELDUNG UNKNOWN"

    return {
        "title": title,
        "url": listing["url"],
        "warm_rent": warm_rent,
        "anmeldung": anmeldung,
    }, "MATCH"


if __name__ == "__main__":

    listings = get_search_listings()

    print("Listings found:", len(listings))
    print()

    reasons = {}
    matches = []

    for listing in listings:
        result, reason = filter_listing(listing)

        reasons[reason] = reasons.get(reason, 0) + 1

        if result:
            matches.append(result)

    print("========== FILTER RESULTS ==========")

    for reason, count in reasons.items():
        print(reason, ":", count)

    print()
    print("MATCHING LISTINGS:", len(matches))
    print()

    for result in matches:
        print("TITLE:", result["title"])
        print("WARM:", result["warm_rent"], "EUR")
        print("ANMELDUNG:", result["anmeldung"])
        print("URL:", result["url"])
        print()
