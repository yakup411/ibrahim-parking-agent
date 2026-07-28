import json
import time
from pathlib import Path

from geopy.distance import geodesic
from geopy.exc import (
    GeocoderRateLimited,
    GeocoderTimedOut,
    GeocoderUnavailable,
)
from geopy.geocoders import Nominatim

CACHE_FILE = Path("data/coordinates_cache.json")

geolocator = Nominatim(
    user_agent="ibrahim-parking-agent",
    timeout=10,
)


def load_cache():
    if not CACHE_FILE.exists():
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            content = file.read().strip()

            if not content:
                return {}

            return json.loads(content)

    except (json.JSONDecodeError, OSError):
        print("⚠️ Cache-Datei ist leer oder ungültig. Neuer Cache wird erstellt.")
        return {}


def save_cache(cache):
    CACHE_FILE.parent.mkdir(exist_ok=True)

    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            cache,
            file,
            ensure_ascii=False,
            indent=4,
        )


coordinate_cache = load_cache()


def get_coordinates(address):
    if not address:
        return None

    if address in coordinate_cache:
        print(f"💾 Cache: {address}")

        latitude, longitude = coordinate_cache[address]

        return (
            latitude,
            longitude,
        )

    print(f"🌍 Geocodiere: {address}")

    try:
        location = geolocator.geocode(address)

        time.sleep(1)

        if location is None:
            print("❌ Adresse konnte nicht gefunden werden.")
            return None

        coordinate_cache[address] = (
            location.latitude,
            location.longitude,
        )

        save_cache(coordinate_cache)

        print("✅ Koordinaten gespeichert.")

        return (
            location.latitude,
            location.longitude,
        )

    except (
        GeocoderUnavailable,
        GeocoderTimedOut,
        GeocoderRateLimited,
    ):
        print("⚠️ Geocoding momentan nicht verfügbar.")

        return None


def is_within_radius(
    search_coordinates,
    offer_address,
    radius_km,
    offer_coordinates=None,
):
    if offer_coordinates is not None:
        distance = geodesic(
            search_coordinates,
            offer_coordinates,
        ).kilometers

        return (
            distance <= radius_km,
            distance,
        )

    offer_coordinates = get_coordinates(
        offer_address,
    )

    if offer_coordinates is None:
        return (
            False,
            None,
        )

    distance = geodesic(
        search_coordinates,
        offer_coordinates,
    ).kilometers

    return (
        distance <= radius_km,
        distance,
    )