

设计目标：

✅ 支持 Git diff 输入

✅ Kotlin 静态规则扫描

✅ Compose / Coroutine 专项规则

✅ LLM 语义增强（可选）

✅ 结构化 JSON 输出

✅ 可用于 GitHub Action


# 说明

主入口： review.py

## DeepSeek 集成说明

### 环境变量配置

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

### 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖说明

- `openai>=1.0.0` - OpenAI 兼容的 Python SDK，支持 DeepSeek API
- `gitpython>=3.1.40` - Git 操作支持

## 运行测试

```bash
cd review_skill
python3 review.py
```

注意：需要设置相应的 API Key 环境变量才能使用 LLM 语义增强功能。
