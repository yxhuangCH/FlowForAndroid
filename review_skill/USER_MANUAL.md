# Android Review Skill - User Manual

## Overview

Android Review Skill is a professional Android/Kotlin code review tool designed specifically for Android developers to automatically detect code quality, best practice compliance, and potential issues. The tool supports:

- **Static Rule Scanning**: Detect code issues based on regular expressions and syntax analysis
- **Multi-domain Rule Support**: Modern Android development technologies including Coroutines, Compose, Flow, Hilt, Dagger2
- **LLM Semantic Enhancement**: Optional AI-powered deep code understanding and suggestions
- **Report Generation**: Detailed review reports in JSON and HTML formats
- **GitHub Action Integration**: Support for CI/CD pipeline automated review

## System Requirements

- Python 3.8+
- Git 2.20+
- For LLM features: DeepSeek API Key or OpenAI API Key

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
1. Review results in JSON format
2. HTML visualization reports (enabled by default)
3. Detailed scores and issue lists
4. PR blocking determination

## Detailed Configuration

### Configuration File Structure

The tool provides detailed configuration options in `review_skill/review_config.json`:

```json
{
  "file_extensions": [".kt", ".kts"],
  "scan_directories": [
    "app/src/main/java",
    "app/src/test/java",
    "app/src/androidTest/java"
  ],
  "exclude_patterns": [
    "*/build/*",
    "*/.gradle/*",
    "*/.idea/*",
    "*/.git/*",
    "*/debug/*"
  ],
  "enable_semantic_review": true,
  "generate_html_report": true,
  "min_score_threshold": 70,
  "language": "en_US",
  
  "rule_engine": {
    "use_new_engine": true,
    "new_engine_config": {
      "enabled_categories": ["security", "performance", "correctness", "concurrency", "lifecycle"],
      "disabled_rules": [],
      "parallel_execution": true,
      "cache_enabled": true,
      "max_workers": 4,
      "cache_ttl": 3600,
      "execution_timeout": 30
    }
  }
}
```

### Configuration Options

#### File Filtering Configuration
- **file_extensions**: List of file extensions to scan (Kotlin files only)
- **scan_directories**: List of directories to scan (relative to project root)
- **exclude_patterns**: File/directory patterns to exclude (supports glob syntax)

#### Feature Configuration
- **enable_semantic_review**: Enable LLM semantic analysis
- **generate_html_report**: Generate HTML visualization reports
- **min_score_threshold**: Minimum passing score (below this will block PR)
- **language**: Interface language (`zh_CN` or `en_US`)

#### Rule Engine Configuration
- **use_new_engine**: Use the new unified rule engine
- **new_engine_config**: Detailed configuration for the new engine
  - **enabled_categories**: Enabled rule categories
  - **disabled_rules**: Disabled specific rule IDs
  - **parallel_execution**: Enable parallel rule execution
  - **cache_enabled**: Enable rule caching
  - **max_workers**: Maximum parallel worker threads

### Environment Variable Configuration

You can also override configuration settings via environment variables:

```bash
# File extension configuration (comma-separated)
export REVIEW_FILE_EXTENSIONS=".kt,.kts"

# Scan directory configuration (comma-separated)
export REVIEW_SCAN_DIRECTORIES="app/src/main/java,app/src/test/java"

# Exclude pattern configuration (comma-separated)
export REVIEW_EXCLUDE_PATTERNS="*/build/*,*/test/*"

# Feature switches
export REVIEW_ENABLE_SEMANTIC="true"
export REVIEW_GENERATE_HTML="true"
export REVIEW_MIN_SCORE_THRESHOLD="70"
export REVIEW_LANGUAGE="en_US"

# Rule engine configuration
export RULE_ENGINE_USE_NEW="true"
```

## API Key Configuration

### DeepSeek API (Recommended)

```bash
# Set DeepSeek API Key
export DEEPSEEK_API_KEY="your_deepseek_api_key_here"

# Optional: Set model (default is deepseek-chat)
export LLM_MODEL="deepseek-chat"

# Optional: Custom API endpoint (default is https://api.deepseek.com)
export OPENAI_BASE_URL="https://api.deepseek.com"
```

### OpenAI API (Alternative)

```bash
# Set OpenAI API Key
export OPENAI_API_KEY="your_openai_api_key_here"

# Set OpenAI model
export LLM_MODEL="gpt-4o-mini"
```

## Rule Details

### Rule Categories

The tool supports the following rule categories:

#### 1. Base Rules
- **no_globalscope**: Prohibit use of `GlobalScope.launch` (lifecycle unsafe)
- **viewmodel_context**: ViewModel should not hold Android Context
- **main_thread_io**: Detect IO operations on main thread

#### 2. Coroutine Rules
- Coroutine lifecycle management
- Coroutine cancellation and exception handling
- Coroutine scope management

