#!/bin/bash
# DeepSeek API 环境变量设置脚本
# 使用方法: source setup_env.sh 或 ./setup_env.sh

echo "=== DeepSeek API 环境变量设置 ==="

# 检查是否已经设置
if [ -n "$DEEPSEEK_API_KEY" ]; then
    echo "✓ DEEPSEEK_API_KEY 已设置"
else
    echo "✗ DEEPSEEK_API_KEY 未设置"
fi

# 显示当前shell
echo "当前shell: $SHELL"
echo "当前用户: $(whoami)"

# 配置文件路径
ZSHRC="$HOME/.zshrc"
BASH_PROFILE="$HOME/.bash_profile"
BASH_RC="$HOME/.bashrc"

# 显示当前配置文件
echo ""
echo "检测到的配置文件:"
for file in "$ZSHRC" "$BASH_PROFILE" "$BASH_RC"; do
    if [ -f "$file" ]; then
        echo "  $file (存在)"
    else
        echo "  $file (不存在)"
    fi
done

echo ""
echo "=== 设置选项 ==="
echo "1. 临时设置（仅在当前终端生效）"
echo "2. 永久设置（添加到 ~/.zshrc）"
echo "3. 永久设置（添加到 ~/.bash_profile）"
echo "4. 永久设置（添加到 ~/.bashrc）"
echo "5. 创建 .env 文件（项目内使用）"
echo "6. 测试当前设置"
echo "7. 退出"
echo ""

read -p "请选择选项 (1-7): " choice

case $choice in
    1)
        # 临时设置
        echo ""
        echo "=== 临时设置 ==="
        read -p "请输入你的 DeepSeek API Key: " api_key
        export DEEPSEEK_API_KEY="$api_key"
        echo "export DEEPSEEK_API_KEY=\"$api_key\"" > /tmp/deepseek_temp.sh
        echo "export LLM_MODEL=\"deepseek-chat\"" >> /tmp/deepseek_temp.sh
        echo "export OPENAI_BASE_URL=\"https://api.deepseek.com\"" >> /tmp/deepseek_temp.sh
        source /tmp/deepseek_temp.sh
        echo "✓ 环境变量已设置（仅当前终端生效）"
        echo "  使用: source /tmp/deepseek_temp.sh 在其他终端应用相同设置"
        ;;
    2|3|4)
        # 永久设置
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
            echo "创建配置文件: $config_file"
            touch "$config_file"
        fi
        
        echo ""
        echo "=== 永久设置 (添加到 $config_name) ==="
        read -p "请输入你的 DeepSeek API Key: " api_key
        
        # 移除已有的设置
        sed -i '' '/^export DEEPSEEK_API_KEY=/d' "$config_file" 2>/dev/null || true
        sed -i '' '/^export LLM_MODEL=/d' "$config_file" 2>/dev/null || true
        sed -i '' '/^export OPENAI_BASE_URL=/d' "$config_file" 2>/dev/null || true
        
        # 添加新的设置
        echo "" >> "$config_file"
        echo "# DeepSeek API 配置" >> "$config_file"
        echo "export DEEPSEEK_API_KEY=\"$api_key\"" >> "$config_file"
        echo "export LLM_MODEL=\"deepseek-chat\"" >> "$config_file"
        echo "export OPENAI_BASE_URL=\"https://api.deepseek.com\"" >> "$config_file"
        
        echo "✓ 已添加到 $config_name"
        echo "  请运行以下命令使配置生效:"
        echo "  source $config_file"
        echo "  或者重新打开终端"
        ;;
    5)
        # 创建 .env 文件
        echo ""
        echo "=== 创建 .env 文件 ==="
        read -p "请输入你的 DeepSeek API Key: " api_key
        
        cat > .env << EOF
# DeepSeek API 配置
DEEPSEEK_API_KEY=$api_key
LLM_MODEL=deepseek-chat
OPENAI_BASE_URL=https://api.deepseek.com
EOF
        
        echo "✓ 已创建 .env 文件"
        echo "  文件内容:"
        cat .env
        echo ""
        echo "  注意: .env 文件需要在脚本中加载才能生效"
        echo "  在 Python 中可以使用 python-dotenv 库加载"
        ;;
    6)
        # 测试设置
        echo ""
        echo "=== 测试当前设置 ==="
        python3 -c "
import os
print('当前环境变量设置:')
print('DEEPSEEK_API_KEY:', '✓ 已设置' if os.environ.get('DEEPSEEK_API_KEY') else '✗ 未设置')
print('OPENAI_API_KEY:', '✓ 已设置' if os.environ.get('OPENAI_API_KEY') else '✗ 未设置')
print('LLM_MODEL:', os.environ.get('LLM_MODEL', 'deepseek-chat (默认)'))
print('OPENAI_BASE_URL:', os.environ.get('OPENAI_BASE_URL', 'https://api.deepseek.com (默认)'))

# 测试导入
try:
    from llm_layer import semantic_review
    print('\\nLLM层导入: ✓ 成功')
    # 测试简单的API调用（不需要实际调用）
    print('LLM配置检查: ✓ 配置完成')
except ImportError as e:
    print(f'\\nLLM层导入: ✗ 失败: {e}')
except Exception as e:
    print(f'\\n其他错误: {e}')
        "
        ;;
    7)
        echo "退出"
        ;;
    *)
        echo "无效选项"
        ;;
esac

echo ""
echo "=== 使用说明 ==="
echo "1. 设置完成后，运行代码审查: python3 review.py"
echo "2. 如果看到 'LLM语义分析失败' 错误，说明API Key未正确设置"
echo "3. 确保API Key有效且网络连接正常"
echo "4. 如需帮助，参考 README.md 中的说明"
echo ""
echo "当前工作目录: $(pwd)"