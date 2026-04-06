# Review Skill 升级计划 v4.0

**版本**: v4.0.0  
**日期**: 2026-04-05  
**状态**: 计划中  
**基于**: PLAN_v3.md (v3 阶段部分完成)  
**目标**: **统一 AST Engine 和 Rule Engine，打造单一、高效、精确的代码审查引擎**

---

## 📋 文档概述

### 核心问题

当前 review_skill 存在两个独立的引擎：
- **AST Engine**: 基于语法树分析，精确但较慢
- **Rule Engine**: 基于正则匹配，快速但误报率高

**维护成本翻倍**: 需要同时维护两套规则系统、两套缓存机制、两套执行流程。

### v4 愿景

**One Engine, One Truth**: 统一为单一引擎，兼具 AST 的精确性和 Rule Engine 的灵活性。

```
当前 (v3):
┌───────────────┐     ┌───────────────┐
│  AST Engine   │     │  Rule Engine  │
│  (12 条规则)   │     │  (25+ 条规则)  │
│  精确但复杂    │     │  快速但误报高  │
└───────────────┘     └───────────────┘
        │                     │
        └──────────┬──────────┘
                   ▼
            review.py
                   ▼
         用户困惑：用哪个？

v4 目标:
┌───────────────────────────────────────┐
│      Unified Engine (统一引擎)         │
│  • AST 解析作为基础层                  │
│  • 规则 DSL 支持简单规则               │
│  • 智能选择执行策略                    │
│  • 单一缓存系统                        │
└───────────────────────────────────────┘
                   │
                   ▼
            review.py
                   ▼
         用户无需选择，引擎自动优化
```

---

## 🔍 现状深度分析

### 双引擎现状对比

| 维度 | AST Engine | Rule Engine | 差距分析 |
|------|------------|-------------|----------|
| **规则数量** | 12 条 | 35+ 条 | Rule Engine 规则更多 |
| **规则质量** | 高 (AST 语义分析) | 中 (正则匹配) | AST 规则更精确 |
| **执行速度** | 200ms/文件 | 30ms/文件 | AST 慢 6-7 倍 |
| **内存占用** | 高 (存储 AST) | 低 | AST 内存开销大 |
| **规则开发** | 复杂 (需懂 AST) | 简单 (正则即可) | Rule Engine 易上手 |
| **缓存效果** | 极佳 (AST 复用) | 一般 | AST 缓存命中率高 |
| **维护成本** | 高 | 高 | 双份维护 |

### 核心痛点

1. **规则重复实现**: 同一条规则需要在两个引擎各实现一次
2. **行为不一致**: 同一问题，两个引擎可能给出不同结果
3. **用户困惑**: 不知道应该用 `USE_AST_ENGINE=true` 还是默认
4. **缓存割裂**: AST 缓存和 Rule Engine 缓存各自为政
5. **测试翻倍**: 需要为两套系统写测试

### 统一的价值

| 价值点 | 说明 |
|--------|------|
| 维护成本 -50% | 只需维护一套规则系统 |
| 用户体验提升 | 无需选择，引擎自动选择最佳策略 |
| 规则质量提升 | 所有规则都能利用 AST 精确性 |
| 性能优化 | 智能调度：简单规则用快速路径，复杂规则用 AST |
| 架构简化 | 移除 Fallback 逻辑，代码更清晰 |

---

## 🏗️ v4 架构设计

### 统一引擎架构 (Unified Engine)

```
┌─────────────────────────────────────────────────────────────────┐
│                    UnifiedRuleEngine (统一引擎)                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  Rule Registry │  │  AST Parser   │  │  Rule Scheduler│       │
│  │  (规则注册表)   │  │  (语法解析器)  │  │  (规则调度器)  │       │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘       │
│          │                  │                  │               │
│          └──────────────────┼──────────────────┘               │
│                             ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Hybrid Execution Strategy                     │ │
│  │         (混合执行策略 - 自动选择最佳路径)                   │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  简单规则 (Regex-able) ────────▶ Fast Path (快速路径)     │ │
│  │  复杂规则 (AST Required) ──────▶ Precise Path (精确路径)  │ │
│  │  混合规则 ────────────────────▶ Two-Phase (两阶段执行)     │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Unified Cache   │
                    │  (统一缓存系统)   │
                    │  • AST 节点缓存   │
                    │  • 规则结果缓存   │
                    │  • 增量缓存      │
                    └─────────────────┘
```

