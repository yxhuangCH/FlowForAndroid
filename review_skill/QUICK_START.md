# Review Skill 快速开始指南

> 在5分钟内运行你的第一个代码审查

本指南将帮助你快速上手Review Skill，让你在最短时间内了解基本功能并开始使用。

## 🚀 极简安装（3步）

### 步骤1：获取项目
```bash
# 如果你还没有项目
git clone https://github.com/your-org/review_skill.git
cd review_skill

# 如果你已经有项目
cd review_skill
```

### 步骤2：安装依赖
```bash
pip install -r requirements.txt
```

### 步骤3：验证安装
```bash
python3 review.py --version
# 应该显示版本信息，如：review_skill v1.0.0
```

### 步骤4：安装 Git Hook（可选，团队使用时推荐）
> ⚠️ **注意**: `.git/hooks/` 目录是本地目录，**不会被 git 追踪或包含在仓库中**。因此克隆仓库后需要手动运行安装脚本。

```bash
chmod +x install-git-hook.sh
./install-git-hook.sh
```

安装后，每次 `git push` 会自动执行代码审查。

## 🔧 最简配置

### 基本配置（可选）
创建最简单的配置文件 `minimal_config.json`：

```json
{
  "file_extensions": [".kt"],
  "scan_directories": ["."],
  "min_score_threshold": 70
}
```

或者直接使用环境变量：
```bash
# 最简单的环境变量配置
export REVIEW_FILE_EXTENSIONS=".kt"
export REVIEW_SCAN_DIRECTORIES="."
export REVIEW_MIN_SCORE_THRESHOLD=70
```

### LLM配置（可选，增强功能）
如果需要AI智能分析：
```bash
# DeepSeek API（推荐）
export DEEPSEEK_API_KEY="your_api_key_here"

# 或者使用OpenAI
export OPENAI_API_KEY="your_openai_api_key"
```

## 📁 准备测试代码

创建一个简单的测试文件 `test.kt`：

```kotlin
// test.kt
class TestViewModel {
    // 这里有一个典型问题：使用GlobalScope
    fun testFunction() {
        GlobalScope.launch {
            println("在GlobalScope中执行")
        }
    }
    
    // 正确的做法
    fun correctFunction() {
        // viewModelScope.launch { }  // 需要ViewModel类
    }
}
```

## ▶️ 运行第一个审查

### 方式1：审查单个文件
```bash
# 创建测试文件的diff
echo "diff --git a/test.kt b/test.kt
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/test.kt
@@ -0,0 +1,12 @@
+// test.kt
+class TestViewModel {
+    // 这里有一个典型问题：使用GlobalScope
+    fun testFunction() {
+        GlobalScope.launch {
+            println(\"在GlobalScope中执行\")
+        }
+    }
+}" > test.diff

# 运行审查
python3 -c "
import sys
sys.path.append('.')
from review import review
import subprocess
result = subprocess.run(['python3', 'review.py'], capture_output=True, text=True)
print(result.stdout)
"
```

### 方式2：使用项目示例
```bash
# 查看项目自带的示例
ls refer_examples/

# 运行完整的审查流程
python3 review.py
```

## 📊 理解结果

### 控制台输出
你会看到类似下面的输出：

```
📊 代码审查结果
├── 总分: 85/100
├── 文件数: 1
├── 发现问题: 1个
│   └── critical: 1个
├── 建议: 通过（高于阈值70分）
├── HTML报告: report/code_review_report_20250303_221045.html
└── 详细JSON: report/code_review_details_20250303_221045.json
```

### 关键指标说明
- **总分**: 代码质量分数，100分为满分
- **发现问题**: 按严重级别分类的问题数量
- **建议**: 是否建议通过（基于配置的阈值）
- **报告文件**: 生成的详细报告位置

## 🔍 查看详细报告

### HTML报告
```bash
# 打开HTML报告（macOS）
open report/code_review_report_*.html

# 或使用浏览器打开
google-chrome report/code_review_report_*.html
```

### JSON报告
```bash
# 查看JSON格式的详细结果
cat report/code_review_details_*.json | python3 -m json.tool
```

## 🎯 核心功能快速体验

### 1. 基本规则检查
```bash
# 检查是否有GlobalScope使用
python3 -c "
code = '''
class MyClass {
    fun test() {
        GlobalScope.launch { }
    }
}
'''
from rules.base_rules import run_base_rules
findings = run_base_rules(code)
print('发现问题:', len(findings))
for f in findings:
    print(f'  - {f[\"rule\"]}: {f[\"message\"]}')
"
```

