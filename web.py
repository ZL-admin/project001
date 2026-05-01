from flask import Flask, abort, redirect
from flask import render_template_string
from datetime import date
from storage import list_digests, load_digest

app = Flask(__name__)

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
       background: #f5f5f7; color: #1d1d1f; line-height: 1.6; }
.navbar { background: #1d1d1f; color: #f5f5f7; padding: 14px 24px;
          display: flex; align-items: center; gap: 12px; }
.navbar a { color: #f5f5f7; text-decoration: none; font-size: 18px; font-weight: 600; }
.navbar span { color: #86868b; font-size: 14px; }
.container { max-width: 900px; margin: 32px auto; padding: 0 20px; }
.card { background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.08);
        padding: 24px; margin-bottom: 16px; }
.card h2 { font-size: 22px; margin-bottom: 8px; }
.card .meta { color: #86868b; font-size: 13px; margin-bottom: 16px; }
.digest-list a { text-decoration: none; color: inherit; display: block; }
.digest-list .card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.14); transition: .2s; }
.badge { display: inline-block; background: #e8f4fd; color: #0071e3;
         border-radius: 20px; padding: 2px 10px; font-size: 12px; margin-left: 8px; }
.digest-content h2 { font-size: 24px; margin: 24px 0 12px; }
.digest-content h3 { font-size: 18px; margin: 20px 0 8px; color: #1d1d1f;
                     border-left: 4px solid #0071e3; padding-left: 10px; }
.digest-content ol, .digest-content ul { padding-left: 20px; }
.digest-content li { margin-bottom: 10px; }
.digest-content a { color: #0071e3; }
.digest-content hr { border: none; border-top: 1px solid #e5e5e5; margin: 24px 0; }
.digest-content p { margin-bottom: 8px; }
.empty { text-align: center; color: #86868b; padding: 60px 0; font-size: 16px; }
.back-link { display: inline-block; margin-bottom: 20px; color: #0071e3;
             text-decoration: none; font-size: 14px; }
.back-link:hover { text-decoration: underline; }
"""

_NAVBAR = """
<div class="navbar">
  <a href="/">🤖 具身智能 · 家政养老科技 日报</a>
  <span>· 全球资讯每日精选</span>
</div>
"""

INDEX_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>具身智能 · 家政养老科技 日报</title><style>{{ css }}</style></head>
<body>{{ navbar | safe }}
<div class="container">
<h2 style="margin-bottom:20px;">历史日报</h2>
{% if digests %}
<div class="digest-list">
  {% for d in digests %}
  <a href="/digest/{{ d.date }}">
    <div class="card">
      <h2>{{ d.date }} <span class="badge">{{ d.article_count }} 条新闻</span></h2>
      <div class="meta">生成时间：{{ d.generated_at[:19].replace('T',' ') if d.generated_at else '—' }} UTC</div>
      <div style="color:#0071e3;font-size:14px;">点击查看 →</div>
    </div>
  </a>
  {% endfor %}
</div>
{% else %}
<div class="empty">暂无日报记录。<br>
运行 <code>python main.py --now</code> 立即生成第一份日报。</div>
{% endif %}
</div></body></html>"""

DETAIL_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>具身智能日报 · {{ digest_date }}</title><style>{{ css }}</style></head>
<body>{{ navbar | safe }}
<div class="container">
<a class="back-link" href="/">← 返回列表</a>
<div class="card digest-content">{{ html | safe }}</div>
</div></body></html>"""


@app.route("/")
def index():
    digests = list_digests()
    return render_template_string(INDEX_TMPL, css=_CSS, navbar=_NAVBAR, digests=digests)


@app.route("/digest/<digest_date>")
def digest(digest_date: str):
    try:
        d = date.fromisoformat(digest_date)
    except ValueError:
        abort(404)
    data = load_digest(d)
    if not data:
        abort(404)
    return render_template_string(
        DETAIL_TMPL, css=_CSS, navbar=_NAVBAR,
        digest_date=digest_date, html=data["html"]
    )


@app.route("/latest")
def latest():
    digests = list_digests()
    if not digests:
        abort(404)
    return redirect(f"/digest/{digests[0]['date']}")


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("WEB_PORT", "5000")), debug=False)
