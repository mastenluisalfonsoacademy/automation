"""
One-shot Instagram check — wird von Railway Cron täglich ausgeführt.
Prüft alle Accounts, schickt Telegram-Nachrichten für neue Beiträge und beendet sich.
"""
import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Bot

from instagram import check_new_posts_for_all

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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


def esc(text: str) -> str:
    """Escaped HTML-Sonderzeichen für sicheres Telegram-HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def main():
    logger.info("Instagram-Check gestartet...")
    bot = Bot(token=TELEGRAM_TOKEN)
    results = check_new_posts_for_all(INSTAGRAM_ACCOUNTS)
    found_any = False

    for account, posts in results.items():
        if not posts:
            continue
        found_any = True

        lines = [f"📸 <b>Neue Beiträge von @{esc(account)}</b>\n"]
        for post in posts:
            icon = "🎥" if post["is_video"] else "🖼"
            lines.append(f"{icon} <i>{esc(post['date'])}</i>")
            if post["caption"]:
                preview = post["caption"][:150]
                if len(post["caption"]) > 150:
                    preview += "…"
                lines.append(esc(preview))
            lines.append(f"🔗 {post['url']}\n")

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="\n".join(lines),
            parse_mode="HTML",
            disable_web_page_preview=False,
        )
        logger.info(f"@{account}: Nachricht gesendet ({len(posts)} Beitrag/Beiträge)")

    if not found_any:
        logger.info("Keine neuen Beiträge gefunden.")

    logger.info("Check abgeschlossen.")


if __name__ == "__main__":
    asyncio.run(main())
