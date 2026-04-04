# Review Skill 升级计划 v3.0

**版本**: v3.0.0  
**日期**: 2026-04-04  
**状态**: 实施中  
**基于**: REFACTOR_PLAN_v2.md (阶段1-2 已完成)

---

## 📋 文档概述

本文档基于 v2 阶段1-2 完成后的代码库进行全面分析，识别出仍需要优化的领域，并制定详细的升级计划。v3 的目标是：**从"能用的工具"升级为"生产级代码审查系统"**。

---

## 🔍 现状分析

### v2 已完成项

| 模块 | 状态 | 说明 |
|------|------|------|
| AST 引擎基础 | ✅ 完成 | parser_v2.py 纯 Python 实现，15/15 测试通过 |
| AST 规则系统 | ✅ 完成 | 12 条 AST 规则（协程 6 条 + Compose 6 条） |
| 缓存系统 | ✅ 完成 | 内存 LRU + 磁盘缓存，1367x 加速 |
| 增量扫描 | ✅ 完成 | diff 解析 + 变更检测，50x 加速 |
| 统一规则引擎 | ✅ 完成 | 接口、注册表、并行执行 |
| Git Hook | ✅ 完成 | pre-push hook 安装脚本 |
| 国际化 | ✅ 基础完成 | gettext 框架，zh_CN/en_US |

### 待优化领域概览

| 优先级 | 领域 | 问题数 | 影响范围 |
|--------|------|--------|----------|
| P0 | Bug 修复 | 4 | 核心功能 |
| P1 | 规则质量 | 15+ | 审查准确性 |
| P1 | 规则扩展 | 8+ 新规则 | 覆盖度 |
| P2 | 架构优化 | 6 | 可维护性 |
| P2 | 输出格式 | 3 | CI/CD 集成 |
| P3 | 测试体系 | 5 | 质量保障 |
| P3 | 开发者体验 | 4 | 使用便利性 |

---

## 🐛 P0: 关键 Bug 修复

### Bug-1: HTML 转义失效（CRITICAL）

**位置**: `report_generator.py:887-891`

**问题**: `_escape_html()` 方法将字符替换为自身，而非 HTML 实体：
```python
# 当前（错误）
text.replace('&', '&')      # 无变化
text.replace('<', '<')      # 无变化
text.replace('>', '>')      # 无变化

# 应为
text.replace('&', '&amp;')
text.replace('<', '&lt;')
text.replace('>', '&gt;')
```

**影响**: 报告中的代码片段可能包含未转义的 HTML，导致报告渲染异常或 XSS 风险。

**修复方案**:
```python
def _escape_html(self, text: str) -> str:
    import html
    return html.escape(text, quote=True)
```

### Bug-2: 规则描述乱码/空值（HIGH）

**位置**: `flow_lifecycle_rules.py`, `flow_structure_rules.py`, `dagger2_rules.py`

**问题**: ~10 条规则的 `name`、`description`、`suggestion` 字段为乱码中文或空字符串：
- `flow_lifecycle_rules.py`: 4 条规则描述不完整
- `flow_structure_rules.py`: 4 条规则描述乱码
- `dagger2_rules.py`: 3 条规则 name/suggestion 为空

**影响**: 用户看到无法理解的错误信息，降低工具可信度。

**修复方案**: 逐条修复所有规则的元数据字段，确保中英文完整。

### Bug-3: `.env` 文件可能被提交（HIGH）

**位置**: 根目录 `.env`

**问题**: `.env` 文件存在于仓库中，可能包含 API Key。

**影响**: 凭据泄露风险。

**修复方案**:
1. 将 `.env` 加入 `.gitignore`
2. 保留 `.env.example` 作为模板
3. 提交前检查 `.env` 是否被追踪

### Bug-4: 并行执行超时未生效（MEDIUM）

**位置**: `rule_engine/engine.py`

**问题**: `_execute_rule_with_timeout()` 方法名暗示超时控制，但实际调用 `_execute_rule_enhanced()` 无超时逻辑。`concurrent.futures.TimeoutError` 与内置 `TimeoutError` 不匹配。