### 2. 分数计算
```bash
# 了解分数计算逻辑
python3 -c "
from scorer import calculate_score
findings = [
    {'severity': 'critical', 'rule': 'test', 'message': 'test'},
    {'severity': 'minor', 'rule': 'test', 'message': 'test'}
]
score = calculate_score(findings)
print(f'分数: {score}/100')
print(f'扣分: {100 - score}分')
"
```

### 3. 配置验证
```bash
# 检查配置是否正确加载
python3 -c "
from config import get_config
config = get_config()
print('文件扩展名:', config.get_file_extensions())
print('扫描目录:', config.get_scan_directories())
print('最小分数阈值:', config.get_min_score_threshold())
"
```

## 🚨 常见问题速查

### 问题1：没有找到任何文件
```bash
# 检查当前目录
pwd

# 检查是否有.kt文件
find . -name "*.kt" | head -5

# 放宽配置
export REVIEW_SCAN_DIRECTORIES="."
export REVIEW_FILE_EXTENSIONS=".kt,.java"
```

### 问题2：依赖安装失败
```bash
# 更新pip
pip install --upgrade pip

# 使用国内镜像（中国用户）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用conda
conda create -n review python=3.9
conda activate review
pip install -r requirements.txt
```

### 问题3：API密钥错误
```bash
# 测试DeepSeek API
python3 test_deepseek_api.py

# 或禁用LLM功能
export REVIEW_ENABLE_SEMANTIC="false"
```

## 📈 下一步学习路径

### 路线1：基本用户
1. ✅ **完成本快速指南** - 已经完成！
2. → [安装指南](docs/guide/01-getting-started/installation.md) - 详细安装说明
3. → [基本使用](docs/guide/01-getting-started/basic-usage.md) - 核心功能详解
4. → [配置说明](docs/guide/01-getting-started/configuration.md) - 完整配置选项
5. → [团队工作流](docs/guide/03-best-practices/team-workflow.md) - 团队协作指南

### 路线2：高级用户
1. ✅ **完成本快速指南** - 已经完成！
2. → [规则引擎](docs/guide/02-features/rule-engine.md) - 深入理解规则系统
3. → [LLM集成](docs/guide/02-features/llm-integration.md) - AI智能分析
4. → [性能调优](docs/guide/03-best-practices/performance-tuning.md) - 优化审查性能
5. → [CI/CD集成](docs/guide/02-features/ci-cd-integration.md) - 自动化流水线

### 路线3：开发者
1. ✅ **完成本快速指南** - 已经完成！
2. → [API参考](docs/api/) - 完整API文档
3. → [规则开发](docs/development/rule-development.md) - 自定义规则开发
4. → [插件开发](docs/development/plugin-development.md) - 插件系统开发
5. → [测试指南](docs/development/testing.md) - 测试策略和方法

## 🔗 实用命令速查

### 常用命令
```bash
# 运行审查
python3 review.py

# 指定配置文件
python3 review.py --config custom_config.json

# 只检查特定目录
export REVIEW_SCAN_DIRECTORIES="app/src/main/java"
python3 review.py

# 生成报告但不阻塞
export REVIEW_MIN_SCORE_THRESHOLD=0
python3 review.py

# 查看帮助（如有）
python3 review.py --help
```

### 调试命令
```bash
# 启用详细日志
export LOG_LEVEL="DEBUG"
python3 review.py

# 只运行特定规则
python3 -c "
from rules.base_rules import run_base_rules
code = 'GlobalScope.launch {}'
print(run_base_rules(code))
"

# 检查配置
python3 test_config.py
```

## 🎉 恭喜！

你已经成功完成了Review Skill的快速入门。接下来：

### 立即行动
1. **应用到你的项目**：在你的Android项目中运行 `python3 review.py`
2. **查看报告**：打开生成的HTML报告，了解代码质量
3. **调整配置**：根据项目需求调整规则和阈值

### 获取帮助
- 遇到问题？查看 [常见问题](docs/guide/04-troubleshooting/common-issues.md)
- 需要详细说明？阅读 [完整文档](docs/guide/)
- 有建议或问题？提交 [Issue](https://github.com/your-org/review_skill/issues)

### 加入社区
- 🌟 **给项目Star**：支持项目发展
- 📢 **分享反馈**：告诉我们你的使用体验
- 👥 **参与讨论**：加入社区交流

---
*完成时间: 5分钟 ✅ | 下一步: [完整用户指南](docs/guide/)*