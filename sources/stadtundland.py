import requests

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
        response = requests.post(
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

        offers = result["data"]

        if not offers:
            break

        for offer in offers:
            all_offers.append(
                Offer(
                    source="STADT UND LAND",
                    title=offer.get("title", ""),
                    address=format_address(offer.get("address")),
                    price=offer.get("rent", ""),
                    link=offer.get("url", ""),
                    latitude=float(offer.get("latitude") or 0.0),
                    longitude=float(offer.get("longitude") or 0.0),
                )
            )

        if len(all_offers) >= result["count"]:
            break

        offset += len(offers)

    return all_offers