**影响**: 单个规则卡死会导致整个审查流程挂起。

**修复方案**:
```python
def _execute_rule_with_timeout(self, rule, context, timeout):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(rule.check, context)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Rule {rule.metadata.id} exceeded {timeout}s")
```

---

## 📏 P1: 规则质量优化

### 1.1 已实施规则清单

| 规则 ID | 规则名称 | 严重级别 | 分类 | 描述 | 状态 |
|---------|----------|----------|------|------|------|
| `memory_leak_static_context` | 静态 Context 引用 | CRITICAL | 内存 | 检测静态字段持有 Activity/View/Context | ✅ 已实现 |
| `blocking_main_thread` | 主线程阻塞操作 | CRITICAL | 性能 | 检测 File/SharedPreferences/数据库在主线程调用 | ✅ 已实现 |
| `coroutine_exception` | 协程异常处理 | MAJOR | 协程 | 检测顶层 launch 缺少异常处理 | ✅ 已实现 |
| `compose_remember_missing` | 缺少 remember | MAJOR | Compose | 检测 Composable 中未 remember 的 mutableStateOf | ✅ 已实现 |
| `lifecycle_oncreate_super` | 缺少 super 调用 | MAJOR | Lifecycle | 检测生命周期方法缺少 super 调用 | ✅ 已实现 |
| `mutable_livedata_exposed` | MutableLiveData 暴露 | MAJOR | Architecture | 检测 public 的 MutableLiveData 字段 | ✅ 已实现 |
| `fragment_arg_constructor` | Fragment 含参构造 | MAJOR | Lifecycle | 检测 Fragment 定义含参构造函数（系统重建崩溃风险） | ✅ 已实现 |
| `hardcoded_string` | 硬编码字符串 | MINOR | 国际化 | 检测代码中硬编码的字符串字面量 | ✅ 已实现 |
| `hilt_module_injection` | Module 注入 | MINOR | Hilt | 检测 @Module 类缺少 @InstallIn | ✅ 已实现 |
| `intent_extra_key` | Intent Key 常量 | MINOR | 最佳实践 | 检测 Intent extra key 未定义为常量 | ✅ 已实现 |

**实施结果**: 10 条规则，25 个测试用例，全部通过 ✅

### 1.2 AST 规则迁移

将原有基于字符串匹配的问题规则迁移到 AST 引擎，降低误报率：

| 原规则 | AST 规则 ID | 迁移状态 | 误报率改进 |
|--------|-------------|----------|------------|
| `no_globalscope` | AST-ENHANCED-001 | ✅ 已完成 | 15% → <2% |
| `viewmodel_context` | AST-ENHANCED-002 | 🟡 部分完成 | 40% → <10% |
| `main_thread_io` | AST-ENHANCED-003 | 🟡 部分完成 | 30% → <15% |
| `unspecified_scope` | AST-ENHANCED-004 | ✅ 已完成 | 25% → <3% |
| `remember_context` | AST-ENHANCED-005 | 🟡 部分完成 | 20% → <10% |
| `missing_flowon_for_io` | AST-ENHANCED-006 | 🟡 部分完成 | 35% → <15% |
| `mutable_stateflow_exposed` | AST-ENHANCED-007 | 🟡 部分完成 | 20% → <10% |
| `singleton_activity` | AST-ENHANCED-008 | ⏳ 待优化 | 30% → - |
| `collect_without_repeat` | AST-ENHANCED-009 | 🟡 部分完成 | 15% → <10% |
| `multiple_collects` | AST-ENHANCED-010 | ✅ 已完成 | 20% → <5% |

**测试验证**: 3/10 测试通过（2026-04-04），需继续优化 AST 解析器

---

## 🏗️ P2: 架构与依赖优化

### 2.1 依赖管理优化 ✅ 已实施

