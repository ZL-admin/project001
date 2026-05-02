# 具身智能 · 家政养老科技 全球日报

每天早上 8 点通过 **GitHub Actions** 自动运行，抓取全球相关新闻，用 Claude AI 整理成中文日报，发送到邮箱。不需要本地电脑保持开启。

---

## 覆盖主题

- **具身智能 · 人形机器人** — 宇树、优必选、傅利叶、智元、银河通用、开普勒、逐际动力、自变量、Figure、Boston Dynamics、Tesla Optimus 等
- **家政与养老科技** — 家政机器人、居家养老、社区养老、养老护理员、长护险、银发经济、适老化改造等

篇幅分配：国内约 80%，国际约 20%。

---

## 日报结构

| 板块 | 内容 |
|------|------|
| 💡 今日洞察 | 趋势归纳、思辨性分析、深层规律，300~500字 |
| 📌 今日要闻 | 3~5条重点新闻，每条附原文链接 |
| 🦾 具身智能·人形机器人 | 各公司最新动态 |
| 🏠 家政与养老科技 | 家政、居家养老、养老政策等 |
| 🔬 技术突破 | 算法、硬件、模型进展 |
| 💰 融资与商业 | 融资、并购、商业合作 |
| 🌏 政策与产业 | 国内外政策、行业报告 |

---

## 新闻来源

**中文媒体（直接 RSS）**
- 机器之心、量子位、36氪

**Google News 中文搜索（14条）**
- 人形机器人、具身智能、具身大模型
- 宇树/优必选/傅利叶/智元、银河通用/开普勒/逐际动力/星动纪元
- 自变量/穿山甲/小鹏机器人、新松/埃斯顿/节卡/越疆/遨博
- 居家养老/社区养老、养老护理员/培训、养老保险/长护险
- 银发经济/老龄化/适老化、家政服务行业、养老/家政机器人

**英文媒体与搜索（5条）**
- Google News: humanoid robot、physical AI、Tesla Optimus/Figure/Boston Dynamics
- IEEE Spectrum Robotics、TechCrunch Robotics

---

## 部署方式

### GitHub Actions（主要方式，推荐）

每天 08:00 北京时间自动运行，无需本地电脑。

**配置步骤：**

1. Fork 或克隆本仓库
2. 进入仓库 **Settings → Secrets and variables → Actions**
3. 添加以下 Secrets：

| Secret 名称 | 说明 |
|-------------|------|
| `ANTHROPIC_API_KEY` | Claude API Key |
| `SMTP_HOST` | 邮件服务器，如 `smtp.gmail.com` |
| `SMTP_PORT` | 端口，如 `587` |
| `SMTP_USER` | 发件邮箱地址 |
| `SMTP_PASSWORD` | 邮箱授权密码（Gmail 需用应用专用密码） |
| `RECIPIENT_EMAIL` | 收件邮箱地址 |

4. 进入 **Actions → 每日资讯日报 → Run workflow** 手动测试一次

之后每天自动运行，也可随时手动触发刷新。

---

### 本地运行（可选）

```bash
# 安装依赖
pip install -r requirements.txt

# 配置（只需填写 ANTHROPIC_API_KEY，邮件可选）
cp .env.example .env

# 立即运行一次
python main.py --now

# 启动本地网页（http://localhost:5000）
python main.py --web-only

# 定时模式（每天 8 点自动运行 + 网页服务）
python main.py
```

---

## 文件结构

```
project001/
├── .github/workflows/
│   └── daily_digest.yml  # GitHub Actions 定时任务
├── main.py               # 入口：调度 + 网页服务
├── news_fetcher.py       # RSS 抓取 + 关键词过滤
├── summarizer.py         # Claude API 生成中文摘要
├── sender.py             # SMTP 邮件发送
├── storage.py            # 日报存储（JSON）
├── web.py                # 本地网页浏览
├── requirements.txt
├── .env.example          # 本地配置模板
└── data/digests/         # 日报存储目录（自动创建）
```
