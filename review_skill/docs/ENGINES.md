# AST Engine 与 Rule Engine 架构说明

本文档详细解释 review_skill 中两个核心引擎的关系、差异和使用场景。

---

## 🏗️ 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                         review.py (入口)                         │
│                     引擎选择 & Fallback 逻辑                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
           ┌───────────────────┴───────────────────┐
           │                                       │
           ▼                                       ▼
┌──────────────────────┐              ┌──────────────────────┐
│     AST Engine       │              │    Rule Engine       │
│   (语法树分析引擎)    │              │   (规则执行引擎)      │
├──────────────────────┤              ├──────────────────────┤
│  • parser_v2.py      │              │  • interfaces.py     │
│  • nodes.py          │              │  • registry.py       │
│  • 纯Python AST解析   │              │  • engine.py         │
│  • 增量扫描/缓存      │              │  • 并行规则执行       │
└──────────┬───────────┘              └──────────┬───────────┘
           │                                     │
           ▼                                     ▼
┌──────────────────────┐              ┌──────────────────────┐
│   AST Rules          │              │   Unified Rules      │
│   (语法树规则)        │              │   (统一规则)          │
├──────────────────────┤              ├──────────────────────┤
│  coroutine_rules.py  │              │  base_rules.py       │
│  compose_rules.py    │              │  android_rules.py    │
│  enhanced_rules.py   │              │  batch1_rules.py     │
│  (12条规则)          │              │  (25+条规则)         │
└──────────────────────┘              └──────────────────────┘
```

---

## 📊 核心差异对比

| 特性 | AST Engine | Rule Engine |
|------|------------|-------------|
| **核心原理** | 将 Kotlin 代码解析为 AST (抽象语法树)，基于树结构分析 | 基于正则表达式和文本模式匹配 |
| **精度** | 高 (能识别语法上下文，减少假阳性) | 中 (依赖正则，可能有误报) |
| **性能** | 较慢 (需要完整解析代码) | 快 (直接文本匹配) |
| **内存占用** | 较高 (需要存储 AST 节点) | 低 |
| **规则编写** | 复杂 (需要理解 AST 结构) | 简单 (正则表达式即可) |
| **缓存支持** | ✅ AST 节点缓存 (LRU + 磁盘) | ✅ 规则结果缓存 |
| **并行执行** | ✅ 文件级别并行扫描 | ✅ 规则级别并行执行 |
| **增量扫描** | ✅ 支持 (变更检测) | ❌ 不支持 |

---

## 🔧 AST Engine 详解

### 核心组件

```python
ast_engine/
├── parser_v2.py          # Kotlin AST 解析器 (纯 Python 实现)
├── nodes.py              # AST 节点定义 (NodeType, ASTNode)
├── integration.py        # 与 review.py 的集成入口
├── cache/                # 缓存系统
│   ├── ast_cache.py      # AST 节点 LRU 缓存
│   └── cache_manager.py  # 缓存管理
├── incremental/          # 增量扫描
│   └── scanner.py        # 变更检测扫描器
└── rules/                # AST 规则
    ├── base_ast_rule.py  # 规则基类
    ├── coroutine_rules.py    # 协程相关规则 (6条)
    ├── compose_rules.py      # Compose 相关规则 (6条)
    └── enhanced_rules.py     # 增强规则 (10条，降低误报)
```

### 工作原理

1. **解析阶段**: `parser_v2.parse_kotlin_ast(code)` 将 Kotlin 代码转为 AST 节点树
2. **遍历阶段**: 规则遍历 AST 树，检查特定节点类型
3. **检测阶段**: 基于节点属性和上下文判断问题

### 示例：检测 GlobalScope

```python
# AST Engine 方式 - 精确识别调用表达式
class NoGlobalScopeRule(BaseASTRule):
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        # 遍历所有函数调用节点
        for node in ast.find_all(NodeType.CALL_EXPRESSION):
            # 检查调用者是否为 GlobalScope
            if node.metadata.get("receiver") == "GlobalScope":
                # 排除注释和字符串中的匹配
                if not self._is_in_comment_or_string(node):
                    findings.append(Finding(...))
        return findings