### 规则分类体系

根据规则复杂度，分为三类：

```
┌─────────────────────────────────────────────────────────────────┐
│                     规则分类 (Rule Categories)                   │
├───────────────────┬───────────────────┬─────────────────────────┤
│  Fast Rule        │  Precise Rule     │  Hybrid Rule            │
│  (快速规则)        │  (精确规则)        │  (混合规则)             │
├───────────────────┼───────────────────┼─────────────────────────┤
│ • 简单模式匹配     │ • 需要语法上下文   │ • 先快速筛选           │
│ • 无需 AST        │ • 复杂嵌套分析     │ • 再精确验证           │
│ • 例如: 硬编码字符串│ • 例如: 生命周期分析│ • 例如: 协程异常处理    │
├───────────────────┼───────────────────┼─────────────────────────┤
│ 执行路径: 纯正则   │ 执行路径: 纯 AST   │ 执行路径: Fast → AST   │
│ 延迟: < 10ms      │ 延迟: 50-200ms    │ 延迟: 10-100ms (自适应) │
└───────────────────┴───────────────────┴─────────────────────────┘
```

### 核心接口设计

```python
# 统一规则接口
class UnifiedRule(ABC):
    """统一规则基类 - 所有规则继承此类"""
    
    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata:
        """规则元数据"""
        pass
    
    @property
    def execution_mode(self) -> ExecutionMode:
        """
        规则执行模式
        - FAST: 仅使用正则快速匹配
        - PRECISE: 必须使用 AST
        - HYBRID: 先快速筛选，再 AST 验证
        """
        return ExecutionMode.HYBRID
    
    @abstractmethod
    def check(self, context: UnifiedContext) -> List[Finding]:
        """
        执行规则检查
        
        Args:
            context: 统一上下文，包含：
                - raw_code: 原始代码
                - ast_node: AST 节点 (按需解析)
                - file_path: 文件路径
                - cache: 缓存接口
        
        Returns:
            发现的问题列表
        """
        pass


# 统一上下文
class UnifiedContext:
    """
    统一执行上下文
    按需解析 AST，避免不必要的解析开销
    """
    
    def __init__(self, code: str, file_path: str):
        self._code = code
        self._file_path = file_path
        self._ast: Optional[ASTNode] = None
        self._ast_parsed = False
    
    @property
    def code(self) -> str:
        """原始代码"""
        return self._code
    
    @property
    def ast(self) -> Optional[ASTNode]:
        """
        AST 节点 - 按需解析
        首次访问时才解析，避免不必要的开销
        """
        if not self._ast_parsed:
            self._ast = self._parse_ast()
            self._ast_parsed = True
        return self._ast
    
    def find_pattern(self, pattern: str) -> List[Match]:
        """快速正则匹配"""
        return re.finditer(pattern, self._code)
    
    def query_ast(self, selector: str) -> List[ASTNode]:
        """
        AST 查询 - 类 CSS 选择器
        例如: query_ast("Function[name='onCreate'] Call[name='super']")
        """
        if not self.ast:
            return []
        return self.ast.select(selector)
```

---

## 📐 详细实施计划

### Phase 1: 统一接口层 (Week 1-2)

**目标**: 建立统一的规则接口和上下文

| 任务 | 说明 | 预计工时 | 状态 |
|------|------|----------|------|
| 1.1 设计 UnifiedRule 接口 | 定义统一规则基类 | 4h | ⏳ 待开始 |
| 1.2 设计 UnifiedContext | 实现按需 AST 解析的上下文 | 6h | ⏳ 待开始 |
| 1.3 创建统一注册表 | 合并 AST 和 Rule 注册表 | 4h | ⏳ 待开始 |
| 1.4 设计混合执行策略 | 实现 Fast/Precise/Hybrid 三种模式 | 8h | ⏳ 待开始 |

**关键产出**:
- `unified_engine/interfaces.py` - 统一接口定义
- `unified_engine/context.py` - 统一上下文实现
- `unified_engine/registry.py` - 统一注册表

### Phase 2: 规则迁移 (Week 3-6)

**目标**: 将现有规则迁移到统一引擎

#### 2.1 Rule Engine 规则迁移