#### 3. Compose Rules
- Recomposition optimization detection
- Compose state management
- Compose side effect management

#### 4. Flow Rules
- Flow lifecycle management
- Flow exception handling
- Flow transformation optimization

#### 5. Hilt/Dagger2 Rules
- Dependency injection best practices
- Scope management
- Component lifecycle

#### 6. Code Structure Rules
- Package structure organization
- Class and method design
- Code reusability

### Rule Severity Levels

Each rule has one of the following severity levels:

1. **blocker** (100 pts): Severe issues that must be fixed
2. **critical** (20 pts): Critical issues affecting app stability
3. **major** (10 pts): Major issues affecting code quality
4. **minor** (5 pts): Minor issues, suggested fixes
5. **info** (0 pts): Informational hints, no score impact

### Score Calculation Rules

- Initial score: 100
- Each issue deducts points based on severity:
  - blocker: -100 (immediate failure)
  - critical: -20
  - major: -10
  - minor: -5
  - info: no deduction
- Final score = max(0, min(100, 100 - total_deduction))

## Usage Scenarios

### Scenario 1: Local Development Real-time Review

```bash
# Run review before code commit
python3 review.py

# Example output:
# - JSON format issue list
# - Score: 85/100
# - HTML report link
# - Submission recommendation
```

### Scenario 2: CI/CD Pipeline Integration

```bash
# Use in GitHub Actions
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
```

### Scenario 3: Batch Review Historical Code

```bash
# Review specific commit range
git diff HEAD~5..HEAD > changes.diff
python3 -c "
import sys
sys.path.append('review_skill')
from review import review
with open('changes.diff', 'r') as f:
    diff = f.read()
# Execute review logic...
"
```

## Output Formats

### 1. JSON Output Format

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
  "file_count": 3,
  "llm_available": true,
  "config": {
    "file_extensions": [".kt", ".kts"],
    "scan_directories": ["app/src/main/java", "app/src/test/java"],
    "min_score_threshold": 70,
    "filtered_diff": true
  }
}
```

### 2. HTML Report

The HTML report includes:
- **Dashboard**: Overall score and statistics
- **Issue Categories**: Classified by severity and rule type
- **File View**: Detailed issues and suggestions for each file
- **Code Comparison**: Display problematic code snippets
- **Fix Suggestions**: Specific fix steps and suggested code

### 3. Command Line Output

```
📊 Code Review Results
├── Total Score: 85/100
├── Files: 3
├── Issues Found: 2
│   ├── critical: 1
│   └── minor: 1
├── Recommendation: PASS (above threshold 70)
├── HTML Report: report/code_review_report_20250228_084325.html
└── Detailed JSON: report/code_review_details_20250228_084325.json
```

## Advanced Features

### 1. Rule Engine Selection

The tool supports two rule engines:

#### Legacy Engine
- Based on independent rule modules
- Simple rule execution
- Suitable for simple scenarios

#### New Engine (Enhanced Engine)
- Unified rule interface
- Parallel rule execution
- Rule cache optimization
- Extensible rule registration mechanism
- Detailed statistics

```python
# Manual use of new engine
from rule_engine.integration.review_runner import ReviewRunner

runner = ReviewRunner(config)
runner.initialize()
results = runner.review_diff(git_diff_text)
```

### 2. Custom Rule Development

#### Creating New Rules

```python
# Create new rule file in review_skill/rules/ directory
# custom_rules.py

import re
from rule_engine.interfaces import Rule, RuleSeverity, RuleCategory

class MyCustomRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="my_custom_rule",
            name="My Custom Rule",
            description="Detect specific patterns",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS
        )
    
    def execute(self, context):
        findings = []
        if "bad_pattern" in context.code:
            findings.append(self.create_finding(
                message="Found bad pattern",
                line_number=self._find_line_number(context.code, "bad_pattern")
            ))
        return findings
```

#### Registering Rules

```python
from rule_engine.registry import RuleRegistry

registry = RuleRegistry()
registry.register(MyCustomRule())
```

### 3. Cache Configuration

```json
{
  "rule_engine": {
    "new_engine_config": {
      "cache_enabled": true,
      "cache_max_size": 1000,
      "cache_ttl": 3600,
      "cache_backend": "memory"
    }
  }
}
```

## Troubleshooting

### Common Issues

#### Issue 1: No Code Changes Detected

**Possible Causes**:
1. Git diff is empty
2. Configuration filtering too strict
3. Code changes not in scan directories

**Solutions**:
```bash
# Check git diff
git diff HEAD~1..HEAD

# Check configuration file
cat review_skill/review_config.json

# Temporarily relax configuration
export REVIEW_SCAN_DIRECTORIES="."
python3 review.py
```

#### Issue 2: LLM Feature Unavailable

**Possible Causes**:
1. API key not set
2. Network connectivity issues
3. API quota exhausted

**Solutions**:
```bash
# Check API key
echo $DEEPSEEK_API_KEY

