"""
Flask web app — browse and view daily digests at http://localhost:5000
"""

from flask import Flask, render_template_string, abort
from datetime import date, datetime
from storage import list_digests, load_digest

app = Flask(__name__)

BASE_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>具身智能日报</title>
<style>
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
  .digest-content h3 { font-size: 18px; margin: 20px 0 8px; color: #1d1d1f; border-left: 4px solid #0071e3; padding-left: 10px; }
  .digest-content ol, .digest-content ul { padding-left: 20px; }
  .digest-content li { margin-bottom: 10px; }
  .digest-content a { color: #0071e3; }
  .digest-content hr { border: none; border-top: 1px solid #e5e5e5; margin: 24px 0; }
  .digest-content p { margin-bottom: 8px; }
  .empty { text-align: center; color: #86868b; padding: 60px 0; font-size: 16px; }
  .back-link { display: inline-block; margin-bottom: 20px; color: #0071e3; text-decoration: none; font-size: 14px; }
  .back-link:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="navbar">
  <a href="/">🤖 具身智能日报</a>
  <span>· 人形机器人全球资讯</span>
</div>
<div class="container">
{% block content %}{% endblock %}
</div>
</body>
</html>
"""

INDEX_BLOCK = """
{% extends base %}
{% block content %}
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
<div class="empty">暂无日报记录。<br>每天早上 8:00 自动生成，或运行 <code>python main.py --now</code> 立即生成。</div>
{% endif %}
{% endblock %}
"""

DETAIL_BLOCK = """
{% extends base %}
{% block content %}
<a class="back-link" href="/">← 返回列表</a>
<div class="card digest-content">
  {{ html | safe }}
</div>
{% endblock %}
"""


@app.route("/")
def index():
    digests = list_digests()
    return render_template_string(INDEX_BLOCK, base=BASE_HTML, digests=digests)


@app.route("/digest/<digest_date>")
def digest(digest_date: str):
    try:
        d = date.fromisoformat(digest_date)
    except ValueError:
        abort(404)

    data = load_digest(d)
    if not data:
        abort(404)

    return render_template_string(DETAIL_BLOCK, base=BASE_HTML, html=data["html"])


@app.route("/latest")
def latest():
    digests = list_digests()
    if not digests:
        abort(404)
    from flask import redirect
    return redirect(f"/digest/{digests[0]['date']}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
