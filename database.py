import json
import os
from dataclasses import asdict

DATABASE_FILE = "data/known_offers.json"


def load_known_offers():
    if not os.path.exists(DATABASE_FILE):
        return []

    with open(DATABASE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_new_offers(offers):
    known_offers = load_known_offers()

    known_links = {
        offer["link"]
        for offer in known_offers
        if "link" in offer
    }

    return [
        offer
        for offer in offers
        if offer.link not in known_links
    ]


def save_known_offers(offers):
    os.makedirs("data", exist_ok=True)

    offers_as_dict = [asdict(offer) for offer in offers]

    with open(DATABASE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            offers_as_dict,
            file,
            ensure_ascii=False,
            indent=4,
        )