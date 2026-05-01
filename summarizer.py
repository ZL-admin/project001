"""
Uses Claude API to produce a structured Chinese daily digest from raw articles.
"""

import anthropic
import logging
from datetime import date

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一名专注于具身智能与人形机器人领域的资深科技分析师。
你的任务是将当天收集到的全球相关新闻整理成一份清晰、专业的中文日报摘要。

输出要求：
- 语言：中文
- 风格：专业、简洁、客观
- 结构：按照下方模板严格输出，使用 HTML 格式（会在网页和邮件中渲染）
"""

DIGEST_TEMPLATE = """请根据以下新闻原文，生成今日（{today}）具身智能&人形机器人全球资讯日报。

输出格式（严格遵循，使用 HTML）：

<h2>🤖 具身智能&人形机器人 全球日报 · {today}</h2>

<h3>📌 今日要闻（3~5条最重要新闻，每条100~150字）</h3>
<ol>
  <li><strong>[公司/机构名]</strong> 标题摘要...<br><a href="原文链接">阅读原文</a></li>
  ...
</ol>

<h3>🏢 公司动态</h3>
<ul>
  <li><strong>公司名</strong>：一句话说明进展...</li>
  ...
</ul>

<h3>🔬 技术突破</h3>
<ul>
  <li>...</li>
</ul>

<h3>💰 融资与商业</h3>
<ul>
  <li>...</li>
</ul>

<h3>🌏 政策与产业</h3>
<ul>
  <li>...</li>
</ul>

<h3>📊 今日数据</h3>
<p>共收录新闻 {count} 条，涵盖来源：{sources}</p>

<hr>
<p><small>由 Claude AI 自动整理 · 如有遗漏欢迎反馈</small></p>

---

新闻原文如下：

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


def summarize(articles: list[dict], api_key: str) -> str:
    if not articles:
        today = date.today().strftime("%Y年%m月%d日")
        return f"<h2>🤖 具身智能&人形机器人 全球日报 · {today}</h2><p>今日暂无相关新闻。</p>"

    client = anthropic.Anthropic(api_key=api_key)

    today = date.today().strftime("%Y年%m月%d日")
    sources = "、".join(sorted({a["source"].split(":")[0].strip() for a in articles}))
    articles_text = build_articles_text(articles)

    prompt = DIGEST_TEMPLATE.format(
        today=today,
        count=len(articles),
        sources=sources,
        articles_text=articles_text,
    )

    logger.info(f"Sending {len(articles)} articles to Claude for summarization...")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    html_content = message.content[0].text
    logger.info("Summarization complete.")
    return html_content


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from news_fetcher import fetch_all_news

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    articles = fetch_all_news()
    html = summarize(articles, os.environ["ANTHROPIC_API_KEY"])
    print(html[:2000])
