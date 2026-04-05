"""
Unified Engine Rules

统一引擎规则集合 - 从 Rule Engine 和 AST Engine 迁移的规则
"""
from typing import List
from unified_engine.interfaces import UnifiedRule

# Import all rule modules
from . import base
from . import batch1
from . import coroutine
from . import compose
from . import android
from . import best_practice
from . import flow
from . import flow_lifecycle
from . import flow_structure
from . import hilt
from . import dagger2


def get_all_rules() -> List[UnifiedRule]:
    """获取所有统一规则"""
    rules = []
    rules.extend(base.get_rules())
    rules.extend(batch1.get_rules())
    rules.extend(coroutine.get_rules())
    rules.extend(compose.get_rules())
    rules.extend(android.get_rules())
    rules.extend(best_practice.get_rules())
    rules.extend(flow.get_rules())
    rules.extend(flow_lifecycle.get_rules())
    rules.extend(flow_structure.get_rules())
    rules.extend(hilt.get_rules())
    rules.extend(dagger2.get_rules())
    return rules


__all__ = [
    "get_all_rules",
    "base",
    "batch1",
    "coroutine",
    "compose",
    "android",
    "best_practice",
    "flow",
    "flow_lifecycle",
    "flow_structure",
    "hilt",
    "dagger2",
]
