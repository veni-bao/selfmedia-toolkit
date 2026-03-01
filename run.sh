#!/bin/bash
# 自媒体工具箱 一键启动脚本
# 用法: ./run.sh [命令]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$SCRIPT_DIR/tools"
HOT_TOPICS_DIR="$SCRIPT_DIR/hot_topics"
DRAFTS_DIR="$SCRIPT_DIR/drafts"
DATA_DIR="$SCRIPT_DIR/affiliate_data"
NAV_SITE_DIR="$SCRIPT_DIR/ai-nav-site"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════╗"
    echo "║       🚀 自媒体工具箱 v1.0              ║"
    echo "║  热点监控 | AI写稿 | 分发调度 | 佣金追踪  ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

help() {
    banner
    echo "可用命令："
    echo "  hot       — 抓取今日热点榜单"
    echo "  write     — AI写稿（交互式）"
    echo "  publish   — 查看/创建发布计划"
    echo "  affiliate — 联盟营销报告"
    echo "  all       — 完整工作流（热点→写稿→调度）"
    echo "  nav       — 在浏览器打开AI导航站"
    echo ""
    echo "示例："
    echo "  ./run.sh hot"
    echo "  ./run.sh write"
    echo "  ./run.sh affiliate"
}

check_python() {
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}❌ 未找到 python3，请先安装 Python 3.8+${NC}"
        exit 1
    fi
}

cmd_hot() {
    echo -e "${YELLOW}📡 正在抓取热点榜单...${NC}"
    check_python
    python3 "$TOOLS_DIR/hot_topics.py"
    echo ""
    echo -e "${GREEN}✅ 热点数据保存至：$HOT_TOPICS_DIR/${NC}"
    # 显示今日热点摘要
    TODAY=$(date +%Y-%m-%d)
    if [ -f "$HOT_TOPICS_DIR/$TODAY.md" ]; then
        echo ""
        echo "📋 今日热点摘要（前10条）："
        head -30 "$HOT_TOPICS_DIR/$TODAY.md" | tail -20
    fi
}

cmd_write() {
    check_python
    echo -e "${YELLOW}✍️  AI写稿流水线${NC}"
    echo ""

    # 如果有今日热点，展示供参考
    TODAY=$(date +%Y-%m-%d)
    if [ -f "$HOT_TOPICS_DIR/$TODAY.md" ]; then
        echo "💡 今日热点参考（选一个话题写稿）："
        grep "^[0-9]" "$HOT_TOPICS_DIR/$TODAY.md" | head -10 | sed 's/^/   /'
        echo ""
    fi

    read -p "话题（直接回车用默认）：" TOPIC
    echo ""
    echo "平台选择："
    echo "  1. xiaohongshu — 小红书"
    echo "  2. zhihu       — 知乎"
    echo "  3. weixin      — 公众号"
    read -p "选择平台（1/2/3，默认1）：" PLATFORM_NUM
    case "$PLATFORM_NUM" in
        2) PLATFORM="zhihu" ;;
        3) PLATFORM="weixin" ;;
        *) PLATFORM="xiaohongshu" ;;
    esac
    echo ""
    python3 "$TOOLS_DIR/ai_writer.py" "${TOPIC:-}" "$PLATFORM"
}

cmd_publish() {
    check_python
    echo -e "${YELLOW}📅 发布计划管理${NC}"
    python3 "$TOOLS_DIR/publisher.py" list
    echo ""
    read -p "为最新草稿创建发布计划？(y/N) " CONFIRM
    if [[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]]; then
        LATEST=$(ls -t "$DRAFTS_DIR"/*.md 2>/dev/null | head -1)
        if [ -z "$LATEST" ]; then
            echo "暂无草稿文件，请先运行 ./run.sh write"
        else
            echo "使用草稿：$LATEST"
            python3 "$TOOLS_DIR/publisher.py" schedule "$LATEST"
        fi
    fi
}

cmd_affiliate() {
    check_python
    echo -e "${YELLOW}💰 联盟营销报告${NC}"
    python3 "$TOOLS_DIR/affiliate_tracker.py" report
    echo ""
    echo -e "${GREEN}完整报告：$DATA_DIR/report.md${NC}"
}

cmd_nav() {
    NAV_FILE="$NAV_SITE_DIR/index.html"
    if [ ! -f "$NAV_FILE" ]; then
        echo -e "${RED}❌ AI导航站文件不存在：$NAV_FILE${NC}"
        exit 1
    fi
    echo -e "${GREEN}🌐 AI导航站：$NAV_FILE${NC}"
    if command -v open &>/dev/null; then
        open "$NAV_FILE"
    elif command -v xdg-open &>/dev/null; then
        xdg-open "$NAV_FILE"
    else
        echo "请手动用浏览器打开上述文件"
    fi
}

cmd_all() {
    banner
    echo -e "${BLUE}🔄 执行完整工作流...${NC}"
    echo ""

    echo "步骤 1/3：抓取热点"
    cmd_hot
    echo ""

    echo "步骤 2/3：AI写稿（演示模式）"
    check_python
    TOPIC="今天最热门的AI工具有哪些"
    python3 "$TOOLS_DIR/ai_writer.py" "$TOPIC" "xiaohongshu"
    echo ""

    echo "步骤 3/3：创建发布计划"
    LATEST=$(ls -t "$DRAFTS_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        python3 "$TOOLS_DIR/publisher.py" schedule "$LATEST" "xiaohongshu,zhihu,weixin"
    fi

    echo ""
    echo -e "${GREEN}✅ 工作流完成！${NC}"
    echo "  热点数据：$HOT_TOPICS_DIR/"
    echo "  草稿文件：$DRAFTS_DIR/"
    echo "  发布计划：$SCRIPT_DIR/publish_schedule/"
}

# 主逻辑
CMD="${1:-help}"

case "$CMD" in
    hot)       banner; cmd_hot ;;
    write)     banner; cmd_write ;;
    publish)   banner; cmd_publish ;;
    affiliate) banner; cmd_affiliate ;;
    nav)       banner; cmd_nav ;;
    all)       cmd_all ;;
    help|*)    help ;;
esac
