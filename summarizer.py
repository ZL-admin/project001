"""
Uses Claude API to produce a structured Chinese daily digest from raw articles.
"""

import anthropic
import json
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

ELDERCARE_KW = [
    "养老", "家政", "护理", "银发", "老龄", "适老", "长护",
    "eldercare", "caregiver", "senior care", "aging",
]
EMBODIED_KW = [
    "人形机器人", "具身智能", "humanoid", "embodied", "robot",
    "机器人",
]


def count_topics(articles: list[dict]) -> dict:
    eldercare, embodied = 0, 0
    for a in articles:
        text = (a["title"] + " " + a["summary"]).lower()
        if any(kw.lower() in text for kw in ELDERCARE_KW):
            eldercare += 1
        else:
            embodied += 1
    return {"embodied": embodied, "eldercare": eldercare}


def _build_chat_button(chat_starter: str, today: str) -> str:
    """Build a Claude.ai deep-dive button to embed in the digest HTML."""
    import urllib.parse
    prompt = (
        f"我刚读了{today}的《具身智能·家政养老科技全球日报》。{chat_starter}"
        f"\n\n请帮我深入分析这个问题，结合当前行业背景展开探讨。"
    )
    url = f"https://claude.ai/new?q={urllib.parse.quote(prompt)}"
    return (
        f'<div style="margin:28px 0;padding:18px 24px;background:#f0f7ff;'
        f'border-radius:10px;text-align:center;">'
        f'<p style="margin:0 0 12px;color:#444;font-size:14px;">对今日洞察有疑问？想深入探讨？</p>'
        f'<a href="{url}" style="display:inline-block;background:#0071e3;color:#fff;'
        f'padding:10px 28px;border-radius:20px;text-decoration:none;font-size:14px;font-weight:500;">'
        f'💬 与 Claude 深入探讨今日洞察 →</a>'
        f'</div>'
    )


def _extract_meta(raw: str, today: str) -> tuple[str, list[str]]:
    """Parse Claude output into (html_with_chat_button, important_events).

    Markers are expected at the START of the response (before the HTML),
    so they're captured even if the digest body gets long.
    """
    # Extract important events
    ev_match = re.search(
        r"<!--IMPORTANT_EVENTS_START-->\s*(.*?)\s*<!--IMPORTANT_EVENTS_END-->",
        raw, re.DOTALL
    )
    events: list[str] = []
    if ev_match:
        try:
            events = json.loads(ev_match.group(1).strip())
            if not isinstance(events, list):
                events = []
        except Exception:
            events = []

    # Extract chat starter
    cs_match = re.search(
        r"<!--CHAT_STARTER_START-->\s*(.*?)\s*<!--CHAT_STARTER_END-->",
        raw, re.DOTALL
    )
    chat_starter = cs_match.group(1).strip() if cs_match else ""

    # HTML starts after the last marker block (markers are now at the top)
    last_marker_end = 0
    for m in [ev_match, cs_match]:
        if m and m.end() > last_marker_end:
            last_marker_end = m.end()
    html = raw[last_marker_end:].strip() if last_marker_end else raw.strip()

    # Inject chat button before closing <hr> / footer line
    if chat_starter:
        button = _build_chat_button(chat_starter, today)
        if "<hr>" in html:
            html = html.replace("<hr>", button + "\n<hr>", 1)
        else:
            html += "\n" + button

    return html, events

SYSTEM_PROMPT = """你是一名专注于具身智能、人形机器人、家政与养老科技领域的资深科技分析师与战略观察者。
你不仅整理新闻，更要透过表象提炼趋势、发现规律、进行思辨性分析。

输出要求：
- 语言：中文
- 风格：深度、犀利、有观点，同时保持客观
- 结构：按照下方模板严格输出，使用 HTML 格式（会在网页和邮件中渲染）
- 每条新闻必须附上原文链接
- 篇幅分配：国内新闻占约 80%，国际新闻占约 20%
- 根据今日各主题的文章数量动态调整板块篇幅：文章多的主题多写，文章少的主题少写，不要强行凑字数
- 若某板块当日无相关新闻，直接写"今日暂无相关动态"，不要捏造内容
- 避免重复昨日已报道的内容，如有后续进展则明确标注"【跟进】"
- 篇幅控制：各板块每条新闻用一句话说明，今日要闻每条不超过80字，今日洞察不超过300字，整体输出保持精炼
"""

