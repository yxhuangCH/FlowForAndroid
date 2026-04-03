# Android Code Review Skill

**[简体中文](./README.md)** | **English**

A professional Android/Kotlin code review tool that automatically detects code quality, best practice adherence, and potential issues.

---

## Features

- ✅ **Git diff input support** - Automatically detects code changes
- ✅ **Kotlin static rule scanning** - Only `.kt` / `.kts` files
- ✅ **Configurable scan scope and file filtering**
- ✅ **Compose / Coroutine / Flow specialized rules**
- ✅ **LLM semantic enhancement** (DeepSeek/OpenAI optional)
- ✅ **Structured JSON + HTML visual reports**
- ✅ **GitHub Action CI/CD integration**

---

## Quick Start

### 1. Install Dependencies

```bash
cd review_skill
pip install -r requirements.txt
```

### 2. Basic Usage

```bash
# Run code review (uses current git diff by default)
python3 review.py

# Or specify configuration file
python3 review.py --config custom_config.json
```

### 3. View Results

The tool outputs:
1. JSON format review results
2. HTML visual report (enabled by default)
3. Detailed scores and issue lists
4. PR blocking judgment

---

## Configuration

### Configuration File

The tool provides detailed configuration options in `review_config.json`:

```json
{
  "file_extensions": [".kt", ".kts"],
  "scan_directories": [
    "app/src/main/java",
    "app/src/test/java"
  ],
  "exclude_patterns": [
    "*/build/*",
    "*/.gradle/*"
  ],
  "enable_semantic_review": true,
  "generate_html_report": true,
  "min_score_threshold": 70,
  "language": "en_US"
}
```

### Environment Variables

```bash
# Language setting
export REVIEW_LANGUAGE="en_US"  # or "zh_CN"

# File extensions
export REVIEW_FILE_EXTENSIONS=".kt,.kts"

# Scan directories
export REVIEW_SCAN_DIRECTORIES="app/src/main/java"

# Minimum score threshold
export REVIEW_MIN_SCORE_THRESHOLD="70"

# LLM configuration
export DEEPSEEK_API_KEY="your_api_key"
export LLM_MODEL="deepseek-chat"
```

---

## Rule System

### Supported Rule Categories

| Category | Description | Rule Count |
|----------|-------------|------------|
| Base Rules | GlobalScope, ViewModel Context, Main thread IO | 3 |
| Coroutine Rules | Coroutine lifecycle, Cancellation, Scope management | 2 |
| Compose Rules | Recomposition optimization, State management | 2 |
| Flow Rules | Flow lifecycle, Exception handling | 5 |
| Flow Lifecycle Rules | stateIn/shareIn scope, repeatOnLifecycle | 4 |
| Flow Structure Rules | Structured concurrency, awaitClose | 4 |
| Hilt Rules | Dependency injection best practices | 1 |
| Dagger2 Rules | DI scope management | 3 |

**Total: ~24 rules**

### Severity Levels

| Severity | Deduction | Description |
|----------|-----------|-------------|
| INFO | 0 | Informational only |
| MINOR | 5 | Minor issue, suggested fix |
| MAJOR | 10 | Major issue, affects quality |
| CRITICAL | 20 | Critical issue, affects stability |
| BLOCKER | 100 | Blocking issue, must fix |

### Score Calculation

```
Initial score: 100
Final score = max(0, min(100, 100 - total_deduction))
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Code Review
on: [pull_request]

jobs:
  code-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r review_skill/requirements.txt
      
      - name: Run code review
        run: |
          cd review_skill
          python3 review.py
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          REVIEW_LANGUAGE: "en_US"
          REVIEW_MIN_SCORE_THRESHOLD: "80"
```

---

## Output Format

### JSON Output

```json
{
  "findings": [
    {
      "severity": "critical",
      "rule": "no_globalscope",
      "message": "GlobalScope is lifecycle unsafe.",
      "file": "app/src/main/java/com/example/MyActivity.kt",
      "line": 42,
      "suggestion": "Use lifecycleScope or viewModelScope"
    }
  ],
  "score": 85,
  "block_pr": false,
  "engine": "new",
  "file_count": 3
}
```

### HTML Report

The HTML report includes:
- **Dashboard**: Overall score and statistics
- **Issue categorization**: By severity and rule type
- **File view**: Detailed issues and suggestions for each file
- **Code diff**: Displays problematic code snippets
- **Fix suggestions**: Specific fix steps and recommended code

