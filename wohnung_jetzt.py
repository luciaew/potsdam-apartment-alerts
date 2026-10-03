import requests
from bs4 import BeautifulSoup
import re


SEARCH_URL = "https://www.wohnung-jetzt.de/suche/potsdam/mieten/wohnung/"


def get_search_listings():
    print("Checking Wohnung-jetzt...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(
            SEARCH_URL,
            headers=headers,
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

    # Find links that look like apartment detail pages
    links = soup.find_all("a", href=True)

    seen_urls = set()

    for link in links:
        href = link.get("href", "").strip()

        if not href:
            continue

        if href.startswith("/"):
            url = "https://www.wohnung-jetzt.de" + href
        elif href.startswith("http"):
            url = href
        else:
            continue

        # Avoid duplicates
        if url in seen_urls:
            continue

        # Only apartment/property detail pages
        if "/immobilien/" not in url and "/angebot/" not in url:
            continue

        seen_urls.add(url)

        title = link.get_text(" ", strip=True)

        if not title:
            title = "Wohnung in Potsdam"

        listings.append({
            "url": url,
            "title": title,
            "source": "Wohnung-jetzt"
        })

    print("Wohnung-jetzt raw listings:", len(listings))

    return listings


def filter_listing(listing):
    text = (
        listing.get("title", "") + " " +
        listing.get("description", "")
    ).lower()

    # Must be Potsdam
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

    # Exclude WG / shared living
    wg_terms = [
        "wg",
        "wg-zimmer",
        "wohngemeinschaft",
        "mitbewohner",
        "mitbewohnerin",
        "mitbewohner gesucht",
        "shared room",
        "shared flat",
        "gemeinschaftszimmer"
    ]

    # Important: don't reject normal "1-zimmer-wohnung"
    for term in wg_terms:
        if term == "wg":
            if re.search(r"\bwg\b", text):
                return False
        elif term in text:
            return False

    # Exclude exchanges / wanted listings
    excluded_terms = [
        "tauschangebot",
        "wohnungstausch",
        "wohnungstauschbörse",
        "tauschwohnung",
        "gesuch",
        "wohnung gesucht",
        "mietgesuch"
    ]

    for term in excluded_terms:
        if term in text:
            return False

    # Exclude explicitly more than 2 rooms
    room_matches = re.findall(
        r"(\d+(?:[.,]\d+)?)\s*[- ]?\s*zimmer",
        text
    )

    for match in room_matches:
        try:
            rooms = float(match.replace(",", "."))
            if rooms > 2:
                return False
        except ValueError:
            pass

    # Warm rent filter
    warm_matches = re.findall(
        r"(?:warmmiete|warmmiete:|warm|wm)\s*[:\-]?\s*"
        r"(\d{2,5}(?:[.,]\d{1,2})?)\s*€?",
        text
    )

    for match in warm_matches:
        try:
            warm = float(match.replace(".", "").replace(",", "."))
            if warm > 900:
                return False
        except ValueError:
            pass

    return True
