from openai import OpenAI
import os
from pathlib import Path

def load_env_if_exists():
    """如果存在 .env 文件，加载环境变量"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
            print(f"✓ 已从 {env_path} 加载环境变量")
            return True
        except ImportError:
            print("⚠ dotenv 未安装，无法从 .env 文件加载")
            return False
    return False

def semantic_review(code):
    # 尝试从 .env 文件加载环境变量
    load_env_if_exists()
    
    # 获取 API key，优先使用 DEEPSEEK_API_KEY，回退到 OPENAI_API_KEY
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("Please set either DEEPSEEK_API_KEY or OPENAI_API_KEY environment variable")
    
    # 默认使用 DeepSeek API，如果设置了 DEEPSEEK_API_KEY
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
    
    # 默认模型，可以通过环境变量覆盖
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    
    # 如果使用 DeepSeek，尝试备用端点
    if "deepseek" in base_url or "deepseek" in model.lower():
        # 尝试备用端点
        backup_endpoints = [
            "https://api.deepseek.com",
            "https://api-dashboard.deepseek.com",
            "https://api.deepseek.ai"
        ]
    else:
        backup_endpoints = [base_url]
    
    client = None
    last_error = None
    
    for endpoint in backup_endpoints:
        try:
            client = OpenAI(
                api_key=api_key,
                base_url=endpoint
            )
            
            # 测试连接
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
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500  # 限制token以节省成本
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            last_error = e
            print(f"⚠ 端点 {endpoint} 失败: {str(e)[:100]}")
            continue
    
    # 所有端点都失败，抛出最后一个错误
    if last_error:
        raise last_error
    else:
        raise ValueError("所有API端点尝试都失败")
