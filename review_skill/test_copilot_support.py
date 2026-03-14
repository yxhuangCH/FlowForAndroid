#!/usr/bin/env python3
"""
测试 GitHub Copilot 支持
验证 LLM 提供商配置和可用性检测
"""

import os
import sys
from pathlib import Path

# 确保可以导入 llm_layer
sys.path.insert(0, str(Path(__file__).parent))

from llm_layer import (
    get_available_providers,
    validate_provider_config,
    semantic_review,
    load_env_if_exists
)
from config import get_config


def test_provider_detection():
    """测试提供商自动检测"""
    print("=" * 60)
    print("测试 LLM 提供商自动检测")
    print("=" * 60)
    
    # 加载环境变量
    load_env_if_exists()
    
    # 获取可用提供商
    providers = get_available_providers()
    print(f"\n✓ 检测到 {len(providers)} 个可用的 LLM 提供商:")
    for provider_id, provider_name in providers:
        print(f"  - {provider_id}: {provider_name}")
    
    return providers


def test_provider_validation():
    """测试提供商配置验证"""
    print("\n" + "=" * 60)
    print("测试 LLM 提供商配置验证")
    print("=" * 60)
    
    providers = ['github_copilot', 'deepseek', 'openai']
    
    for provider in providers:
        is_valid, message = validate_provider_config(provider)
        status = "✓" if is_valid else "✗"
        print(f"\n{status} {provider}:")
        print(f"   {message}")


def test_config_integration():
    """测试配置集成"""
    print("\n" + "=" * 60)
    print("测试配置集成")
    print("=" * 60)
    
    config = get_config()
    
    print(f"\nLLM 提供商: {config.get_llm_provider()}")
    print(f"LLM 模型: {config.get_llm_model()}")
    print(f"LLM 完整配置: {config.get_llm_config()}")


def test_semantic_review_mock():
    """测试语义审查功能（使用 mock）"""
    print("\n" + "=" * 60)
    print("测试语义审查功能")
    print("=" * 60)
    
    # 测试代码
    test_code = """
class UserManager {
    fun processUser(user: User) {
        // 验证用户
        if (user.age < 0) throw IllegalArgumentException()
        // 保存到数据库
        database.save(user)
        // 发送邮件
        emailService.sendWelcomeEmail(user)
        // 记录日志
        logger.info("User processed")
    }
}
"""
    
    # 检查是否有任何提供商配置
    providers = get_available_providers()
    
    if not providers:
        print("\n✗ 未配置任何 LLM 提供商，跳过测试")
        print("   请设置 GITHUB_COPILOT_TOKEN、DEEPSEEK_API_KEY 或 OPENAI_API_KEY")
        return
    
    # 尝试使用第一个可用提供商
    provider_id = providers[0][0]
    print(f"\n✓ 使用提供商: {provider_id}")
    
    try:
        # 由于需要真实 API key，这里只是演示调用方式
        # 实际使用时取消注释下面这行:
        # result = semantic_review(test_code, provider=provider_id)
        print("   (跳过实际 API 调用，需要有效的 API key)")
        print("   调用方式: semantic_review(code, provider='github_copilot')")
    except Exception as e:
        print(f"   ✗ 调用失败: {e}")


def print_setup_guide():
    """打印设置指南"""
    print("\n" + "=" * 60)
    print("GitHub Copilot 设置指南")
    print("=" * 60)
    
    guide = """
1. 获取 GitHub Copilot Token:
   - 访问 https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 勾选 'copilot' scope
   - 生成并复制 token (格式: ghp_xxx)

2. 配置环境变量:
   复制 .env.example 为 .env:
   $ cp .env.example .env
   
   编辑 .env 文件，添加:
   GITHUB_COPILOT_TOKEN=ghp_your_token_here
   LLM_PROVIDER=github_copilot

3. 验证配置:
   $ python test_copilot_support.py

4. 使用:
   - 设置 LLM_PROVIDER=github_copilot 指定使用 Copilot
   - 或保持 LLM_PROVIDER=auto 自动检测
"""
    print(guide)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Review Skill - GitHub Copilot 支持测试")
    print("=" * 60)
    
    try:
        # 运行测试
        test_provider_detection()
        test_provider_validation()
        test_config_integration()
        test_semantic_review_mock()
        print_setup_guide()
        
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
