"""
Dieses Skript einmalig lokal ausführen — es öffnet deinen Browser für die
Google-Anmeldung und gibt danach die 3 Werte aus, die du in Railway brauchst.

Aufruf:
    python setup_auth.py
"""
import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

CREDS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google-credentials.json")


def main():
    if not Path(CREDS_FILE).exists():
        print(f"\n❌ Datei nicht gefunden: {CREDS_FILE}")
        print("→ Bitte die google-credentials.json aus Google Cloud in diesen Ordner legen.")
        return

    print("\n🔑 Browser öffnet sich — bitte Google-Konto auswählen und alle Berechtigungen erlauben.\n")

    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("✅ Authentifizierung erfolgreich!")
    print("=" * 60)
    print("\nTrage diese 3 Werte in Railway als Environment-Variablen ein:\n")
    print(f"  GOOGLE_CLIENT_ID     = {creds.client_id}")
    print(f"  GOOGLE_CLIENT_SECRET = {creds.client_secret}")
    print(f"  GOOGLE_REFRESH_TOKEN = {creds.refresh_token}")
    print("\n" + "=" * 60)

    # Auch lokal speichern
    token_data = {
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "refresh_token": creds.refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    with open("token.json", "w") as f:
        json.dump(token_data, f, indent=2)

    print("\n📁 Werte wurden auch in token.json gespeichert.")
    print("⚠️  ACHTUNG: token.json und google-credentials.json NIEMALS auf GitHub hochladen!\n")


if __name__ == "__main__":
    main()
