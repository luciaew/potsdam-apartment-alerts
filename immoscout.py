import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


SEARCH_URL = (
    "https://www.immobilienscout24.de/Suche/de/"
    "brandenburg/potsdam/wohnung-mieten"
)

BASE_URL = "https://www.immobilienscout24.de"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

MAX_WARM_RENT = 900


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_number(text):
    """
    Extract first German-style number from text.
    Examples:
    825 €
    1.051,78 €
    53,5 m²
    """
    if not text:
        return None

    match = re.search(
        r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)",
        text
    )

    if not match:
        return None

    value = match.group(1)

    # German number format:
    # 1.051,78 -> 1051.78
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    else:
        # 1.051 -> 1051
        if value.count(".") > 1:
            value = value.replace(".", "")
        elif value.count(".") == 1:
            before, after = value.split(".")
            if len(after) == 3:
                value = value.replace(".", "")

    try:
        return float(value)
    except ValueError:
        return None


def is_wg(text):
    text_lower = text.lower()

    excluded_phrases = [
        "wg-zimmer",
        "wg zimmer",
        "zimmer in wg",
        "zimmer in einer wg",
        "wohngemeinschaft",
        "mitbewohner gesucht",
        "mitbewohnerin gesucht",
        "wg gesucht",
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
        "wohnung gesucht",
        "suche wohnung",
        "suche eine wohnung",
        "gesuch",
    ]

    return any(phrase in text_lower for phrase in excluded_phrases)


def extract_rooms(text):
    """
    Extract number of rooms from:
    1 Zi.
    2 Zi.
    1 Zimmer
    2-Zimmer-Wohnung
    """

    patterns = [
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*zimmer\b",
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*zi\.",
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*z\.",
    ]

    text_lower = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text_lower)

        if match:
            value = match.group(1).replace(",", ".")

            try:
                return float(value)
            except ValueError:
                pass

    return None


def extract_warm_rent(text):
    """
    Look specifically for Warmmiete / Gesamtmiete /
    Pauschalmiete.
    """

    patterns = [
        r"warmmiete\s*[:\-]?\s*([\d\.,]+)\s*€?",
        r"gesamtmiete\s*[:\-]?\s*([\d\.,]+)\s*€?",
        r"pauschalmiete\s*[:\-]?\s*([\d\.,]+)\s*€?",
    ]

    text_lower = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text_lower)

        if match:
            value = match.group(1)

            value = value.replace(".", "").replace(",", ".")

            try:
                return float(value)
            except ValueError:
                pass

    return None


def extract_area(text):
    """
    Extract Wohnfläche / Fläche.

    Examples:
    35 m²
    53 m²
    51,12 m²
    """

    patterns = [
        r"wohnfläche\s*(?:ca\.)?\s*[:\-]?\s*([\d\.,]+)\s*m²",
        r"wohnfläche\s*(?:ca\.)?\s*([\d\.,]+)\s*qm",
        r"fläche\s*(?:ca\.)?\s*[:\-]?\s*([\d\.,]+)\s*m²",
        r"([\d\.,]+)\s*m²",
        r"([\d\.,]+)\s*qm",
    ]

    text_lower = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text_lower)

        if match:
            value = match.group(1)

            value = value.replace(".", "").replace(",", ".")

            try:
                return float(value)
            except ValueError:
                pass

    return None


def extract_available_from(text):
    """
    Extract Bezugsfrei ab / available from.
    """

    patterns = [
        r"bezugsfrei\s*ab\s*:?\s*(.{0,30})",
        r"frei\s*ab\s*:?\s*(.{0,30})",
    ]

    text_lower = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text_lower)

        if match:
            value = clean_text(match.group(1))

            if value:
                return value

    return None