| 规则文件 | 规则数量 | 迁移策略 | 预计工时 | 优先级 |
|----------|----------|----------|----------|--------|
| `base_rules.py` | 3 条 | Fast Mode | 4h | P0 |
| `coroutine_rules.py` | 4 条 | Hybrid Mode | 8h | P0 |
| `compose_rules.py` | 4 条 | Hybrid Mode | 8h | P0 |
| `flow_rules.py` | 5 条 | Precise Mode | 10h | P1 |
| `flow_lifecycle_rules.py` | 4 条 | Precise Mode | 8h | P1 |
| `flow_structure_rules.py` | 4 条 | Precise Mode | 8h | P1 |
| `android_rules.py` | 1 条 | Hybrid Mode | 4h | P1 |
| `hilt_rules.py` | 1 条 | Fast Mode | 2h | P2 |
| `dagger2_rules.py` | 3 条 | Fast Mode | 4h | P2 |
| `batch1_rules.py` | 10 条 | Hybrid Mode | 16h | P0 |

**迁移示例**:

```python
# 迁移前 (Rule Engine - 纯正则)
class NoGlobalScopeRule(Rule):
    def check(self, context: RuleContext) -> List[Finding]:
        findings = []
        for match in context.find_pattern(r"GlobalScope\.\w+"):
            findings.append(Finding(...))  # 可能误报注释中的内容
        return findings

# 迁移后 (Unified Engine - Hybrid Mode)
class NoGlobalScopeRule(UnifiedRule):
    execution_mode = ExecutionMode.HYBRID
    
    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []
        # Phase 1: Fast - 快速筛选候选
        candidates = list(context.find_pattern(r"GlobalScope\.\w+"))
        if not candidates:
            return findings  # 快速返回，无需解析 AST
        
        # Phase 2: Precise - AST 验证
        for node in context.query_ast("Call[receiver='GlobalScope']"):
            if not self._is_in_comment(node):  # 排除注释
                findings.append(Finding(...))
        return findings
```

#### 2.2 AST Engine 规则整合

| 规则文件 | 规则数量 | 整合方式 | 预计工时 | 优先级 |
|----------|----------|----------|----------|--------|
| `coroutine_rules.py` | 6 条 | 合并到统一规则 | 6h | P0 |
| `compose_rules.py` | 6 条 | 合并到统一规则 | 6h | P0 |
| `enhanced_rules.py` | 10 条 | 作为 Precise 规则 | 8h | P1 |

**整合策略**: 保持 AST 规则的核心逻辑，但适配统一接口。

### Phase 3: 统一缓存系统 (Week 5-6)

**目标**: 建立统一的缓存层

```python
# 统一缓存架构
class UnifiedCache:
    """
    三级缓存系统
    """
    
    def __init__(self):
        # L1: 内存缓存 (进程内)
        self._memory_cache = LRUCache(maxsize=1000)
        
        # L2: 磁盘缓存 (跨进程)
        self._disk_cache = DiskCache(cache_dir=".review_cache")
        
        # L3: 增量缓存 (Git 感知)
        self._incremental_cache = IncrementalCache()
    
    def get_ast(self, file_hash: str) -> Optional[ASTNode]:
        """获取缓存的 AST"""
        # L1 -> L2 -> L3 逐级查找
        
    def get_rule_result(self, rule_id: str, file_hash: str) -> Optional[List[Finding]]:
        """获取缓存的规则执行结果"""
        # 规则结果也可以缓存，避免重复执行
```

| 任务 | 说明 | 预计工时 | 状态 |
|------|------|----------|------|
| 3.1 设计三级缓存架构 | L1 内存 + L2 磁盘 + L3 增量 | 4h | ⏳ 待开始 |
| 3.2 实现 AST 缓存 | 缓存解析后的 AST 节点 | 6h | ⏳ 待开始 |
| 3.3 实现规则结果缓存 | 缓存规则执行结果 | 4h | ⏳ 待开始 |
| 3.4 实现增量缓存 | Git 感知的增量缓存 | 8h | ⏳ 待开始 |
| 3.5 缓存一致性保证 | 处理缓存失效和更新 | 6h | ⏳ 待开始 |

### Phase 4: 执行引擎重构 (Week 7-8)

**目标**: 实现智能的规则调度器

