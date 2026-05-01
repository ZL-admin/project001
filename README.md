# 🤖 具身智能&人形机器人 全球日报

每天早上 8 点自动抓取全球人形机器人/具身智能相关新闻，用 Claude AI 整理成中文日报，通过邮件发送，并提供本地网页查阅。

---

## 功能

- 抓取 Google News、IEEE、TechCrunch、MIT TR 等多源 RSS
- 关键词过滤（Figure、Boston Dynamics、宇树、优必选、具身智能等）
- Claude AI 生成结构化中文摘要（要闻 / 公司动态 / 技术突破 / 融资 / 政策）
- 每天 8:00 自动运行，邮件发送
- 本地网页 `http://localhost:5000` 浏览历史日报

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 只需填写 ANTHROPIC_API_KEY，其余保持默认即可
```

### 3. 运行

```bash
# 立即运行一次（测试用）
python main.py --now
# → 抓取新闻 → Claude 生成中文摘要 → 保存到本地
# → 打开 http://localhost:5000 查看结果

# 正常模式：每天 08:00 自动运行 + 常驻网页服务
python main.py

# 只启动网页（浏览历史日报）
python main.py --web-only
```

### 4. 开机自启（可选，Mac）

```bash
# 创建 launchd plist，让程序开机后台运行
# 参考 README 下方"开机自启"章节
```

---

## 文件结构

```
project001/
├── main.py          # 入口：定时任务 + 启动 web
├── news_fetcher.py  # RSS 抓取 + 关键词过滤
├── summarizer.py    # Claude API 生成中文摘要
├── sender.py        # SMTP 邮件发送
├── storage.py       # 保存/读取日报 JSON
├── web.py           # Flask 网页服务
├── requirements.txt
├── .env.example     # 配置模板
└── data/digests/    # 日报存储（自动创建）
```

---

## 开机自启（Mac）

创建文件 `~/Library/LaunchAgents/com.robotdigest.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.robotdigest</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/path/to/project001/main.py</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>WorkingDirectory</key>
  <string>/path/to/project001</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.robotdigest.plist
```

**Windows** 用户可用"任务计划程序"设置开机启动。