```

### 优势场景
- 需要精确识别代码结构 (如区分注释中的代码)
- 复杂的上下文分析 (如检查嵌套层级)
- 需要类型信息 (如识别 Composable 函数)

---

## 🔧 Rule Engine 详解

### 核心组件

```python
rule_engine/
├── interfaces.py         # 核心接口 (Rule, Finding, RuleContext)
├── registry.py           # 规则注册表 (RuleRegistry)
├── engine.py             # 规则执行引擎 (并行执行、缓存)
├── context.py            # 规则执行上下文
├── adapters/             # 适配器
│   └── decorators.py     # @rule 装饰器
├── integration/          # 集成模块
│   └── review_runner.py  # ReviewRunner 入口
└── rules/                # 统一规则
    ├── base_rules.py     # 基础规则
    ├── coroutine_rules.py
    ├── compose_rules.py
    ├── android_rules.py
    └── batch1_rules.py   # 第一批 10 条规则
```

### 工作原理

1. **注册阶段**: 规则通过 `RuleRegistry` 注册
2. **执行阶段**: `RuleEngine` 并行执行所有规则
3. **上下文**: 每个规则获得 `RuleContext` (包含代码、文件路径等)

### 示例：检测 GlobalScope

```python
# Rule Engine 方式 - 正则匹配
class NoGlobalScopeRule(Rule):
    def check(self, context: RuleContext) -> List[Finding]:
        findings = []
        # 简单的正则匹配
        matches = context.find_pattern(r"GlobalScope\.\w+")
        for match in matches:
            findings.append(Finding(...))
        return findings
```

### 优势场景
- 简单的模式匹配
- 快速原型开发
- 规则快速迭代

---

## 🔄 引擎选择策略

在 `review.py` 中，引擎选择逻辑如下：

```python
# 优先级: AST Engine (if enabled) > Rule Engine > Fallback

if AST_ENGINE_AVAILABLE and is_ast_engine_enabled():
    # 使用 AST Engine
    result = _review_with_ast_engine(diff, config)
elif RULE_ENGINE_AVAILABLE:
    # 使用 Rule Engine
    result = _review_with_new_engine(diff, config)
else:
    # 使用旧引擎 (Fallback)
    result = _review_with_old_engine(diff, config)
```

### 启用 AST Engine

```bash
export USE_AST_ENGINE=true
python3 review.py
```

---

## 📈 性能对比

| 场景 | AST Engine | Rule Engine | 说明 |
|------|------------|-------------|------|
| 首次扫描 | ~500ms/文件 | ~50ms/文件 | AST 需要解析 |
| 缓存命中 | ~10ms/文件 | ~50ms/文件 | AST 缓存优势明显 |
| 1000行代码 | ~200ms | ~30ms | 正则更快 |
| 误报率 | <5% | ~30% | AST 更精确 |

---

## 🎯 使用建议

### 何时使用 AST Engine？

1. **追求精确性**: 需要降低误报率的场景
2. **复杂规则**: 需要分析代码结构而非简单文本匹配
3. **大型项目**: 文件多、需要增量扫描和缓存
4. **生产环境**: 作为 CI/CD 的主要审查引擎

### 何时使用 Rule Engine？

1. **快速迭代**: 需要快速添加/修改规则
2. **简单检查**: 只需要基础的模式匹配
3. **资源受限**: 内存/CPU 有限的场景
4. **开发调试**: 快速验证规则逻辑

---

## 🔮 未来规划

### 短期 (v3.x)
- 增强 AST 解析器对函数体的解析深度
- 将更多 Rule Engine 规则迁移到 AST Engine
- 混合引擎：简单规则用 Rule Engine，复杂规则用 AST Engine

### 长期 (v4.0)
- 统一为 AST Engine (弃用正则方式)
- 支持跨文件分析 (类继承、DI 关系)
- 完整的类型系统支持

---

## 📚 相关文档

- [PLAN_v2.md](./plans/PLAN_v2.md) - v2 阶段 AST 引擎实现
- [PLAN_v3.md](./plans/PLAN_v3.md) - v3 阶段规则质量优化
- [技术说明书](../TECHNICAL_SPECIFICATION.md) - 系统架构详情

---

*最后更新: 2026-04-05*
