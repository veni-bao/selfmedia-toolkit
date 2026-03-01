#!/usr/bin/env python3
"""
热点监控脚本 - 抓取多平台热榜
支持：微博热搜、知乎热榜、抖音热点、B站热门、36氪
输出：按热度排序的JSON + Markdown日报
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from html.parser import HTMLParser


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

OUTPUT_DIR = Path(__file__).parent.parent / "hot_topics"
OUTPUT_DIR.mkdir(exist_ok=True)


def fetch_url(url: str, timeout: int = 10) -> str:
    """Fetch URL content."""
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [fetch error] {url}: {e}")
        return ""


# ──────────────────────────────────────────────
# 微博热搜
# ──────────────────────────────────────────────
def fetch_weibo() -> list[dict]:
    """Fetch Weibo hot search via public API."""
    url = "https://weibo.com/ajax/side/hotSearch"
    try:
        html = fetch_url(url)
        data = json.loads(html)
        items = data.get("data", {}).get("realtime", [])
        results = []
        for item in items[:20]:
            note = item.get("note", "")
            if not note:
                continue
            results.append({
                "source": "微博热搜",
                "title": note,
                "hot": item.get("num", 0),
                "url": f"https://s.weibo.com/weibo?q={note}",
            })
        return results
    except Exception as e:
        print(f"  [weibo] {e}")
        return []


# ──────────────────────────────────────────────
# 知乎热榜
# ──────────────────────────────────────────────
def fetch_zhihu() -> list[dict]:
    """Fetch Zhihu hot list via API."""
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20"
    try:
        html = fetch_url(url)
        data = json.loads(html)
        results = []
        for item in data.get("data", []):
            target = item.get("target", {})
            title = target.get("title", "")
            qid = target.get("id", "")
            if title:
                results.append({
                    "source": "知乎热榜",
                    "title": title,
                    "hot": item.get("detail_text", ""),
                    "url": f"https://www.zhihu.com/question/{qid}",
                })
        return results
    except Exception as e:
        print(f"  [zhihu] {e}")
        return []


# ──────────────────────────────────────────────
# 36氪热文
# ──────────────────────────────────────────────
def fetch_36kr() -> list[dict]:
    """Fetch 36Kr hot articles via RSS."""
    url = "https://36kr.com/feed"
    try:
        html = fetch_url(url)
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", html)
        links = re.findall(r"<link>(https://36kr\.com/p/\d+)</link>", html)
        results = []
        for title, link in zip(titles[:15], links[:15]):
            if title and "36氪" not in title:
                results.append({
                    "source": "36氪",
                    "title": title.strip(),
                    "hot": "",
                    "url": link,
                })
        return results
    except Exception as e:
        print(f"  [36kr] {e}")
        return []


# ──────────────────────────────────────────────
# 少数派 SSPAI
# ──────────────────────────────────────────────
def fetch_sspai() -> list[dict]:
    """Fetch SSPAI hot articles via RSS."""
    url = "https://sspai.com/feed"
    try:
        html = fetch_url(url)
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", html)
        links = re.findall(r"<link>(https://sspai\.com/post/\d+)</link>", html)
        results = []
        for title, link in zip(titles[:10], links[:10]):
            if title and "少数派" not in title:
                results.append({
                    "source": "少数派",
                    "title": title.strip(),
                    "hot": "",
                    "url": link,
                })
        return results
    except Exception as e:
        print(f"  [sspai] {e}")
        return []


# ──────────────────────────────────────────────
# Hacker News（英文热点，适合技术内容参考）
# ──────────────────────────────────────────────
def fetch_hackernews() -> list[dict]:
    """Fetch HackerNews top stories."""
    try:
        ids_raw = fetch_url("https://hacker-news.firebaseio.com/v0/topstories.json")
        ids = json.loads(ids_raw)[:10]
        results = []
        for story_id in ids:
            item_raw = fetch_url(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            item = json.loads(item_raw)
            title = item.get("title", "")
            url = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
            score = item.get("score", 0)
            if title:
                results.append({
                    "source": "Hacker News",
                    "title": title,
                    "hot": score,
                    "url": url,
                })
            time.sleep(0.1)
        return results
    except Exception as e:
        print(f"  [hackernews] {e}")
        return []


# ──────────────────────────────────────────────
# 汇总 & 输出
# ──────────────────────────────────────────────
def build_markdown(all_topics: list[dict], date_str: str) -> str:
    lines = [
        f"# 🔥 热点日报 — {date_str}",
        "",
        f"> 共 {len(all_topics)} 条热点，来源：微博、知乎、36氪、少数派、Hacker News",
        "",
    ]
    by_source: dict[str, list] = {}
    for item in all_topics:
        by_source.setdefault(item["source"], []).append(item)

    for source, items in by_source.items():
        lines.append(f"## {source}")
        lines.append("")
        for i, item in enumerate(items, 1):
            hot_str = f" `{item['hot']}`" if item.get("hot") else ""
            lines.append(f"{i}. [{item['title']}]({item['url']}){hot_str}")
        lines.append("")

    return "\n".join(lines)


def run():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M")
    file_date = now.strftime("%Y-%m-%d")

    print(f"\n{'='*50}")
    print(f"  热点监控 — {date_str}")
    print(f"{'='*50}\n")

    all_topics = []

    print("[微博热搜]")
    all_topics.extend(fetch_weibo())
    print(f"  → {len([x for x in all_topics if x['source']=='微博热搜'])} 条")

    print("[知乎热榜]")
    all_topics.extend(fetch_zhihu())
    print(f"  → {len([x for x in all_topics if x['source']=='知乎热榜'])} 条")

    print("[36氪]")
    all_topics.extend(fetch_36kr())
    print(f"  → {len([x for x in all_topics if x['source']=='36氪'])} 条")

    print("[少数派]")
    all_topics.extend(fetch_sspai())
    print(f"  → {len([x for x in all_topics if x['source']=='少数派'])} 条")

    print("[Hacker News]")
    all_topics.extend(fetch_hackernews())
    print(f"  → {len([x for x in all_topics if x['source']=='Hacker News'])} 条")

    print(f"\n总计 {len(all_topics)} 条热点\n")

    # 保存 JSON
    json_path = OUTPUT_DIR / f"{file_date}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"date": date_str, "total": len(all_topics), "topics": all_topics},
                  f, ensure_ascii=False, indent=2)

    # 保存 Markdown
    md_content = build_markdown(all_topics, date_str)
    md_path = OUTPUT_DIR / f"{file_date}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"✅ 已保存：")
    print(f"   JSON: {json_path}")
    print(f"   Markdown: {md_path}")

    return all_topics


if __name__ == "__main__":
    run()
