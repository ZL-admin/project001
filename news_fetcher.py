"""
Fetches humanoid robot / embodied AI news from multiple RSS and web sources.
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import Optional
import time
import logging
import re

logger = logging.getLogger(__name__)

# News sources: (name, rss_url)
RSS_SOURCES = [
    # Google News — English queries
    ("Google News: humanoid robot", "https://news.google.com/rss/search?q=humanoid+robot&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: embodied AI", "https://news.google.com/rss/search?q=embodied+AI+robot&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: Figure Boston Dynamics", "https://news.google.com/rss/search?q=Figure+robot+OR+Boston+Dynamics+OR+Agility+Robotics&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: 1X Apptronik Sanctuary", "https://news.google.com/rss/search?q=1X+robot+OR+Apptronik+OR+Sanctuary+AI+humanoid&hl=en-US&gl=US&ceid=US:en"),
    # Google News — Chinese queries (embodied AI)
    ("Google News: 人形机器人", "https://news.google.com/rss/search?q=%E4%BA%BA%E5%BD%A2%E6%9C%BA%E5%99%A8%E4%BA%BA&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 具身智能", "https://news.google.com/rss/search?q=%E5%85%B7%E8%BA%AB%E6%99%BA%E8%83%BD&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 宇树优必选傅利叶", "https://news.google.com/rss/search?q=%E5%AE%87%E6%A0%91%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E4%BC%98%E5%BF%85%E9%80%89+OR+%E5%82%85%E5%88%A9%E5%8F%B6&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    # Google News — Chinese queries (home & eldercare)
    ("Google News: 家政机器人", "https://news.google.com/rss/search?q=%E5%AE%B6%E6%94%BF%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E5%AE%B6%E5%8A%A1%E6%9C%BA%E5%99%A8%E4%BA%BA&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 养老机器人", "https://news.google.com/rss/search?q=%E5%85%BB%E8%80%81%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E8%80%81%E5%B9%B4%E6%8A%A4%E7%90%86%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E6%99%BA%E6%85%A7%E5%85%BB%E8%80%81&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    # Google News — English queries (home & eldercare)
    ("Google News: home care robot", "https://news.google.com/rss/search?q=home+care+robot+OR+eldercare+robot+OR+caregiving+robot&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: aging robot", "https://news.google.com/rss/search?q=robot+elderly+care+OR+senior+care+robot+OR+aging+AI&hl=en-US&gl=US&ceid=US:en"),
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
    # English — embodied AI / humanoid
    "humanoid", "embodied", "bipedal", "android robot", "robot arm",
    "figure robot", "boston dynamics", "agility robotics", "1x robot",
    "apptronik", "sanctuary ai", "tesla optimus", "digit robot",
    "atlas robot", "spot robot", "robotics ai", "manipulation robot",
    "locomotion", "dexterous", "whole-body control",
    # English — home & eldercare
    "home care robot", "caregiving robot", "eldercare robot", "elder care robot",
    "senior care robot", "domestic robot", "household robot",
    "aging robot", "robot caregiver", "care robot",
    # Chinese — embodied AI / humanoid
    "人形机器人", "具身智能", "双足机器人", "仿人机器人",
    "宇树", "优必选", "傅利叶", "智元", "达闼", "乐聚",
    "阿尔法机器人", "小米机器人", "华为机器人",
    # Chinese — home & eldercare
    "家政机器人", "家务机器人", "家用机器人", "养老机器人",
    "老年护理机器人", "智慧养老", "养老科技", "护理机器人",
    "居家养老", "陪伴机器人", "康复机器人",
]


def is_relevant(title: str, summary: str = "") -> bool:
    text = (title + " " + summary).lower()
    return any(kw.lower() in text for kw in ROBOT_KEYWORDS)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def _parse_rss(xml_bytes: bytes, source_name: str, cutoff: datetime) -> list[dict]:
    """Parse RSS/Atom XML bytes, return relevant articles newer than cutoff."""
    articles = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.warning(f"[{source_name}] XML parse error: {e}")
        return articles

    # Support both RSS <item> and Atom <entry>
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)

    for item in items:
        def _text(tag: str) -> str:
            el = item.find(tag)
            if el is None:
                el = item.find(f"atom:{tag}", ns)
            return (el.text or "").strip() if el is not None else ""

        title = _text("title")
        url = _text("link")
        # Atom <link> uses href attribute
        if not url:
            link_el = item.find("atom:link", ns)
            url = (link_el.get("href", "") if link_el is not None else "")
        summary = _strip_html(_text("description") or _text("summary") or _text("content"))
        pub_raw = _text("pubDate") or _text("published") or _text("updated")

        if not title or not url:
            continue

        pub_time: Optional[datetime] = None
        if pub_raw:
            try:
                pub_time = parsedate_to_datetime(pub_raw)
            except Exception:
                try:
                    pub_time = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                except Exception:
                    pass

        if pub_time and pub_time.tzinfo is None:
            pub_time = pub_time.replace(tzinfo=timezone.utc)

        if pub_time and pub_time < cutoff:
            continue

        if not is_relevant(title, summary):
            continue

        articles.append({
            "title": title,
            "url": url,
            "source": source_name,
            "published": pub_time.strftime("%Y-%m-%d %H:%M UTC") if pub_time else "未知时间",
            "summary": summary[:500],
        })

    return articles


def fetch_all_news(hours_back: int = 26) -> list[dict]:
    """
    Fetches and deduplicates news from all sources published within `hours_back` hours.
    Returns list of dicts: {title, url, source, published, summary}
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    all_articles: list[dict] = []

    for source_name, rss_url in RSS_SOURCES:
        try:
            resp = requests.get(rss_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            articles = _parse_rss(resp.content, source_name, cutoff)
            logger.info(f"[{source_name}] {len(articles)} relevant entries")
        except Exception as e:
            logger.warning(f"[{source_name}] fetch failed: {e}")
            continue

        for a in articles:
            title_key = a["title"].lower()[:80]
            if a["url"] in seen_urls or title_key in seen_titles:
                continue
            seen_urls.add(a["url"])
            seen_titles.add(title_key)
            all_articles.append(a)

        time.sleep(0.5)

    logger.info(f"Total relevant articles collected: {len(all_articles)}")
    return all_articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    news = fetch_all_news()
    for a in news[:5]:
        print(f"[{a['source']}] {a['title']}\n  {a['url']}\n")
