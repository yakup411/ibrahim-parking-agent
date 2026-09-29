from bs4 import BeautifulSoup

from http_client import source_session
from offer import Offer

BASE_URL = "https://www.gewobag.de/fuer-mietinteressentinnen/suche/parken"

QUERY = (
    "objekttyp%5B0%5D=parken&"
    "parken_type%5B0%5D=NA0070&"
    "parken_type%5B1%5D=NA0073&"
    "parken_type%5B2%5D=NA0074&"
    "parken_type%5B3%5D=NA0075&"
    "parken_type%5B4%5D=NA0076&"
    "parken_type%5B5%5D=NA0077&"
    "parken_type%5B6%5D=NA0079&"
    "lat-suggest&"
    "lng-suggest&"
    "address-suggest&"
    "distance-around=0&"
    "sort-by"
)


def get_address(detail_url):
    try:
        response = source_session.get(
            detail_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        text = soup.get_text("\n", strip=True)

        for line in text.split("\n"):
            line = line.strip()

            if "Berlin" in line and any(char.isdigit() for char in line):
                return line

    except Exception as exc:
        print(f"⚠️ Angebotsadresse konnte nicht geladen werden ({type(exc).__name__}).")

    return ""


def get_offers():
    print("🔍 Prüfe Gewobag...")

    offers = []
    seen_links = set()

    page = 1

    while True:

        if page == 1:
            url = f"{BASE_URL}/?{QUERY}"
        else:
            url = f"{BASE_URL}/page/{page}/?{QUERY}"

        print(f"📄 Seite {page}")

        response = source_session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )

        if response.status_code == 404:
            break

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        new_offers = 0

        for article in soup.find_all("article"):
            try:
                link = article.find("a", href=True)
                if not link:
                    continue

                href = link["href"]
                if "/mietangebote/" not in href:
                    continue
                if href.startswith("/"):
                    href = "https://www.gewobag.de" + href
                if href in seen_links:
                    continue
                seen_links.add(href)

                lines = [
                    line.strip()
                    for line in article.get_text("\n", strip=True).split("\n")
                    if line.strip()
                ]
                title = f"{lines[1]} ({lines[0]})" if len(lines) >= 2 else "Stellplatz"
                price = next((line for line in lines if "€" in line), "")
                offers.append(
                    Offer(
                        source="Gewobag",
                        title=title,
                        address=get_address(href),
                        price=price,
                        link=href,
                        latitude=0.0,
                        longitude=0.0,
                    )
                )
                new_offers += 1
            except Exception as exc:
                print(f"⚠️ Fehlerhaftes Gewobag-Angebot übersprungen ({type(exc).__name__}).")

        print(f"   → Neue Angebote: {new_offers}")

        if new_offers == 0:
            print("🏁 Keine neuen Angebote mehr gefunden.")
            break

        page += 1

    print(f"✅ Gewobag: {len(offers)} eindeutige Angebote gefunden")

    return offers