# Test API connection
python3 review_skill/test_deepseek_api.py

# Disable LLM feature
export REVIEW_ENABLE_SEMANTIC="false"
```

#### Issue 3: Rule Engine Initialization Failed

**Possible Causes**:
1. Missing dependency packages
2. Python version incompatibility
3. Configuration file errors

**Solutions**:
```bash
# Reinstall dependencies
pip install -r review_skill/requirements.txt --force-reinstall

# Use legacy engine
export RULE_ENGINE_USE_NEW="false"

# Check Python version
python3 --version
```

### Debug Mode

```bash
# Enable verbose logging
export LOG_LEVEL="DEBUG"
python3 review.py

# Or modify code directly
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Optimization

### 1. Caching Strategy

- **Memory Cache**: Default enabled, suitable for small projects
- **File Cache**: Suitable for large projects, reduces repeated calculations
- **Redis Cache**: Suitable for distributed environments

### 2. Parallel Processing

- **max_workers**: Adjust based on CPU core count
- **Execution Timeout**: Prevent individual rules from taking too long
- **Resource Limits**: Control memory and CPU usage

### 3. Incremental Scanning

- Only scan changed files
- Cache rule execution results
- Incrementally update reports

## Best Practices

### 1. Team Collaboration

1. **Unified Configuration**: Team shares the same configuration file
2. **Rule Consensus**: Team jointly decides which rules to enable
3. **Score Threshold**: Set reasonable passing scores
4. **Regular Updates**: Regularly update rules and tool versions

### 2. CI/CD Integration

```yaml
# .github/workflows/review.yml
name: Code Review
on:
  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main ]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup
        run: |
          pip install -r review_skill/requirements.txt
      - name: Run Review
        run: |
          cd review_skill
          python3 review.py
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          REVIEW_MIN_SCORE_THRESHOLD: 80
```

### 3. Custom Rules

1. **Project-specific Rules**: Add custom rules based on project characteristics
2. **Gradual Enablement**: Enable some rules first, gradually increase
3. **Regular Review**: Periodically review rule effectiveness and necessity

## Appendices

### A. Command Line Arguments

```bash
# View help (if supported)
python3 review.py --help

# Specify configuration file
python3 review.py --config my_config.json

# Specify git references
python3 review.py --base original/develop --head HEAD

# Output format control
python3 review.py --format json
python3 review.py --format html
python3 review.py --format both
```

### B. Environment Variable Reference

| Variable | Description | Default |
|----------|-------------|---------|
| REVIEW_FILE_EXTENSIONS | File extensions | .kt,.kts |
| REVIEW_SCAN_DIRECTORIES | Scan directories | app/src/main/java,app/src/test/java |
| REVIEW_EXCLUDE_PATTERNS | Exclude patterns | */build/*,*/test/* |
| REVIEW_ENABLE_SEMANTIC | Enable semantic analysis | true |
| REVIEW_GENERATE_HTML | Generate HTML report | true |
| REVIEW_MIN_SCORE_THRESHOLD | Minimum score threshold | 70 |
| REVIEW_LANGUAGE | Interface language | zh_CN |
| DEEPSEEK_API_KEY | DeepSeek API key | - |
| OPENAI_API_KEY | OpenAI API key | - |
| LLM_MODEL | LLM model name | deepseek-chat |
| LOG_LEVEL | Log level | INFO |

### C. File Structure

```
review_skill/
├── README.md                    # Brief description
├── review.py                    # Main entry file
├── config.py                    # Configuration management
├── review_config.json           # Default configuration file
├── scorer.py                    # Score calculation
├── requirements.txt             # Python dependencies
├── llm_layer.py                 # LLM integration layer
├── report_generator.py          # Report generator
├── user_manual.md               # Detailed manual (this file)
├── refer_examples/              # Reference examples
│   ├── no_globalscope_refer.kt
│   └── ...
├── rules/                       # Rule implementations
│   ├── base_rules.py
│   ├── coroutine_rules.py
│   └── ...
├── rule_engine/                 # New rule engine
│   ├── interfaces.py
│   ├── engine.py
│   ├── engine_enhanced.py
│   ├── registry.py
│   ├── context.py
│   ├── rules/                   # New rules
│   ├── adapters/               # Decorator adapters (rule, pattern_rule)
│   └── integration/            # Integration modules
├── tests/                       # Test code
└── report/                      # Generated reports
```

### D. Technical Support

- **Documentation**: Check this manual and README.md
- **Examples**: Refer to `refer_examples/` directory
- **Testing**: Run `python3 -m unittest discover test_rule`
- **Issue Feedback**: Check log files or contact development team

---

**Version**: 1.0  
**Last Updated**: February 28, 2025  
**Applicable Version**: review_skill v1.0+
