from config import (
    SEARCH_ADDRESS,
    SEARCH_LATITUDE,
    SEARCH_LONGITUDE,
    SEARCH_RADIUS_KM,
)
from filter import is_within_radius
from database import (
    load_known_offers,
    save_known_offers,
    get_new_offers,
)
from source_manager import get_all_offers
from telegram_bot import send_telegram_message


def main():
    print("=" * 50)
    print("🚗 Ibrahim Parking Agent")
    print("=" * 50)

    print(f"📍 Suchadresse: {SEARCH_ADDRESS}")
    print(f"📏 Radius: {SEARCH_RADIUS_KM} km")

    search_coordinates = (
        SEARCH_LATITUDE,
        SEARCH_LONGITUDE,
    )

    offers = get_all_offers()

    print(f"📦 Insgesamt gefunden: {len(offers)} Angebote")

    known_offers = load_known_offers()
    print(f"💾 Bekannte Angebote: {len(known_offers)}")

    # ======= ERSTER START =======
    if len(known_offers) == 0:
        print("🆕 Erster Start erkannt.")
        print("💾 Speichere alle aktuellen Angebote als bekannt.")
        print("📨 Es werden keine Telegram-Nachrichten versendet.")

        save_known_offers(offers)

        print("✅ Initialisierung abgeschlossen.")
        return
    # ============================

    new_offers = get_new_offers(offers)
    print(f"🆕 Neue Angebote: {len(new_offers)}")

    filtered_offers = []

    for offer in new_offers:

        offer_coordinates = None

        if offer.latitude != 0.0 and offer.longitude != 0.0:
            offer_coordinates = (
                offer.latitude,
                offer.longitude,
            )

        inside, distance = is_within_radius(
            search_coordinates=search_coordinates,
            offer_address=offer.address,
            radius_km=SEARCH_RADIUS_KM,
            offer_coordinates=offer_coordinates,
        )

        if inside:
            filtered_offers.append((offer, distance))
            print(f"✅ {distance:.2f} km | {offer.address}")

    print(f"📍 Neue Angebote im Radius: {len(filtered_offers)}")

    for offer, distance in filtered_offers:
        message = (
            "🅿️ Neues Parkplatzangebot gefunden!\n\n"
            f"🏢 Anbieter: {offer.source}\n"
            f"📌 Titel: {offer.title}\n"
            f"📍 Adresse: {offer.address}\n"
            f"📏 Entfernung: {distance:.2f} km\n"
            f"💶 Preis: {offer.price}\n"
            f"🔗 {offer.link}"
        )

        send_telegram_message(message)
        print(f"📨 Telegram gesendet: {offer.address}")

    save_known_offers(offers)

    print("✅ Datenbank aktualisiert")


if __name__ == "__main__":
    main()