DIGEST_TEMPLATE = """请根据以下新闻原文，生成今日（{today}）全球资讯日报。涵盖两个主题：①具身智能&人形机器人；②家政与养老科技。

今日各主题文章数量（请据此动态调整各板块篇幅）：
- 具身智能·人形机器人：{embodied_count} 条
- 家政与养老科技：{eldercare_count} 条
- 合计：{count} 条

{yesterday_section}

【重要】请严格按以下顺序输出，先输出两个标记块，再输出HTML日报正文：

第一步：输出重要事件标记（重大融资>1亿、重磅政策、技术里程碑、行业并购，无则空数组）：
<!--IMPORTANT_EVENTS_START-->
["用一句话描述的重要事件1", "重要事件2"]
<!--IMPORTANT_EVENTS_END-->

第二步：输出对话引导语（50字以内，提炼今日最值得深入探讨的一个问题，用第一人称"我"开头，结尾加问号）：
<!--CHAT_STARTER_START-->
我在今天的日报里看到……（你的引导语）？
<!--CHAT_STARTER_END-->

第三步：输出完整HTML日报：

<h2>🤖 具身智能 · 家政养老科技 全球日报 · {today}</h2>

{followup_section}

<h3>💡 今日洞察</h3>
<p>
  （基于今日所有新闻，用200~300字写出深度分析：<br>
  · 1~2个最值得关注的<strong>趋势</strong><br>
  · 1个<strong>思辨性问题</strong><br>
  · 1个容易被忽视的<strong>深层规律</strong><br>
  语气有主见，有分析师判断力，不要罗列。）
</p>

<h3>📌 今日要闻（3条最重要新闻）</h3>
<ol>
  <li>
    <strong>[公司/机构名]</strong> 用60~80字描述事件及其意义。
    <br><a href="原文URL">阅读原文 →</a>
  </li>
  ...（每条都必须有阅读原文链接）
</ol>

<h3>🦾 具身智能 · 人形机器人</h3>
<ul>
  <li><strong>公司/机构名</strong>：一句话说明进展。<a href="原文URL">↗</a></li>
  ...
</ul>

<h3>🏠 家政与养老科技</h3>
<ul>
  <li><strong>公司/机构名 或 研究机构</strong>：一句话说明进展。<a href="原文URL">↗</a></li>
  ...
</ul>

<h3>🔬 技术突破</h3>
<ul>
  <li>内容。<a href="原文URL">↗</a></li>
  ...
</ul>

<h3>💰 融资与商业</h3>
<ul>
  <li>内容。<a href="原文URL">↗</a></li>
  ...
</ul>

<h3>🌏 政策与产业</h3>
<ul>
  <li>内容。<a href="原文URL">↗</a></li>
  ...
</ul>

<h3>📊 今日数据</h3>
<p>共收录新闻 {count} 条，涵盖来源：{sources}</p>

<hr>
<p><small>由 Claude AI 自动整理 · 如有遗漏欢迎反馈</small></p>

---

新闻原文如下（每条均含链接，请在输出中保留对应链接）：

{articles_text}
"""


def build_articles_text(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(
            f"[{i}] 标题：{a['title']}\n"
            f"    来源：{a['source']}  时间：{a['published']}\n"
            f"    链接：{a['url']}\n"
            f"    摘要：{a['summary']}\n"
        )
    return "\n".join(lines)


def summarize(
    articles: list[dict],
    api_key: str,
    yesterday_context: dict | None = None,
    topic_stats: dict | None = None,
) -> tuple[str, list[str]]:
    """Returns (html_content, important_events)."""
    today = date.today().strftime("%Y年%m月%d日")

    if not articles:
        html = f"<h2>🤖 具身智能 · 家政养老科技 全球日报 · {today}</h2><p>今日暂无相关新闻。</p>"
        return html, []

    client = anthropic.Anthropic(api_key=api_key)
    sources = "、".join(sorted({a["source"].split(":")[0].strip() for a in articles}))
    articles_text = build_articles_text(articles)
    stats = topic_stats or count_topics(articles)

    # Build yesterday context block
    yesterday_section = ""
    if yesterday_context:
        headlines = yesterday_context.get("headlines", [])
        prev_events = yesterday_context.get("important_events", [])
        if headlines:
            hl_text = "\n".join(f"- {h}" for h in headlines[:30])
            yesterday_section = f"【昨日已报道标题（今日请勿重复，若有后续请标注【跟进】）】\n{hl_text}"
        if prev_events:
            ev_text = "\n".join(f"- {e}" for e in prev_events)
            yesterday_section += f"\n\n【昨日重要事件（请在今日日报开篇酌情跟进）】\n{ev_text}"

    # Build followup section placeholder
    followup_section = ""
    if yesterday_context and yesterday_context.get("important_events"):
        followup_section = (
            "<h3>🔔 昨日重要事件跟进</h3>\n"
            "<ul>\n"
            "  （若今日有相关后续新闻，在此列出；若无则删去此板块）\n"
            "</ul>\n"
        )

    prompt = DIGEST_TEMPLATE.format(
        today=today,
        count=len(articles),
        sources=sources,
        embodied_count=stats.get("embodied", 0),
        eldercare_count=stats.get("eldercare", 0),
        yesterday_section=yesterday_section,
        followup_section=followup_section,
        articles_text=articles_text,
    )

    logger.info(f"Sending {len(articles)} articles to Claude (embodied={stats.get('embodied')}, eldercare={stats.get('eldercare')})...")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=10000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    html_content, important_events = _extract_meta(raw, today)
    logger.info(f"Summarization complete. Important events: {len(important_events)}")
    return html_content, important_events


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from news_fetcher import fetch_all_news

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    articles = fetch_all_news()
    html = summarize(articles, os.environ["ANTHROPIC_API_KEY"])
    print(html[:2000])
