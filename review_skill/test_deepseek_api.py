#!/usr/bin/env python3
"""
DeepSeek API Test Script
Used to verify if the API Key is valid
"""

import os
import sys
from pathlib import Path
import json

def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
            print(f"✓ Environment variables loaded from {env_path}")
        except ImportError:
            print("⚠ dotenv not installed, skipping .env loading")
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY environment variable not found")
        return None
    
    return api_key

def test_api_key_direct(api_key):
    """Test API Key directly"""
    print(f"\n=== Direct API Key Test ===")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Length: {len(api_key)} characters")
    print(f"Starts with 'sk-': {api_key.startswith('sk-')}")
    
    # Check common issues
    issues = []
    if not api_key.startswith('sk-'):
        issues.append("API Key should start with 'sk-'")
    if len(api_key) < 32:
        issues.append("API Key may be too short (usually at least 32 characters)")
    if len(api_key) > 64:
        issues.append("API Key may be too long")
    
    if issues:
        print("⚠ Potential issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ API Key format check passed")

def test_with_curl(api_key):
    """Test API using curl"""
    print(f"\n=== Testing API with curl ===")
    
    # Test getting model list
    print("Testing /v1/models endpoint...")
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
        
        print(f"Status code: {result.returncode}")
        print(f"Response: {result.stdout}")
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                if "data" in data:
                    print("✓ API connection successful!")
                    print(f"Available models: {len(data['data'])} models")
                    return True
                elif "error" in data:
                    print(f"❌ API error: {data['error']}")
                else:
                    print(f"⚠ Unknown response format: {data}")
            except json.JSONDecodeError:
                print(f"⚠ Cannot parse JSON: {result.stdout}")
        else:
            print(f"❌ curl command failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    return False

def test_with_openai_library(api_key):
    """Test API using OpenAI library"""
    print(f"\n=== Testing API with OpenAI library ===")
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        # Test simple chat request
        print("Sending test request...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": "Hello, say 'test successful' if you can read this."}
            ],
            max_tokens=10
        )
        
        print(f"✓ API request successful!")
        print(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI library test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== DeepSeek API Verification Tool ===")
    
    # Load API Key
    api_key = load_env()
    if not api_key:
        sys.exit(1)
    
    # Direct analysis of API Key
    test_api_key_direct(api_key)
    
    # Test curl
    print("\n" + "="*50)
    if test_with_curl(api_key):
        print("\n✓ curl test successful!")
    else:
        print("\n❌ curl test failed")
    
    # Test OpenAI library
    print("\n" + "="*50)
    if test_with_openai_library(api_key):
        print("\n✓ OpenAI library test successful!")
    else:
        print("\n❌ OpenAI library test failed")
    
    print("\n" + "="*50)
    print("Summary:")
    print("1. If all tests fail, the API Key may be invalid or expired")
    print("2. Try regenerating the API Key: https://platform.deepseek.com/api_keys")
    print("3. Check network connection and firewall settings")
    print("4. Confirm account balance or usage limits")

if __name__ == "__main__":
    main()
