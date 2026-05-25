import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
APIFY_URL = "https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items"


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def fetch_from_apify(usernames: list, results_limit: int = 10) -> dict:
    """Ruft aktuelle Beiträge für alle Accounts via Apify ab. Gibt dict {username: [posts]} zurück."""
    urls = [f"https://www.instagram.com/{u}/" for u in usernames]

    try:
        response = httpx.post(
            APIFY_URL,
            json={
                "directUrls": urls,
                "resultsType": "posts",
                "resultsLimit": results_limit,
            },
            params={"token": APIFY_TOKEN},
            timeout=180.0,
        )
        response.raise_for_status()
        items = response.json()
    except httpx.TimeoutException:
        logger.error("Apify: Timeout — Anfrage hat zu lange gedauert")
        return {}
    except Exception as e:
        logger.error(f"Apify API Fehler: {e}")
        return {}

    # Nach Username gruppieren
    by_username = {}
    for item in items:
        uname = (item.get("ownerUsername") or "").lower()
        by_username.setdefault(uname, []).append(item)

    return by_username


def check_new_posts_for_all(usernames: list) -> dict:
    """
    Überprüft alle Accounts auf neue Beiträge.
    Gibt dict zurück: {username: [neue Beiträge]}
    Beim ersten Lauf eines Accounts wird nur die Baseline gesetzt (leere Liste).
    """
    state = load_state()
    all_posts = fetch_from_apify(usernames)
    results = {}
    state_changed = False

    for username in usernames:
        posts = all_posts.get(username.lower(), [])

        if not posts:
            logger.warning(f"@{username}: Keine Beiträge von Apify erhalten")
            results[username] = []
            continue

        is_first_run = username not in state
        last_shortcode = state.get(username, {}).get("last_post_shortcode")
        latest_shortcode = posts[0].get("shortCode")

        new_posts = []
        if not is_first_run:
            for post in posts:
                if post.get("shortCode") == last_shortcode:
                    break
                timestamp = post.get("timestamp", "")[:16].replace("T", " ")
                new_posts.append({
                    "date": timestamp,
                    "is_video": post.get("type", "") == "Video",
                    "caption": post.get("caption") or "",
                    "url": post.get("url") or f"https://www.instagram.com/p/{post.get('shortCode', '')}/",
                })

        if latest_shortcode:
            state[username] = {"last_post_shortcode": latest_shortcode}
            state_changed = True

        if is_first_run:
            logger.info(f"@{username}: Erster Lauf — Baseline gesetzt ({latest_shortcode})")
            results[username] = []
        else:
            logger.info(f"@{username}: {len(new_posts)} neuer Beitrag/Beiträge")
            results[username] = new_posts

    if state_changed:
        save_state(state)

    return results
