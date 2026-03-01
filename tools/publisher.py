#!/usr/bin/env python3
"""
内容分发调度器 - 把AI生成的草稿按平台要求格式化，并生成发布清单
支持：公众号、小红书、知乎、B站专栏、抖音话题
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

DRAFTS_DIR = Path(__file__).parent.parent / "drafts"
SCHEDULE_DIR = Path(__file__).parent.parent / "publish_schedule"
SCHEDULE_DIR.mkdir(exist_ok=True)
DRAFTS_DIR.mkdir(exist_ok=True)

# ─── 平台发布最佳时段 ─────────────────────────────────────────────────────────
BEST_TIMES = {
    "xiaohongshu": ["07:00", "12:00", "21:00"],
    "weixin":       ["07:30", "12:00", "20:30"],
    "zhihu":        ["09:00", "13:00", "20:00"],
    "bilibili":     ["11:00", "18:00", "21:00"],
    "douyin":       ["07:00", "12:00", "18:00", "21:00"],
}

PLATFORM_NAMES = {
    "xiaohongshu": "小红书",
    "weixin":       "公众号",
    "zhihu":        "知乎",
    "bilibili":     "B站专栏",
    "douyin":       "抖音",
}

# ─── 格式化函数 ──────────────────────────────────────────────────────────────

def format_for_xiaohongshu(content: str, title: str) -> str:
    """小红书：强调换行、emoji、标签"""
    # 提取或生成标签
    tags = re.findall(r"#\S+", content)
    if not tags:
        tags = ["#干货分享", "#经验总结", "#生活技巧"]

    # 清理过多空行
    body = re.sub(r"\n{3,}", "\n\n", content.strip())

    result = f"{'🔥' * 3} {title} {'🔥' * 3}\n\n"
    result += body
    if not any(t in content for t in tags):
        result += f"\n\n{' '.join(tags[:5])}"
    return result


def format_for_zhihu(content: str, title: str) -> str:
    """知乎：支持Markdown，适合长篇"""
    return f"# {title}\n\n{content}"


def format_for_weixin(content: str, title: str) -> str:
    """公众号：HTML友好，重视排版"""
    body = content.strip()
    result = f"**{title}**\n\n---\n\n{body}\n\n---\n\n*觉得有用？点击右下角「在看」支持一下 ❤️*"
    return result


def format_for_bilibili(content: str, title: str) -> str:
    """B站专栏：Markdown"""
    return f"# {title}\n\n{content}\n\n---\n如果这篇文章对你有帮助，点赞+收藏是最大的支持！"


FORMATTERS = {
    "xiaohongshu": format_for_xiaohongshu,
    "weixin":       format_for_weixin,
    "zhihu":        format_for_zhihu,
    "bilibili":     format_for_bilibili,
}


# ─── 调度计划 ────────────────────────────────────────────────────────────────

def create_schedule(
    title: str,
    content: str,
    platforms: list[str],
    start_date: str = None,
) -> dict:
    """
    创建一篇内容的多平台发布计划
    策略：不同平台错开时间发布，避免同质内容同时出现
    """
    if start_date:
        base = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        base = datetime.now()

    schedule = {
        "title": title,
        "created_at": datetime.now().isoformat(),
        "items": [],
    }

    for i, platform in enumerate(platforms):
        best_times = BEST_TIMES.get(platform, ["09:00"])
        publish_time_str = best_times[i % len(best_times)]
        h, m = map(int, publish_time_str.split(":"))

        # 第一平台当天，后续每平台间隔1天
        pub_dt = base.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=i)

        formatter = FORMATTERS.get(platform, lambda c, t: c)
        formatted = formatter(content, title)

        item = {
            "platform": platform,
            "platform_name": PLATFORM_NAMES.get(platform, platform),
            "publish_at": pub_dt.strftime("%Y-%m-%d %H:%M"),
            "status": "pending",
            "formatted_content": formatted,
            "char_count": len(formatted),
        }
        schedule["items"].append(item)

    return schedule


def save_schedule(schedule: dict) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_title = re.sub(r"[^\w\u4e00-\u9fff]", "_", schedule["title"])[:20]
    filename = f"{timestamp}_{safe_title}.json"
    path = SCHEDULE_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
    return path


def print_schedule(schedule: dict):
    print(f"\n{'='*60}")
    print(f"📅 发布计划：{schedule['title']}")
    print(f"{'='*60}")
    for item in schedule["items"]:
        status_icon = {"pending": "⏳", "published": "✅", "failed": "❌"}.get(item["status"], "❓")
        print(f"\n{status_icon} {item['platform_name']} — {item['publish_at']}")
        print(f"   字数：{item['char_count']}")
        print(f"   内容预览：{item['formatted_content'][:80].replace(chr(10), ' ')}...")
    print()


def list_pending():
    """列出所有待发布的内容"""
    files = sorted(SCHEDULE_DIR.glob("*.json"), reverse=True)
    if not files:
        print("暂无发布计划")
        return

    print(f"\n📋 待发布内容（共 {len(files)} 个计划）\n")
    now = datetime.now()

    for f in files:
        with open(f, encoding="utf-8") as fp:
            s = json.load(fp)

        pending = [i for i in s["items"] if i["status"] == "pending"]
        published = [i for i in s["items"] if i["status"] == "published"]

        print(f"📝 {s['title']}")
        for item in s["items"]:
            pub_dt = datetime.strptime(item["publish_at"], "%Y-%m-%d %H:%M")
            delta = pub_dt - now
            if item["status"] == "pending":
                if delta.total_seconds() < 0:
                    status = "⚠️ 已过期"
                elif delta.total_seconds() < 3600:
                    status = f"🔴 {int(delta.total_seconds()/60)}分钟后"
                elif delta.total_seconds() < 86400:
                    status = f"🟡 {int(delta.total_seconds()/3600)}小时后"
                else:
                    status = f"🟢 {delta.days}天后"
            else:
                status = "✅ 已发布"
            print(f"   {item['platform_name']}: {item['publish_at']} — {status}")
        print()


# ─── 主入口 ──────────────────────────────────────────────────────────────────

DEMO_CONTENT = """很多人问我：大学期间如何利用AI提升效率？