```python
class RuleScheduler:
    """
    智能规则调度器
    根据规则特性和文件内容，自动选择最优执行策略
    """
    
    def schedule(self, rules: List[UnifiedRule], context: UnifiedContext) -> ExecutionPlan:
        """
        创建执行计划
        """
        plan = ExecutionPlan()
        
        # 分类规则
        fast_rules = [r for r in rules if r.execution_mode == ExecutionMode.FAST]
        hybrid_rules = [r for r in rules if r.execution_mode == ExecutionMode.HYBRID]
        precise_rules = [r for r in rules if r.execution_mode == ExecutionMode.PRECISE]
        
        # Phase 1: 执行 Fast Rules (并行)
        plan.add_stage(ParallelStage(fast_rules))
        
        # Phase 2: 执行 Hybrid Rules
        # 先 Fast 筛选，再根据结果决定是否解析 AST
        for rule in hybrid_rules:
            plan.add_stage(HybridStage(rule))
        
        # Phase 3: 执行 Precise Rules (需要 AST)
        if precise_rules:
            plan.add_stage(PreciseStage(precise_rules))
        
        return plan
```

| 任务 | 说明 | 预计工时 | 状态 |
|------|------|----------|------|
| 4.1 实现 RuleScheduler | 智能调度器 | 8h | ⏳ 待开始 |
| 4.2 实现并行执行框架 | 基于 asyncio/threading | 8h | ⏳ 待开始 |
| 4.3 实现执行监控 | 性能指标收集 | 6h | ⏳ 待开始 |
| 4.4 实现动态策略调整 | 根据文件大小/复杂度调整策略 | 8h | ⏳ 待开始 |

### Phase 5: 测试与验证 (Week 9-10)

**目标**: 确保统一引擎的正确性和性能

| 任务 | 说明 | 预计工时 | 状态 |
|------|------|----------|------|
| 5.1 单元测试 | 所有规则的单元测试 | 16h | ✅ 已完成 |
| 5.2 性能基准测试 | 对比 v3 双引擎性能 | 8h | ✅ 已完成 |
| 5.3 假阳性测试 | 验证规则精确性 | 8h | ⚠️ 部分完成 |
| 5.4 端到端测试 | 完整流程测试 | 8h | ✅ 已完成 |
| 5.5 回归测试 | 确保不破坏现有功能 | 8h | ✅ 已完成 |

### Phase 6: 旧引擎废弃 (Week 11-12)

**目标**: 平稳迁移，移除旧引擎

| 任务 | 说明 | 预计工时 | 状态 |
|------|------|----------|------|
| 6.1 添加废弃警告 | 旧引擎 API 标记废弃 | 4h | ⏳ 待开始 |
| 6.2 迁移文档 | 编写迁移指南 | 8h | ⏳ 待开始 |
| 6.3 移除 ast_engine/ | 删除旧 AST 引擎目录 | 4h | ⏳ 待开始 |
| 6.4 移除 rule_engine/ | 删除旧 Rule 引擎目录 | 4h | ⏳ 待开始 |
| 6.5 清理环境变量 | 移除 USE_AST_ENGINE 等变量 | 2h | ⏳ 待开始 |

---

## 📊 目标与指标

### 功能目标

| 目标 | 当前 (v3) | v4 目标 | 说明 |
|------|-----------|---------|------|
| 引擎数量 | 2 个 | **1 个** | 统一为单一引擎 |
| 规则维护成本 | 2x | **1x** | 只需维护一套规则 |
| 规则总数 | ~40 条 | **50+ 条** | 新增统一规则 |
| 用户配置复杂度 | 高 | **低** | 无需选择引擎 |

### 性能目标

| 指标 | 当前 AST | 当前 Rule | v4 目标 | 说明 |
|------|----------|-----------|---------|------|
| 首次扫描 | 200ms/文件 | 30ms/文件 | **50ms/文件** | 接近 Rule Engine |
| 缓存命中 | 10ms/文件 | - | **5ms/文件** | 比 AST 更快 |
| 内存占用 | 高 | 低 | **中** | 优化 AST 内存 |
| 误报率 | <5% | ~30% | **<5%** | 达到 AST 水平 |

### 代码质量目标

| 指标 | 当前 | v4 目标 |
|------|------|---------|
| 测试覆盖率 | ~60% | **>90%** |
| 代码重复率 | 高 (双引擎) | **<5%** |
| 圈复杂度 | 高 | **<10** |
| 文档完整度 | 80% | **100%** |

