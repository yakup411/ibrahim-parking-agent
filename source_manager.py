from sources.stadtundland import get_offers as get_stadtundland_offers
from sources.gewobag import get_offers as get_gewobag_offers


def get_all_offers():
    offers = []

    print("🔍 Prüfe STADT UND LAND...")
    offers.extend(get_stadtundland_offers())

    offers.extend(get_gewobag_offers())

    return offers