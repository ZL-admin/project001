"""
Entry point.

Usage:
  python main.py            # start scheduler + web server (normal mode)
  python main.py --now      # run digest immediately, then exit
  python main.py --web-only # start web server only (no scheduler)
"""

import argparse
import logging
import os
import sys
import threading
import time
from datetime import date

import schedule
from dotenv import load_dotenv

from news_fetcher import fetch_all_news
from summarizer import summarize
from sender import send_email
from storage import save_digest, load_digest

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("robot_digest.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


def _require_env(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        logger.error(f"Missing required env var: {key}")
        sys.exit(1)
    return val


def run_digest() -> None:
    logger.info("=== Starting daily digest run ===")

    api_key = _require_env("ANTHROPIC_API_KEY")
    send_email_enabled = os.environ.get("SEND_EMAIL", "false").lower() != "false"

    try:
        articles = fetch_all_news(hours_back=26)
        html = summarize(articles, api_key)
        save_digest(html, articles)

        if send_email_enabled:
            send_email(
                html_content=html,
                smtp_host=_require_env("SMTP_HOST"),
                smtp_port=int(os.environ.get("SMTP_PORT", "587")),
                smtp_user=_require_env("SMTP_USER"),
                smtp_password=_require_env("SMTP_PASSWORD"),
                recipient=_require_env("RECIPIENT_EMAIL"),
            )
        else:
            logger.info("Email disabled — view digest at http://localhost:%s", os.environ.get("WEB_PORT", "5000"))

        logger.info("=== Digest run complete ===")
    except Exception as e:
        logger.exception(f"Digest run failed: {e}")


def start_web_server() -> None:
    from web import app
    port = int(os.environ.get("WEB_PORT", "5000"))
    logger.info(f"Web server starting at http://localhost:{port}")
    # Use werkzeug directly to avoid reloader issues in threads
    from werkzeug.serving import make_server
    server = make_server("0.0.0.0", port, app)
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="具身智能日报机器人")
    parser.add_argument("--now", action="store_true", help="立即运行一次，然后退出")
    parser.add_argument("--web-only", action="store_true", help="只启动网页服务，不运行定时任务")
    args = parser.parse_args()

    if args.now:
        run_digest()
        return

    # Start web server in a background thread
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()

    if args.web_only:
        logger.info("Running in web-only mode. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Stopped.")
        return

    # 启动时检查今日日报是否已生成，没有则立即补跑
    run_time = os.environ.get("DAILY_RUN_TIME", "08:00")
    now_hour, now_min = time.localtime().tm_hour, time.localtime().tm_min
    sched_hour, sched_min = map(int, run_time.split(":"))
    past_run_time = (now_hour, now_min) >= (sched_hour, sched_min)
    if past_run_time and load_digest(date.today()) is None:
        logger.info("今日日报尚未生成（错过定时或首次启动），立即补跑...")
        threading.Thread(target=run_digest, daemon=True).start()

    # Schedule daily digest at run_time
    schedule.every().day.at(run_time).do(run_digest)
    logger.info(f"Scheduler started. Daily digest will run at {run_time}.")
    logger.info(f"Web UI available at http://localhost:{os.environ.get('WEB_PORT', '5000')}")
    logger.info("Press Ctrl+C to stop.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Stopped.")


if __name__ == "__main__":
    main()
