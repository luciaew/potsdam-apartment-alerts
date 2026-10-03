import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


URL = "https://www.kleinanzeigen.de/s-wohnung-mieten/potsdam/wohnung-mieten/k0c203l7958"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0 Safari/537.36"
    )
}


def get_listings():
    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    print("HTTP status:", response.status_code)
    print("Page size:", len(response.text))

    soup = BeautifulSoup(response.text, "html.parser")

    listings = []

    for link in soup.find_all("a", href=True):

        href = link["href"]

        if "/s-anzeige/" not in href:
            continue

        title = link.get_text(" ", strip=True)

        if not title:
            continue

        full_url = urljoin(
            "https://www.kleinanzeigen.de",
            href
        )

        listings.append({
            "title": title,
            "url": full_url
        })

    # Remove duplicates
    unique = {}

    for listing in listings:
        unique[listing["url"]] = listing

    return list(unique.values())


if __name__ == "__main__":

    listings = get_listings()

    print("Listings found:", len(listings))

    for listing in listings[:20]:
        print()
        print("TITLE:", listing["title"])
        print("URL:", listing["url"])