---

## Internationalization (i18n)

This tool supports bilingual interface (Chinese/English):

### Switch Language

```bash
# Via environment variable
export REVIEW_LANGUAGE="en_US"

# Via configuration file
# Set "language": "en_US" in review_config.json
```

### Supported Languages

- `zh_CN` - Simplified Chinese (default)
- `en_US` - English

---

## Architecture

```
┌─────────────────────────────────────┐
│  Application Layer                   │
│  ├─ CLI Interface (review.py)        │
│  └─ CI/CD Integration                │
├─────────────────────────────────────┤
│  Rule Engine Layer                   │
│  ├─ Rule Registry                    │
│  ├─ Rule Engine (Parallel/Cached)    │
│  ├─ Rule Context                     │
│  └─ Adapter Layer (Decorators)       │
├─────────────────────────────────────┤
│  Rule Layer                          │
│  ├─ Base/Coroutine/Compose/Flow      │
│  └─ Hilt/Dagger2 Rules               │
├─────────────────────────────────────┤
│  External Integration                │
│  ├─ LLM Service                      │
│  └─ Report Generator                 │
└─────────────────────────────────────┘
```

---

## Project Structure

```
review_skill/
├── review.py                    # Main entry
├── i18n.py                      # Internationalization
├── config.py                    # Configuration management
├── llm_layer.py                 # LLM integration
├── report_generator.py          # HTML report generation
├── review_config.json           # Default configuration
├── requirements.txt             # Python dependencies
├── locale/                      # Translation files
│   ├── zh_CN/LC_MESSAGES/
│   └── en_US/LC_MESSAGES/
├── rule_engine/                 # Rule engine core
│   ├── interfaces.py
│   ├── engine.py
│   ├── registry.py
│   ├── context.py
│   ├── adapters/
│   ├── rules/
│   └── integration/
├── test_rule/                   # Unit tests
├── tests/                       # Integration tests
└── docs/                        # Documentation
    ├── README.md
    ├── USER_MANUAL.md
    └── TECHNICAL_SPEC.md
```

---

## Development

### Run Tests

```bash
# Run all tests
python3 -m unittest discover test_rule

# Run specific test
python3 -m unittest test_rule.test_base_rules
```

### Add Custom Rules

```python
# rule_engine/rules/custom_rules.py
from ..interfaces import Rule, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from typing import List

class MyCustomRule(Rule):
    @property
    def metadata(self):
        return RuleMetadata(
            id="my_custom_rule",
            name="My Custom Rule",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS
        )
    
    def check(self, context: RuleContext) -> List[Finding]:
        findings = []
        # Your rule logic here
        return findings
```

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License

---

## Git Hook Integration

### Install Pre-Push Hook

> ⚠️ **Note**: The `.git/hooks/` directory is a **local-only** directory and is **NOT tracked by git or included in the repository**. Therefore:
> - After cloning the repository for the first time, you need to manually run the installation script
> - Each team member needs to run the installation script on their own machine

After installation, every `git push` will automatically execute code review, and push will be blocked if the review fails:

```bash
cd review_skill
chmod +x install-git-hook.sh
./install-git-hook.sh
```

### Skip Code Review

There are four ways to skip the pre-push check:

**Method 1: git push-skip-review (recommended)**
```bash
# Skip review and push directly
git push-skip-review

# Supports all git push arguments
git push-skip-review origin main
git push-skip-review --force-with-lease origin feature-branch
```

**Method 2: Environment variable (temporary skip)**
```bash
SKIP_REVIEW=1 git push
```

**Method 3: Git config (permanent disable)**
```bash
# Disable
git config hooks.skip-review true

# Re-enable
git config hooks.skip-review false
```

**Method 4: --no-verify (skip all hooks, not recommended)**
```bash
git push --no-verify
```

### How the Hook Works

1. When `git push` is executed, the pre-push hook is triggered
2. Automatically runs `python3 review.py` for code review
3. If review fails (exit code ≠ 0), push is rejected
4. Shows skip hint, user can choose to skip or fix code

---

## Support

- **Documentation**: See docs/ directory
- **Examples**: See refer_examples/ directory
- **Issues**: Please use GitHub Issues

**Version**: 1.1.0  
**Last Updated**: 2024
