# Review Skill - Quick Start Guide

> Run your first code review in 5 minutes

This guide will help you get started with Review Skill quickly, allowing you to understand the basic features and start using it in the shortest time possible.

## 🚀 Minimal Installation (3 Steps)

### Step 1: Get the Project
```bash
# If you don't have the project yet
git clone https://github.com/your-org/review_skill.git
cd review_skill

# If you already have the project
cd review_skill
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Verify Installation
```bash
python3 review.py --version
# Should display version info, e.g.: review_skill v1.0.0
```

### Step 4: Install Git Hook (Optional, Recommended for Team Usage)
> ⚠️ **Note**: The `.git/hooks/` directory is a **local-only** directory and is **NOT tracked by git or included in the repository**. Therefore, after cloning the repository, you need to manually run the installation script.

```bash
chmod +x install-git-hook.sh
./install-git-hook.sh
```

After installation, every `git push` will automatically execute code review.

## 🔧 Minimal Configuration

### Basic Configuration (Optional)
Create the simplest configuration file `minimal_config.json`:

```json
{
  "file_extensions": [".kt"],
  "scan_directories": ["."],
  "min_score_threshold": 70,
  "language": "en_US"
}
```

Or use environment variables directly:
```bash
# Simplest environment variable configuration
export REVIEW_FILE_EXTENSIONS=".kt"
export REVIEW_SCAN_DIRECTORIES="."
export REVIEW_MIN_SCORE_THRESHOLD=70
export REVIEW_LANGUAGE="en_US"
```

### LLM Configuration (Optional, Enhanced Features)
If you need AI-powered intelligent analysis:
```bash
# DeepSeek API (Recommended)
export DEEPSEEK_API_KEY="your_api_key_here"

# Or use OpenAI
export OPENAI_API_KEY="your_openai_api_key"
```

## 📁 Prepare Test Code

Create a simple test file `test.kt`:

```kotlin
// test.kt
class TestViewModel {
    // Typical issue: using GlobalScope
    fun testFunction() {
        GlobalScope.launch {
            println("Executing in GlobalScope")
        }
    }
    
