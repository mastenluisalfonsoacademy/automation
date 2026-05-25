import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from google_services import (
    format_event,
    get_today_events,
    get_unread_emails,
    get_urgent_emails,
    get_week_events,
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def is_authorized(update: Update) -> bool:
    """Nur autorisierte Chat-ID darf den Bot nutzen."""
    return update.message.chat_id == TELEGRAM_CHAT_ID


def format_sender(from_str: str) -> str:
    """Extrahiert den Namen aus einer E-Mail-Absenderadresse."""
    if "<" in from_str:
        return from_str.split("<")[0].strip().strip('"')
    return from_str


def esc(text: str) -> str:
    """Escaped Markdown-Sonderzeichen in Nutzerinhalten."""
    for char in ["*", "_", "`", "[", "]"]:
        text = text.replace(char, f"\\{char}")
    return text


# ── Commands ──────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "👋 *Google Assistant Bot*\n\n"
        "Was kann ich für dich tun?\n\n"
        "/heute — Heutige Kalender-Termine\n"
        "/woche — Termine diese Woche\n"
        "/mails — Neueste ungelesene E-Mails\n"
        "/dringend — Dringende E-Mails",
        parse_mode="Markdown",
    )


async def cmd_heute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("📅 Lade heutige Termine…")
    try:
        events = get_today_events()
        if not events:
            await update.message.reply_text("✅ Heute keine Termine!")
            return

        today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%A, %d. %B %Y")
        lines = [f"📅 *{today}*\n"]
        lines += [format_event(e) for e in events]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"/heute Fehler: {e}")
        await update.message.reply_text(f"❌ Fehler beim Laden der Termine:\n{e}")


async def cmd_woche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("📅 Lade Wochentermine…")
    try:
        events = get_week_events()
        if not events:
            await update.message.reply_text("✅ Diese Woche keine Termine!")
            return

        lines = ["📅 *Termine diese Woche*\n"]
        current_day = None
        for event in events:
            start = event.get("start", {})
            if "dateTime" in start:
                dt = datetime.fromisoformat(start["dateTime"]).astimezone(ZoneInfo(TIMEZONE))
            else:
                dt = datetime.fromisoformat(start["date"])
            day = dt.strftime("%A, %d. %B")
            if day != current_day:
                current_day = day
                lines.append(f"\n*{day}*")
            lines.append(format_event(event))

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"/woche Fehler: {e}")
        await update.message.reply_text(f"❌ Fehler beim Laden der Termine:\n{e}")


async def cmd_mails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("📧 Lade E-Mails…")
    try:
        emails = get_unread_emails(5)
        if not emails:
            await update.message.reply_text("✅ Keine ungelesenen E-Mails!")
            return

        lines = [f"📧 Ungelesene E-Mails\n"]
        for i, mail in enumerate(emails, 1):
            lines.append(f"{i}. {mail['subject']}")
            lines.append(f"Von: {format_sender(mail['from'])}")
            snippet = mail["snippet"][:120] + "…" if len(mail["snippet"]) > 120 else mail["snippet"]
            lines.append(f"{snippet}\n")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.error(f"/mails Fehler: {e}")
        await update.message.reply_text(f"❌ Fehler beim Laden der E-Mails:\n{e}")


async def cmd_dringend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("🚨 Suche dringende E-Mails…")
    try:
        emails = get_urgent_emails()
        if not emails:
            await update.message.reply_text("✅ Keine dringenden E-Mails gefunden!")
            return

        lines = [f"🚨 Dringende E-Mails ({len(emails)})\n"]
        for i, mail in enumerate(emails, 1):
            lines.append(f"{i}. {mail['subject']}")
            lines.append(f"Von: {format_sender(mail['from'])}")
            snippet = mail["snippet"][:120] + "…" if len(mail["snippet"]) > 120 else mail["snippet"]
            lines.append(f"{snippet}\n")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.error(f"/dringend Fehler: {e}")
        await update.message.reply_text(f"❌ Fehler beim Laden der E-Mails:\n{e}")


def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN fehlt in .env!")
    if not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID fehlt in .env!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("heute", cmd_heute))
    app.add_handler(CommandHandler("woche", cmd_woche))
    app.add_handler(CommandHandler("mails", cmd_mails))
    app.add_handler(CommandHandler("dringend", cmd_dringend))

    logger.info("Google Assistant Bot gestartet!")
    app.run_polling()


if __name__ == "__main__":
    main()
