
# Android 代码审查工具

设计目标：

✅ 支持 Git diff 输入

✅ Kotlin 静态规则扫描（仅扫描 .kt/.kts 文件）

✅ 可配置的扫描范围和文件过滤

✅ Compose / Coroutine 专项规则

✅ LLM 语义增强（可选）

✅ 结构化 JSON 输出

✅ HTML 可视化报告

✅ 可用于 GitHub Action


# 快速开始

主入口： `review.py`

## 安装依赖

```bash
cd review_skill
pip install -r requirements.txt
```

## 基本使用

```bash
cd review_skill
python3 review.py
```

## 配置说明

### 配置文件 (review_config.json)

工具支持通过配置文件自定义扫描行为。默认配置文件位于 `review_skill/review_config.json`。

配置项说明：

```json
{
  "file_extensions": [".kt", ".kts"],           // 要扫描的文件扩展名
  "scan_directories": [                         // 要扫描的目录（相对项目根目录）
    "app/src/main/java",
    "app/src/test/java", 
    "app/src/androidTest/java"
  ],
  "exclude_patterns": [                         // 要排除的文件/目录模式（glob语法）
    "*/build/*",
    "*/.gradle/*",
    "*/.idea/*",
    "*/.git/*",
    "*/debug/*"
  ],
  "enable_semantic_review": true,               // 是否启用LLM语义分析
  "generate_html_report": true,                 // 是否生成HTML报告
  "min_score_threshold": 70                     // 最小通过分数（低于此分数会阻塞PR）
}
```

### 环境变量配置

也可以通过环境变量覆盖配置文件中的设置：

```bash
# 文件扩展名配置（逗号分隔）
export REVIEW_FILE_EXTENSIONS=".kt,.kts"

# 扫描目录配置（逗号分隔）
export REVIEW_SCAN_DIRECTORIES="app/src/main/java,app/src/test/java"

# 排除模式配置（逗号分隔）
export REVIEW_EXCLUDE_PATTERNS="*/build/*,*/test/*"

# 其他配置
export REVIEW_ENABLE_SEMANTIC="true"
export REVIEW_GENERATE_HTML="true"
export REVIEW_MIN_SCORE_THRESHOLD="70"
```

### DeepSeek API 集成

默认情况下，系统会优先使用 DeepSeek API。配置方法：

```bash
# 设置 DeepSeek API Key
export DEEPSEEK_API_KEY="your_deepseek_api_key"

# 可选：设置模型（默认为 deepseek-chat）
export LLM_MODEL="deepseek-chat"

# 可选：自定义 API 端点（默认为 https://api.deepseek.com）
export OPENAI_BASE_URL="https://api.deepseek.com"
```

### 使用 OpenAI API（备用选项）

如果需要使用 OpenAI API：

```bash
# 设置 OpenAI API Key
export OPENAI_API_KEY="your_openai_api_key"
# 设置 OpenAI 模型
export LLM_MODEL="gpt-4o-mini"
```

## 工作原理

1. **获取变更**：工具通过 `git diff` 获取代码变更
2. **文件过滤**：根据配置文件过滤只扫描 Kotlin 文件
3. **规则扫描**：应用各种静态规则检查代码质量
4. **语义分析**：可选地使用 LLM 进行语义分析
5. **评分与报告**：生成评分、JSON 报告和 HTML 可视化报告

## 文件过滤示例

假设有以下文件变更：
- `app/src/main/java/com/example/MainActivity.kt` ✅ 扫描
- `app/build.gradle` ❌ 跳过（不是 .kt 文件）
- `app/src/main/res/layout/activity_main.xml` ❌ 跳过（不是 .kt 文件）
- `app/src/test/java/com/example/MainActivityTest.kt` ✅ 扫描（在扫描目录中）
- `app/src/debug/java/com/example/DebugActivity.kt` ❌ 跳过（在 debug 目录中）

## 依赖说明

- `openai>=1.0.0` - OpenAI 兼容的 Python SDK，支持 DeepSeek API
- `gitpython>=3.1.40` - Git 操作支持
- `python-dotenv>=1.0.0` - 环境变量加载

## 测试

```bash
# 运行单元测试
cd review_skill
python3 -m unittest discover test_rule

# 测试配置功能
python3 test_config.py
```

注意：需要设置相应的 API Key 环境变量才能使用 LLM 语义增强功能。

## 详细文档

### 用户手册
- [用户手册](./用户手册.md) - 详细的使用说明和配置指南

### 技术文档
- [技术说明书](./技术说明书.md) - 系统架构和实现细节

### 参考示例
- [代码示例](./refer_examples/) - 各种规则的代码示例和最佳实践
