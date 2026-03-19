#!/bin/bash
# DeepSeek API Environment Variable Setup Script
# Usage: source setup_env.sh or ./setup_env.sh

echo "=== DeepSeek API Environment Variable Setup ==="

# Check if already set
if [ -n "$DEEPSEEK_API_KEY" ]; then
    echo "✓ DEEPSEEK_API_KEY is already set"
else
    echo "✗ DEEPSEEK_API_KEY is not set"
fi

# Display current shell
echo "Current shell: $SHELL"
echo "Current user: $(whoami)"

# Configuration file paths
ZSHRC="$HOME/.zshrc"
BASH_PROFILE="$HOME/.bash_profile"
BASH_RC="$HOME/.bashrc"

# Display current configuration files
echo ""
echo "Detected configuration files:"
for file in "$ZSHRC" "$BASH_PROFILE" "$BASH_RC"; do
    if [ -f "$file" ]; then
        echo "  $file (exists)"
    else
        echo "  $file (not exists)"
    fi
done

echo ""
echo "=== Setup Options ==="
echo "1. Temporary setup (only effective in current terminal)"
echo "2. Permanent setup (add to ~/.zshrc)"
echo "3. Permanent setup (add to ~/.bash_profile)"
echo "4. Permanent setup (add to ~/.bashrc)"
echo "5. Create .env file (for project use)"
echo "6. Test current setup"
echo "7. Exit"
echo ""

read -p "Please select an option (1-7): " choice

case $choice in
    1)
        # Temporary setup
        echo ""
        echo "=== Temporary Setup ==="
        read -p "Please enter your DeepSeek API Key: " api_key
        export DEEPSEEK_API_KEY="$api_key"
        echo "export DEEPSEEK_API_KEY=\"$api_key\"" > /tmp/deepseek_temp.sh
        echo "export LLM_MODEL=\"deepseek-chat\"" >> /tmp/deepseek_temp.sh
        echo "export OPENAI_BASE_URL=\"https://api.deepseek.com\"" >> /tmp/deepseek_temp.sh
        source /tmp/deepseek_temp.sh
        echo "✓ Environment variables set (only effective in current terminal)"
        echo "  Usage: source /tmp/deepseek_temp.sh to apply same settings in other terminals"
        ;;
    2|3|4)
        # Permanent setup
        if [ $choice -eq 2 ]; then
            config_file="$ZSHRC"
            config_name="~/.zshrc"
        elif [ $choice -eq 3 ]; then
            config_file="$BASH_PROFILE"
            config_name="~/.bash_profile"
        else
            config_file="$BASH_RC"
            config_name="~/.bashrc"
        fi
        
        if [ ! -f "$config_file" ]; then
            echo "Creating configuration file: $config_file"
            touch "$config_file"
        fi
        
        echo ""
        echo "=== Permanent Setup (add to $config_name) ==="
        read -p "Please enter your DeepSeek API Key: " api_key
        
        # Remove existing settings
        sed -i '' '/^export DEEPSEEK_API_KEY=/d' "$config_file" 2>/dev/null || true
        sed -i '' '/^export LLM_MODEL=/d' "$config_file" 2>/dev/null || true
        sed -i '' '/^export OPENAI_BASE_URL=/d' "$config_file" 2>/dev/null || true
        
        # Add new settings
        echo "" >> "$config_file"
        echo "# DeepSeek API Configuration" >> "$config_file"
        echo "export DEEPSEEK_API_KEY=\"$api_key\"" >> "$config_file"
        echo "export LLM_MODEL=\"deepseek-chat\"" >> "$config_file"
        echo "export OPENAI_BASE_URL=\"https://api.deepseek.com\"" >> "$config_file"
        
        echo "✓ Added to $config_name"
        echo "  Please run the following command to make configuration effective:"
        echo "  source $config_file"
        echo "  Or reopen the terminal"
        ;;
    5)
        # Create .env file
        echo ""
        echo "=== Creating .env File ==="
        read -p "Please enter your DeepSeek API Key: " api_key
        
        cat > .env << EOF
# DeepSeek API Configuration
DEEPSEEK_API_KEY=$api_key
LLM_MODEL=deepseek-chat
OPENAI_BASE_URL=https://api.deepseek.com
EOF
        
        echo "✓ .env file created"
        echo "  File content:"
        cat .env
        echo ""
        echo "  Note: .env file needs to be loaded in scripts to take effect"
        echo "  Can use python-dotenv library to load in Python"
        ;;
    6)
        # Test setup
        echo ""
        echo "=== Testing Current Setup ==="
        python3 -c "
import os
print('Current environment variables:')
print('DEEPSEEK_API_KEY:', '✓ Set' if os.environ.get('DEEPSEEK_API_KEY') else '✗ Not set')
print('OPENAI_API_KEY:', '✓ Set' if os.environ.get('OPENAI_API_KEY') else '✗ Not set')
print('LLM_MODEL:', os.environ.get('LLM_MODEL', 'deepseek-chat (default)'))
print('OPENAI_BASE_URL:', os.environ.get('OPENAI_BASE_URL', 'https://api.deepseek.com (default)'))

# Test import
try:
    from llm_layer import semantic_review
    print('\nLLM layer import: ✓ Success')
    # Test simple API call (no actual call needed)
    print('LLM configuration check: ✓ Complete')
except ImportError as e:
    print(f'\nLLM layer import: ✗ Failed: {e}')
except Exception as e:
    print(f'\nOther error: {e}')
        "
        ;;
    7)
        echo "Exit"
        ;;
    *)
        echo "Invalid option"
        ;;
esac

echo ""
echo "=== Usage Instructions ==="
echo "1. After setup, run code review: python3 review.py"
echo "2. If you see 'LLM semantic analysis failed' error, API Key is not set correctly"
echo "3. Ensure API Key is valid and network connection is normal"
echo "4. For help, refer to README.md"
echo ""
echo "Current working directory: $(pwd)"
