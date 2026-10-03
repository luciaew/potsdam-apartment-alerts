import json
import math
import re
import time

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

GEOCODE_CACHE_FILE = "geocoded.json"

# Potsdam Hauptbahnhof
HBF_LAT = 52.391667
HBF_LON = 13.066667

# FH Potsdam
FH_LAT = 52.41372
FH_LON = 13.05141


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


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


def explicit_room_count(text):
    text_lower = text.lower()

    patterns = [
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*zimmer\b",
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*zi\.",
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*z\.",
        r"\b(\d+(?:[.,]\d+)?)\s*[-–]?\s*zkb\b",
    ]

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
    patterns = [
        r"warmmiete\s*:?\s*(\d[\d\.\s]*)\s*€",
        r"warmmiete\s*:?\s*€\s*(\d[\d\.\s]*)",
        r"gesamtmiete\s*:?\s*(\d[\d\.\s]*)\s*€",
        r"gesamtmiete\s*:?\s*€\s*(\d[\d\.\s]*)",
        r"warm\s*:?\s*(\d[\d\.\s]*)\s*€",
        r"warm\s*:?\s*€\s*(\d[\d\.\s]*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if not match:
            continue

        value = match.group(1)
        value = value.replace(".", "").replace(" ", "").replace(",", ".")

        try:
            return float(value)
        except ValueError:
            continue

    return None


def extract_address(soup):
    """
    Find an exact published Potsdam address.

    We first try structured data and then fall back
    to the visible address shown on the Kleinanzeigen page.
    """

    # 1. JSON-LD structured data
    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:
        try:
            data = json.loads(
                script.string or script.get_text()
            )

            objects = (
                data
                if isinstance(data, list)
                else [data]
            )

            for obj in objects:

                if not isinstance(obj, dict):
                    continue

                address = obj.get("address")

                if isinstance(address, dict):

                    street = address.get(
                        "streetAddress"
                    )

                    postcode = address.get(
                        "postalCode"
                    )

                    city = address.get(
                        "addressLocality"
                    )

                    if (
                        street
                        and postcode
                        and city
                        and "potsdam"
                        in str(city).lower()
                    ):
                        return clean_text(
                            f"{street}, "
                            f"{postcode} {city}"
                        )

        except Exception:
            continue


    # 2. HTML itemprop fields
    street = soup.find(
        attrs={"itemprop": "streetAddress"}
    )

    postcode = soup.find(
        attrs={"itemprop": "postalCode"}
    )

    city = soup.find(
        attrs={"itemprop": "addressLocality"}
    )

    if street and postcode and city:

        street_text = clean_text(
            street.get_text(
                " ",
                strip=True
            )
        )

        postcode_text = clean_text(
            postcode.get_text(
                " ",
                strip=True
            )
        )

        city_text = clean_text(
            city.get_text(
                " ",
                strip=True
            )
        )

        if "potsdam" in city_text.lower():

            return (
                f"{street_text}, "
                f"{postcode_text} {city_text}"
            )


    # 3. Visible address on Kleinanzeigen
    page_text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    address_pattern = (
        r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\-'\s]{2,60}"
        r"\s+\d+[A-Za-z]?)"
        r"\s*,?\s*"
        r"(\d{5})"
        r"\s+"
        r"(?:Brandenburg\s*-\s*)?"
        r"Potsdam"
    )

    match = re.search(
        address_pattern,
        page_text
    )

    if match:

        street = clean_text(
            match.group(1)
        )

        postcode = match.group(2)

        return (
            f"{street}, "
            f"{postcode} Potsdam"
        )


    return None


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

        listings.append(
            {
                "title": title,
                "url": full_url,
            }
        )

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
            return "", None

        soup = BeautifulSoup(response.text, "html.parser")

        text = clean_text(
            soup.get_text(" ", strip=True)
        )

        address = extract_address(soup)

        return text, address

    except requests.RequestException:
        return "", None


def load_geocode_cache():
    try:
        with open(
            GEOCODE_CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except Exception:
        return {}


def save_geocode_cache(cache):
    with open(
        GEOCODE_CACHE_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            cache,
            file,
            ensure_ascii=False,
            indent=2,
        )


def geocode_address(address, cache):
    if not address:
        return None

    if address in cache:
        return cache[address]

    print("Geocoding:", address)

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": address,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "de",
    }

    headers = {
        "User-Agent": (
            "PotsdamApartmentAlerts/1.0 "
            "(GitHub apartment alert bot)"
        )
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30,
        )

        if response.status_code != 200:
            print(
                "Geocoding failed:",
                response.status_code
            )
            return None

        results = response.json()

        if not results:
            cache[address] = None
            save_geocode_cache(cache)
            return None

        latitude = float(results[0]["lat"])
        longitude = float(results[0]["lon"])

        coordinates = {
            "lat": latitude,
            "lon": longitude,
        }

        cache[address] = coordinates
        save_geocode_cache(cache)

        # Avoid making repeated rapid requests.
        time.sleep(1.1)

        return coordinates

    except Exception as error:
        print("Geocoding error:", error)
        return None


def distance_km(lat1, lon1, lat2, lon2):
    """
    Haversine distance in kilometers.
    """

    radius = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return radius * c


def calculate_distances(address):
    if not address:
        return None, None

    cache = load_geocode_cache()

    coordinates = geocode_address(
        address,
        cache,
    )

    if not coordinates:
        return None, None

    lat = coordinates["lat"]
    lon = coordinates["lon"]

    hbf_distance = distance_km(
        lat,
        lon,
        HBF_LAT,
        HBF_LON,
    )

    fh_distance = distance_km(
        lat,
        lon,
        FH_LAT,
        FH_LON,
    )

    return hbf_distance, fh_distance


def filter_listing(listing):
    title = listing["title"]

    if is_exchange_or_wanted(title):
        return None, "TAUSCH/GESUCH"

    if is_wg(title):
        return None, "WG"

    rooms = explicit_room_count(title)

    if rooms is not None and rooms > 2:
        return None, f"MORE THAN 2 ROOMS ({rooms})"

    details, address = get_listing_details(
        listing["url"]
    )

    if not details:
        return {
            "title": title,
            "url": listing["url"],
            "warm_rent": None,
            "anmeldung": "UNKNOWN",
            "address": address,
            "hbf_distance": None,
            "fh_distance": None,
        }, "MATCH - NO DETAILS"

    combined_text = title + " " + details

    warm_rent = extract_warm_rent(
        combined_text
    )

    if (
        warm_rent is not None
        and warm_rent > MAX_WARM_RENT
    ):
        return None, (
            f"WARM > 900 ({warm_rent} EUR)"
        )

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

    hbf_distance, fh_distance = calculate_distances(
        address
    )

    return {
        "title": title,
        "url": listing["url"],
        "warm_rent": warm_rent,
        "anmeldung": anmeldung,
        "address": address,
        "hbf_distance": hbf_distance,
        "fh_distance": fh_distance,
    }, "MATCH"


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
        print(reason, ":", count)

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

        print(
            "WARM:",
            result["warm_rent"]
        )

        print(
            "ANMELDUNG:",
            result["anmeldung"]
        )

        print(
            "ADDRESS:",
            result["address"]
        )

        print(
            "HBF:",
            result["hbf_distance"]
        )

        print(
            "FH:",
            result["fh_distance"]
        )

        print(
            "URL:",
            result["url"]
        )

        print()
