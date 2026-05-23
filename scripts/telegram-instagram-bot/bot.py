import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from instagram import check_new_posts_for_all, load_state

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_HOUR = int(os.getenv("CHECK_HOUR", "9"))
CHECK_MINUTE = int(os.getenv("CHECK_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")

INSTAGRAM_ACCOUNTS = [
    "juliatrost.official",
    "wright_mode",
    "dawidprzybylski_official",
    "moritz.maaker",
]

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def run_check(bot):
    """Alle Accounts prüfen und neue Beiträge per Telegram melden."""
    logger.info("Instagram-Check gestartet...")
    results = check_new_posts_for_all(INSTAGRAM_ACCOUNTS)
    found_any = False

    for account, posts in results.items():
        if not posts:
            continue
        found_any = True

        lines = [f"📸 *Neue Beiträge von @{account}*\n"]
        for post in posts:
            icon = "🎥" if post["is_video"] else "🖼"
            lines.append(f"{icon} _{post['date']}_")
            if post["caption"]:
                preview = post["caption"][:150]
                if len(post["caption"]) > 150:
                    preview += "…"
                preview = preview.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
                lines.append(preview)
            lines.append(f"🔗 {post['url']}\n")

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="\n".join(lines),
            parse_mode="Markdown",
            disable_web_page_preview=False,
        )

    if not found_any:
        logger.info("Keine neuen Beiträge gefunden.")


async def scheduled_check(context: ContextTypes.DEFAULT_TYPE):
    await run_check(context.bot)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accounts_list = "\n".join(f"• @{a}" for a in INSTAGRAM_ACCOUNTS)
    await update.message.reply_text(
        f"👋 *Instagram Monitor Bot*\n\n"
        f"Überwachte Accounts:\n{accounts_list}\n\n"
        f"⏰ Tägliche Überprüfung: {CHECK_HOUR:02d}:{CHECK_MINUTE:02d} Uhr ({TIMEZONE})\n\n"
        f"Befehle:\n"
        f"/check — Sofortige manuelle Überprüfung\n"
        f"/status — Letzte bekannte Beiträge je Account",
        parse_mode="Markdown",
    )


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Überprüfe Instagram-Accounts via Apify…")
    await run_check(context.bot)
    await update.message.reply_text("✅ Fertig!")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    lines = ["📊 *Status — Letzte gespeicherte Beiträge*\n"]
    for account in INSTAGRAM_ACCOUNTS:
        if account in state:
            shortcode = state[account].get("last_post_shortcode", "?")
            url = f"https://www.instagram.com/p/{shortcode}/"
            lines.append(f"@{account}: {url}")
        else:
            lines.append(f"@{account}: _noch nicht überprüft_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN fehlt in .env!")
    if not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID fehlt in .env!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("status", cmd_status))

    app.job_queue.run_daily(
        scheduled_check,
        time=time(hour=CHECK_HOUR, minute=CHECK_MINUTE, tzinfo=ZoneInfo(TIMEZONE)),
    )

    logger.info(f"Bot gestartet — tägliche Überprüfung um {CHECK_HOUR:02d}:{CHECK_MINUTE:02d} Uhr ({TIMEZONE})")
    app.run_polling()


if __name__ == "__main__":
    main()
