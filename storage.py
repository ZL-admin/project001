"""
Persists daily digests as JSON files under ./data/digests/.
Each file is named YYYY-MM-DD.json.
"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data" / "digests"


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_digest(
    html_content: str,
    articles: list[dict],
    run_date: date | None = None,
    important_events: list[str] | None = None,
) -> Path:
    _ensure_dir()
    today = run_date or date.today()
    filename = DATA_DIR / f"{today.isoformat()}.json"

    payload = {
        "date": today.isoformat(),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "article_count": len(articles),
        "important_events": important_events or [],
        "html": html_content,
        "articles": articles,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(f"Digest saved to {filename}")
    return filename


def get_yesterday_summary() -> dict:
    """Load yesterday's digest headlines and important events for memory context."""
    yesterday = date.today() - timedelta(days=1)
    data = load_digest(yesterday)
    if not data:
        return {"headlines": [], "important_events": []}
    headlines = [a["title"] for a in data.get("articles", [])[:30]]
    important_events = data.get("important_events", [])
    return {"headlines": headlines, "important_events": important_events}


def load_digest(target_date: date) -> dict | None:
    path = DATA_DIR / f"{target_date.isoformat()}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_digests() -> list[dict]:
    """Returns metadata for all saved digests, newest first."""
    _ensure_dir()
    results = []
    for p in sorted(DATA_DIR.glob("*.json"), reverse=True):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            results.append({
                "date": data["date"],
                "generated_at": data.get("generated_at", ""),
                "article_count": data.get("article_count", 0),
            })
        except Exception:
            continue
    return results
