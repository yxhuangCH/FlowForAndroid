# Migration Guide: From v3 to v4

## Overview

v4 introduces **unified_engine** - a single, unified code review engine that combines the best of AST Engine and Rule Engine.

**What's New:**
- Single engine with smart execution (FAST/PRECISE/HYBRID modes)
- Automatic performance optimization
- Simplified configuration
- Better accuracy with lower false positive rate

---

## Architecture Changes

### Before (v3)
```
review.py
    ├── rule_engine/ (legacy)
    └── ast_engine/ (legacy)
```

### After (v4)
```
review.py
    └── unified_engine/ (unified)
```

---

## API Changes

### Engine Classes

| Old API | New API | Status |
|---------|---------|--------|
| `RuleEngine` | `UnifiedExecutionEngine` | ✅ REPLACED |
| `ASTEngine` | `UnifiedExecutionEngine` | ✅ MERGED |
| `RuleScheduler` | `RuleScheduler` (in unified) | ✅ KEPT |

### Context Classes

| Old API | New API | Status |
|---------|---------|--------|
| `RuleContext` | `UnifiedContext` | ✅ RENAMED |
| `ASTContext` | `UnifiedContext` | ✅ MERGED |

### Execution Modes

| Mode | Description |
|------|-------------|
| `FAST` | Regex-only matching (< 10ms/file) |
| `PRECISE` | AST-only analysis (50-200ms/file) |
| `HYBRID` | Smart combination (default, 10-100ms/file) |

---

## Configuration Changes

### Removed Options

```yaml
# These options are now REMOVED
rule_engine:
  use_ast_engine: true    # REMOVED - auto-detected
  ast_cache_enabled: true # REMOVED - always enabled
  rule_cache_enabled:     # REMOVED - always enabled
```

### New Options

```yaml
# New unified engine options
unified_engine:
  max_workers: 4          # Parallel execution workers
  parallel: true          # Enable parallel execution
  adaptive: true          # Auto-select execution strategy
```

---

## Migration for Users

### CLI Usage (No Change)

```bash
# Just run as before - no changes needed
python review.py

# Old way (deprecated)
# USE_AST_ENGINE=true python review.py

# New way (automatic)
# python review.py (auto-selects best strategy)
```

---

## Migration for Developers

### Python API

```python
# Old (deprecated)
from rule_engine.engine import RuleEngine
engine = RuleEngine()

# New (recommended)
from unified_engine.engine import UnifiedExecutionEngine
engine = UnifiedExecutionEngine()
```

### Context Usage

```python
# Old (deprecated)
from rule_engine.context import RuleContext
ctx = RuleContext(code, file_path)

# New (recommended)
from unified_engine.context import UnifiedContext
ctx = UnifiedContext(code, file_path)
```

### Rule Creation

```python
# Old (deprecated)
class MyRule(Rule):
    def check(self, context: RuleContext) -> List[Finding]:
        ...

# New (recommended)
from unified_engine import UnifiedRule, ExecutionMode

class MyRule(UnifiedRule):
    execution_mode = ExecutionMode.HYBRID
    
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(id="my_rule", ...)
    
    def check(self, context: UnifiedContext) -> List[Finding]:
        ...
```

---

## Troubleshooting

### "UnifiedEngine not found"

```bash
# Make sure you're in the right directory
cd review_skill
pip install -e .
```

### Performance Issues

- FAST mode: ~10ms/file
- HYBRID mode: ~50ms/file  
- PRECISE mode: ~100ms/file

If scans are slower, check file size and complexity.

---

## Deprecation Timeline

| Version | Status |
|---------|--------|
| v4.0 | unified_engine available (preferred) |
| v4.1 | rule_engine/ast_engine show warnings |
| v5.0 | rule_engine/ast_engine removed |

---

## Contact

For issues or questions, please open an issue on GitHub.
