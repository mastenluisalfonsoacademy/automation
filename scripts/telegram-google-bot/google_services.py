import os
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")


def get_credentials():
    """Erstellt Google-Zugangsdaten aus Environment-Variablen."""
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES,
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds


# ── Kalender ──────────────────────────────────────────────────

def get_today_events():
    """Holt die Termine von heute."""
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    result = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return result.get("items", [])


def get_week_events():
    """Holt die Termine der nächsten 7 Tage."""
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)

    result = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return result.get("items", [])


def format_event(event: dict) -> str:
    """Formatiert einen Kalender-Termin als Text."""
    start = event.get("start", {})
    if "dateTime" in start:
        dt = datetime.fromisoformat(start["dateTime"]).astimezone(ZoneInfo(TIMEZONE))
        time_str = dt.strftime("%H:%M")
    else:
        time_str = "Ganztägig"

    summary = event.get("summary", "(kein Titel)")
    location = event.get("location", "")
    line = f"🕐 {time_str} — {summary}"
    if location:
        line += f"\n   📍 {location}"
    return line


# ── Gmail ─────────────────────────────────────────────────────

def _get_mail_details(service, msg_id: str) -> dict:
    """Holt Metadaten einer einzelnen E-Mail."""
    msg = service.users().messages().get(
        userId="me",
        id=msg_id,
        format="metadata",
        metadataHeaders=["From", "Subject", "Date"],
    ).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    return {
        "id": msg_id,
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", "(kein Betreff)"),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
    }


def get_unread_emails(max_results: int = 5) -> list:
    """Holt die neuesten ungelesenen E-Mails."""
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    result = service.users().messages().list(
        userId="me", q="is:unread", maxResults=max_results
    ).execute()

    return [_get_mail_details(service, m["id"]) for m in result.get("messages", [])]


def get_urgent_emails(max_results: int = 10) -> list:
    """Holt dringende ungelesene E-Mails anhand von Stichwörtern."""
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    keywords = ["dringend", "urgent", "wichtig", "asap", "sofort", "deadline", "URGENT"]
    query = "is:unread (" + " OR ".join(f"subject:{k}" for k in keywords) + ")"

    result = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    return [_get_mail_details(service, m["id"]) for m in result.get("messages", [])]
