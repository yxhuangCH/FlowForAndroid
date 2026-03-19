"""Rule Registry
"""
import threading
from typing import Dict, List, Optional, Set, Callable, Any
from .interfaces import Rule, RuleMetadata, RuleCategory, RuleSeverity


class RuleRegistry:
    """Rule Registry, Singleton pattern"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize registry"""
        self._rules: Dict[str, Rule] = {}  # id -> Rule
        self._categories: Dict[RuleCategory, List[Rule]] = {}  # category -> List[Rule]
        self._tags: Dict[str, List[Rule]] = {}  # tag -> List[Rule]
        self._listeners: List[Callable] = []  # register/unregister listeners
    
    def register(self, rule: Rule) -> None:
        """Register rule"""
        rule_id = rule.metadata.id
        
        if rule_id in self._rules:
            raise ValueError(f"Rule ID already exists: {rule_id}")
        
        self._rules[rule_id] = rule
        
        # Update category index
        category = rule.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(rule)
        
        # Update tag index
        for tag in rule.metadata.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            self._tags[tag].append(rule)
        
        # Call rule registration callback
        rule.on_register()
        
        # Notify listeners
        self._notify_listeners("register", rule)
    
    def unregister(self, rule_id: str) -> None:
        """Unregister rule"""
        if rule_id not in self._rules:
            raise ValueError(f"Rule ID does not exist: {rule_id}")
        
        rule = self._rules[rule_id]
        
        # Remove from category index
        category = rule.metadata.category
        if category in self._categories and rule in self._categories[category]:
            self._categories[category].remove(rule)
        
        # Remove from tag index
        for tag in rule.metadata.tags:
            if tag in self._tags and rule in self._tags[tag]:
                self._tags[tag].remove(rule)
        
        # Call rule unregistration callback
        rule.on_unregister()
        
        # Remove from main index
        del self._rules[rule_id]
        
        # Notify listeners
        self._notify_listeners("unregister", rule)
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID"""
        return self._rules.get(rule_id)
    
    def get_rules_by_category(self, category: RuleCategory, enabled_only: bool = True) -> List[Rule]:
        """Get rules by category"""
        rules = self._categories.get(category, [])
        if enabled_only:
            rules = [r for r in rules if r.metadata.enabled]
        return rules
    
    def get_rules_by_tag(self, tag: str, enabled_only: bool = True) -> List[Rule]:
        """Get rules by tag"""
        rules = self._tags.get(tag, [])
        if enabled_only:
            rules = [r for r in rules if r.metadata.enabled]
        return rules
    
    def get_rules_by_severity(self, severity: RuleSeverity, enabled_only: bool = True) -> List[Rule]:
        """Get rules by severity"""
        rules = []
        for rule in self._rules.values():
            if rule.metadata.severity == severity:
                if not enabled_only or rule.metadata.enabled:
                    rules.append(rule)
        return rules
    
    def get_all_rules(self, enabled_only: bool = True) -> List[Rule]:
        """Get all rules"""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.metadata.enabled]
        return rules
    
    def get_all_rule_ids(self) -> List[str]:
        """Get all rule IDs"""
        return list(self._rules.keys())
    
    def get_all_categories(self) -> List[RuleCategory]:
        """Get all categories"""
        return list(self._categories.keys())
    
    def get_all_tags(self) -> Set[str]:
        """Get all tags"""
        return set(self._tags.keys())
    
    def enable_rule(self, rule_id: str):
        """Enable rule"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.metadata.enabled = True
    
    def disable_rule(self, rule_id: str):
        """Disable rule"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.metadata.enabled = False
    
    def is_rule_enabled(self, rule_id: str) -> bool:
        """Check if rule is enabled"""
        rule = self.get_rule(rule_id)
        return rule.metadata.enabled if rule else False
    
    def add_listener(self, listener: Callable):
        """Add register/unregister listener"""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable):
        """Remove listener"""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def _notify_listeners(self, event_type: str, rule: Rule):
        """Notify listeners"""
        for listener in self._listeners:
            try:
                listener(event_type, rule)
            except Exception:
                # Ignore listener errors
                pass
    
    def clear(self):
        """Clear all rules"""
        rule_ids = list(self._rules.keys())
        for rule_id in rule_ids:
            self.unregister(rule_id)
    
    def count_rules(self) -> int:
        """Count rules"""
        return len(self._rules)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics"""
        from .interfaces import RuleSeverity
        
        # Process categories stats, compatible with string and enum
        categories_stats = {}
        for cat, rules in self._categories.items():
            if hasattr(cat, 'value'):
                # Enum type
                cat_key = cat.value
            else:
                # String type
                cat_key = str(cat)
            categories_stats[cat_key] = len(rules)
        
        return {
            "total_rules": self.count_rules(),
            "enabled_rules": len(self.get_all_rules(enabled_only=True)),
            "categories": categories_stats,
            "tags": {tag: len(rules) for tag, rules in self._tags.items()},
            "severities": {
                severity.value: len(self.get_rules_by_severity(severity, enabled_only=False))
                for severity in RuleSeverity
            }
        }