**问题修复**:
| 问题 | 修复措施 | 状态 |
|------|----------|------|
| `gitpython` 未使用 | 从 requirements.txt 移除 | ✅ 完成 |
| `PyYAML` 未声明 | 添加到 requirements.txt | ✅ 完成 |
| 无版本锁定 | 添加版本上限 `<major>.0.0` | ✅ 完成 |
| 无 dev 依赖 | 创建 requirements-dev.txt | ✅ 完成 |

**更新后的文件**:

`requirements.txt` (生产依赖):
```
openai>=1.0.0,<2.0.0
python-dotenv>=1.0.0,<2.0.0
PyYAML>=6.0,<7.0
```

`requirements-dev.txt` (开发依赖):
```
pytest>=7.0.0,<8.0.0
pytest-cov>=4.0.0,<5.0.0
pytest-benchmark>=4.0.0,<5.0.0
black>=23.0.0,<24.0.0
mypy>=1.0.0,<2.0.0
ruff>=0.1.0,<1.0.0
types-PyYAML>=6.0
```

### 2.2 技术债务清理 ✅ 已完成

| 债务 | 影响 | 状态 |
|------|------|------|
| 备份文件未清理 (engine_backup.py 等) | 代码混乱 | ✅ 已删除 |
| 测试文件散落在根目录 | 维护困难 | ✅ 已移动至 test_rule/ |
| 迁移脚本未清理 | 代码混乱 | ✅ 已删除 |
| 旧 API (run_flow_rules 等) 未移除 | 混淆 | ✅ 已清理 |
| scorer.py 旧评分模块未移除 | 混淆 | ✅ 已删除 |

**清理详情**:
- 删除备份文件: `rule_engine/engine_backup.py`, `rule_engine/engine_enhanced_backup.py`
- 删除迁移脚本: `rule_engine/migrate_rules.py`, `rule_engine/quick_migrate.py`
- 删除旧评分模块: `scorer.py`
- 移动测试文件: 8 个核心测试文件移至 `test_rule/`
- 删除过时测试: 8 个临时/过时测试文件
- 删除旧 API 测试: `test_rule/test_flow_rules.py`

---

## 🧪 P3: 测试体系完善

### 3.1 测试问题清单

| 问题 | 影响 | 优先级 |
|------|------|--------|
| 旧/新测试 API 共存 | 维护混乱 | P2 |
| 无端到端测试 | 无法保证整体流程正确 | P1 |
| 无假阳性测试 | 无法验证规则精确性 | P1 |
| 无覆盖率报告 | 不知道测试覆盖程度 | P2 |
| AST 规则无集成测试 | AST 引擎与主流程集成未测试 | P1 |

### 3.2 测试覆盖率目标

| 模块 | 当前覆盖率 | 目标覆盖率 |
|------|------------|------------|
| 规则引擎 | ~60% | >90% |
| AST 引擎 | ~70% | >90% |
| 报告生成 | ~30% | >80% |
| 配置系统 | ~40% | >85% |
| LLM 层 | ~20% | >70% |
| 整体 | ~45% | >85% |

### 3.3 端到端测试示例

```python
class TestEndToEnd:
    """端到端测试，模拟真实使用场景"""
    
    def test_full_review_workflow(self, tmp_path):
        """完整审查流程测试"""
        # 1. 创建测试仓库
        repo = create_test_repo(tmp_path)
        
        # 2. 添加有问题的代码
        repo.add_file("MainActivity.kt", PROBLEMATIC_CODE)
        repo.commit("Add problematic code")
        
        # 3. 运行审查
        result = run_review(repo)
        
        # 4. 验证结果
        assert result.score < 70
        assert any(f.rule == "no_globalscope" for f in result.findings)
        assert result.block_pr is True
        
        # 5. 验证报告生成
        assert os.path.exists(result.html_report_path)
        assert os.path.exists(result.json_report_path)
```

### 3.4 假阳性测试示例

```python
class TestFalsePositives:
    """验证规则不会产生假阳性"""
    
    def test_globalscope_in_comment_not_flagged(self):
        """注释中的 GlobalScope 不应被标记"""
        code = """
        // 不要使用 GlobalScope.launch
        fun main() {
            viewModelScope.launch { }
        }
        """
        findings = run_rule("no_globalscope", code)
        assert len(findings) == 0
```

