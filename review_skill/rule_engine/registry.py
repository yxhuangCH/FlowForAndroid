"""
规则注册表
"""
import threading
from typing import Dict, List, Optional, Set, Callable, Any
from .interfaces import Rule, RuleMetadata, RuleCategory, RuleSeverity


class RuleRegistry:
    """规则注册表，单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """初始化注册表"""
        self._rules: Dict[str, Rule] = {}  # id -> Rule
        self._categories: Dict[RuleCategory, List[Rule]] = {}  # category -> List[Rule]
        self._tags: Dict[str, List[Rule]] = {}  # tag -> List[Rule]
        self._listeners: List[Callable] = []  # 注册/注销监听器
    
    def register(self, rule: Rule) -> None:
        """注册规则"""
        rule_id = rule.metadata.id
        
        if rule_id in self._rules:
            raise ValueError(f"规则ID已存在: {rule_id}")
        
        self._rules[rule_id] = rule
        
        # 更新分类索引
        category = rule.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(rule)
        
        # 更新标签索引
        for tag in rule.metadata.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            self._tags[tag].append(rule)
        
        # 调用规则注册回调
        rule.on_register()
        
        # 通知监听器
        self._notify_listeners("register", rule)
    
    def unregister(self, rule_id: str) -> None:
        """注销规则"""
        if rule_id not in self._rules:
            raise ValueError(f"规则ID不存在: {rule_id}")
        
        rule = self._rules[rule_id]
        
        # 从分类索引移除
        category = rule.metadata.category
        if category in self._categories and rule in self._categories[category]:
            self._categories[category].remove(rule)
        
        # 从标签索引移除
        for tag in rule.metadata.tags:
            if tag in self._tags and rule in self._tags[tag]:
                self._tags[tag].remove(rule)
        
        # 调用规则注销回调
        rule.on_unregister()
        
        # 从主索引移除
        del self._rules[rule_id]
        
        # 通知监听器
        self._notify_listeners("unregister", rule)
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """根据ID获取规则"""
        return self._rules.get(rule_id)
    
    def get_rules_by_category(self, category: RuleCategory, enabled_only: bool = True) -> List[Rule]:
        """根据分类获取规则"""
        rules = self._categories.get(category, [])
        if enabled_only:
            rules = [r for r in rules if r.metadata.enabled]
        return rules
    
    def get_rules_by_tag(self, tag: str, enabled_only: bool = True) -> List[Rule]:
        """根据标签获取规则"""
        rules = self._tags.get(tag, [])
        if enabled_only:
            rules = [r for r in rules if r.metadata.enabled]
        return rules
    
    def get_rules_by_severity(self, severity: RuleSeverity, enabled_only: bool = True) -> List[Rule]:
        """根据严重级别获取规则"""
        rules = []
        for rule in self._rules.values():
            if rule.metadata.severity == severity:
                if not enabled_only or rule.metadata.enabled:
                    rules.append(rule)
        return rules
    
    def get_all_rules(self, enabled_only: bool = True) -> List[Rule]:
        """获取所有规则"""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.metadata.enabled]
        return rules
    
    def get_all_rule_ids(self) -> List[str]:
        """获取所有规则ID"""
        return list(self._rules.keys())
    
    def get_all_categories(self) -> List[RuleCategory]:
        """获取所有分类"""
        return list(self._categories.keys())
    
    def get_all_tags(self) -> Set[str]:
        """获取所有标签"""
        return set(self._tags.keys())
    
    def enable_rule(self, rule_id: str):
        """启用规则"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.metadata.enabled = True
    
    def disable_rule(self, rule_id: str):
        """禁用规则"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.metadata.enabled = False
    
    def is_rule_enabled(self, rule_id: str) -> bool:
        """检查规则是否启用"""
        rule = self.get_rule(rule_id)
        return rule.metadata.enabled if rule else False
    
    def add_listener(self, listener: Callable):
        """添加注册/注销监听器"""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable):
        """移除监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def _notify_listeners(self, event_type: str, rule: Rule):
        """通知监听器"""
        for listener in self._listeners:
            try:
                listener(event_type, rule)
            except Exception:
                # 忽略监听器错误
                pass
    
    def clear(self):
        """清空所有规则"""
        rule_ids = list(self._rules.keys())
        for rule_id in rule_ids:
            self.unregister(rule_id)
    
    def count_rules(self) -> int:
        """统计规则数量"""
        return len(self._rules)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        from .interfaces import RuleSeverity
        
        return {
            "total_rules": self.count_rules(),
            "enabled_rules": len(self.get_all_rules(enabled_only=True)),
            "categories": {cat.value: len(rules) for cat, rules in self._categories.items()},
            "tags": {tag: len(rules) for tag, rules in self._tags.items()},
            "severities": {
                severity.value: len(self.get_rules_by_severity(severity, enabled_only=False))
                for severity in RuleSeverity
            }
        }