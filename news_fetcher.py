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
# 比例目标：国内约80%，国外约20%
RSS_SOURCES = [
    # ========== 中文科技媒体 RSS ==========
    ("机器之心", "https://www.jiqizhixin.com/rss"),
    ("量子位", "https://www.qbitai.com/feed"),
    ("36氪", "https://36kr.com/feed"),

    # ========== Google News 中文 — 具身智能·人形机器人 ==========
    ("Google News: 人形机器人",
     "https://news.google.com/rss/search?q=%E4%BA%BA%E5%BD%A2%E6%9C%BA%E5%99%A8%E4%BA%BA&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 具身智能",
     "https://news.google.com/rss/search?q=%E5%85%B7%E8%BA%AB%E6%99%BA%E8%83%BD&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 具身大模型",
     "https://news.google.com/rss/search?q=%E5%85%B7%E8%BA%AB%E5%A4%A7%E6%A8%A1%E5%9E%8B+OR+%E6%9C%BA%E5%99%A8%E4%BA%BA%E5%A4%A7%E6%A8%A1%E5%9E%8B&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 宇树优必选傅利叶智元",
     "https://news.google.com/rss/search?q=%E5%AE%87%E6%A0%91+OR+%E4%BC%98%E5%BF%85%E9%80%89+OR+%E5%82%85%E5%88%A9%E5%8F%B6+OR+%E6%99%BA%E5%85%83%E6%9C%BA%E5%99%A8%E4%BA%BA&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 银河通用开普勒逐际星动",
     "https://news.google.com/rss/search?q=%E9%93%B6%E6%B2%B3%E9%80%9A%E7%94%A8+OR+%E5%BC%80%E6%99%AE%E5%8B%92%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E9%80%90%E9%99%85%E5%8A%A8%E5%8A%9B+OR+%E6%98%9F%E5%8A%A8%E7%BA%AA%E5%85%83&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 自变量穿山甲小鹏机器人",
     "https://news.google.com/rss/search?q=%E8%87%AA%E5%8F%98%E9%87%8F%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E7%A9%BF%E5%B1%B1%E7%94%B2%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E5%B0%8F%E9%B9%8F%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E5%AE%87%E7%A0%BE%E6%99%BA%E8%83%BD&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 新松埃斯顿节卡越疆遨博",
     "https://news.google.com/rss/search?q=%E6%96%B0%E6%9D%BE%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E5%9F%83%E6%96%AF%E9%A1%BF+OR+%E8%8A%82%E5%8D%A1%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E8%B6%8A%E7%96%86+OR+%E9%81%A8%E5%8D%9A&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),

    # ========== Google News 中文 — 养老·家政（大幅扩充） ==========
    ("Google News: 居家养老社区养老",
     "https://news.google.com/rss/search?q=%E5%B1%85%E5%AE%B6%E5%85%BB%E8%80%81+OR+%E7%A4%BE%E5%8C%BA%E5%85%BB%E8%80%81+OR+%E5%8C%BB%E5%85%BB%E7%BB%93%E5%90%88&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 养老护理员培训",
     "https://news.google.com/rss/search?q=%E5%85%BB%E8%80%81%E6%8A%A4%E7%90%86%E5%91%98+OR+%E5%85%BB%E8%80%81%E6%8A%A4%E7%90%86%E5%9F%B9%E8%AE%AD+OR+%E6%8A%A4%E5%B7%A5+OR+%E9%95%BF%E6%9C%9F%E7%85%A7%E6%8A%A4&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 养老保险长护险",
     "https://news.google.com/rss/search?q=%E5%85%BB%E8%80%81%E4%BF%9D%E9%99%A9+OR+%E9%95%BF%E6%9C%9F%E6%8A%A4%E7%90%86%E9%99%A9+OR+%E9%95%BF%E6%8A%A4%E9%99%A9&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 银发经济老龄化适老化",
     "https://news.google.com/rss/search?q=%E9%93%B6%E5%8F%91%E7%BB%8F%E6%B5%8E+OR+%E8%80%81%E9%BE%84%E5%8C%96+OR+%E9%80%82%E8%80%81%E5%8C%96&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 家政服务行业",
     "https://news.google.com/rss/search?q=%E5%AE%B6%E6%94%BF%E6%9C%8D%E5%8A%A1+OR+%E5%AE%B6%E6%94%BF%E5%85%AC%E5%8F%B8+OR+%E5%AE%B6%E6%94%BF%E8%A1%8C%E4%B8%9A&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ("Google News: 养老机器人家政机器人",
     "https://news.google.com/rss/search?q=%E5%85%BB%E8%80%81%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E5%AE%B6%E6%94%BF%E6%9C%BA%E5%99%A8%E4%BA%BA+OR+%E5%AE%B6%E5%8A%A1%E6%9C%BA%E5%99%A8%E4%BA%BA&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),

    # ========== Google News 英文 — 具身智能（缩减为精华） ==========
    ("Google News: humanoid robot",
     "https://news.google.com/rss/search?q=humanoid+robot&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: physical AI embodied",
     "https://news.google.com/rss/search?q=%22physical+AI%22+OR+%22embodied+AI%22+OR+%22robot+foundation+model%22&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: Tesla Optimus Figure Boston Dynamics",
     "https://news.google.com/rss/search?q=Tesla+Optimus+OR+Figure+robot+OR+Boston+Dynamics+OR+Agility+Robotics&hl=en-US&gl=US&ceid=US:en"),

    # ========== 英文专业媒体（保留精华） ==========
    ("IEEE Spectrum Robotics", "https://spectrum.ieee.org/feeds/topic/robotics.rss"),
    ("TechCrunch Robotics", "https://techcrunch.com/tag/robotics/feed/"),
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
    "humanoid", "embodied", "bipedal", "android robot",
    "figure robot", "boston dynamics", "agility robotics", "1x robot",
    "apptronik", "sanctuary ai", "tesla optimus", "digit robot",
    "atlas robot", "physical ai", "robot foundation model",
    "locomotion", "dexterous", "whole-body control",
    # English — home & eldercare
    "home care robot", "caregiving robot", "eldercare robot",
    "senior care robot", "domestic robot", "household robot",
    "aging robot", "robot caregiver",
    # Chinese — 具身智能·人形机器人
    "人形机器人", "具身智能", "具身大模型", "机器人大模型",
    "双足机器人", "仿人机器人",
    # 国内头部企业
    "宇树", "优必选", "傅利叶", "智元", "达闼", "乐聚",
    # 新兴企业
    "银河通用", "开普勒机器人", "逐际动力", "星动纪元",
    "自变量机器人", "穿山甲机器人", "小鹏机器人", "宇砾智能",
    "新松机器人", "埃斯顿", "节卡机器人", "越疆", "遨博",
    "云深处", "小米机器人", "华为机器人",
    # Chinese — 养老（宽口径）
    "养老机器人", "养老护理", "养老护理员", "养老护理培训",
    "养老保险", "长期护理险", "长护险",
    "居家养老", "社区养老", "医养结合",
    "银发经济", "老龄化", "适老化", "老年护理",
    "智慧养老", "养老科技", "陪伴机器人", "康复机器人",
    # Chinese — 家政
    "家政机器人", "家务机器人", "家政服务", "家政行业",
    "家政公司", "家政培训",
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
