import requests
from bs4 import BeautifulSoup


URL = "https://www.kleinanzeigen.de/s-wohnung-mieten/potsdam/c203l7958"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0 Safari/537.36"
    )
}


def get_listings():
    response = requests.get(URL, headers=HEADERS, timeout=30)

    print("HTTP status:", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    listings = []

    for article in soup.select("article.aditem"):
        title_element = article.select_one("h2")
        link_element = article.select_one("a[href]")

        if not title_element or not link_element:
            continue

        title = title_element.get_text(" ", strip=True)
        link = link_element.get("href")

        if not link:
            continue

        if link.startswith("/"):
            link = "https://www.kleinanzeigen.de" + link

        listings.append({
            "title": title,
            "url": link,
        })

    return listings


if __name__ == "__main__":
    listings = get_listings()

    print("Listings found:", len(listings))

    for listing in listings[:10]:
        print()
        print(listing["title"])
        print(listing["url"])
