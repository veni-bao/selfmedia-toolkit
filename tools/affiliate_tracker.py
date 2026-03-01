#!/usr/bin/env python3
"""
联盟营销追踪工具 - 管理推广链接、记录点击、统计佣金
支持：淘宝客、京东联盟、海外Affiliate（Gumroad/Notion等）
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

DATA_DIR = Path(__file__).parent.parent / "affiliate_data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "links.json"
LOG_PATH = DATA_DIR / "clicks.jsonl"
REPORT_PATH = DATA_DIR / "report.md"


# ─── 数据库操作 ──────────────────────────────────────────────────────────────

def load_db() -> dict:
    if DB_PATH.exists():
        with open(DB_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"links": [], "stats": {}}


def save_db(db: dict):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# ─── 链接管理 ────────────────────────────────────────────────────────────────

def add_link(
    name: str,
    original_url: str,
    affiliate_url: str,
    platform: str,
    commission_rate: float,
    product_price: float = 0.0,
    category: str = "其他",
    notes: str = "",
):
    """添加一条推广链接"""
    db = load_db()
    link_id = f"lnk_{int(time.time())}"
    entry = {
        "id": link_id,
        "name": name,
        "original_url": original_url,
        "affiliate_url": affiliate_url,
        "platform": platform,
        "commission_rate": commission_rate,
        "product_price": product_price,
        "category": category,
        "notes": notes,
        "clicks": 0,
        "conversions": 0,
        "total_commission": 0.0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    db["links"].append(entry)
    save_db(db)
    print(f"✅ 已添加推广链接：{name} [{link_id}]")
    return link_id


def record_click(link_id: str, source: str = "unknown"):
    """记录一次点击"""
    db = load_db()
    for link in db["links"]:
        if link["id"] == link_id:
            link["clicks"] += 1
            link["updated_at"] = datetime.now().isoformat()
            break
    save_db(db)

    # 追加到日志
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "event": "click",
            "link_id": link_id,
            "source": source,
            "ts": datetime.now().isoformat(),
        }, ensure_ascii=False) + "\n")


def record_conversion(link_id: str, actual_amount: float = 0.0):
    """记录一次成功转化（购买）"""
    db = load_db()
    for link in db["links"]:
        if link["id"] == link_id:
            link["conversions"] += 1
            commission = actual_amount * link["commission_rate"] / 100 if actual_amount else \
                         link["product_price"] * link["commission_rate"] / 100
            link["total_commission"] += commission
            link["updated_at"] = datetime.now().isoformat()
            print(f"💰 转化记录：{link['name']} +¥{commission:.2f}")
            break
    save_db(db)


# ─── 统计报告 ────────────────────────────────────────────────────────────────

def generate_report() -> str:
    db = load_db()
    links = db["links"]
    if not links:
        return "暂无推广链接数据"

    total_clicks = sum(l["clicks"] for l in links)
    total_conversions = sum(l["conversions"] for l in links)
    total_commission = sum(l["total_commission"] for l in links)
    avg_cvr = (total_conversions / total_clicks * 100) if total_clicks else 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 📊 联盟营销周报 — {now}",
        "",
        "## 整体概览",
        f"- 推广链接总数：**{len(links)}**",
        f"- 总点击量：**{total_clicks}**",
        f"- 总转化量：**{total_conversions}**",
        f"- 平均转化率：**{avg_cvr:.1f}%**",
        f"- 累计佣金：**¥{total_commission:.2f}**",
        "",
        "## 各链接详情",
        "",
        "| 链接名称 | 平台 | 点击 | 转化 | 转化率 | 累计佣金 |",
        "|---------|------|-----|-----|-------|---------|",
    ]

    for link in sorted(links, key=lambda x: x["total_commission"], reverse=True):
        cvr = (link["conversions"] / link["clicks"] * 100) if link["clicks"] else 0
        lines.append(
            f"| {link['name']} | {link['platform']} | "
            f"{link['clicks']} | {link['conversions']} | "
            f"{cvr:.1f}% | ¥{link['total_commission']:.2f} |"
        )

    lines += [
        "",
        "## 按平台汇总",
        "",
    ]

    by_platform: dict[str, dict] = {}
    for link in links:
        p = link["platform"]
        if p not in by_platform:
            by_platform[p] = {"clicks": 0, "conversions": 0, "commission": 0.0}
        by_platform[p]["clicks"] += link["clicks"]
        by_platform[p]["conversions"] += link["conversions"]
        by_platform[p]["commission"] += link["total_commission"]

    for platform, stats in sorted(by_platform.items(), key=lambda x: x[1]["commission"], reverse=True):
        lines.append(f"### {platform}")
        lines.append(f"- 点击：{stats['clicks']} | 转化：{stats['conversions']} | 佣金：¥{stats['commission']:.2f}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 💡 优化建议",
        "",
    ]

    # 自动给出优化建议
    if links:
        best = max(links, key=lambda x: x["total_commission"])
        worst_clicked = [l for l in links if l["clicks"] > 0]
        if worst_clicked:
            worst = min(worst_clicked, key=lambda x: x["conversions"] / x["clicks"])
            lines.append(f"- 🏆 表现最佳：**{best['name']}**（佣金 ¥{best['total_commission']:.2f}）→ 加大推广力度")
            if worst["id"] != best["id"]:
                cvr = worst["conversions"] / worst["clicks"] * 100
                lines.append(f"- ⚠️ 需优化：**{worst['name']}**（转化率仅 {cvr:.1f}%）→ 考虑更换推广话术或替换产品")

    if avg_cvr < 1.0:
        lines.append("- 📌 整体转化率偏低，建议优化落地页文案或提升目标人群精准度")
    if total_clicks < 100:
        lines.append("- 📌 点击量不足，建议增加内容分发渠道（多平台铺量）")

    report = "\n".join(lines)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 报告已保存：{REPORT_PATH}")
    return report


# ─── 内置示例数据 ────────────────────────────────────────────────────────────

def init_sample_data():
    """初始化示例推广链接（可根据自己实际链接替换）"""
    db = load_db()
    if db["links"]:
        print("数据库已有数据，跳过初始化")
        return

    samples = [
        # 国内联盟
        {
            "name": "Notion Pro版",
            "original_url": "https://notion.so/pricing",
            "affiliate_url": "https://notion.so/pricing?ref=YOUR_ID",
            "platform": "Notion联盟",
            "commission_rate": 50.0,
            "product_price": 96.0,  # $8/月 ≈ ¥58，按¥96估算年费
            "category": "AI工具",
            "notes": "海外SaaS，佣金50%，通过联盟后台获取专属链接",
        },
        {
            "name": "Cursor Pro订阅",
            "original_url": "https://cursor.sh/pricing",
            "affiliate_url": "https://cursor.sh/pricing?ref=YOUR_ID",
            "platform": "Cursor联盟",
            "commission_rate": 20.0,
            "product_price": 240.0,  # $20/月
            "category": "AI工具",
            "notes": "AI编程工具，程序员群体转化率高",
        },
        {
            "name": "京东联盟-机械键盘",
            "original_url": "https://item.jd.com/xxxxx.html",
            "affiliate_url": "https://union-click.jd.com/jdc?xxxxx",
            "platform": "京东联盟",
            "commission_rate": 3.0,
            "product_price": 299.0,
            "category": "数码外设",
            "notes": "学习用品，大学生群体相关度高",
        },
        {
            "name": "爱发卡-雅思资料包",
            "original_url": "https://ifdian.net/xxxxx",
            "affiliate_url": "https://ifdian.net/xxxxx?ref=YOUR_ID",
            "platform": "爱发卡",
            "commission_rate": 15.0,
            "product_price": 49.0,
            "category": "考试备考",
            "notes": "自己发布的资料包，这里只是示例",
        },
    ]

    for s in samples:
        add_link(**s)

    # 模拟一些点击和转化数据
    db = load_db()
    for i, link in enumerate(db["links"]):
        clicks = [50, 120, 30, 80][i % 4]
        conversions = [3, 8, 1, 12][i % 4]
        link["clicks"] = clicks
        link["conversions"] = conversions
        link["total_commission"] = conversions * link["product_price"] * link["commission_rate"] / 100
    save_db(db)

    print("✅ 示例数据初始化完成！")


# ─── 主入口 ──────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2 or sys.argv[1] == "report":
        # 默认：生成报告
        init_sample_data()
        report = generate_report()
        print("\n" + "=" * 60)
        print(report)

    elif sys.argv[1] == "add":
        # 添加链接：python affiliate_tracker.py add "Notion" "url1" "url2" "平台" 50.0 96.0
        if len(sys.argv) < 7:
            print("用法：python affiliate_tracker.py add <名称> <原始URL> <推广URL> <平台> <佣金率%> [价格]")
            sys.exit(1)
        add_link(
            name=sys.argv[2],
            original_url=sys.argv[3],
            affiliate_url=sys.argv[4],
            platform=sys.argv[5],
            commission_rate=float(sys.argv[6]),
            product_price=float(sys.argv[7]) if len(sys.argv) > 7 else 0.0,
        )

    elif sys.argv[1] == "click":
        if len(sys.argv) < 3:
            print("用法：python affiliate_tracker.py click <link_id> [来源]")
            sys.exit(1)
        source = sys.argv[3] if len(sys.argv) > 3 else "manual"
        record_click(sys.argv[2], source)
        print(f"✅ 记录点击：{sys.argv[2]}")

    elif sys.argv[1] == "convert":
        if len(sys.argv) < 3:
            print("用法：python affiliate_tracker.py convert <link_id> [实际成交额]")
            sys.exit(1)
        amount = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        record_conversion(sys.argv[2], amount)

    else:
        print("可用命令：report / add / click / convert")
        print("示例：python affiliate_tracker.py report")


if __name__ == "__main__":
    main()
