#!/usr/bin/env python3
"""収集した記事をトピックごとの保存データにマージし、RSS 2.0 フィードを生成する。

使い方:
    python3 scripts/update_feed.py new_items.json

new_items.json の形式（配列）:
    [{"topic": "tech", "title": "...", "link": "https://...",
      "description": "要約", "source": "配信元名", "published": "2026-11-06T09:00:00+09:00"}]

- 同じリンクの記事は1件にまとめる（先に保存された方の取得時刻を維持）。
- 公開日時（無ければ取得時刻）から retention_hours（既定48時間）を過ぎた記事は削除する。
- 標準ライブラリのみ使用する。
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
TOPICS_FILE = ROOT / "topics.json"
DATA_DIR = ROOT / "data"
FEEDS_DIR = ROOT / "feeds"
FEED_BASE_URL = "https://raw.githubusercontent.com/doll-automatic/rss-news-page/main/feeds"


def parse_time(value):
    """ISO 8601 文字列を UTC の datetime にする。解釈できなければ None。"""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))  # タイムゾーン無しは日本時間とみなす
    return dt.astimezone(timezone.utc)


def valid_item(item):
    link = str(item.get("link", "")).strip()
    parts = urlsplit(link)
    return bool(str(item.get("title", "")).strip()) and parts.scheme in ("http", "https") and parts.netloc


def item_time(item):
    """保持期間の判定と並べ替えに使う時刻（公開日時、無ければ取得時刻）。"""
    return parse_time(item.get("published")) or parse_time(item["fetched_at"])


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def build_rss(topic, items, now):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = topic["title"]
    ET.SubElement(channel, "link").text = f"{FEED_BASE_URL}/{topic['slug']}.xml"
    ET.SubElement(channel, "description").text = f"Claude が Web 検索で収集したニュース（{topic['query_hints']}）"
    ET.SubElement(channel, "language").text = "ja"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(now)
    for item in items:
        el = ET.SubElement(channel, "item")
        ET.SubElement(el, "title").text = item["title"]
        ET.SubElement(el, "link").text = item["link"]
        ET.SubElement(el, "guid", isPermaLink="true").text = item["link"]
        # 配信元名は説明文の先頭に付ける（アプリはリンクのドメインも表示する）。
        prefix = f"【{item['source']}】" if item.get("source") else ""
        description = (prefix + item.get("description", "")).strip()
        if description:
            ET.SubElement(el, "description").text = description
        ET.SubElement(el, "pubDate").text = format_datetime(item_time(item))
    ET.indent(rss)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode") + "\n"


def main(new_items_path, now=None):
    now = now or datetime.now(timezone.utc)
    config = load_json(TOPICS_FILE, {})
    retention = timedelta(hours=config.get("retention_hours", 48))
    new_items = load_json(Path(new_items_path), [])
    DATA_DIR.mkdir(exist_ok=True)
    FEEDS_DIR.mkdir(exist_ok=True)

    for topic in config["topics"]:
        slug = topic["slug"]
        store_path = DATA_DIR / f"{slug}.json"
        stored = {i["link"]: i for i in load_json(store_path, [])}
        added = 0
        for raw in new_items:
            if raw.get("topic") != slug or not valid_item(raw):
                continue
            link = raw["link"].strip()
            if link in stored:
                continue
            stored[link] = {
                "title": raw["title"].strip(),
                "link": link,
                "description": str(raw.get("description") or "").strip(),
                "source": str(raw.get("source") or "").strip(),
                "published": raw.get("published") if parse_time(raw.get("published")) else None,
                "fetched_at": now.isoformat(),
            }
            added += 1

        # 未来の日時は取得時刻に置き換えてから、保持期間で絞り込み新しい順に並べる。
        for item in stored.values():
            if item.get("published") and parse_time(item["published"]) > now + timedelta(hours=1):
                item["published"] = None
        kept = sorted(
            (i for i in stored.values() if now - item_time(i) <= retention),
            key=item_time,
            reverse=True,
        )
        removed = len(stored) - len(kept)
        store_path.write_text(json.dumps(kept, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (FEEDS_DIR / f"{slug}.xml").write_text(build_rss(topic, kept, now), encoding="utf-8")
        print(f"{slug}: +{added} 件追加, -{removed} 件削除（期限切れ）, 計 {len(kept)} 件")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: update_feed.py new_items.json")
    main(sys.argv[1])
