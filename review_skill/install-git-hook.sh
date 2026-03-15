#!/bin/bash
#
# Git Hook 安装脚本
# 将 pre-push hook 安装到 .git/hooks/ 目录
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
HOOK_FILE="$HOOKS_DIR/pre-push"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Git Hook Installer${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查是否在 git 仓库中
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}❌ Error: Not a git repository${NC}"
    exit 1
fi

# 创建 hooks 目录（如果不存在）
mkdir -p "$HOOKS_DIR"

# 创建 pre-push hook 内容
cat > "$HOOK_FILE" << 'HOOK_CONTENT'
#!/bin/bash
#
# Git Pre-Push Hook
# 在 push 前自动执行代码审查
# 支持通过 --no-verify 或环境变量跳过检查
#

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Pre-Push Hook: Code Review Check${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查是否跳过审查
# 方式1: 使用 --no-verify (git 原生支持，此 hook 不会被执行)
# 方式2: 设置环境变量 SKIP_REVIEW=1
if [ "$SKIP_REVIEW" = "1" ] || [ "$SKIP_REVIEW" = "true" ]; then
    echo -e "${YELLOW}⚠️  SKIP_REVIEW is set, skipping code review...${NC}"
    exit 0
fi

# 方式3: 通过 git config 配置跳过
if git config --bool hooks.skip-review >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  hooks.skip-review is enabled, skipping code review...${NC}"
    exit 0
fi

# 获取项目根目录
PROJECT_ROOT=$(git rev-parse --show-toplevel)
REVIEW_SKILL_DIR="$PROJECT_ROOT/review_skill"

# 检查 review_skill 目录是否存在
if [ ! -d "$REVIEW_SKILL_DIR" ]; then
    echo -e "${RED}❌ Error: review_skill directory not found at $REVIEW_SKILL_DIR${NC}"
    echo -e "${YELLOW}   Push aborted.${NC}"
    exit 1
fi

# 检查 Python 是否可用
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 is not installed${NC}"
    exit 1
fi

# 切换到 review_skill 目录执行检查
cd "$REVIEW_SKILL_DIR"

# 检查依赖是否安装
if ! python3 -c "import git" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing dependencies...${NC}"
    pip3 install -r requirements.txt -q
fi

echo -e "${BLUE}🔍 Running code review...${NC}"
echo ""

# 执行代码审查并捕获输出
REVIEW_OUTPUT=$(python3 review.py 2>&1)
REVIEW_EXIT_CODE=$?

# 显示审查结果
echo "$REVIEW_OUTPUT"
echo ""

# 检查审查结果
if [ $REVIEW_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ❌ Code Review Failed${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${RED}Push rejected due to code quality issues.${NC}"
    echo ""
    echo -e "${YELLOW}To skip this check and push anyway, use:${NC}"
    echo -e "  ${GREEN}SKIP_REVIEW=1 git push${NC}"
    echo -e "  ${GREEN}git push --no-verify${NC} (not recommended)"
    echo ""
    exit 1
else
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✅ Code Review Passed${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    exit 0
fi
HOOK_CONTENT

# 设置执行权限
chmod +x "$HOOK_FILE"

# 安装 git-push-skip-review 命令到 PATH
SCRIPT_SOURCE="$SCRIPT_DIR/git-push-skip-review"
if [ -f "$SCRIPT_SOURCE" ]; then
    # 复制到 git 可执行路径
    GIT_BIN_DIR="$(git --exec-path)"
    if [ -d "$GIT_BIN_DIR" ] && [ -w "$GIT_BIN_DIR" ]; then
        cp "$SCRIPT_SOURCE" "$GIT_BIN_DIR/git-push-skip-review"
        chmod +x "$GIT_BIN_DIR/git-push-skip-review"
        echo -e "${GREEN}✅ Installed git push-skip-review command${NC}"
    else
        # 如果没有写权限，安装到项目 bin 目录
        PROJECT_BIN="$PROJECT_ROOT/bin"
        mkdir -p "$PROJECT_BIN"
        cp "$SCRIPT_SOURCE" "$PROJECT_BIN/git-push-skip-review"
        chmod +x "$PROJECT_BIN/git-push-skip-review"
        
        # 提示用户添加 PATH
        if ! echo "$PATH" | grep -q "$PROJECT_BIN"; then
            echo -e "${YELLOW}⚠️  Please add the following to your shell profile:${NC}"
            echo -e "   ${GREEN}export PATH=\"$PROJECT_BIN:\$PATH\"${NC}"
        fi
    fi
fi

echo -e "${GREEN}✅ Pre-push hook installed successfully!${NC}"
echo ""
echo -e "${BLUE}Hook location:${NC} $HOOK_FILE"
echo ""
echo -e "${YELLOW}Usage:${NC}"
echo "  git push                    # 自动执行代码审查"
echo "  git push-skip-review        # 跳过审查直接 push"
echo "  SKIP_REVIEW=1 git push      # 跳过审查"
echo "  git push --no-verify        # 跳过所有 hooks"
echo ""
echo -e "${YELLOW}Examples:${NC}"
echo "  git push-skip-review origin main"
echo "  git push-skip-review --force-with-lease origin feature-branch"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  git config hooks.skip-review true   # 永久禁用"
echo "  git config hooks.skip-review false  # 重新启用"
echo ""
