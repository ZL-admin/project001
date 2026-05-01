"""
Uses Claude API to produce a structured Chinese daily digest from raw articles.
"""

import anthropic
import logging
from datetime import date

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一名专注于具身智能、人形机器人、家政与养老科技领域的资深科技分析师与战略观察者。
你不仅整理新闻，更要透过表象提炼趋势、发现规律、进行思辨性分析。

输出要求：
- 语言：中文
- 风格：深度、犀利、有观点，同时保持客观
- 结构：按照下方模板严格输出，使用 HTML 格式（会在网页和邮件中渲染）
- 每条新闻必须附上原文链接
"""

DIGEST_TEMPLATE = """请根据以下新闻原文，生成今日（{today}）全球资讯日报。涵盖两个主题：①具身智能&人形机器人；②家政与养老科技。

输出格式（严格遵循，使用 HTML）：

<h2>🤖 具身智能 · 家政养老科技 全球日报 · {today}</h2>

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
  ...（若今日无相关新闻则写"今日暂无相关动态"）
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
        max_tokens=8192,
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
