from openai import OpenAI
import os

def semantic_review(code):
    # 获取 API key，优先使用 DEEPSEEK_API_KEY，回退到 OPENAI_API_KEY
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("Please set either DEEPSEEK_API_KEY or OPENAI_API_KEY environment variable")
    
    # 默认使用 DeepSeek API，如果设置了 DEEPSEEK_API_KEY
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
    
    # 默认模型，可以通过环境变量覆盖
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    prompt = f"""
你是 Android 代码审查专家。
分析以下代码是否：
1. 违反单一职责
2. 过度耦合
3. 难以单元测试
输出 JSON。
代码：
{code}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
