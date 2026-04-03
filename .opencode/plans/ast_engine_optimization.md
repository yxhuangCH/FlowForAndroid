# AST引擎性能优化计划文档

**版本**: v1.0  
**日期**: 2026-04-03  
**状态**: 已完成

---

## 1. 背景与目标

### 1.1 当前状态

AST引擎已完成基础功能开发，具备以下能力：
- Kotlin源码解析（类、函数、属性、调用表达式等）
- 12条规则（协程规则6条 + Compose规则6条）
- 与主流程集成（通过`USE_AST_ENGINE=true`环境变量启用）

### 1.2 性能问题

基准测试结果（2026-04-03）:

| 测试规模 | AST引擎 | Rule引擎 | 性能比 |
|---------|---------|----------|--------|
| 10类/368行 | 0.0131s | 0.0010s | 13x |
| 50类/1808行 | 0.0621s | 0.0025s | 25x |
| 100类/3608行 | 0.1194s | 0.0035s | 34x |

### 1.3 性能瓶颈分析

使用cProfile分析50类文件的执行时间：

```
性能瓶颈 (按累积时间排序):
1. tokenize(): 58ms (49%)    - 词法分析
2. _parse_top_level_declaration: 55ms (46%)
3. _scan_token: 52ms (44%)   - 单字符扫描
4. _parse_class_declaration: 48ms (41%)
5. _parse_class_body: 43ms (36%)
```

**根本原因**:
- Python函数调用开销大（~29万次/50类文件）
- 字符级扫描效率低
- 递归解析有大量边界检查
- `find_all`遍历整棵树

### 1.4 优化目标

| 指标 | 当前值 | 目标值 | 提升 |
|-----|-------|--------|-----|
| 100类解析时间 | 0.12s | <0.05s | 2.4x |
| 增量扫描 | N/A | <0.01s/文件 | 新增 |
| 缓存命中率 | N/A | >80% | 新增 |

---

## 2. 优化方案

### 方案1: AST缓存系统 ✅ 已完成

**目标**: 避免重复解析相同文件

**实现位置**: `review_skill/ast_engine/cache/`

- `ast_cache.py` - AST缓存
- `file_cache.py` - 文件内容缓存
- `cache_manager.py` - 统一缓存管理

**测试结果**:
- 缓存加速比: **1367.8x**
- 1000行代码: 43.70ms -> 0.03ms

---

### 方案2: 增量扫描系统 ✅ 已完成

**目标**: 只扫描变更的文件

**实现位置**: `review_skill/ast_engine/incremental/`

- `scanner.py` - 增量扫描器
- `parallel_scanner.py` - 并行扫描器

**测试结果**:
- 增量扫描加速: **35.6x**
- 首次扫描: 0.43ms
- 缓存扫描: 0.01ms

---

### 方案3: 解析器优化 - 未实现

保留为后续优化项

### 方案4: 并行处理 ✅ 已完成

- 实现: `parallel_scanner.py`
- 注意: 对于小规模文件并行开销较大，不建议用于小规模场景

---

## 3. 实施结果

### 完成情况

| 任务 | 状态 | 备注 |
|-----|------|------|
| ASTCache类 | ✅ | 内存+磁盘缓存 |
| FileCache类 | ✅ | 文件内容缓存 |
| CacheManager | ✅ | 统一管理 |
| 增量扫描 | ✅ | 支持git diff |
| 并行处理 | ✅ | ThreadPoolExecutor |
| 性能测试 | ✅ | 验证通过 |

### 性能提升

| 指标 | 优化前 | 优化后 | 提升 |
|-----|-------|--------|-----|
| 重复扫描 | 43.70ms | 0.03ms | 1367x |
| 增量扫描 | 0.43ms | 0.01ms | 35x |

---

## 4. 使用方式

```python
# 使用增量扫描
from ast_engine.incremental import IncrementalScanner
from ast_engine.cache import CacheManager

# 创建缓存管理器
cache_manager = CacheManager()

# 创建增量扫描器
scanner = IncrementalScanner(cache_manager=cache_manager)

# 执行扫描
result = scanner.scan_incremental(diff_text)

print(f"实际扫描: {result['files_scanned']}")
print(f"缓存命中: {result['files_from_cache']}")
print(f"findings: {len(result['findings'])}")
```

---

## 5. 文件清单

```
review_skill/ast_engine/
├── cache/
│   ├── __init__.py
│   ├── ast_cache.py         # AST缓存
│   ├── file_cache.py       # 文件缓存
│   └── cache_manager.py    # 缓存管理
└── incremental/
    ├── __init__.py
    ├── scanner.py           # 增量扫描器
    └── parallel_scanner.py  # 并行扫描器
```

---

**下一步**: 可选Lexer优化或与review.py集成
