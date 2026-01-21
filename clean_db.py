from sqlalchemy import text
from app.core.database import engine


def clean_history():
    print("🧹 Bereinige Datenbank-Verlauf...")
    with engine.connect() as con:
        # 1. Zuerst Favoriten löschen (wegen Fremdschlüssel-Abhängigkeit)
        try:
            con.execute(text("DELETE FROM favorites"))
            print("✅ Favoriten gelöscht.")
        except Exception as e:
            print(f"ℹ️ Favoriten waren leer oder Fehler: {e}")

        # 2. Verlauf der gesendeten Nachrichten löschen
        con.execute(text("DELETE FROM sent_listings"))
        print("✅ Sendeverlauf gelöscht.")

        # 3. Immobilien-Cache löschen
        con.execute(text("DELETE FROM immobilien"))
        print("✅ Immobilien-Cache gelöscht.")

        con.commit()

    print("\n🎉 Alles sauber! Der Bot wird beim nächsten Start alle 5 Wohnungen erneut senden.")


if __name__ == "__main__":
    clean_history()