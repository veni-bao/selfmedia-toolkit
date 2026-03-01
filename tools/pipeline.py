#!/usr/bin/env python3
"""
🚀 自媒体一键流水线 - 从热点到发布稿的全自动链路
用法：
  python3 pipeline.py              # 抓热点 → 写稿 → 生成发布计划
  python3 pipeline.py --topic 话题  # 指定话题，直接写稿
  python3 pipeline.py --report     # 只生成今日报告

完整流程：
  1. 热点监控：抓取百度/微博/知乎/HN 热榜
  2. 选题推荐：从热点中挑 3 个最有价值的话题
  3. AI写稿：生成小红书 + 知乎双版本草稿
  4. 发布计划：生成多平台发布时间表
  5. 摘要输出：控制台打印今日工作摘要
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# 添加 tools 目录到路径
TOOLS_DIR = Path(__file__).parent
ROOT_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

try:
    from hot_topics import run as fetch_hot_topics
    from ai_writer import generate_article, save_draft
    from publisher import create_schedule, save_schedule, print_schedule
    HAS_ALL = True
except ImportError as e:
    print(f"⚠️ 模块导入失败：{e}")
    HAS_ALL = False


# ─── 选题推荐 ────────────────────────────────────────────────────────────────

TOPIC_SCORE_KEYWORDS = {
    # 高分话题关键词（技术、AI、学习类容易产生高质量内容）
    "high": ["AI", "人工智能", "ChatGPT", "大学", "考研", "编程", "Python", "副业", "赚钱",
             "效率", "工具", "技术", "学习", "求职", "面试", "算法"],
    # 低分话题关键词（娱乐热点，时效性强但质量难保证）
    "low":  ["明星", "娱乐", "八卦", "综艺", "电影", "电视剧"],
}


def score_topic(title: str) -> int:
    """给话题打分（0-10），越高越适合创作"""
    score = 5  # 基础分
    title_upper = title.upper()
    for kw in TOPIC_SCORE_KEYWORDS["high"]:
        if kw.upper() in title_upper:
            score += 2
    for kw in TOPIC_SCORE_KEYWORDS["low"]:
        if kw.upper() in title_upper:
            score -= 2
    # 长度加分（太短的话题可能不具体）
    if len(title) > 8:
        score += 1
    return max(0, min(10, score))


def recommend_topics(all_topics: list[dict], top_n: int = 3) -> list[dict]:
    """从所有热点中推荐最值得写的话题"""
    # 只取中文平台的话题
    cn_sources = {"百度热搜", "微博热搜", "知乎热榜", "36氪", "少数派"}
    cn_topics = [t for t in all_topics if t.get("source") in cn_sources]

    if not cn_topics:
        cn_topics = all_topics[:10]

    # 打分排序
    scored = [(score_topic(t["title"]), t) for t in cn_topics]
    scored.sort(key=lambda x: x[0], reverse=True)

    return [t for _, t in scored[:top_n]]


# ─── 主流水线 ────────────────────────────────────────────────────────────────

def run_pipeline(
    force_topic: str = None,
    api_key: str = None,
    platforms: list[str] = None,
    silent: bool = False,
) -> dict:
    """
    执行完整的内容生产流水线。
    返回本次运行的摘要字典。
    """
    if platforms is None:
        platforms = ["xiaohongshu", "zhihu", "weixin"]

    start = datetime.now()
    summary = {
        "run_at": start.strftime("%Y-%m-%d %H:%M"),
        "topics": [],
        "drafts": [],
        "schedules": [],
        "errors": [],
    }

    def log(msg: str):
        if not silent:
            print(msg)

    log(f"\n{'='*60}")
    log(f"  🚀 自媒体流水线 — {start.strftime('%Y-%m-%d %H:%M')}")
    log(f"{'='*60}\n")

    # ─── Step 1: 获取热点 ─────────────────────────────────────────────────
    if force_topic:
        topics_to_write = [{"title": force_topic, "source": "手动指定", "url": ""}]
        log(f"📌 手动指定话题：{force_topic}\n")
    else:
        log("📡 Step 1 - 抓取热点榜单...")
        try:
            all_topics = fetch_hot_topics()
            topics_to_write = recommend_topics(all_topics)
            log(f"  抓取到 {len(all_topics)} 条热点，推荐 {len(topics_to_write)} 个话题\n")
        except Exception as e:
            log(f"  ⚠️ 热点抓取失败：{e}")
            summary["errors"].append(f"热点抓取失败: {e}")
            # 使用备用话题
            topics_to_write = [
                {"title": "大学生如何用AI提升学习效率", "source": "备用", "url": ""},
                {"title": "2026年最值得学的编程技能", "source": "备用", "url": ""},
            ]

    summary["topics"] = [t["title"] for t in topics_to_write]

    # ─── Step 2: AI写稿 ──────────────────────────────────────────────────
    log("✍️  Step 2 - AI生成草稿...")
    for topic_item in topics_to_write:
        topic = topic_item["title"]
        log(f"\n  话题：{topic}")

        for platform in ["xiaohongshu", "zhihu"]:  # 每个话题生成两个版本
            try:
                content = generate_article(topic, platform, api_key)
                path = save_draft(topic, platform, content)
                summary["drafts"].append(str(path))
                log(f"  ✅ [{platform}] 草稿已生成：{path.name}")
            except Exception as e:
                log(f"  ❌ [{platform}] 生成失败：{e}")
                summary["errors"].append(f"写稿失败 ({topic}/{platform}): {e}")

    # ─── Step 3: 生成发布计划 ────────────────────────────────────────────
    log("\n📅 Step 3 - 生成发布计划...")
    if topics_to_write:
        main_topic = topics_to_write[0]["title"]
        # 加载刚生成的草稿内容
        draft_files = sorted(
            ROOT_DIR.glob("drafts/*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if draft_files:
            latest_draft = draft_files[0].read_text(encoding="utf-8")
        else:
            latest_draft = f"关于《{main_topic}》的深度分析..."

        try:
            schedule = create_schedule(main_topic, latest_draft, platforms)
            sch_path = save_schedule(schedule)
            summary["schedules"].append(str(sch_path))
            if not silent:
                print_schedule(schedule)
            log(f"✅ 发布计划已保存：{sch_path.name}")
        except Exception as e:
            log(f"⚠️ 发布计划生成失败：{e}")
            summary["errors"].append(f"发布计划失败: {e}")

    # ─── 完成摘要 ─────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).seconds
    log(f"\n{'='*60}")
    log(f"  🎉 流水线完成！耗时 {elapsed}s")
    log(f"  话题数：{len(summary['topics'])}")
    log(f"  草稿数：{len(summary['drafts'])}")
    log(f"  发布计划：{len(summary['schedules'])}")
    if summary["errors"]:
        log(f"  ⚠️ 错误：{len(summary['errors'])} 个")
    log(f"{'='*60}\n")

    # 保存摘要
    summary_path = ROOT_DIR / "hot_topics" / f"pipeline_{start.strftime('%Y%m%d_%H%M')}.json"
    summary_path.parent.mkdir(exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    force_topic = None
    api_key = None
    report_only = "--report" in args

    if "--topic" in args:
        idx = args.index("--topic")
        force_topic = args[idx + 1] if idx + 1 < len(args) else None

    if "--api-key" in args:
        idx = args.index("--api-key")
        api_key = args[idx + 1] if idx + 1 < len(args) else None

    if report_only:
        # 只生成联盟营销报告
        sys.path.insert(0, str(TOOLS_DIR))
        try:
            from affiliate_tracker import generate_report, init_sample_data
            init_sample_data()
            report = generate_report()
            print(report)
        except Exception as e:
            print(f"❌ 报告生成失败：{e}")
    else:
        run_pipeline(force_topic=force_topic, api_key=api_key)


if __name__ == "__main__":
    main()
