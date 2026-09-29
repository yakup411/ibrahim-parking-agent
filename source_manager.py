from sources.stadtundland import get_offers as get_stadtundland_offers
from sources.gewobag import get_offers as get_gewobag_offers


def get_all_offers():
    offers = []
    source_errors = []

    for source_name, fetch_offers in (
        ("STADT UND LAND", get_stadtundland_offers),
        ("Gewobag", get_gewobag_offers),
    ):
        print(f"🔍 Prüfe {source_name}...")
        try:
            offers.extend(fetch_offers())
        except Exception as exc:
            source_errors.append((source_name, exc))
            print(f"⚠️ {source_name} ist fehlgeschlagen ({type(exc).__name__}).")

    if source_errors and not offers:
        raise RuntimeError("All offer sources failed; preserving the current database.") from source_errors[0][1]

    return offers