我用了一年时间，总结出这套方法：

✅ **第一步：用AI辅助笔记**
把课堂录音丢给 Whisper 转文字，再让 Claude 整理成结构化笔记。
每周节省 5+ 小时整理时间。

✅ **第二步：用AI突破论文写作瓶颈**
不是让AI写论文（有学术诚信风险），而是让它：
- 帮你理清论证逻辑
- 检查论据漏洞
- 润色表达方式

✅ **第三步：用AI做代码助手**
Cursor / GitHub Copilot 是程序员的生产力倍增器。
写作业效率提升 3 倍不夸张。

⚠️ **注意事项**：
AI是工具，不是替代品。核心思考还是你来，AI负责执行。

你有什么用AI提效的技巧？评论区分享！

#AI工具 #大学生必看 #学习效率 #技术分享 #效率提升
"""


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"

    if cmd == "list":
        list_pending()

    elif cmd == "schedule":
        # 从草稿文件创建发布计划
        if len(sys.argv) < 3:
            print("用法：python publisher.py schedule <draft_file.md> [平台1,平台2,...]")
            sys.exit(1)

        draft_path = Path(sys.argv[2])
        if not draft_path.exists():
            print(f"文件不存在：{draft_path}")
            sys.exit(1)

        content = draft_path.read_text(encoding="utf-8")
        title = content.split("\n")[0].lstrip("#").strip() or draft_path.stem

        platforms_arg = sys.argv[3] if len(sys.argv) > 3 else "xiaohongshu,zhihu,weixin"
        platforms = [p.strip() for p in platforms_arg.split(",")]

        schedule = create_schedule(title, content, platforms)
        path = save_schedule(schedule)
        print_schedule(schedule)
        print(f"✅ 计划已保存：{path}")

    else:
        # demo：演示功能
        print("\n📣 内容分发调度器 — 演示模式\n")
        title = "大学生用AI提升效率的3个方法"
        platforms = ["xiaohongshu", "zhihu", "weixin", "bilibili"]

        schedule = create_schedule(title, DEMO_CONTENT, platforms)
        path = save_schedule(schedule)
        print_schedule(schedule)
        print(f"✅ 演示计划已保存：{path}")
        print("\n提示：运行 `python publisher.py list` 查看所有待发布内容")


if __name__ == "__main__":
    main()
