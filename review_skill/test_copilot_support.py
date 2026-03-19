#!/usr/bin/env python3
"""
Test GitHub Copilot Support

Verify LLM provider configuration and availability detection
"""

import sys
from pathlib import Path

# Ensure llm_layer can be imported
sys.path.insert(0, str(Path(__file__).parent))

from llm_layer import (
    get_available_providers,
    validate_provider_config,
    LLMConfig,
    semantic_review
)
from dotenv import load_dotenv


def load_env_if_exists():
    """Load environment variables if .env file exists"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)


def test_provider_detection():
    """Test provider auto-detection"""
    print("=" * 60)
    print("Testing LLM Provider Auto-Detection")
    print("=" * 60)

    # Load environment variables
    load_env_if_exists()

    # Get available providers
    providers = get_available_providers()

    print(f"\n✓ Detected {len(providers)} available LLM providers:")
    for provider_id, provider_name in providers:
        print(f"  - {provider_id}: {provider_name}")

    return len(providers) > 0


def test_provider_validation():
    """Test provider configuration validation"""
    print("\n" + "=" * 60)
    print("Testing LLM Provider Configuration Validation")
    print("=" * 60)

    # Load environment variables
    load_env_if_exists()

    # Test each provider
    all_providers = ['github_copilot', 'deepseek', 'openai']

    print("\nProvider configuration validation results:")
    for provider_id in all_providers:
        is_valid, message = validate_provider_config(provider_id)
        status = "✓" if is_valid else "✗"
        print(f"  {status} {provider_id}: {message}")


def test_config_integration():
    """Test configuration integration"""
    print("\n" + "=" * 60)
    print("Testing Configuration Integration")
    print("=" * 60)

    # Load environment variables
    load_env_if_exists()

    # Test configuration class
    config = LLMConfig()

    print(f"\nLLM Provider: {config.get_llm_provider()}")
    print(f"LLM Model: {config.get_llm_model()}")
    print(f"LLM Full Configuration: {config.get_llm_config()}")


def test_semantic_review_mock():
    """Test semantic review functionality (using mock)"""
    print("\n" + "=" * 60)
    print("Testing Semantic Review Functionality")
    print("=" * 60)

    # Load environment variables
    load_env_if_exists()

    # Test code
    test_code = """
    fun processUser(user: User) {
        // Validate user
        if (user.age < 0) throw IllegalArgumentException()

        // Save to database
        database.save(user)

        // Send email
        emailService.sendWelcomeEmail(user)

        // Log
        logger.info("User processed")
    }
    """

    print("\nTest code:")
    print(test_code)

    # Check if any provider is configured
    providers = get_available_providers()
    if not providers:
        print("\n✗ No LLM providers configured, skipping test")
        print("   Please set GITHUB_COPILOT_TOKEN, DEEPSEEK_API_KEY, or OPENAI_API_KEY")
        return

    # Try using the first available provider
    provider_id = providers[0][0]

    print(f"\n✓ Using provider: {provider_id}")

    try:
        # Since real API keys are needed, this is just a demonstration of the call method

        # Uncomment below line for actual usage:
        # result = semantic_review(test_code, provider=provider_id)

        print("   (Skipping actual API call, needs valid API key)")
        print("   Call method: semantic_review(code, provider='github_copilot')")
    except Exception as e:
        print(f"   ✗ Call failed: {e}")


def print_setup_guide():
    """Print setup guide"""
    print("\n" + "=" * 60)
    print("GitHub Copilot Setup Guide")
    print("=" * 60)
    guide = """
1. Get GitHub Copilot Token:

   - Visit https://github.com/settings/tokens

   - Click "Generate new token (classic)"

   - Check 'copilot' scope

   - Generate and copy token (format: ghp_xxx)

2. Configure Environment Variables:

   Copy .env.example to .env:
   $ cp .env.example .env

   Edit .env file, add:
   GITHUB_COPILOT_TOKEN=ghp_your_token_here

3. Verify Configuration:
   $ python test_copilot_support.py

4. Usage:

   - Set LLM_PROVIDER=github_copilot to use Copilot

   - Or keep LLM_PROVIDER=auto for auto-detection
"""
    print(guide)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Review Skill - GitHub Copilot Support Test")
    print("=" * 60)
    try:
        # Run tests
        test_provider_detection()
        print("\n" + "=" * 60)
        test_provider_validation()
        test_config_integration()
        test_semantic_review_mock()

        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
