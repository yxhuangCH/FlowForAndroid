#!/usr/bin/env python3
"""
DeepSeek API 测试脚本
用于验证 API Key 是否有效
"""

import os
import sys
from pathlib import Path
import json

def load_env():
    """从 .env 文件加载环境变量"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
            print(f"✓ 已从 {env_path} 加载环境变量")
        except ImportError:
            print("⚠ dotenv 未安装，跳过 .env 加载")
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 未找到 DEEPSEEK_API_KEY 环境变量")
        return None
    
    return api_key

def test_api_key_direct(api_key):
    """直接测试 API Key"""
    print(f"\n=== 直接测试 API Key ===")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"长度: {len(api_key)} 字符")
    print(f"以 'sk-' 开头: {api_key.startswith('sk-')}")
    
    # 检查常见问题
    issues = []
    if not api_key.startswith('sk-'):
        issues.append("API Key 应以 'sk-' 开头")
    if len(api_key) < 32:
        issues.append("API Key 可能过短（通常至少32字符）")
    if len(api_key) > 64:
        issues.append("API Key 可能过长")
    
    if issues:
        print("⚠ 潜在问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ API Key 格式检查通过")

def test_with_curl(api_key):
    """使用 curl 测试 API"""
    print(f"\n=== 使用 curl 测试 API ===")
    
    # 测试获取模型列表
    print("测试 /v1/models 端点...")
    import subprocess
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "GET",
                "https://api.deepseek.com/v1/models",
                "-H", f"Authorization: Bearer {api_key}"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"状态码: {result.returncode}")
        print(f"响应: {result.stdout}")
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                if "data" in data:
                    print("✓ API 连接成功！")
                    print(f"可用模型: {len(data['data'])} 个")
                    return True
                elif "error" in data:
                    print(f"❌ API 错误: {data['error']}")
                else:
                    print(f"⚠ 未知响应格式: {data}")
            except json.JSONDecodeError:
                print(f"⚠ 无法解析 JSON: {result.stdout}")
        else:
            print(f"❌ curl 命令失败: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    return False

def test_with_openai_library(api_key):
    """使用 OpenAI 库测试 API"""
    print(f"\n=== 使用 OpenAI 库测试 API ===")
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        # 测试简单的聊天请求
        print("发送测试请求...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": "Hello, say 'test successful' if you can read this."}
            ],
            max_tokens=10
        )
        
        print(f"✓ API 请求成功！")
        print(f"响应: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI 库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== DeepSeek API 验证工具 ===")
    
    # 加载 API Key
    api_key = load_env()
    if not api_key:
        sys.exit(1)
    
    # 直接分析 API Key
    test_api_key_direct(api_key)
    
    # 测试 curl
    print("\n" + "="*50)
    if test_with_curl(api_key):
        print("\n✓ curl 测试成功！")
    else:
        print("\n❌ curl 测试失败")
    
    # 测试 OpenAI 库
    print("\n" + "="*50)
    if test_with_openai_library(api_key):
        print("\n✓ OpenAI 库测试成功！")
    else:
        print("\n❌ OpenAI 库测试失败")
    
    print("\n" + "="*50)
    print("总结:")
    print("1. 如果所有测试都失败，API Key 可能无效或已过期")
    print("2. 尝试重新生成 API Key: https://platform.deepseek.com/api_keys")
    print("3. 检查网络连接和防火墙设置")
    print("4. 确认账户余额或使用限制")

if __name__ == "__main__":
    main()