# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a dual-component repository containing:

1. **Android App** (`app/`): A Kotlin Android app demonstrating Flow and permission handling patterns with Jetpack Compose
2. **Review Skill** (`review_skill/`): A Python-based code review system that performs static analysis on Kotlin code using rule engines and AST parsing

## Common Commands

### Android App

```bash
# Build debug APK
./gradlew :app:assembleDebug

# Build release APK
./gradlew :app:assembleRelease

# Run unit tests
./gradlew :app:testDebugUnitTest

# Run a single test class
./gradlew :app:testDebugUnitTest --tests="com.yxhuang.flowforandroid.ExampleUnitTest"

# Run a single test method
./gradlew :app:testDebugUnitTest --tests="com.yxhuang.flowforandroid.ExampleUnitTest.addition_isCorrect"

# Run instrumentation tests (requires emulator/device)
./gradlew :app:connectedAndroidTest

# Run lint
./gradlew :app:lint

# Clean build
./gradlew clean
```

### Review Skill (Python)

```bash
cd review_skill

# Install dependencies
pip install -r requirements.txt

# Run code review on current git diff
python3 review.py

# Run all unit tests
python3 -m unittest discover test_rule

# Run specific test file
python3 -m unittest test_rule.test_batch1_rules

# Run specific test
python3 -m unittest test_rule.test_batch1_rules.test_memory_leak_static_context

# Install git pre-push hook
chmod +x install-git-hook.sh
./install-git-hook.sh

# Skip review and push
git push-skip-review
```

## Architecture Overview

### Review Skill System

The code review system is built with a multi-layer architecture:

**Entry Point**: `review_skill/review.py`
- Main entry that orchestrates the review process
- Chooses between available engines (AST Engine → Unified Rule Engine → Fallback)
- Handles git diff retrieval and filtering
- Generates HTML/JSON reports

**Engine Hierarchy**:
1. **AST Engine** (`ast_engine/`): Pattern-based analysis using custom Kotlin AST parser
   - `parser_v2.py`: Kotlin code parser producing AST nodes
   - `rules/`: AST-based rules (coroutine_rules.py, compose_rules.py, enhanced_rules.py)
   - `incremental/`: Parallel file scanning for large codebases
   - `cache/`: LRU caching with TTL for parsed AST nodes

2. **Unified Rule Engine** (`rule_engine/`): Regex-based rule system
   - `engine.py`: Core execution engine with parallel processing and caching
   - `interfaces.py`: Rule abstractions (Rule, Finding, RuleSeverity, RuleCategory)
   - `registry.py`: Rule registration and discovery
   - `context.py`: Rule execution context
   - `rules/`: Individual rule implementations (e.g., `memory_leak_static_context.py`)
   - `integration/review_runner.py`: Adapter for unified execution

**Configuration** (`config.py`, `review_config.json`):
- Controls file extensions, scan directories, exclusions
- Sets minimum score threshold (default: 70)
- Toggles semantic review (LLM) and HTML report generation
- Language setting (zh_CN/en_US)

**Report Generation** (`report_generator.py`):
- Parses git diff into structured data
- Generates HTML reports with findings visualization
- Outputs JSON reports with detailed metadata

### Key Environment Variables

```bash
# LLM Configuration (for semantic review)
export DEEPSEEK_API_KEY="your_key"
export LLM_MODEL="deepseek-chat"
export OPENAI_BASE_URL="https://api.deepseek.com"

# Review Configuration
export REVIEW_FILE_EXTENSIONS=".kt,.kts"
export REVIEW_SCAN_DIRECTORIES="app/src/main/java,app/src/test/java"
export REVIEW_EXCLUDE_PATTERNS="*/build/*,*/test/*"
export REVIEW_ENABLE_SEMANTIC="true"
export REVIEW_MIN_SCORE_THRESHOLD="70"

# Feature Flags
export USE_AST_ENGINE="true"  # Enable AST engine
export SKIP_REVIEW="1"        # Skip pre-push hook
```

### Android App Structure

```
app/src/main/java/com/yxhuang/flowforandroid/
├── MainActivity.kt          # Main Activity with Compose setup
├── FlowApplication.kt       # Application class
├── HomeViewModel.kt         # ViewModel demonstrating Flow patterns
├── TestClass.kt             # Test utilities
├── permission/              # Permission handling components
│   ├── PermissionManager.kt
│   ├── PermissionResult.kt
│   └── PermissionExample.kt
└── ui/theme/                # Compose theming
    ├── Color.kt
    ├── Theme.kt
    └── Type.kt
```

## Code Style Guidelines (from AGENTS.md)

### Kotlin
- Use `val` by default; prefer immutability
- Composable functions: PascalCase nouns with default Modifier parameter
- Use `viewModelScope`/`rememberCoroutineScope`, never `GlobalScope`
- Use `StateFlow` for UI state, `SharedFlow` for one-time events
- Trailing commas always (for better diffs)
- Import order: Kotlin stdlib → Android → AndroidX → Compose → Third-party → Project

### Python (Review Skill)
- Follow existing patterns in rule definitions
- Rules inherit from `Rule` base class with `metadata` property and `check()` method
- Use `RuleContext` for accessing code and file information
- Register rules in `RuleRegistry` for discovery

## Testing

### Android Tests
- Unit tests: `app/src/test/java/`
- Instrumentation tests: `app/src/androidTest/java/`
- Naming: `test[MethodName]_[ExpectedBehavior]`

### Python Tests
- Located in `review_skill/test_rule/`
- Each rule file has corresponding test file (e.g., `test_batch1_rules.py`)
- Tests use `RuleContext` with sample code to verify rule detection

## Important File Paths

| Purpose | Path |
|---------|------|
| Review config | `review_skill/review_config.json` |
| Requirements | `review_skill/requirements.txt` |
| Main review entry | `review_skill/review.py` |
| Rule definitions | `review_skill/rule_engine/rules/` |
| AST rules | `review_skill/ast_engine/rules/` |
| Test suite | `review_skill/test_rule/` |
| Reports output | `review_skill/report/` |
| Gradle version catalog | `gradle/libs.versions.toml` |
| App build config | `app/build.gradle` |
