#!/usr/bin/env python3
"""
Automatischer E-Mail-Agent für mastenluisalfonso.academy@gmail.com
Läuft als Railway Cron Job — jeden Werktag um 06:00 Uhr.
"""

import base64
import json
import logging
import os
import re
from email.mime.text import MIMEText

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

MY_EMAIL = "mastenluisalfonso.academy@gmail.com"

# ── Kategorisierung ────────────────────────────────────────────

CATEGORIES = {
    "kuendigung": {
        "keywords": [
            "kündigen", "kündigung", "stornieren", "storno", "widerruf", "widerrufen",
            "rückerstattung", "geld zurück", "abmelden", "abmeldung", "cancel", "refund",
            "zurückbuchen", "rücktritt",
        ],
        "action": "send",
        "subject_prefix": "Re:",
        "template": """\
Hi {Name},

natürlich, kein Problem — ich kümmere mich darum.

Ich storniere deine Buchung und veranlasse die Rückerstattung. Der Betrag ist in der Regel innerhalb von 5–7 Werktagen zurück auf deinem Konto.

Falls du mir kurz mitteilen möchtest, was nicht gepasst hat — ich freue mich über jedes Feedback, auch wenn es kritisch ist. Wir lernen daraus.

Liebe Grüße
Luis Alfonso""",
    },
    "login": {
        "keywords": [
            "zugang", "login", "passwort", "password", "einloggen", "anmelden",
            "kann nicht", "zugriff", "link funktioniert nicht", "konto", "account",
            "vergessen", "reset", "freischalten", "aktivieren",
        ],
        "action": "send",
        "subject_prefix": "Re:",
        "template": """\
Hi {Name},

kein Problem, das kriegen wir hin!

Bitte geh auf die Login-Seite und klicke auf "Passwort vergessen" — du bekommst dann sofort eine E-Mail mit einem neuen Zugangslink.

Falls du weiterhin Probleme hast, antworte einfach auf diese Mail und ich schaue es mir direkt an.

Liebe Grüße
Luis Alfonso""",
    },
    "aria": {
        "keywords": [
            "aria", "ki", "künstliche intelligenz", "artificial intelligence",
            "wie funktioniert", "was kann", "erklär mir", "assistent", "chatbot",
            "ki-assistent", "tool",
        ],
        "action": "draft",
        "subject_prefix": "Re:",
        "template": """\
Hi {Name},

danke für deine Frage zu ARIA!

[HIER ANTWORT EINFÜGEN — bitte vor dem Senden prüfen]

Liebe Grüße
Luis Alfonso""",
    },
    "webinar": {
        "keywords": [
            "webinar", "termin", "wann", "aufzeichnung", "verpasst", "nächste session",
            "online-kurs", "zoom", "meeting", "live", "session", "kurs",
        ],
        "action": "draft",
        "subject_prefix": "Re:",
        "template": """\
Hi {Name},

danke für deine Nachricht!

[WEBINAR-LINK UND TERMINE HIER EINFÜGEN — bitte vor dem Senden prüfen]

Liebe Grüße
Luis Alfonso""",
    },
}

IGNORE_PATTERNS = [
    r"noreply@", r"no-reply@", r"donotreply@", r"do-not-reply@",
    r"notifications?@", r"mailer@", r"bounce@", r"postmaster@",
    r"thrivecart", r"samcart", r"stripe", r"paypal", r"digistore",
    r"newsletter", r"marketing", r"info@.*\.(com|de|io)$",
]

# ── Google Auth ────────────────────────────────────────────────

def get_credentials():
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


def get_gmail():
    return build("gmail", "v1", credentials=get_credentials())

# ── Hilfsfunktionen ───────────────────────────────────────────

def get_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def extract_first_name(from_str: str) -> str:
    if "<" in from_str:
        name_part = from_str.split("<")[0].strip().strip('"')
    else:
        name_part = from_str.split("@")[0]
    first = name_part.split()[0] if name_part.split() else name_part
    return first.capitalize() if first else "du"


def decode_body(payload: dict) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def should_ignore(from_str: str, subject: str) -> bool:
    from_lower = from_str.lower()
    for pattern in IGNORE_PATTERNS:
        if re.search(pattern, from_lower):
            return True
    # Keine echte Person → ignorieren
    if not any(c.isalpha() for c in from_str.split("<")[0]):
        return True
    return False


def categorize(subject: str, body: str, snippet: str) -> str | None:
    text = (subject + " " + body + " " + snippet).lower()
    for category, config in CATEGORIES.items():
        for keyword in config["keywords"]:
            if keyword in text:
                return category
    return "unbekannt"


