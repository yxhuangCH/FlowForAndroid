# Review Skill - Android代码审查工具

[![版本](https://img.shields.io/badge/版本-1.0.0-blue)]()
[![许可证](https://img.shields.io/badge/许可证-MIT-green)]()
[![Python](https://img.shields.io/badge/Python-3.8+-yellow)]()

> 专为Android/Kotlin项目设计的智能代码审查工具

## ✨ 特性
- 🔍 **多领域规则支持**：协程、Compose、Flow、Hilt等现代Android开发技术
- 🧠 **LLM语义增强**：基于DeepSeek的智能代码分析和建议
- 📊 **可视化报告**：HTML和JSON格式的详细审查报告
- ⚡ **高性能引擎**：并行执行、智能缓存和增量扫描
- 🔧 **高度可配置**：支持自定义规则、配置和插件扩展
- 🔌 **无缝集成**：支持本地开发、CI/CD流水线和IDE插件

## 🚀 快速开始

### 安装
```bash
# 1. 克隆项目（如果尚未克隆）
git clone https://github.com/your-org/review_skill.git

# 2. 安装依赖
cd review_skill
pip install -r requirements.txt
```

### 运行第一个审查
```bash
# 在Android项目根目录运行
python3 review.py

# 查看结果
open report/code_review_report_*.html
```

### 配置（可选）
```bash
# 如果需要LLM语义分析，设置API密钥
export DEEPSEEK_API_KEY="your_api_key_here"

# 或者使用OpenAI
export OPENAI_API_KEY="your_openai_api_key"
```

## 📚 文档导航

### 用户指南
- **[快速开始](guide/01-getting-started/)** - 5分钟上手教程
- **[安装指南](guide/01-getting-started/installation.md)** - 详细安装说明
- **[基本使用](guide/01-getting-started/basic-usage.md)** - 核心功能使用指南
- **[配置说明](guide/01-getting-started/configuration.md)** - 配置文件详解

### 功能特性
- **[规则引擎](guide/02-features/rule-engine.md)** - 规则系统工作原理
- **[LLM集成](guide/02-features/llm-integration.md)** - 人工智能代码分析
- **[报告生成](guide/02-features/reporting.md)** - 可视化报告功能
- **[CI/CD集成](guide/02-features/ci-cd-integration.md)** - 自动化流水线

### 最佳实践
- **[团队工作流](guide/03-best-practices/team-workflow.md)** - 团队协作指南
- **[规则配置](guide/03-best-practices/rule-configuration.md)** - 规则设置最佳实践
- **[性能调优](guide/03-best-practices/performance-tuning.md)** - 优化审查性能

### API参考
- **[规则引擎API](api/rule-engine-api/)** - 核心API接口
- **[命令行API](api/cli-api/)** - CLI命令参考
- **[Python API](api/integration-api/python-api.md)** - Python集成接口

### 开发指南
- **[架构设计](development/architecture.md)** - 系统架构说明
- **[规则开发](development/rule-development.md)** - 自定义规则开发
- **[插件开发](development/plugin-development.md)** - 插件扩展开发
- **[测试指南](development/testing.md)** - 测试策略和方法

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                   应用层 (Application Layer)             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  命令行接口  │  │  CI/CD集成   │  │  Web界面    │    │
│  │    (CLI)    │  │  (GitHub)   │  │  (HTML)    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────┐
│                业务逻辑层 (Business Logic Layer)         │
│  ┌─────────────────────────────────────────────────┐    │
│  │              审查核心引擎 (Review Core)          │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  │    │
│  │  │ Git集成   │  │ 文件过滤   │  │ 配置管理   │  │    │
│  │  └───────────┘  └───────────┘  └───────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────┐
│                规则引擎层 (Rule Engine Layer)           │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐          │
│  │ 规则注册表 │  │ 规则执行器 │  │ 规则上下文 │          │
│  └───────────┘  └───────────┘  └───────────┘          │
└─────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────┐
│                    规则层 (Rule Layer)                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐          │
│  │ 基础规则   │  │ 协程规则   │  │ Compose规则│          │
│  └───────────┘  └───────────┘  └───────────┘          │
└─────────────────────────────────────────────────────────┘
```

## 🔍 支持的技术领域

### 协程 (Coroutines)
- 生命周期管理
- 作用域管理
- 异常处理
- 结构化并发

### Jetpack Compose
- 重组优化
- 状态管理
- 副作用管理
- 性能最佳实践

### Flow
- 生命周期感知
- 背压处理
- 异常处理
- 转换优化

### 依赖注入 (Hilt/Dagger2)
- 作用域管理
- 组件生命周期
- 测试友好性
- 最佳实践

### 架构组件
- ViewModel最佳实践
- LiveData/StateFlow使用
- 数据层设计
- 错误处理

## 💡 使用场景

### 本地开发
```bash
# 提交前检查代码质量
python3 review.py

# 只检查特定目录
export REVIEW_SCAN_DIRECTORIES="app/src/main/java/com/example/"
python3 review.py
```

### CI/CD流水线
```yaml
# GitHub Actions示例
name: Code Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Code Review
        run: |
          pip install -r review_skill/requirements.txt
          cd review_skill
          python3 review.py
```

### 团队协作
```bash
# 共享配置文件
cp review_config.json team_review_config.json
# 自定义团队规则
# 设置团队质量阈值
```

## 🛠️ 扩展开发

### 自定义规则
```python
from rule_engine.interfaces import Rule, RuleSeverity, RuleCategory

class MyCustomRule(Rule):
    """自定义规则示例"""
    
    @property
    def metadata(self):
        return RuleMetadata(
            id="my_custom_rule",
            name="我的自定义规则",
            description="检测特定代码模式",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS
        )
    
    def check(self, context):
        # 实现规则逻辑
        findings = []
        if "bad_pattern" in context.code:
            findings.append(Finding(
                rule_id=self.metadata.id,
                message="发现不良代码模式",
                severity=self.metadata.severity
            ))
        return findings
```

### 插件开发
```python
from rule_engine.plugins import Plugin

class MyPlugin(Plugin):
    """自定义插件示例"""
    
    def before_review_start(self, context):
        """审查开始前执行"""
        print(f"开始审查: {context.file_path}")
    
    def after_review_finish(self, results):
        """审查结束后执行"""
        print(f"审查完成，发现 {len(results)} 个问题")
```

## 📊 输出示例

### JSON报告
```json
{
  "score": 85,
  "findings": [
    {
      "severity": "critical",
      "rule": "no_globalscope",
      "message": "GlobalScope is lifecycle unsafe.",
      "file": "app/src/main/java/com/example/MainActivity.kt",
      "line": 42,
      "suggestion": "使用 lifecycleScope 或 viewModelScope"
    }
  ],
  "block_pr": false,
  "statistics": {
    "total_files": 5,
    "total_findings": 3,
    "execution_time": 1.234
  }
}
```

### HTML报告
![HTML报告示例](resources/diagrams/html-report-preview.png)

## 💬 社区支持

### 获取帮助
- **[常见问题](guide/04-troubleshooting/common-issues.md)** - 常见问题解决方案
- **[故障排除](guide/04-troubleshooting/)** - 详细调试指南
- **[讨论区](https://github.com/your-org/review_skill/discussions)** - 社区讨论

### 报告问题
- **[问题追踪](https://github.com/your-org/review_skill/issues)** - 提交Bug或功能请求
- **[功能建议](CONTRIBUTING.md#feature-requests)** - 提出改进建议

### 贡献代码
- **[贡献指南](CONTRIBUTING.md)** - 参与开发指南
- **[代码规范](CONTRIBUTING.md#coding-standards)** - 代码编写规范
- **[开发流程](CONTRIBUTING.md#development-workflow)** - 开发工作流程

## 📈 性能指标

### 基准测试
| 场景 | 文件数 | 行数 | 执行时间 | 内存使用 |
|------|--------|------|----------|----------|
| 小型项目 | 10-50 | 1k-5k | < 5秒 | < 100MB |
| 中型项目 | 50-200 | 5k-20k | 5-30秒 | 100-500MB |
| 大型项目 | 200+ | 20k+ | 30-120秒 | 500MB-1GB |

### 优化特性
- ✅ **增量扫描**：只分析变更的代码
- ✅ **智能缓存**：避免重复计算
- ✅ **并行执行**：充分利用多核CPU
- ✅ **内存优化**：高效的数据结构

## 🔄 更新与维护

### 版本策略
- **主版本** (X.0.0)：架构重大变化
- **次版本** (0.X.0)：新功能添加
- **修订版本** (0.0.X)：错误修复

### 更新记录
查看完整的版本变更记录：
- **[CHANGELOG.md](CHANGELOG.md)** - 详细版本历史
- **[升级指南](guide/01-getting-started/upgrade.md)** - 版本升级说明

### 长期支持
- **活跃维护**：定期更新和错误修复
- **安全更新**：及时的安全漏洞修复
- **社区支持**：活跃的社区和文档更新

## 📄 许可证

本项目采用 **MIT许可证** - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

### 核心技术
- **DeepSeek API**：提供强大的LLM语义分析能力
- **OpenAI**：备选的AI分析服务
- **Python生态**：丰富的库和工具支持

### 贡献者
感谢所有为此项目做出贡献的开发者，完整的贡献者列表请见 [CONTRIBUTORS.md](CONTRIBUTORS.md)。

### 相关项目
- [Kotlin](https://kotlinlang.org/) - 目标语言支持
- [Android Studio](https://developer.android.com/studio) - 开发环境
- [GitHub Actions](https://github.com/features/actions) - CI/CD集成

---

**开始使用** → [快速开始指南](guide/01-getting-started/)

**了解更多** → [完整文档目录](guide/)

**参与开发** → [贡献指南](CONTRIBUTING.md)

**获取帮助** → [常见问题](guide/04-troubleshooting/common-issues.md)

---
*最后更新: 2026年3月3日 | 版本: 1.0.0*