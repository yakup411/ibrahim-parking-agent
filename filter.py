import json
import math
import os
import tempfile
from pathlib import Path

from geopy.distance import geodesic
from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

CACHE_FILE = Path("data/coordinates_cache.json")
geolocator = Nominatim(user_agent="ibrahim-parking-agent", timeout=10)
_rate_limited_geocode = RateLimiter(
    geolocator.geocode,
    min_delay_seconds=1,
    max_retries=2,
    error_wait_seconds=2,
    swallow_exceptions=False,
)


def _valid_coordinates(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return False
    try:
        latitude, longitude = (float(part) for part in value)
    except (OverflowError, TypeError, ValueError):
        return False
    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def load_cache():
    if not CACHE_FILE.exists():
        return {}
    try:
        content = CACHE_FILE.read_text(encoding="utf-8")
        if not content.strip():
            print("⚠️ Koordinaten-Cache ist leer; starte mit leerem Cache.")
            return {}
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("cache root must be an object")
        valid = {
            address: [float(pair[0]), float(pair[1])]
            for address, pair in data.items()
            if isinstance(address, str) and address.strip() and _valid_coordinates(pair)
        }
        if len(valid) != len(data):
            print("⚠️ Ungültige Cache-Einträge wurden ignoriert.")
        return valid
    except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
        print(f"⚠️ Koordinaten-Cache nicht lesbar ({type(exc).__name__}); nutze leeren Cache.")
        return {}


def save_cache(cache):
    temp_name = None
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        valid = {
            address: [float(pair[0]), float(pair[1])]
            for address, pair in cache.items()
            if isinstance(address, str) and address.strip() and _valid_coordinates(pair)
        }
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=CACHE_FILE.parent, delete=False
        ) as file:
            temp_name = file.name
            json.dump(valid, file, ensure_ascii=False, indent=4)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_name, CACHE_FILE)
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        if temp_name and os.path.exists(temp_name):
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        print(f"⚠️ Koordinaten-Cache konnte nicht gespeichert werden ({type(exc).__name__}).")


coordinate_cache = load_cache()


def get_coordinates(address):
    if not isinstance(address, str) or not address.strip():
        return None
    address = address.strip()
    cached = coordinate_cache.get(address)
    if _valid_coordinates(cached):
        print(f"💾 Cache: {address}")
        return tuple(cached)
    coordinate_cache.pop(address, None)

    print(f"🌍 Geocodiere: {address}")
    try:
        location = _rate_limited_geocode(address)
    except GeocoderServiceError as exc:
        print(f"⚠️ Geocoding momentan nicht verfügbar ({type(exc).__name__}).")
        return None
    except Exception as exc:
        print(f"⚠️ Unerwarteter Geocoding-Fehler ({type(exc).__name__}).")
        return None

    if location is None:
        print("❌ Adresse konnte nicht gefunden werden.")
        return None

    coordinates = (location.latitude, location.longitude)
    if not _valid_coordinates(coordinates):
        print("⚠️ Geocoding lieferte ungültige Koordinaten.")
        return None

    coordinate_cache[address] = coordinates
    save_cache(coordinate_cache)
    print("✅ Koordinaten gespeichert.")
    return coordinates


def is_within_radius(search_coordinates, offer_address, radius_km, offer_coordinates=None):
    if not _valid_coordinates(search_coordinates) or radius_km < 0:
        raise ValueError("Search coordinates or radius are invalid")
    if not _valid_coordinates(offer_coordinates):
        offer_coordinates = get_coordinates(offer_address)
    if offer_coordinates is None:
        return False, None
    try:
        distance = geodesic(search_coordinates, offer_coordinates).kilometers
    except (TypeError, ValueError):
        return False, None
    return distance <= radius_km, distance