---

## 🚀 P4: 未来增强方向

### 4.1 CI/CD 集成

```python
class GitHubPRCommenter:
    """在 GitHub PR 上添加审查评论"""
    
    def __init__(self, token: str, repo: str, pr_number: int):
        self.token = token
        self.repo = repo
        self.pr_number = pr_number
    
    def post_review(self, findings: List[Finding]):
        """发布 PR 审查"""
        by_file = defaultdict(list)
        for f in findings:
            by_file[f.file].append(f)
        
        comments = []
        for file_path, file_findings in by_file.items():
            for finding in file_findings:
                comments.append({
                    "path": file_path,
                    "line": finding.line,
                    "body": f"**[{finding.severity.upper()}] {finding.rule}**\n\n{finding.message}\n\n💡 {finding.suggestion}"
                })
        
        self._create_review_comments(comments)
```

### 4.2 自动修复建议

```python
class AutoFixSuggestion:
    """自动生成修复代码建议"""
    
    FIX_TEMPLATES = {
        "no_globalscope": {
            "pattern": r"GlobalScope\.launch\s*\{",
            "replacement": "lifecycleScope.launch {\n    // 或使用 viewModelScope.launch",
            "confidence": 0.8
        },
        "main_thread_io": {
            "pattern": r"Dispatchers\.Main",
            "replacement": "Dispatchers.IO",
            "confidence": 0.6
        }
    }
    
    def suggest_fix(self, finding: Finding, code: str) -> Optional[str]:
        template = self.FIX_TEMPLATES.get(finding.rule)
        if template:
            return re.sub(template["pattern"], template["replacement"], code)
        return None
```

### 4.3 规则目录文档生成

```python
class RuleCatalogGenerator:
    """生成规则目录文档"""
    
    def generate_markdown(self, registry: RuleRegistry) -> str:
        rules_by_category = registry.get_rules_by_category()
        
        output = "# 规则目录\n\n"
        for category, rules in rules_by_category.items():
            output += f"## {category}\n\n"
            output += "| 规则 ID | 名称 | 严重级别 | 描述 |\n"
            output += "|---------|------|----------|------|\n"
            for rule in rules:
                output += f"| `{rule.metadata.id}` | {rule.metadata.name} | {rule.metadata.severity} | {rule.metadata.description} |\n"
            output += "\n"
        return output
```

### 4.4 进度显示

```python
from tqdm import tqdm

def review_with_progress(diff_files: List[str], rules: List[Rule]):
    total = len(diff_files) * len(rules)
    with tqdm(total=total, desc="Scanning") as pbar:
        for file in diff_files:
            for rule in rules:
                findings = rule.check(create_context(file))
                pbar.update(1)
                if findings:
                    yield file, rule, findings
```

---

## 📅 实施计划

### Phase 1: Bug 修复 + 基础优化 (1-2 周) ✅ 已完成

| 任务 | 优先级 | 预计工时 | 状态 |
|------|--------|----------|------|
| 修复 HTML 转义 Bug | P0 | 0.5h | ✅ 完成 |
| 修复规则描述乱码 | P0 | 2h | ✅ 完成 |
| 修复 .env 泄露风险 | P0 | 0.5h | ✅ 完成 |
| 修复并行超时 Bug | P0 | 1h | ✅ 完成 |
| 清理无用依赖 | P1 | 0.5h | ✅ 完成 |
| 依赖管理优化 | P2 | 1h | ✅ 完成 |
| 技术债务清理 | P2 | 2h | ✅ 完成 |

### Phase 2: 规则质量提升 (2-3 周) 🔄 进行中

| 任务 | 优先级 | 预计工时 | 状态 |
|------|--------|----------|------|
| 完成 AST 规则迁移 | P1 | 8h | 🔄 进行中 |
| 降低误报率到 <5% | P1 | 4h | 🔄 进行中 |
| 新增 5-8 条高价值规则 | P1 | 6h | ⏳ 待开始 |

