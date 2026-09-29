import hashlib
import json
import os
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DATABASE_FILE = Path("data/known_offers.json")


class DatabaseError(RuntimeError):
    """Raised when the known-offers file cannot be trusted or saved."""


def _value(offer, name, default=""):
    if isinstance(offer, dict):
        return offer.get(name, default)
    return getattr(offer, name, default)


def offer_key(offer):
    """Return a stable identity, using offer details when no link is present."""
    source = str(_value(offer, "source")).strip().casefold()
    link = str(_value(offer, "link")).strip()

    if link:
        parts = urlsplit(link)
        normalized_link = urlunsplit(
            (parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), parts.query, "")
        )
        return f"link:{normalized_link}"

    details = (
        " ".join(str(_value(offer, "address")).split()).casefold(),
        " ".join(str(_value(offer, "title")).split()).casefold(),
        " ".join(str(_value(offer, "price")).split()).casefold(),
    )
    if not any(details):
        return None
    identity = "\x1f".join((source, *details))
    return "fallback:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def load_known_offers():
    if not DATABASE_FILE.exists():
        return []

    try:
        content = DATABASE_FILE.read_text(encoding="utf-8")
        if not content.strip():
            raise DatabaseError("Known-offers database is empty; refusing to initialize over it.")
        records = json.loads(content)
        if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
            raise DatabaseError("Known-offers database has an unexpected structure.")
        if not records:
            raise DatabaseError("Known-offers database contains no records; refusing a false first start.")
        return records
    except (json.JSONDecodeError, OSError) as exc:
        raise DatabaseError("Known-offers database is unreadable; refusing to overwrite it.") from exc


def get_new_offers(offers, known_offers=None):
    if known_offers is None:
        known_offers = load_known_offers()
    known_keys = {key for offer in known_offers if (key := offer_key(offer)) is not None}
    return [offer for offer in offers if offer_key(offer) is None or offer_key(offer) not in known_keys]


def save_known_offers(offers):
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    records = [asdict(offer) if is_dataclass(offer) else dict(offer) for offer in offers]
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=DATABASE_FILE.parent, delete=False
        ) as file:
            temp_name = file.name
            json.dump(records, file, ensure_ascii=False, indent=4)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_name, DATABASE_FILE)
    except (OSError, TypeError, ValueError) as exc:
        if temp_name and os.path.exists(temp_name):
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        raise DatabaseError("Could not safely save known offers.") from exc