---

## 🗂️ 新目录结构

```
review_skill/
├── review.py                      # 入口 (简化)
├── unified_engine/                # 统一引擎 (新增)
│   ├── __init__.py
│   ├── interfaces.py              # 统一接口
│   ├── context.py                 # 统一上下文
│   ├── registry.py                # 统一注册表
│   ├── scheduler.py               # 规则调度器
│   ├── cache.py                   # 统一缓存
│   ├── parser/                    # 解析器模块
│   │   ├── __init__.py
│   │   ├── kotlin_parser.py       # Kotlin AST 解析
│   │   └── nodes.py               # AST 节点定义
│   └── rules/                     # 统一规则目录
│       ├── __init__.py
│       ├── base.py                # 基础规则集
│       ├── coroutine.py           # 协程规则
│       ├── compose.py             # Compose 规则
│       ├── flow.py                # Flow 规则
│       ├── android.py             # Android 规则
│       └── custom/                # 用户自定义规则
│           └── .gitkeep
├── config.py                      # 配置 (保持不变)
├── report_generator.py            # 报告生成 (保持不变)
├── llm_layer.py                   # LLM 层 (保持不变)
└── i18n.py                        # 国际化 (保持不变)

# 废弃目录 (v4 最终删除)
# ast_engine/                      # 已合并到 unified_engine/
# rule_engine/                     # 已合并到 unified_engine/
```

---

## ⚠️ 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 规则迁移不完整 | 高 | 中 | 分阶段迁移，每个规则都有测试覆盖 |
| 性能下降 | 高 | 中 | 早期做性能基准测试，设置性能回归阈值 |
| 缓存兼容性问题 | 中 | 低 | 新缓存使用不同目录，支持旧缓存清理 |
| 用户习惯改变 | 低 | 高 | 保持 CLI 接口不变，内部自动选择 |
| 开发周期延长 | 中 | 中 | 分 6 个 Phase 交付，每个 Phase 都可独立发布 |

---

## 📅 实施时间表

```
Week 1-2:  [Phase 1] 统一接口层
Week 3-4:  [Phase 2] 规则迁移 (P0/P1 规则)
Week 5-6:  [Phase 2] 规则迁移 (P2 规则) + [Phase 3] 统一缓存
Week 7-8:  [Phase 4] 执行引擎重构
Week 9-10: [Phase 5] 测试与验证
Week 11-12: [Phase 6] 旧引擎废弃 + 文档

里程碑:
├── M1 (Week 2): 统一接口完成，可运行基础规则
├── M2 (Week 6): 所有规则迁移完成，性能达标
├── M3 (Week 8): 执行引擎优化完成
├── M4 (Week 10): 测试通过，Beta 发布
└── M5 (Week 12): v4.0.0 正式发布
```

---

## 🎯 成功标准

1. **功能完整**: 所有 v3 规则都能在统一引擎运行
2. **性能达标**: 平均扫描速度比 v3 Rule Engine 慢不超过 50%
3. **精确性达标**: 误报率 < 5%，达到 v3 AST Engine 水平
4. **代码简化**: 引擎相关代码量减少 40%+
5. **测试覆盖**: 统一引擎测试覆盖率 > 90%

---

## 📝 附录

### A. 规则迁移清单

| 规则 ID | 当前引擎 | 目标模式 | 迁移状态 |
|---------|----------|----------|----------|
| no_globalscope | Rule + AST | Hybrid | ⏳ 待迁移 |
| viewmodel_context | Rule + AST | Precise | ⏳ 待迁移 |
| ... | ... | ... | ... |

### B. API 变更记录

| 旧 API | 新 API | 说明 |
|--------|--------|------|
| `USE_AST_ENGINE=true` | 移除 | 自动选择 |
| `RuleEngine` | `UnifiedEngine` | 新接口 |
| `ASTEngine` | `UnifiedEngine` | 合并 |

### C. 参考文档

- [ENGINES.md](../ENGINES.md) - 双引擎架构说明
- [PLAN_v3.md](./PLAN_v3.md) - v3 计划

---

**文档版本**: v4.0.0-draft  
**最后更新**: 2026-04-05  
**作者**: AI Assistant  
**状态**: 草案，待评审

---

## 📝 修订记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.0-draft | 2026-04-05 | 初始版本，制定统一引擎计划 |
