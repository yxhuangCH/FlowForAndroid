from openai import OpenAI
import os
from pathlib import Path
import requests

def load_env_if_exists():
    """Load environment variables from .env file if exists"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
            print(f"✓ Environment variables loaded from {env_path}")
            return True
        except ImportError:
            print("⚠ dotenv not installed, cannot load from .env file")
            return False
    return False


def create_github_copilot_client(access_token: str):
    """Create GitHub Copilot Chat API client
    
    GitHub Copilot Chat API uses GitHub Access Token for authentication
    Need to obtain Copilot Chat usage permission first
    
    Args:
        access_token: GitHub Personal Access Token (ghp_xxx) or Copilot Token (ghu_xxx)
    
    Returns:
        Configured OpenAI client
    """
    # GitHub Copilot Chat API endpoint
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
    """Perform semantic code review
    
    Args:
        code: Code to review
        provider: LLM provider, optional values: 'deepseek', 'openai', 'github_copilot', None (auto-detect)
    
    Returns:
        Review result text content
    """
    # Try to load environment variables from .env file
    load_env_if_exists()
    
    # If no provider specified, read from environment variable
    if provider is None:
        provider = os.environ.get("LLM_PROVIDER", "auto").lower()
    
    # Get API key
    github_copilot_token = os.environ.get("GITHUB_COPILOT_TOKEN")
    deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    # Auto-detect provider
    if provider == "auto":
        if github_copilot_token:
            provider = "github_copilot"
        elif deepseek_api_key:
            provider = "deepseek"
        elif openai_api_key:
            provider = "openai"
        else:
            raise ValueError("No LLM API Key configured. Please set GITHUB_COPILOT_TOKEN, DEEPSEEK_API_KEY, or OPENAI_API_KEY")
    
    # Create client based on provider
    client = None
    model = None
    base_url = None
    
    if provider == "github_copilot":
        if not github_copilot_token:
            raise ValueError("GITHUB_COPILOT_TOKEN environment variable is required when using GitHub Copilot")
        
        try:
            client = create_github_copilot_client(github_copilot_token)
            model = os.environ.get("LLM_MODEL", "gpt-4o-copilot")  # Copilot defaults to gpt-4o-copilot
            print(f"✓ Using GitHub Copilot Chat API")
        except Exception as e:
            raise ValueError(f"Failed to initialize GitHub Copilot client: {e}")
    
    elif provider == "deepseek":
        if not deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required when using DeepSeek")
        
        api_key = deepseek_api_key
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
        model = os.environ.get("LLM_MODEL", "deepseek-chat")
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"✓ Using DeepSeek API")
    
    elif provider == "openai":
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required when using OpenAI")
        
        api_key = openai_api_key
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"✓ Using OpenAI API")
    
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    
    # Build prompt
    prompt = f"""
You are an Android code review expert.
Analyze the following code for:
1. Single responsibility violations
2. Excessive coupling
3. Difficulty in unit testing
Output JSON.
Code:
{code}
"""
    
    # Execute API call
    try:
        # For GitHub Copilot, need to handle special error cases
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
                        "GitHub Copilot authentication failed. Please check:\n"
                        "1. Whether GITHUB_COPILOT_TOKEN is correct\n"
                        "2. Whether the token has Copilot Chat permission\n"
                        "3. Confirm Copilot is enabled at https://github.com/settings/copilot"
                    )
                elif "403" in error_msg or "forbidden" in error_msg:
                    raise ValueError(
                        "GitHub Copilot access denied. Please check:\n"
                        "1. Whether your GitHub account has GitHub Copilot subscription\n"
                        "2. Whether the token has 'copilot' scope\n"
                        "3. Create a token with copilot permission at https://github.com/settings/tokens"
                    )
                else:
                    raise
        else:
            # DeepSeek and OpenAI use backup endpoint logic
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
                    print(f"⚠ Endpoint {endpoint} failed: {str(e)[:100]}")
                    continue
            
            if last_error:
                raise last_error
    
    except Exception as e:
        raise ValueError(f"LLM API call failed: {e}")


def get_available_providers():
    """Get list of currently available LLM providers"""
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
    """Validate LLM provider configuration
    
    Args:
        provider: Provider name
    
    Returns:
        (is valid, error message)
    """
    load_env_if_exists()
    
    if provider == "github_copilot":
        token = os.environ.get("GITHUB_COPILOT_TOKEN")
        if not token:
            return False, "GITHUB_COPILOT_TOKEN not set"
        
        # Simple token format validation
        if not (token.startswith("ghp_") or token.startswith("ghu_")):
            return False, "GITHUB_COPILOT_TOKEN format incorrect, should start with ghp_ or ghu_"
        
        return True, "Configuration valid"
    
    elif provider == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            return False, "DEEPSEEK_API_KEY not set"
        if not api_key.startswith("sk-"):
            return False, "DEEPSEEK_API_KEY format incorrect, should start with sk-"
        return True, "Configuration valid"
    
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return False, "OPENAI_API_KEY not set"
        if not api_key.startswith("sk-"):
            return False, "OPENAI_API_KEY format incorrect, should start with sk-"
        return True, "Configuration valid"
    
    else:
        return False, f"Unknown provider: {provider}"