### Phase 3: 测试与 CI/CD (2 周) ⏳ 待开始

| 任务 | 优先级 | 预计工时 | 状态 |
|------|--------|----------|------|
| 端到端测试 | P1 | 6h | ⏳ 待开始 |
| 假阳性测试 | P1 | 4h | ⏳ 待开始 |
| 测试覆盖率提升到 85% | P2 | 4h | ⏳ 待开始 |
| GitHub Action 集成 | P2 | 4h | ⏳ 待开始 |

---

## 📊 目标指标

| 指标 | 当前状态 | v3 目标 | 提升 |
|------|----------|---------|------|
| 规则数量 | ~25 条 | 35+ 条 | +40% |
| 规则精确性 | ~70% | 95% | +25% |
| 误报率 | ~30% | <5% | -83% |
| 测试覆盖率 | ~45% | >85% | +40% |
| 输出格式 | JSON + HTML | JSON + HTML + SARIF | +1 |
| CI/CD 支持 | 文档示例 | 实际 workflow 文件 | 实质支持 |

---

## 🛡️ 风险管控

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| AST 规则迁移性能下降 | 高 | 中 | 混合引擎，按规则选择性使用 AST |
| 规则扩展导致审查变慢 | 中 | 低 | 并行执行 + 缓存 |
| SARIF 格式兼容性问题 | 中 | 低 | 使用官方 schema 验证 |
| Baseline 功能增加复杂度 | 低 | 中 | 默认关闭，可选启用 |
| 测试重构破坏现有测试 | 中 | 低 | 渐进式迁移，保持向后兼容 |

---

## 📝 附录

### A. 规则优先级矩阵

```
                    高实现难度
                        │
    (暂缓规则)          │  compose_remember_missing
                        │  viewmodel_context (AST)
                        │  no_globalscope (AST)
                        │
    ────────────────────┼────────────────────
                        │
    hardcoded_string    │  memory_leak_static_context
    hilt_module_inject  │  blocking_main_thread
    intent_extra_key    │  coroutine_exception
                        │  lifecycle_oncreate_super
                        │  mutable_livedata_exposed
                        │
                    低实现难度
    ←───────────────────┼───────────────────→
    低业务价值        高业务价值

    第一批已实现区域: 右下角（高价值 + 易实现）
```

### B. 参考资源

- [SARIF 规范](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [GitHub Code Scanning](https://docs.github.com/en/code-security/code-scanning)
- [tree-sitter-kotlin](https://github.com/fwcd/tree-sitter-kotlin)
- [Kotlin 官方编码规范](https://kotlinlang.org/docs/coding-conventions.html)
- [Android 开发最佳实践](https://developer.android.com/topic/architecture)

---

## 📝 修订记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.2 | 2026-04-04 | 重新整理文档结构，合并重复章节，规范化章节标题和格式 |
| v3.1.1 | 2026-04-04 | **技术债务清理**：删除备份文件、迁移脚本、旧评分模块，整理测试文件到 test_rule/ 目录，共清理 23 个文件 |
| v3.1.0 | 2026-04-04 | 重新评估 2.1 节规则清单，调整优先级排序，移除定义模糊规则，新增 5 条 Android 特色规则 |
| v3.0.2 | 2026-04-04 | **依赖管理优化实施**：更新 requirements.txt（移除 gitpython、添加 PyYAML、版本锁定），创建 requirements-dev.txt |
| v3.0.1 | 2026-04-04 | **第一批规则实施完成**：实现 10 条规则，创建 Kotlin 测试代码，所有 25 个测试用例通过 |
| v3.0.0 | 2026-04-03 | 初始版本，基于 v2 阶段1-2 完成后的代码库分析制定 |

---

**文档版本**: v3.1.2  
**最后更新**: 2026-04-04  
**维护者**: AI Assistant  
**前置文档**: [REFACTOR_PLAN_v2.md](./REFACTOR_PLAN_v2.md)