    // Correct approach
    fun correctFunction() {
        // viewModelScope.launch { }  // Requires ViewModel class
    }
}
```

## ▶️ Run Your First Review

### Method 1: Review Single File
```bash
# Create diff for test file
echo "diff --git a/test.kt b/test.kt
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/test.kt
@@ -0,0 +1,12 @@
+// test.kt
+class TestViewModel {
+    // Typical issue: using GlobalScope
+    fun testFunction() {
+        GlobalScope.launch {
+            println(\"Executing in GlobalScope\")
+        }
+    }
+}" > test.diff

# Run review
python3 -c "
import sys
sys.path.append('.')
from review import review
import subprocess
result = subprocess.run(['python3', 'review.py'], capture_output=True, text=True)
print(result.stdout)
"
```

### Method 2: Use Project Examples
```bash
# View built-in examples
ls refer_examples/

# Run full review workflow
python3 review.py
```

## 📊 Understanding Results

### Console Output
You will see output similar to:

```
📊 Code Review Results
├── Total Score: 85/100
├── Files: 1
├── Issues Found: 1
│   └── critical: 1
├── Recommendation: PASS (above threshold 70)
├── HTML Report: report/code_review_report_20250303_221045.html
└── Detailed JSON: report/code_review_details_20250303_221045.json
```

### Key Metrics
- **Total Score**: Code quality score, 100 is perfect
- **Issues Found**: Number of issues by severity level
- **Recommendation**: Whether to pass (based on configured threshold)
- **Report Files**: Location of generated detailed reports

## 🔍 View Detailed Reports

### HTML Report
```bash
# Open HTML report (macOS)
open report/code_review_report_*.html

# Or use browser
google-chrome report/code_review_report_*.html
```

### JSON Report
```bash
# View detailed results in JSON format
cat report/code_review_details_*.json | python3 -m json.tool
```

## 🎯 Quick Experience of Core Features

### 1. Basic Rule Checking
```bash
# Check for GlobalScope usage
python3 -c "
code = '''
class MyClass {
    fun test() {
        GlobalScope.launch { }
    }
}
'''
from rules.base_rules import run_base_rules
findings = run_base_rules(code)
print('Issues found:', len(findings))
for f in findings:
    print(f'  - {f[\"rule\"]}: {f[\"message\"]}')
"
```

### 2. Score Calculation
```bash
# Understand score calculation logic
python3 -c "
from scorer import calculate_score
findings = [
    {'severity': 'critical', 'rule': 'test', 'message': 'test'},
    {'severity': 'minor', 'rule': 'test', 'message': 'test'}
]
score = calculate_score(findings)
print(f'Score: {score}/100')
print(f'Deducted: {100 - score} points')
"
```

### 3. Configuration Validation
```bash
# Check if configuration loads correctly
python3 -c "
from config import get_config
config = get_config()
print('File extensions:', config.get_file_extensions())
print('Scan directories:', config.get_scan_directories())
print('Min score threshold:', config.get_min_score_threshold())
"
```

## 🚨 Common Issues Quick Reference

### Issue 1: No Files Found
```bash
# Check current directory
pwd

# Check for .kt files
find . -name "*.kt" | head -5

# Relax configuration
export REVIEW_SCAN_DIRECTORIES="."
export REVIEW_FILE_EXTENSIONS=".kt,.java"
```

### Issue 2: Dependency Installation Failed
```bash
# Update pip
pip install --upgrade pip

# Use domestic mirror (for China users)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Or use conda
conda create -n review python=3.9
conda activate review
pip install -r requirements.txt
```

### Issue 3: API Key Error
```bash
# Test DeepSeek API
python3 test_deepseek_api.py

# Or disable LLM feature
export REVIEW_ENABLE_SEMANTIC="false"
```

## 📈 Next Steps Learning Path

### Path 1: Basic User
1. ✅ **Complete this quick guide** - Done!
2. → [Installation Guide](docs/guide/01-getting-started/installation.md) - Detailed installation instructions
3. → [Basic Usage](docs/guide/01-getting-started/basic-usage.md) - Core feature details
4. → [Configuration Guide](docs/guide/01-getting-started/configuration.md) - Complete configuration options
5. → [Team Workflow](docs/guide/03-best-practices/team-workflow.md) - Team collaboration guide

### Path 2: Advanced User
1. ✅ **Complete this quick guide** - Done!
2. → [Rule Engine](docs/guide/02-features/rule-engine.md) - Deep understanding of rule system
3. → [LLM Integration](docs/guide/02-features/llm-integration.md) - AI intelligent analysis
4. → [Performance Tuning](docs/guide/03-best-practices/performance-tuning.md) - Optimize review performance
5. → [CI/CD Integration](docs/guide/02-features/ci-cd-integration.md) - Automated pipeline

### Path 3: Developer
1. ✅ **Complete this quick guide** - Done!
2. → [API Reference](docs/api/) - Complete API documentation
3. → [Rule Development](docs/development/rule-development.md) - Custom rule development
4. → [Plugin Development](docs/development/plugin-development.md) - Plugin system development
5. → [Testing Guide](docs/development/testing.md) - Testing strategies and methods

## 🔗 Useful Command Quick Reference

### Common Commands
```bash
# Run review
python3 review.py

# Specify configuration file
python3 review.py --config custom_config.json

# Check specific directory only
export REVIEW_SCAN_DIRECTORIES="app/src/main/java"
python3 review.py

# Generate report without blocking
export REVIEW_MIN_SCORE_THRESHOLD=0
python3 review.py

# View help (if supported)
python3 review.py --help
```

### Debug Commands
```bash
# Enable verbose logging
export LOG_LEVEL="DEBUG"
python3 review.py

# Run specific rule only
python3 -c "
from rules.base_rules import run_base_rules
code = 'GlobalScope.launch {}'
print(run_base_rules(code))
"

# Check configuration
python3 test_config.py
```

## 🎉 Congratulations!

You have successfully completed the quick start for Review Skill. Next steps:

### Take Action Now
1. **Apply to your project**: Run `python3 review.py` in your Android project
2. **View reports**: Open the generated HTML report to understand code quality
3. **Adjust configuration**: Adjust rules and thresholds according to project needs

### Get Help
- Encountered issues? Check [Common Issues](docs/guide/04-troubleshooting/common-issues.md)
- Need detailed instructions? Read [Complete User Guide](docs/guide/)
- Have suggestions or questions? Submit [Issue](https://github.com/your-org/review_skill/issues)

### Join Community
- 🌟 **Star the project**: Support project development
- 📢 **Share feedback**: Tell us about your experience
- 👥 **Join discussions**: Participate in community exchange

---
*Completion time: 5 minutes ✅ | Next: [Complete User Guide](docs/guide/)*
