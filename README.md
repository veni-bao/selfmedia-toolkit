# 🚀 自媒体变现工具箱

> 面向技术人的自媒体 + AI 变现工具集，帮助你用技术手段批量生产内容、追踪收益、管理分发。

---

## 📦 工具清单

| 工具 | 文件 | 功能 |
|------|------|------|
| 🔥 热点监控 | `tools/hot_topics.py` | 抓取微博/知乎/36氪/少数派/HN热榜 |
| ✍️ AI写稿流水线 | `tools/ai_writer.py` | 一键生成小红书/知乎/公众号风格内容 |
| 📅 内容分发调度 | `tools/publisher.py` | 多平台发布计划管理，计算最佳发布时段 |
| 💰 联盟营销追踪 | `tools/affiliate_tracker.py` | 管理推广链接、记录点击转化、生成周报 |
| 🌐 AI工具导航站 | `ai-nav-site/index.html` | 静态导航网站，收录50+ AI工具，可直接部署 |
| 🎯 一键启动 | `run.sh` | 集成所有工具的交互式入口 |

---

## 🚀 快速开始

```bash
git clone https://github.com/veni-bao/selfmedia-toolkit.git
cd selfmedia-toolkit

# 一键启动交互式菜单
./run.sh help

# 各工具独立运行
python3 tools/hot_topics.py          # 抓取今日热点
python3 tools/ai_writer.py           # AI写稿（交互式）
python3 tools/publisher.py demo      # 演示发布计划
python3 tools/affiliate_tracker.py   # 生成联盟营销报告
```

---

## 🛠️ 工具详解

### 1. 热点监控 `hot_topics.py`

多平台热榜聚合，无需 API key，开箱即用。

```bash
python3 tools/hot_topics.py
# 输出：hot_topics/2026-03-02.md（Markdown日报）
#       hot_topics/2026-03-02.json（结构化数据）
```

**数据源：**
- 微博热搜（Top 20）
- 知乎热榜（Top 20）
- 36氪热文（RSS）
- 少数派（RSS）
- Hacker News Top 10（英文技术热点）

---

### 2. AI写稿流水线 `ai_writer.py`

给话题，出文章。支持三种平台风格，有 API key 时直接调用 GPT，没有则给出详细写作框架。

```bash
# 交互式
python3 tools/ai_writer.py

# 命令行参数
python3 tools/ai_writer.py "大学生如何用AI赚钱" xiaohongshu
python3 tools/ai_writer.py "Python学习路线" zhihu YOUR_OPENAI_KEY

# 支持平台：xiaohongshu / zhihu / weixin
```

**输出：** `drafts/20260302_0930_xiaohongshu_大学生如何用AI赚钱.md`

---

### 3. 内容分发调度 `publisher.py`

把一篇草稿自动格式化并分发到多个平台，计算最佳发布时间。

```bash
# 演示
python3 tools/publisher.py demo

# 为草稿创建发布计划
python3 tools/publisher.py schedule drafts/my_article.md xiaohongshu,zhihu,weixin

# 查看所有待发布内容
python3 tools/publisher.py list
```

**最佳发布时段参考：**
| 平台 | 推荐时间 |
|------|---------|
| 小红书 | 07:00 / 12:00 / 21:00 |
| 公众号 | 07:30 / 12:00 / 20:30 |
| 知乎 | 09:00 / 13:00 / 20:00 |
| B站专栏 | 11:00 / 18:00 / 21:00 |
| 抖音 | 07:00 / 12:00 / 18:00 / 21:00 |

---

### 4. 联盟营销追踪 `affiliate_tracker.py`

管理所有推广链接，记录点击和转化，自动生成佣金周报。

```bash
# 生成报告（首次运行自动生成示例数据）
python3 tools/affiliate_tracker.py report

# 添加新推广链接
python3 tools/affiliate_tracker.py add "Notion Pro" "https://notion.so" "https://notion.so?ref=YOUR_ID" "Notion联盟" 50.0 96.0

# 记录点击
python3 tools/affiliate_tracker.py click lnk_xxxxxxxx 微博

# 记录转化
python3 tools/affiliate_tracker.py convert lnk_xxxxxxxx 96.0
```

**适合接入的联盟平台：**
- 🌍 海外：Notion、Cursor、Vercel（佣金 20-50%）
- 🇨🇳 国内：京东联盟、淘宝客、爱发卡代销

---

### 5. AI工具导航站 `ai-nav-site/`

收录 50+ AI工具的静态网站，支持分类筛选和全文搜索，无需后端，直接部署即用。

**一键部署到 Vercel：**
```bash
npm i -g vercel
vercel ai-nav-site/
```

**或部署到 GitHub Pages：**
1. 把 `ai-nav-site/index.html` 推到仓库
2. Settings → Pages → Source 选 main branch
3. 完成 🎉

**变现方式：**
- 推广位销售（¥99-999/月/位）
- 在工具卡片中嵌入联盟链接
- Google AdSense / 国内广点通

---

## 💡 推荐工作流

```
每天 10 分钟完成内容生产：

1. python3 tools/hot_topics.py      # 5分钟：看今日热点
2. python3 tools/ai_writer.py       # 3分钟：选题 + 生成框架
3. python3 tools/publisher.py list  # 2分钟：确认发布计划
```

---

## 📊 变现路线图

```
第1个月：搭建工具，开通平台账号
第2-3月：日更内容，积累数据，摸索爆款规律
第3-6月：矩阵扩张，导航站上线接广告，AI工具联盟收佣
第6-12月：稳定月入 3000-10000 元
```

---

## 📝 待办

- [ ] 自动发布脚本（调用各平台API）
- [ ] TTS 配音脚本（文章转短视频配音）
- [ ] 爱发卡自动发货配置指南
- [ ] 更多数据源（抖音热点、B站热门）

---

## License

MIT — 随便用，如果觉得有帮助，欢迎 Star ⭐
