from openai import OpenAI
import os
from pathlib import Path
import requests

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


def create_github_copilot_client(access_token: str):
    """创建 GitHub Copilot Chat API 客户端
    
    GitHub Copilot Chat API 使用 GitHub Access Token 进行认证
    需要先获取 Copilot Chat 的使用权限
    
    Args:
        access_token: GitHub Personal Access Token (ghp_xxx) 或 Copilot Token (ghu_xxx)
    
    Returns:
        配置好的 OpenAI 客户端
    """
    # GitHub Copilot Chat API 端点
    base_url = "https://api.githubcopilot.com"
    
    client = OpenAI(
        api_key=access_token,
        base_url=base_url,
        default_headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Editor-Version": "vscode/1.85.0",
            "Editor-Plugin-Version": "copilot-chat/0.11.0",
        }
    )
    
    return client


def semantic_review(code, provider: str = None):
    """执行语义代码审查
    
    Args:
        code: 要审查的代码
        provider: LLM 提供商，可选值: 'deepseek', 'openai', 'github_copilot', None(自动检测)
    
    Returns:
        审查结果的文本内容
    """
    # 尝试从 .env 文件加载环境变量
    load_env_if_exists()
    
    # 如果没有指定 provider，从环境变量读取
    if provider is None:
        provider = os.environ.get("LLM_PROVIDER", "auto").lower()
    
    # 获取 API key
    github_copilot_token = os.environ.get("GITHUB_COPILOT_TOKEN")
    deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    # 自动检测 provider
    if provider == "auto":
        if github_copilot_token:
            provider = "github_copilot"
        elif deepseek_api_key:
            provider = "deepseek"
        elif openai_api_key:
            provider = "openai"
        else:
            raise ValueError("未配置任何 LLM API Key，请设置 GITHUB_COPILOT_TOKEN、DEEPSEEK_API_KEY 或 OPENAI_API_KEY")
    
    # 根据 provider 创建客户端
    client = None
    model = None
    base_url = None
    
    if provider == "github_copilot":
        if not github_copilot_token:
            raise ValueError("使用 GitHub Copilot 时需要设置 GITHUB_COPILOT_TOKEN 环境变量")
        
        try:
            client = create_github_copilot_client(github_copilot_token)
            model = os.environ.get("LLM_MODEL", "gpt-4o-copilot")  # Copilot 默认使用 gpt-4o-copilot
            print(f"✓ 使用 GitHub Copilot Chat API")
        except Exception as e:
            raise ValueError(f"初始化 GitHub Copilot 客户端失败: {e}")
    
    elif provider == "deepseek":
        if not deepseek_api_key:
            raise ValueError("使用 DeepSeek 时需要设置 DEEPSEEK_API_KEY 环境变量")
        
        api_key = deepseek_api_key
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
        model = os.environ.get("LLM_MODEL", "deepseek-chat")
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"✓ 使用 DeepSeek API")
    
    elif provider == "openai":
        if not openai_api_key:
            raise ValueError("使用 OpenAI 时需要设置 OPENAI_API_KEY 环境变量")
        
        api_key = openai_api_key
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"✓ 使用 OpenAI API")
    
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
    
    # 构建提示词
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
    
    # 执行 API 调用
    try:
        # 对于 GitHub Copilot，需要处理特殊的错误情况
        if provider == "github_copilot":
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500
                )
                return response.choices[0].message.content
            except Exception as e:
                error_msg = str(e).lower()
                if "401" in error_msg or "unauthorized" in error_msg:
                    raise ValueError(
                        "GitHub Copilot 认证失败。请检查:\n"
                        "1. GITHUB_COPILOT_TOKEN 是否正确\n"
                        "2. Token 是否有 Copilot Chat 权限\n"
                        "3. 在 https://github.com/settings/copilot 确认已启用 Copilot"
                    )
                elif "403" in error_msg or "forbidden" in error_msg:
                    raise ValueError(
                        "GitHub Copilot 访问被拒绝。请检查:\n"
                        "1. 你的 GitHub 账户是否订阅了 GitHub Copilot\n"
                        "2. Token 是否有 'copilot' scope\n"
                        "3. 在 https://github.com/settings/tokens 创建带有 copilot 权限的 token"
                    )
                else:
                    raise
        else:
            # DeepSeek 和 OpenAI 使用备用端点逻辑
            if provider == "deepseek":
                backup_endpoints = [
                    base_url,
                    "https://api.deepseek.com",
                    "https://api-dashboard.deepseek.com",
                    "https://api.deepseek.ai"
                ]
            else:
                backup_endpoints = [base_url]
            
            last_error = None
            for endpoint in backup_endpoints:
                try:
                    test_client = OpenAI(
                        api_key=api_key if provider == "deepseek" else openai_api_key,
                        base_url=endpoint
                    )
                    
                    response = test_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=500
                    )
                    
                    return response.choices[0].message.content
                    
                except Exception as e:
                    last_error = e
                    print(f"⚠ 端点 {endpoint} 失败: {str(e)[:100]}")
                    continue
            
            if last_error:
                raise last_error
    
    except Exception as e:
        raise ValueError(f"LLM API 调用失败: {e}")


def get_available_providers():
    """获取当前可用的 LLM 提供商列表"""
    load_env_if_exists()
    
    providers = []
    
    if os.environ.get("GITHUB_COPILOT_TOKEN"):
        providers.append(("github_copilot", "GitHub Copilot"))
    if os.environ.get("DEEPSEEK_API_KEY"):
        providers.append(("deepseek", "DeepSeek"))
    if os.environ.get("OPENAI_API_KEY"):
        providers.append(("openai", "OpenAI"))
    
    return providers


def validate_provider_config(provider: str) -> tuple[bool, str]:
    """验证 LLM 提供商的配置是否正确
    
    Args:
        provider: 提供商名称
    
    Returns:
        (是否有效, 错误信息)
    """
    load_env_if_exists()
    
    if provider == "github_copilot":
        token = os.environ.get("GITHUB_COPILOT_TOKEN")
        if not token:
            return False, "未设置 GITHUB_COPILOT_TOKEN"
        
        # 简单验证 token 格式
        if not (token.startswith("ghp_") or token.startswith("ghu_")):
            return False, "GITHUB_COPILOT_TOKEN 格式不正确，应以 ghp_ 或 ghu_ 开头"
        
        return True, "配置有效"
    
    elif provider == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            return False, "未设置 DEEPSEEK_API_KEY"
        if not api_key.startswith("sk-"):
            return False, "DEEPSEEK_API_KEY 格式不正确，应以 sk- 开头"
        return True, "配置有效"
    
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return False, "未设置 OPENAI_API_KEY"
        if not api_key.startswith("sk-"):
            return False, "OPENAI_API_KEY 格式不正确，应以 sk- 开头"
        return True, "配置有效"
    
    else:
        return False, f"未知的提供商: {provider}"
