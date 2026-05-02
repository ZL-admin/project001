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


def _extract_important_events(raw: str) -> tuple[str, list[str]]:
    """Split Claude's output into (html, important_events list)."""
    match = re.search(
        r"<!--IMPORTANT_EVENTS_START-->\s*(.*?)\s*<!--IMPORTANT_EVENTS_END-->",
        raw, re.DOTALL
    )
    if not match:
        return raw.strip(), []
    html = raw[:match.start()].strip()
    try:
        events = json.loads(match.group(1).strip())
        if not isinstance(events, list):
            events = []
    except Exception:
        events = []
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
"""

DIGEST_TEMPLATE = """请根据以下新闻原文，生成今日（{today}）全球资讯日报。涵盖两个主题：①具身智能&人形机器人；②家政与养老科技。

今日各主题文章数量（请据此动态调整各板块篇幅）：
- 具身智能·人形机器人：{embodied_count} 条
- 家政与养老科技：{eldercare_count} 条
- 合计：{count} 条

{yesterday_section}

输出格式（严格遵循，使用 HTML）：

<h2>🤖 具身智能 · 家政养老科技 全球日报 · {today}</h2>

{followup_section}

<h3>💡 今日洞察</h3>
<p>
  （基于今日所有新闻，用300~500字写出你的深度分析。要求：<br>
  · 归纳1~3个当前最值得关注的<strong>趋势</strong>（跨多条新闻的共同信号）<br>
  · 提出1~2个<strong>思辨性问题</strong>（比如：这个方向真的可行吗？谁会是最终赢家？）<br>
  · 点出1个容易被忽视的<strong>深层规律</strong>（技术、商业或社会层面均可）<br>
  语气要有主见，不要罗列，要有分析师的判断力。）
</p>

<h3>📌 今日要闻（3~5条最重要新闻）</h3>
<ol>
  <li>
    <strong>[公司/机构名]</strong> 用100~150字描述事件及其意义。
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

---
请在完整 HTML 日报输出结束后，另起一行输出以下格式的重要事件标记。
重要事件定义：重大融资（>1亿）、重磅政策、技术里程碑、行业并购。若无则输出空数组。

<!--IMPORTANT_EVENTS_START-->
["用一句话描述的重要事件1", "重要事件2"]
<!--IMPORTANT_EVENTS_END-->
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
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    html_content, important_events = _extract_important_events(raw)
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
