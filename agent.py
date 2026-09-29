from config import SEARCH_ADDRESS, SEARCH_LATITUDE, SEARCH_LONGITUDE, SEARCH_RADIUS_KM
from database import DatabaseError, get_new_offers, load_known_offers, offer_key, save_known_offers
from filter import is_within_radius
from source_manager import get_all_offers
from telegram_bot import send_telegram_message


def _message_for(offer, distance):
    return (
        "🅿️ Neues Parkplatzangebot gefunden!\n\n"
        f"🏢 Anbieter: {offer.source}\n"
        f"📌 Titel: {offer.title}\n"
        f"📍 Adresse: {offer.address}\n"
        f"📏 Entfernung: {distance:.2f} km\n"
        f"💶 Preis: {offer.price}\n"
        f"🔗 {offer.link}"
    )


def main():
    print("=" * 50)
    print("🚗 Ibrahim Parking Agent")
    print("=" * 50)
    print(f"📍 Suchadresse: {SEARCH_ADDRESS}")
    print(f"📏 Radius: {SEARCH_RADIUS_KM} km")

    try:
        known_offers = load_known_offers()
    except DatabaseError as exc:
        print(f"❌ {exc}")
        return

    try:
        offers = get_all_offers()
    except Exception as exc:
        print(f"❌ Keine Angebotsquelle verfügbar ({type(exc).__name__}); Datenbank bleibt unverändert.")
        return

    print(f"📦 Insgesamt gefunden: {len(offers)} Angebote")
    print(f"💾 Bekannte Angebote: {len(known_offers)}")

    if not known_offers:
        print("🆕 Erster Start erkannt.")
        print("💾 Speichere aktuelle Angebote als bekannt; es werden keine Telegram-Nachrichten versendet.")
        try:
            save_known_offers(offers)
        except DatabaseError as exc:
            print(f"❌ {exc}")
            return
        print("✅ Initialisierung abgeschlossen.")
        return

    new_offers = get_new_offers(offers, known_offers)
    print(f"🆕 Neue Angebote: {len(new_offers)}")
    known_keys = {offer_key(offer) for offer in known_offers}

    for offer in new_offers:
        try:
            key = offer_key(offer)
            if key is None:
                print("⚠️ Angebot ohne ausreichende Identitätsdaten übersprungen; wird erneut geprüft.")
                continue
            if key in known_keys:
                continue
            coordinates = None
            if offer.latitude != 0.0 and offer.longitude != 0.0:
                coordinates = (offer.latitude, offer.longitude)

            inside, distance = is_within_radius(
                search_coordinates=(SEARCH_LATITUDE, SEARCH_LONGITUDE),
                offer_address=offer.address,
                radius_km=SEARCH_RADIUS_KM,
                offer_coordinates=coordinates,
            )
            if distance is None:
                print(f"⚠️ Angebot bleibt ungeprüft und wird später erneut geprüft: {offer.address}")
                continue

            if inside:
                print(f"✅ {distance:.2f} km | {offer.address}")
                try:
                    send_telegram_message(_message_for(offer, distance))
                except Exception as exc:
                    print(f"⚠️ Telegram-Versand fehlgeschlagen; Angebot bleibt offen ({type(exc).__name__}).")
                    continue
                print(f"📨 Telegram gesendet: {offer.address}")

            if key is None or key in known_keys:
                continue
            known_offers.append(offer)
            try:
                save_known_offers(known_offers)
            except DatabaseError:
                known_offers.pop()
                raise
            known_keys.add(key)
        except DatabaseError as exc:
            print(f"❌ {exc}")
            return
        except Exception as exc:
            print(f"⚠️ Fehlerhaftes Angebot übersprungen ({type(exc).__name__}); wird erneut geprüft.")

    print("✅ Datenbank aktualisiert")


if __name__ == "__main__":
    main()
