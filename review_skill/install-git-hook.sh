#!/bin/bash
#
# Git Hook Installation Script
# Installs pre-push hook to .git/hooks/ directory
#

set -e

# Color definitions
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

# Check if in git repository
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}❌ Error: Not a git repository${NC}"
    exit 1
fi

# Create hooks directory (if not exists)
mkdir -p "$HOOKS_DIR"

# Create pre-push hook content
cat > "$HOOK_FILE" << 'HOOK_CONTENT'
#!/bin/bash
#
# Git Pre-Push Hook
# Automatically executes code review before push
# Supports skipping check via --no-verify or environment variable
#

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Pre-Push Hook: Code Review Check${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if review should be skipped
# Method 1: Use --no-verify (git native support, this hook will not be executed)
# Method 2: Set environment variable SKIP_REVIEW=1
if [ "$SKIP_REVIEW" = "1" ] || [ "$SKIP_REVIEW" = "true" ]; then
    echo -e "${YELLOW}⚠️  SKIP_REVIEW is set, skipping code review...${NC}"
    exit 0
fi

# Method 3: Skip via git config
if git config --bool hooks.skip-review >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  hooks.skip-review is enabled, skipping code review...${NC}"
    exit 0
fi

# Get project root directory
PROJECT_ROOT=$(git rev-parse --show-toplevel)
REVIEW_SKILL_DIR="$PROJECT_ROOT/review_skill"

# Check if review_skill directory exists
if [ ! -d "$REVIEW_SKILL_DIR" ]; then
    echo -e "${RED}❌ Error: review_skill directory not found at $REVIEW_SKILL_DIR${NC}"
    echo -e "${YELLOW}   Push aborted.${NC}"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 is not installed${NC}"
    exit 1
fi

# Switch to review_skill directory and execute check
cd "$REVIEW_SKILL_DIR"

# Check if dependencies are installed
if ! python3 -c "import yaml" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing dependencies...${NC}"
    pip3 install -r requirements.txt -q
fi

echo -e "${BLUE}🔍 Running code review...${NC}"
echo ""

# Execute code review and capture output
REVIEW_OUTPUT=$(python3 review.py 2>&1)
REVIEW_EXIT_CODE=$?

# Display review results
echo "$REVIEW_OUTPUT"
echo ""

# Check review results
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

# Set execute permission
chmod +x "$HOOK_FILE"

# Install git-push-skip-review command to PATH
SCRIPT_SOURCE="$SCRIPT_DIR/git-push-skip-review"
if [ -f "$SCRIPT_SOURCE" ]; then
    # Copy to git executable path
    GIT_BIN_DIR="$(git --exec-path)"
    if [ -d "$GIT_BIN_DIR" ] && [ -w "$GIT_BIN_DIR" ]; then
        cp "$SCRIPT_SOURCE" "$GIT_BIN_DIR/git-push-skip-review"
        chmod +x "$GIT_BIN_DIR/git-push-skip-review"
        echo -e "${GREEN}✅ Installed git push-skip-review command${NC}"
    else
        # If no write permission, install to project bin directory
        PROJECT_BIN="$PROJECT_ROOT/bin"
        mkdir -p "$PROJECT_BIN"
        cp "$SCRIPT_SOURCE" "$PROJECT_BIN/git-push-skip-review"
        chmod +x "$PROJECT_BIN/git-push-skip-review"
        
        # Prompt user to add PATH
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
echo "  git push                    # Automatically execute code review"
echo "  git push-skip-review        # Push directly without review"
echo "  SKIP_REVIEW=1 git push      # Skip review"
echo "  git push --no-verify        # Skip all hooks"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  git config hooks.skip-review true   # Disable permanently"
echo "  git config hooks.skip-review false  # Re-enable"
echo ""