def make_reply_message(to: str, subject: str, body: str, thread_id: str = "", original_msg_id: str = "") -> dict:
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["From"] = MY_EMAIL
    msg["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"
    if original_msg_id:
        msg["In-Reply-To"] = original_msg_id
        msg["References"] = original_msg_id
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = {"raw": raw}
    if thread_id:
        result["threadId"] = thread_id
    return result

# ── Hauptlogik ────────────────────────────────────────────────

def run():
    logger.info("=== E-Mail-Agent gestartet ===")
    service = get_gmail()

    # Ungelesene E-Mails abrufen
    result = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        maxResults=50,
    ).execute()

    messages = result.get("messages", [])
    if not messages:
        logger.info("Keine ungelesenen E-Mails. Fertig.")
        return

    logger.info(f"{len(messages)} ungelesene E-Mail(s) gefunden.")

    stats = {
        "gesendet_kuendigung": 0,
        "gesendet_login": 0,
        "entwurf_aria": 0,
        "entwurf_webinar": 0,
        "entwurf_pruefen": 0,
        "ignoriert": 0,
        "fehler": 0,
    }

    for msg_ref in messages:
        msg_id = msg_ref["id"]
        try:
            detail = service.users().messages().get(
                userId="me", id=msg_id, format="full",
            ).execute()

            headers = detail.get("payload", {}).get("headers", [])
            from_str = get_header(headers, "From")
            subject = get_header(headers, "Subject") or "(kein Betreff)"
            original_msg_id = get_header(headers, "Message-ID")
            thread_id = detail.get("threadId", "")
            snippet = detail.get("snippet", "")
            body = decode_body(detail.get("payload", {}))
            first_name = extract_first_name(from_str)

            logger.info(f"Verarbeite: '{subject}' von {from_str}")

            # Ignorieren?
            if should_ignore(from_str, subject):
                logger.info(f"  → Ignoriert (System/Newsletter)")
                stats["ignoriert"] += 1
                continue

            # Kategorisieren
            category = categorize(subject, body, snippet)
            config = CATEGORIES.get(category)

            if config:
                reply_body = config["template"].replace("{Name}", first_name)
                reply_subject = f"Re: {subject}"

                if config["action"] == "send":
                    # Sofort antworten
                    message = make_reply_message(
                        to=from_str,
                        subject=reply_subject,
                        body=reply_body,
                        thread_id=thread_id,
                        original_msg_id=original_msg_id,
                    )
                    service.users().messages().send(userId="me", body=message).execute()
                    logger.info(f"  → Gesendet ({category})")
                    if category == "kuendigung":
                        stats["gesendet_kuendigung"] += 1
                    else:
                        stats["gesendet_login"] += 1

                else:  # draft
                    msg = MIMEText(reply_body, "plain", "utf-8")
                    msg["To"] = from_str
                    msg["From"] = MY_EMAIL
                    msg["Subject"] = reply_subject
                    if original_msg_id:
                        msg["In-Reply-To"] = original_msg_id
                        msg["References"] = original_msg_id
                    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
                    draft_body = {"message": {"raw": raw, "threadId": thread_id}}
                    service.users().drafts().create(userId="me", body=draft_body).execute()
                    logger.info(f"  → Entwurf erstellt ({category})")
                    if category == "aria":
                        stats["entwurf_aria"] += 1
                    else:
                        stats["entwurf_webinar"] += 1

            else:
                # Unbekannt → Entwurf mit [PRÜFEN]
                template = (
                    f"Hi {first_name},\n\n"
                    "vielen Dank für deine Nachricht!\n\n"
                    "[HIER INDIVIDUELL ANTWORTEN — bitte vor dem Senden prüfen]\n\n"
                    "Liebe Grüße\nLuis Alfonso"
                )
                msg = MIMEText(template, "plain", "utf-8")
                msg["To"] = from_str
                msg["From"] = MY_EMAIL
                msg["Subject"] = f"[PRÜFEN] Re: {subject}"
                if original_msg_id:
                    msg["In-Reply-To"] = original_msg_id
                    msg["References"] = original_msg_id
                raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
                draft_body = {"message": {"raw": raw, "threadId": thread_id}}
                service.users().drafts().create(userId="me", body=draft_body).execute()
                logger.info(f"  → Entwurf [PRÜFEN] erstellt")
                stats["entwurf_pruefen"] += 1

            # Als gelesen markieren
            service.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()

        except Exception as e:
            logger.error(f"  ✗ Fehler bei Nachricht {msg_id}: {e}")
            stats["fehler"] += 1

    # Abschlussbericht
    logger.info("=== Zusammenfassung ===")
    logger.info(f"Gesendet (Kündigung):     {stats['gesendet_kuendigung']}")
    logger.info(f"Gesendet (Login):          {stats['gesendet_login']}")
    logger.info(f"Entwurf (ARIA):            {stats['entwurf_aria']}")
    logger.info(f"Entwurf (Webinar):         {stats['entwurf_webinar']}")
    logger.info(f"Entwurf ([PRÜFEN]):        {stats['entwurf_pruefen']}")
    logger.info(f"Ignoriert:                 {stats['ignoriert']}")
    logger.info(f"Fehler:                    {stats['fehler']}")
    logger.info("=== Fertig ===")


if __name__ == "__main__":
    run()
