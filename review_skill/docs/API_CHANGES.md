# API Changes v3 → v4

## Engine API

| Old Class | New Class | Status | Notes |
|-----------|-----------|--------|-------|
| `RuleEngine` | `UnifiedExecutionEngine` | REPLACED | Main engine class |
| `ASTEngine` | `UnifiedExecutionEngine` | MERGED | Now unified |
| `RuleScheduler` | `RuleScheduler` | KEPT | Same interface |

## Context API

| Old Class | New Class | Status | Notes |
|-----------|-----------|--------|-------|
| `RuleContext` | `UnifiedContext` | RENAMED | Unified interface |
| `ASTContext` | `UnifiedContext` | MERGED | Now unified |
| `LineMatch` | `LineMatch` | KEPT | Same structure |

## Rule API

| Old | New | Status |
|-----|-----|--------|
| `Rule` | `UnifiedRule` | REPLACED |
| `RuleMetadata` | `RuleMetadata` | KEPT |
| `Finding` | `Finding` | KEPT |
| `RuleSeverity` | `RuleSeverity` | KEPT |
| `RuleCategory` | `RuleCategory` | KEPT |

## Execution Modes

```python
# v4 Execution Modes
class ExecutionMode(Enum):
    FAST = "fast"      # Regex only (< 10ms)
    PRECISE = "precise"  # AST only (50-200ms)
    HYBRID = "hybrid"    # Smart combo (default)
```

## Configuration

### Removed Options

| Option | Replacement |
|--------|-------------|
| `USE_AST_ENGINE` | Removed (auto-detected) |
| `AST_CACHE_ENABLED` | Always enabled |
| `RULE_CACHE_ENABLED` | Always enabled |

### New Options

| Option | Default | Description |
|--------|---------|-------------|
| `max_workers` | 4 | Parallel workers |
| `enable_parallel` | True | Enable parallel |
| `enable_adaptive` | True | Auto strategy |
| `enable_monitor` | True | Performance监控 |

## Function Signatures

### UnifiedExecutionEngine

```python
# v4
class UnifiedExecutionEngine:
    def __init__(
        self,
        cache: UnifiedCache = None,
        scheduler: RuleScheduler = None,
        max_workers: int = 4,
        enable_parallel: bool = True,
        enable_monitor: bool = True,
        enable_adaptive: bool = True,
        rules: List[UnifiedRule] = None
    ):
        ...
    
    def scan_file(self, file_path: str, content: str = None) -> ScanResult:
        ...
    
    def scan_files(self, file_paths: List[str]) -> Dict[str, ScanResult]:
        ...
```

### ScanResult

```python
@dataclass
class ScanResult:
    findings: List[Finding]
    execution_time: float  # milliseconds
    files_scanned: int
    rules_executed: int
```

---

## Import Changes

```python
# v3 (deprecated)
from rule_engine.engine import RuleEngine
from rule_engine.context import RuleContext
from rule_engine.interfaces import Rule, Finding

# v4 (new)
from unified_engine.engine import UnifiedExecutionEngine
from unified_engine.context import UnifiedContext
from unified_engine.interfaces import UnifiedRule, Finding
```

---

## Error Handling

| v3 Error | v4 Error | Notes |
|----------|----------|-------|
| `ReviewError` | `RuleExecutionError` | Rule execution |
| `ConfigurationError` | `ConfigurationError` | Same |
| `IntegrationError` | - | Removed |

---

Last Updated: 2026-04-06
