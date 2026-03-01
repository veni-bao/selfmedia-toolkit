#!/usr/bin/env python3
"""
AI写稿流水线 - 给定话题，自动生成适合各平台发布的文章
支持：小红书风格、知乎风格、公众号风格
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# ─── 平台模板 ───────────────────────────────────────────────────────────────

PLATFORM_PROMPTS = {
    "xiaohongshu": """你是一个小红书爆款内容创作者。
根据话题写一篇小红书笔记，要求：
- 标题包含emoji，吸引眼球，带数字
- 正文分点，每点一个emoji开头
- 末尾加3-5个相关话题标签（#话题）
- 语气轻松，像朋友分享
- 字数400-600字
- 结尾有互动引导（"你们觉得呢？"等）
话题：{topic}
""",
    "zhihu": """你是知乎专业答主。
根据话题写一篇知乎回答，要求：
- 开头用一句有力的论点或故事吸引注意
- 结构清晰，有小标题
- 引用数据或案例支撑观点
- 语气专业但不枯燥
- 字数800-1500字
- 结尾总结要点
话题：{topic}
""",
    "weixin": """你是公众号主笔。
根据话题写一篇公众号文章，要求：
- 标题10字以内，引发好奇或共鸣
- 开头故事/痛点切入，3句以内
- 正文分3-5个核心观点，每段有小标题
- 语气有温度，像和读者对话
- 字数1000-2000字
- 结尾引导关注/转发
话题：{topic}
""",
}

OUTPUT_DIR = Path(__file__).parent.parent / "drafts"
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_article(topic: str, platform: str, api_key: str = None) -> str:
    """
    Generate article for given topic and platform.
    If api_key is provided, calls OpenAI-compatible API.
    Otherwise returns a template with instructions.
    """
    prompt_template = PLATFORM_PROMPTS.get(platform, PLATFORM_PROMPTS["zhihu"])
    prompt = prompt_template.format(topic=topic)

    if api_key:
        return _call_api(prompt, api_key)
    else:
        # 返回写作指南（无API时）
        return _template_guide(topic, platform, prompt)


def _call_api(prompt: str, api_key: str) -> str:
    """Call OpenAI-compatible API."""
    import urllib.request
    import json

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]


def _template_guide(topic: str, platform: str, prompt: str) -> str:
    """Generate a structured writing guide without API."""
    guides = {
        "xiaohongshu": f"""# 📝 小红书写作指南 — {topic}

## 推荐标题（选一个）
- 🔥 {topic}，这{len(topic)+3}件事你必须知道！
- 💡 关于{topic}，我踩过的坑全在这里了
- ✨ {topic}完全指南｜建议收藏

## 正文结构
✅ **第一点**：[核心信息/技巧1]
→ 详细说明，加个人体验

💡 **第二点**：[核心信息/技巧2]  
→ 数据/案例支撑

🎯 **第三点**：[核心信息/技巧3]
→ 实操步骤

⚠️ **注意事项**：
→ 常见误区提醒

## 结尾互动
"你们试过吗？评论区告诉我！"

## 话题标签
#{topic} #干货分享 #经验总结 #必看 #收藏

---
*使用 AI 自动填充内容后发布*
""",
        "zhihu": f"""# 📝 知乎回答框架 — {topic}

## 开篇（抓注意力）
用一个反常识的数据或有趣故事开头...

## 核心观点
### 一、[第一个要点]
论据 + 数据 + 案例

### 二、[第二个要点]
论据 + 数据 + 案例

### 三、[第三个要点]
论据 + 数据 + 案例

## 总结
重申核心观点，给读者可操作的建议

---
*配合AI API可自动生成完整内容*
""",
    }
    return guides.get(platform, guides["zhihu"])


def save_draft(topic: str, platform: str, content: str) -> Path:
    """Save article draft to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_topic = topic.replace("/", "_").replace(" ", "_")[:20]
    filename = f"{timestamp}_{platform}_{safe_topic}.md"
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def run(topic: str = None, platform: str = "xiaohongshu", api_key: str = None):
    if not topic:
        topic = input("请输入话题：").strip()
        if not topic:
            topic = "大学生如何用AI提升学习效率"

    print(f"\n{'='*50}")
    print(f"  AI写稿流水线")
    print(f"  话题：{topic}")
    print(f"  平台：{platform}")
    print(f"{'='*50}\n")

    content = generate_article(topic, platform, api_key)
    path = save_draft(topic, platform, content)

    print(content)
    print(f"\n✅ 已保存到：{path}")
    return content, path


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else None
    platform = sys.argv[2] if len(sys.argv) > 2 else "xiaohongshu"
    api_key = sys.argv[3] if len(sys.argv) > 3 else None
    run(topic, platform, api_key)
