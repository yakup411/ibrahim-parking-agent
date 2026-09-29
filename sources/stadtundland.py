from http_client import source_session
from offer import Offer

API_URL = "https://d2396ha8oiavw0.cloudfront.net/sul-main/immoSearch"

HEADERS = {
    "Content-Type": "application/json"
}


def format_address(address):
    if isinstance(address, dict):
        street = address.get("street", "")
        house_number = address.get("house_number", "")
        postal_code = address.get("postal_code", "")
        city = address.get("city", "")

        return f"{street} {house_number}, {postal_code} {city}".strip()

    return address or ""


def get_offers():
    all_offers = []
    offset = 0

    while True:
        response = source_session.post(
            API_URL,
            json={
                "offset": offset,
                "cat": "parken"
            },
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        offers = result.get("data")
        if not isinstance(offers, list):
            raise ValueError("STADT UND LAND returned an invalid offers list")

        if not offers:
            break

        for offer in offers:
            try:
                if not isinstance(offer, dict):
                    raise ValueError("offer is not an object")
                all_offers.append(
                    Offer(
                        source="STADT UND LAND",
                        title=str(offer.get("title") or ""),
                        address=format_address(offer.get("address")),
                        price=str(offer.get("rent") or ""),
                        link=str(offer.get("url") or ""),
                        latitude=float(offer.get("latitude") or 0.0),
                        longitude=float(offer.get("longitude") or 0.0),
                    )
                )
            except (AttributeError, OverflowError, TypeError, ValueError) as exc:
                print(f"⚠️ Fehlerhaftes STADT-UND-LAND-Angebot übersprungen ({type(exc).__name__}).")

        count = result.get("count")
        if isinstance(count, int) and len(all_offers) >= count:
            break

        offset += len(offers)

    return all_offers
