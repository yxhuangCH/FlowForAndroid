from openai import OpenAI

def semantic_review(code):
    client = OpenAI()

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
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