def extract_address(soup, text):
    """
    Try several ways of finding the address.
    """

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        script_text = script.get_text(" ", strip=True)

        address_match = re.search(
            r'"streetAddress"\s*:\s*"([^"]+)"',
            script_text
        )

        postal_match = re.search(
            r'"postalCode"\s*:\s*"?(144\d{2})"?',
            script_text
        )

        if address_match and postal_match:
            return (
                address_match.group(1),
                postal_match.group(1)
            )

    # itemprop
    street = soup.find(attrs={"itemprop": "streetAddress"})
    postal = soup.find(attrs={"itemprop": "postalCode"})

    if street and postal:
        return (
            clean_text(street.get_text(" ", strip=True)),
            clean_text(postal.get_text(" ", strip=True))
        )

    # Visible text fallback
    address_pattern = re.search(
        r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\- ]+straße"
        r"|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\- ]+strasse"
        r"|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\- ]+weg"
        r"|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\- ]+allee"
        r"|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\- ]+platz)"
        r"\s+\d+[a-zA-Z]?"
        r"[,\s]+144\d{2}\s+Potsdam",
        text
    )

    if address_pattern:
        full_address = clean_text(address_pattern.group(0))

        postal_match = re.search(r"(144\d{2})", full_address)

        if postal_match:
            return (
                full_address,
                postal_match.group(1)
            )

    # PLZ only
    postal_match = re.search(r"\b(144\d{2})\b", text)

    if postal_match:
        return (
            None,
            postal_match.group(1)
        )

    return None, None


def get_listing_details(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        text = clean_text(
            soup.get_text(" ", strip=True)
        )

        title = None

        h1 = soup.find("h1")

        if h1:
            title = clean_text(
                h1.get_text(" ", strip=True)
            )

        if not title:
            title_tag = soup.find("title")

            if title_tag:
                title = clean_text(
                    title_tag.get_text(" ", strip=True)
                )

        address, postcode = extract_address(
            soup,
            text
        )

        warm_rent = extract_warm_rent(text)

        rooms = extract_rooms(text)

        area = extract_area(text)

        available_from = extract_available_from(text)

        return {
            "title": title or "Wohnung in Potsdam",
            "url": url,
            "warm_rent": warm_rent,
            "rooms": rooms,
            "area": area,
            "available_from": available_from,
            "address": address,
            "postcode": postcode,
        }

    except Exception as e:
        print(
            f"Error reading ImmoScout24 listing: {url} -> {e}"
        )

        return None


def get_search_listings():
    """
    Get current Potsdam listings from ImmoScout24.
    """

    try:
        response = requests.get(
            SEARCH_URL,
            headers=HEADERS,
            timeout=20
        )

        print(
            "ImmoScout24 status:",
            response.status_code
        )

        if response.status_code != 200:
            print(
                "ImmoScout24 could not be accessed."
            )
            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = []

        # Find links to Exposés
        for link in soup.find_all("a", href=True):

            href = link["href"]

            if "/expose/" not in href:
                continue

            url = urljoin(
                BASE_URL,
                href
            )

            # Remove tracking parameters
            url = url.split("?")[0]

            if url not in links:
                links.append(url)

        print(
            f"ImmoScout24: found {len(links)} listing links"
        )

        listings = []

        for url in links[:50]:

            listing = get_listing_details(url)

            if not listing:
                continue

            combined_text = " ".join(
                str(value)
                for value in listing.values()
                if value is not None
            )

            # Only Potsdam
            if (
                listing["postcode"]
                and not listing["postcode"].startswith("144")
            ):
                continue

            # No WG
            if is_wg(combined_text):
                continue

            # No exchange / wanted listings
            if is_exchange_or_wanted(combined_text):
                continue

            # If room count is explicitly >2 -> exclude
            if (
                listing["rooms"] is not None
                and listing["rooms"] > 2
            ):
                continue

            # If Warmmiete is known and >900 -> exclude
            if (
                listing["warm_rent"] is not None
                and listing["warm_rent"] > MAX_WARM_RENT
            ):
                continue

            listings.append(listing)

        return listings

    except Exception as e:
        print(
            f"Error searching ImmoScout24: {e}"
        )

        return []
