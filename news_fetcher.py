"""
Fetches humanoid robot / embodied AI news from multiple RSS and web sources.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)

# News sources: (name, rss_url)
RSS_SOURCES = [
    # Google News — English queries
    ("Google News: humanoid robot", "https://news.google.com/rss/search?q=humanoid+robot&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: embodied AI", "https://news.google.com/rss/search?q=embodied+AI+robot&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: Figure Boston Dynamics", "https://news.google.com/rss/search?q=Figure+robot+OR+Boston+Dynamics+OR+Agility+Robotics&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: 1X Apptronik Sanctuary", "https://news.google.com/rss/search?q=1X+robot+OR+Apptronik+OR+Sanctuary+AI+humanoid&hl=en-US&gl=US&ceid=US:en"),
    # Google News — Chinese queries
    ("Google News: 人形机器人", "https://news.google.com/rss/search?q=%E4%BA%BA%E5%BD%A2%E6%9C%BA%E5%99%A8%E4%BA%BA&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 具身智能", "https://news.google.com/rss/search?q=%E5%85%B7%E8%BA%AB%E6%99%BA%E8%83%BD&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 宇树优必选傅利叶", "https://news.google.com/rss/search?q=%E5%AE%87%E6%A0%91%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E4%BC%98%E5%BF%85%E9%80%89+OR+%E5%82%85%E5%88%A9%E5%8F%B6&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    # Tech media RSS
    ("IEEE Spectrum Robotics", "https://spectrum.ieee.org/feeds/topic/robotics.rss"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
    ("TechCrunch Robotics", "https://techcrunch.com/tag/robotics/feed/"),
    ("The Verge Tech", "https://www.theverge.com/rss/index.xml"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

ROBOT_KEYWORDS = [
    # English
    "humanoid", "embodied", "bipedal", "android robot", "robot arm",
    "figure robot", "boston dynamics", "agility robotics", "1x robot",
    "apptronik", "sanctuary ai", "tesla optimus", "digit robot",
    "atlas robot", "spot robot", "robotics ai", "manipulation robot",
    "locomotion", "dexterous", "whole-body control",
    # Chinese
    "人形机器人", "具身智能", "双足机器人", "仿人机器人",
    "宇树", "优必选", "傅利叶", "智元", "达闼", "乐聚",
    "阿尔法机器人", "小米机器人", "华为机器人",
]


def is_relevant(title: str, summary: str = "") -> bool:
    text = (title + " " + summary).lower()
    return any(kw.lower() in text for kw in ROBOT_KEYWORDS)


def fetch_article_text(url: str, max_chars: int = 2000) -> str:
    """Best-effort: fetch article body text for richer context."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs)
        return text[:max_chars]
    except Exception:
        return ""


def fetch_all_news(hours_back: int = 26) -> list[dict]:
    """
    Fetches and deduplicates news from all sources published within `hours_back` hours.
    Returns list of dicts: {title, url, source, published, summary}
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    articles: list[dict] = []

    for source_name, rss_url in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            logger.info(f"[{source_name}] fetched {len(feed.entries)} entries")
        except Exception as e:
            logger.warning(f"[{source_name}] RSS fetch failed: {e}")
            continue

        for entry in feed.entries:
            url = entry.get("link", "")
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "")

            if not title or not url:
                continue

            # Dedup by URL and normalised title
            title_key = title.lower()[:80]
            if url in seen_urls or title_key in seen_titles:
                continue

            # Parse publish time
            pub_time: Optional[datetime] = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass

            if pub_time and pub_time < cutoff:
                continue

            if not is_relevant(title, summary):
                continue

            seen_urls.add(url)
            seen_titles.add(title_key)
            articles.append({
                "title": title,
                "url": url,
                "source": source_name,
                "published": pub_time.strftime("%Y-%m-%d %H:%M UTC") if pub_time else "未知时间",
                "summary": BeautifulSoup(summary, "lxml").get_text(strip=True)[:500],
            })

        # Be polite to servers
        time.sleep(0.5)

    logger.info(f"Total relevant articles collected: {len(articles)}")
    return articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    news = fetch_all_news()
    for a in news[:5]:
        print(f"[{a['source']}] {a['title']}\n  {a['url']}\n")
