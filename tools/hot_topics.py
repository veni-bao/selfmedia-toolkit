#!/usr/bin/env python3
"""
热点监控脚本 v2 - 抓取多平台热榜
支持：微博热搜、知乎热榜、百度热搜、36氪、少数派、Hacker News
输出：按热度排序的JSON + Markdown日报

使用方法：
  python3 hot_topics.py         # 运行一次，保存结果
  python3 hot_topics.py --json  # 只输出JSON，不打印日志
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

OUTPUT_DIR = Path(__file__).parent.parent / "hot_topics"
OUTPUT_DIR.mkdir(exist_ok=True)

SILENT = "--json" in sys.argv


def log(msg: str):
    if not SILENT:
        print(msg)


def fetch_url(url: str, timeout: int = 12, extra_headers: dict = None) -> str:
    """Fetch URL content with retry."""
    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    req = Request(url, headers=headers)
    for attempt in range(2):
        try:
            with urlopen(req, timeout=timeout) as resp:
                charset = "utf-8"
                ct = resp.headers.get("Content-Type", "")
                if "charset=" in ct:
                    charset = ct.split("charset=")[-1].strip().split(";")[0]
                return resp.read().decode(charset, errors="replace")
        except (HTTPError, URLError) as e:
            log(f"  [fetch attempt {attempt+1}] {url}: {e}")
            if attempt == 0:
                time.sleep(1)
    return ""


# ──────────────────────────────────────────────
# 百度热搜（最可靠的中文热搜来源）
# ──────────────────────────────────────────────
def fetch_baidu() -> list[dict]:
    """Fetch Baidu hot search via API."""
    # 尝试百度实时热点API
    url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
    try:
        html = fetch_url(url, extra_headers={"Referer": "https://top.baidu.com/board"})
        data = json.loads(html)
        cards = data.get("data", {}).get("cards", [])
        results = []
        for card in cards:
            for item in card.get("content", []):
                title = item.get("word", "")
                hot = item.get("hotScore", "")
                desc = item.get("desc", "")
                if title:
                    results.append({
                        "source": "百度热搜",
                        "title": title,
                        "desc": desc,
                        "hot": hot,
                        "url": f"https://www.baidu.com/s?wd={title}",
                    })
        return results[:20]
    except Exception as e:
        log(f"  [baidu] {e}")

    # 备用：抓取百度热搜HTML
    try:
        url2 = "https://top.baidu.com/board?tab=realtime"
        html2 = fetch_url(url2, extra_headers={"Referer": "https://www.baidu.com"})
        titles = re.findall(r'"word":"([^"]+)"', html2)
        results2 = []
        for title in titles[:20]:
            results2.append({
                "source": "百度热搜",
                "title": title,
                "hot": "",
                "url": f"https://www.baidu.com/s?wd={title}",
            })
        return results2
    except Exception as e2:
        log(f"  [baidu fallback] {e2}")
        return []


# ──────────────────────────────────────────────
# 微博热搜
# ──────────────────────────────────────────────
def fetch_weibo() -> list[dict]:
    """Fetch Weibo hot search."""
    # 方法1：官方热搜API
    url = "https://weibo.com/ajax/side/hotSearch"
    try:
        html = fetch_url(url, extra_headers={
            "Cookie": "SUB=; SUBP=; Referer=https://weibo.com/",
            "Referer": "https://weibo.com/",
        })
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
        if results:
            return results
    except Exception as e:
        log(f"  [weibo v1] {e}")

    # 方法2：微博热搜页面
    try:
        url2 = "https://s.weibo.com/top/summary"
        html2 = fetch_url(url2, extra_headers={
            "Referer": "https://weibo.com/",
        })
        pattern = r'<td class="td-02"[^>]*><a[^>]*>([^<]+)</a>'
        titles = re.findall(pattern, html2)
        results2 = []
        for title in titles[:20]:
            title = title.strip()
            if title and len(title) > 2:
                results2.append({
                    "source": "微博热搜",
                    "title": title,
                    "hot": "",
                    "url": f"https://s.weibo.com/weibo?q={title}",
                })
        return results2
    except Exception as e2:
        log(f"  [weibo v2] {e2}")
        return []


# ──────────────────────────────────────────────
# 知乎热榜
# ──────────────────────────────────────────────
def fetch_zhihu() -> list[dict]:
    """Fetch Zhihu hot list."""
    # 方法1：官方API
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20"
    try:
        html = fetch_url(url, extra_headers={
            "X-Requested-With": "fetch",
            "Referer": "https://www.zhihu.com/",
            "X-Zse-93": "101_3_3.0",
        })
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
        if results:
            return results
    except Exception as e:
        log(f"  [zhihu v1] {e}")
    return []


# ──────────────────────────────────────────────
# 36氪热文
# ──────────────────────────────────────────────
def fetch_36kr() -> list[dict]:
    """Fetch 36Kr hot articles via RSS."""
    url = "https://36kr.com/feed"
    try:
        html = fetch_url(url)
        if not html:
            return []
        # CDATA格式
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", html)
        links = re.findall(r"<link>(https://36kr\.com/p/\d+)</link>", html)
        # 普通格式
        if not titles:
            titles = re.findall(r"<title>(?:<!\[CDATA\[)?([^<\]]+?)(?:\]\]>)?</title>", html)
        results = []
        for title, link in zip(titles[:15], links[:15]):
            title = title.strip()
            if title and "36氪" not in title and len(title) > 4:
                results.append({
                    "source": "36氪",
                    "title": title,
                    "hot": "",
                    "url": link,
                })
        return results[:10]
    except Exception as e:
        log(f"  [36kr] {e}")
        return []


# ──────────────────────────────────────────────
# 少数派 SSPAI
# ──────────────────────────────────────────────
def fetch_sspai() -> list[dict]:
    """Fetch SSPAI hot articles via RSS."""
    url = "https://sspai.com/feed"
    try:
        html = fetch_url(url)
        if not html:
            return []
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", html)
        links = re.findall(r"<link>(https://sspai\.com/post/\d+)</link>", html)
        if not titles:
            titles = re.findall(r"<title>(?:<!\[CDATA\[)?([^<\]]+?)(?:\]\]>)?</title>", html)
        results = []
        for title, link in zip(titles[:10], links[:10]):
            title = title.strip()
            if title and "少数派" not in title and len(title) > 4:
                results.append({
                    "source": "少数派",
                    "title": title,
                    "hot": "",
                    "url": link,
                })
        return results[:8]
    except Exception as e:
        log(f"  [sspai] {e}")
        return []


# ──────────────────────────────────────────────
# Hacker News（英文热点，适合技术内容参考）
# ──────────────────────────────────────────────
def fetch_hackernews() -> list[dict]:
    """Fetch HackerNews top stories."""
    try:
        ids_raw = fetch_url("https://hacker-news.firebaseio.com/v0/topstories.json")
        if not ids_raw:
            return []
        ids = json.loads(ids_raw)[:10]
        results = []
        for story_id in ids:
            item_raw = fetch_url(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            if not item_raw:
                continue
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
        log(f"  [hackernews] {e}")
        return []


# ──────────────────────────────────────────────
# 汇总 & 输出
# ──────────────────────────────────────────────
def build_markdown(all_topics: list[dict], date_str: str) -> str:
    """Build a nicely-formatted Markdown hot-topics report."""
    sources = list(dict.fromkeys(t["source"] for t in all_topics))
    total = len(all_topics)
    lines = [
        f"# 🔥 热点日报 — {date_str}",
        "",
        f"> 共 {total} 条热点｜来源：{' · '.join(sources)}",
        "",
    ]

    by_source: dict[str, list] = {}
    for item in all_topics:
        by_source.setdefault(item["source"], []).append(item)

    emoji_map = {
        "百度热搜": "🔴",
        "微博热搜": "🟠",
        "知乎热榜": "🔵",
        "36氪": "🟢",
        "少数派": "🟣",
        "Hacker News": "⚫",
    }

    for source, items in by_source.items():
        icon = emoji_map.get(source, "⚪")
        lines.append(f"## {icon} {source}")
        lines.append("")
        for i, item in enumerate(items, 1):
            hot_str = f" `{item['hot']}`" if item.get("hot") else ""
            desc = f"\n   > {item['desc']}" if item.get("desc") else ""
            lines.append(f"{i}. [{item['title']}]({item['url']}){hot_str}{desc}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 📌 内容建议",
        "",
        "根据以上热点，适合今日创作的角度：",
        "",
    ]

    # 简单选题建议：取前5个中文热搜
    cn_topics = [t for t in all_topics if t["source"] in ("百度热搜", "微博热搜", "知乎热榜")][:5]
    for t in cn_topics:
        lines.append(f"- **{t['title']}** — 可从个人视角/实操技巧/避坑指南切入")
    lines.append("")

    return "\n".join(lines)


def run():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M")
    file_date = now.strftime("%Y-%m-%d")

    log(f"\n{'='*52}")
    log(f"  🔥 热点监控 v2 — {date_str}")
    log(f"{'='*52}\n")

    all_topics: list[dict] = []

    def _add(source_name: str, fetcher):
        log(f"[{source_name}]")
        items = fetcher()
        all_topics.extend(items)
        log(f"  → {len(items)} 条\n")

    _add("百度热搜", fetch_baidu)
    _add("微博热搜", fetch_weibo)
    _add("知乎热榜", fetch_zhihu)
    _add("36氪", fetch_36kr)
    _add("少数派", fetch_sspai)
    _add("Hacker News", fetch_hackernews)

    log(f"\n📊 总计 {len(all_topics)} 条热点\n")

    # 保存 JSON
    json_path = OUTPUT_DIR / f"{file_date}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_str,
            "total": len(all_topics),
            "sources": {s: len([x for x in all_topics if x["source"] == s])
                        for s in dict.fromkeys(t["source"] for t in all_topics)},
            "topics": all_topics,
        }, f, ensure_ascii=False, indent=2)

    # 保存 Markdown
    md_content = build_markdown(all_topics, date_str)
    md_path = OUTPUT_DIR / f"{file_date}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    log(f"✅ 已保存：")
    log(f"   JSON: {json_path}")
    log(f"   Markdown: {md_path}")

    if SILENT:
        print(json.dumps({
            "date": date_str,
            "total": len(all_topics),
            "topics": all_topics,
        }, ensure_ascii=False))

    return all_topics


if __name__ == "__main__":
    run()
