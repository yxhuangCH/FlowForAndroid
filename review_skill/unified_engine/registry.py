"""Unified Rule Registry

统一规则注册表

本模块提供 UnifiedRegistry 类，它是单例模式实现的规则注册表，
支持按分类、执行模式、标签等多维度索引规则。
"""

from typing import List, Dict, Optional, Type, Callable, Any
import threading

from .interfaces import UnifiedRule, ExecutionMode, RuleCategory, RuleSeverity


class UnifiedRegistry:
    """统一规则注册表（单例模式）

    管理所有统一规则的注册、注销和查询。提供多维度索引：
    - 按规则 ID 索引
    - 按分类索引
    - 按执行模式索引
    - 按标签索引

    Example:
        ```python
        # 获取注册表实例
        registry = UnifiedRegistry()

        # 注册规则
        registry.register(MyRule())

        # 查询规则
        rule = registry.get_rule("my_rule_id")
        fast_rules = registry.get_rules_by_mode(ExecutionMode.FAST)
        coroutine_rules = registry.get_rules_by_category(RuleCategory.CONCURRENCY)

        # 装饰器注册
        @unified_rule
        class MyAutoRegisteredRule(UnifiedRule):
            pass
        ```
    """

    _instance: Optional["UnifiedRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "UnifiedRegistry":
        """创建或返回单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """初始化注册表内部数据结构"""
        # 规则存储: rule_id -> UnifiedRule
        self._rules: Dict[str, UnifiedRule] = {}

        # 按分类索引: category -> List[UnifiedRule]
        self._categories: Dict[RuleCategory, List[UnifiedRule]] = {}

        # 按执行模式索引: mode -> List[UnifiedRule]
        self._modes: Dict[ExecutionMode, List[UnifiedRule]] = {
            ExecutionMode.FAST: [],
            ExecutionMode.HYBRID: [],
            ExecutionMode.PRECISE: [],
        }

        # 按标签索引: tag -> List[UnifiedRule]
        self._tags: Dict[str, List[UnifiedRule]] = {}

        # 按严重程度索引: severity -> List[UnifiedRule]
        self._severities: Dict[RuleSeverity, List[UnifiedRule]] = {}

        # 注册监听器
        self._listeners: List[Callable[[str, UnifiedRule, str], None]] = []

        # 线程锁
        self._registry_lock = threading.RLock()

    # ==================== 注册/注销 ====================

    def register(self, rule: UnifiedRule) -> None:
        """注册规则

        将规则添加到注册表，并建立所有索引。

        Args:
            rule: 要注册的规则实例

        Raises:
            ValueError: 如果规则 ID 已存在或无效
        """
        with self._registry_lock:
            rule_id = rule.metadata.id

            # 验证规则 ID
            if not rule_id:
                raise ValueError("Rule ID cannot be empty")

            # 检查是否已存在
            if rule_id in self._rules:
                raise ValueError(f"Rule with ID '{rule_id}' is already registered")

            # 存储规则
            self._rules[rule_id] = rule

            # 建立分类索引
            category = rule.metadata.category
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(rule)

            # 建立执行模式索引
            mode = rule.execution_mode
            self._modes[mode].append(rule)

            # 建立标签索引
            for tag in rule.metadata.tags:
                if tag not in self._tags:
                    self._tags[tag] = []
                self._tags[tag].append(rule)

            # 建立严重程度索引
            severity = rule.metadata.severity
            if severity not in self._severities:
                self._severities[severity] = []
            self._severities[severity].append(rule)

            # 调用注册回调
            rule.on_register()

            # 通知监听器
            self._notify_listeners(rule_id, rule, "registered")

    def unregister(self, rule_id: str) -> Optional[UnifiedRule]:
        """注销规则

        从注册表中移除指定规则，并清理所有索引。

        Args:
            rule_id: 规则 ID

        Returns:
            Optional[UnifiedRule]: 被移除的规则，如果不存在则返回 None
        """
        with self._registry_lock:
            if rule_id not in self._rules:
                return None

            rule = self._rules.pop(rule_id)

            # 清理分类索引
            category = rule.metadata.category
            if category in self._categories:
                self._categories[category].remove(rule)
                if not self._categories[category]:
                    del self._categories[category]

            # 清理执行模式索引
            mode = rule.execution_mode
            if rule in self._modes[mode]:
                self._modes[mode].remove(rule)

            # 清理标签索引
            for tag in rule.metadata.tags:
                if tag in self._tags and rule in self._tags[tag]:
                    self._tags[tag].remove(rule)
                    if not self._tags[tag]:
                        del self._tags[tag]

            # 清理严重程度索引
            severity = rule.metadata.severity
            if severity in self._severities and rule in self._severities[severity]:
                self._severities[severity].remove(rule)
                if not self._severities[severity]:
                    del self._severities[severity]

            # 调用注销回调
            rule.on_unregister()

            # 通知监听器
            self._notify_listeners(rule_id, rule, "unregistered")

            return rule

    def clear(self) -> None:
        """清空所有规则"""
        with self._registry_lock:
            for rule in list(self._rules.values()):
                rule.on_unregister()
            self._rules.clear()
            self._categories.clear()
            self._modes = {
                ExecutionMode.FAST: [],
                ExecutionMode.HYBRID: [],
                ExecutionMode.PRECISE: [],
            }
            self._tags.clear()
            self._severities.clear()

    # ==================== 查询方法 ====================

    def get_rule(self, rule_id: str) -> Optional[UnifiedRule]:
        """根据 ID 获取规则

        Args:
            rule_id: 规则 ID

        Returns:
            Optional[UnifiedRule]: 规则实例，或 None
        """
        return self._rules.get(rule_id)

    def has_rule(self, rule_id: str) -> bool:
        """检查规则是否存在

        Args:
            rule_id: 规则 ID

        Returns:
            bool: 是否存在
        """
        return rule_id in self._rules

    def get_all_rules(self, enabled_only: bool = True) -> List[UnifiedRule]:
        """获取所有规则

        Args:
            enabled_only: 是否只返回启用的规则

        Returns:
            List[UnifiedRule]: 规则列表
        """
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.metadata.enabled]
        return rules

    def get_rules_by_mode(self, mode: ExecutionMode) -> List[UnifiedRule]:
        """按执行模式获取规则

        Args:
            mode: 执行模式

        Returns:
            List[UnifiedRule]: 该模式下的所有规则
        """
        return list(self._modes.get(mode, []))

    def get_rules_by_category(self, category: RuleCategory) -> List[UnifiedRule]:
        """按分类获取规则

        Args:
            category: 规则分类

        Returns:
            List[UnifiedRule]: 该分类下的所有规则
        """
        return list(self._categories.get(category, []))

    def get_rules_by_tag(self, tag: str) -> List[UnifiedRule]:
        """按标签获取规则

        Args:
            tag: 标签

        Returns:
            List[UnifiedRule]: 带有该标签的所有规则
        """
        return list(self._tags.get(tag, []))

    def get_rules_by_severity(self, severity: RuleSeverity) -> List[UnifiedRule]:
        """按严重程度获取规则

        Args:
            severity: 严重程度

        Returns:
            List[UnifiedRule]: 该严重程度的所有规则
        """
        return list(self._severities.get(severity, []))

    def get_rules_by_ids(self, rule_ids: List[str]) -> List[UnifiedRule]:
        """根据 ID 列表获取规则

        Args:
            rule_ids: 规则 ID 列表

        Returns:
            List[UnifiedRule]: 存在的规则列表
        """
        return [self._rules[r_id] for r_id in rule_ids if r_id in self._rules]

    # ==================== 批量操作 ====================

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则

        Args:
            rule_id: 规则 ID

        Returns:
            bool: 是否成功启用
        """
        rule = self.get_rule(rule_id)
        if rule:
            rule.metadata.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则

        Args:
            rule_id: 规则 ID

        Returns:
            bool: 是否成功禁用
        """
        rule = self.get_rule(rule_id)
        if rule:
            rule.metadata.enabled = False
            return True
        return False

    def enable_rules_by_category(self, category: RuleCategory) -> int:
        """启用指定分类的所有规则

        Args:
            category: 规则分类

        Returns:
            int: 启用的规则数量
        """
        count = 0
        for rule in self.get_rules_by_category(category):
            rule.metadata.enabled = True
            count += 1
        return count

    def disable_rules_by_category(self, category: RuleCategory) -> int:
        """禁用指定分类的所有规则

        Args:
            category: 规则分类

        Returns:
            int: 禁用的规则数量
        """
        count = 0
        for rule in self.get_rules_by_category(category):
            rule.metadata.enabled = False
            count += 1
        return count

    # ==================== 监听器 ====================

    def add_listener(self, listener: Callable[[str, UnifiedRule, str], None]) -> None:
        """添加注册表变更监听器

        Args:
            listener: 回调函数，参数为 (rule_id, rule, event)
                       event 可以是 "registered" 或 "unregistered"
        """
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[str, UnifiedRule, str], None]) -> None:
        """移除注册表变更监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_listeners(self, rule_id: str, rule: UnifiedRule, event: str) -> None:
        """通知所有监听器"""
        for listener in self._listeners:
            try:
                listener(rule_id, rule, event)
            except Exception:
                # 忽略监听器错误
                pass

    # ==================== 统计信息 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取注册表统计信息

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(
                1 for r in self._rules.values() if r.metadata.enabled
            ),
            "disabled_rules": sum(
                1 for r in self._rules.values() if not r.metadata.enabled
            ),
            "by_mode": {
                mode.value: len(rules) for mode, rules in self._modes.items()
            },
            "by_category": {
                cat.value: len(rules) for cat, rules in self._categories.items()
            },
            "by_severity": {
                sev.value: len(rules) for sev, rules in self._severities.items()
            },
            "tag_count": len(self._tags),
        }

    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        return list(self._tags.keys())

    def get_all_categories(self) -> List[RuleCategory]:
        """获取所有分类"""
        return list(self._categories.keys())

    def __len__(self) -> int:
        """返回规则总数"""
        return len(self._rules)

    def __contains__(self, rule_id: str) -> bool:
        """检查是否包含指定规则"""
        return rule_id in self._rules

    def __repr__(self) -> str:
        return f"UnifiedRegistry(rules={len(self._rules)})"


# ==================== 装饰器 ====================


def unified_rule(rule_class: Type[UnifiedRule]) -> Type[UnifiedRule]:
    """规则注册装饰器

    装饰 UnifiedRule 子类，自动实例化并注册到统一注册表。

    Example:
        ```python
        @unified_rule
        class NoGlobalScopeRule(UnifiedRule):
            @property
            def metadata(self) -> RuleMetadata:
                return RuleMetadata(id="no_globalscope", ...)

            def check(self, context: UnifiedContext) -> List[Finding]:
                ...
        ```
    """
    registry = UnifiedRegistry()
    registry.register(rule_class())
    return rule_class


def unified_rule_instance(rule: UnifiedRule) -> UnifiedRule:
    """规则实例注册装饰器

    用于直接注册规则实例。

    Example:
        ```python
        @unified_rule_instance
        NoGlobalScopeRule()
        ```
    """
    registry = UnifiedRegistry()
    registry.register(rule)
    return rule
