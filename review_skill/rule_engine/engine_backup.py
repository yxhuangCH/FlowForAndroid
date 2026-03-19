"""Rule Execution Engine"""
import threading
import time
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from .interfaces import Rule, Finding, RuleSeverity
from .context import RuleContext
from .registry import RuleRegistry


class RuleEngine:
    """Rule Execution Engine"""
    
    def __init__(self, registry: Optional[RuleRegistry] = None):
        self.registry = registry or RuleRegistry()
        self.cache: Dict[str, List[Finding]] = {}  # Cache：cache_key -> findings
        self.cache_lock = threading.Lock()
        self.execution_stats: Dict[str, Dict[str, Any]] = {}  # Execution stats
    
    def execute_all(self, context: RuleContext, parallel: bool = False) -> Tuple[List[Finding], Dict[str, Any]]:
        """
        Execute all enabled rules
        
        Args:
            context: rule context
            parallel: 
            
        Returns:
            (list of findings, execution statistics)
        """
        rules = self.registry.get_all_rules(enabled_only=True)
        
        if not rules:
            return [], {}
        
        if parallel:
            return self._execute_parallel(context, rules)
        else:
            return self._execute_sequential(context, rules)
    
    def _execute_sequential(self, context: RuleContext, rules: List[Rule]) -> Tuple[List[Finding], Dict[str, Any]]:
        """Rule"""
        all_findings = []
        execution_stats = {
            "total_rules": len(rules),
            "execution_time": 0,
            "rule_stats": {}
        }
        
        start_time = time.time()
        
        for rule in rules:
            rule_start_time = time.time()
            rule_findings = self._execute_rule(rule, context)
            rule_execution_time = time.time() - rule_start_time
            
            all_findings.extend(rule_findings)
            
            # RuleCount
            execution_stats["rule_stats"][rule.metadata.id] = {
                "execution_time": rule_execution_time,
                "findings_count": len(rule_findings),
                "severity_counts": self._count_findings_by_severity(rule_findings)
            }
        
        execution_stats["execution_time"] = time.time() - start_time
        execution_stats["total_findings"] = len(all_findings)
        
        return all_findings, execution_stats
    
    def _execute_parallel(self, context: RuleContext, rules: List[Rule], max_workers: int = 4) -> Tuple[List[Finding], Dict[str, Any]]:
        """Rule"""
        all_findings = []
        execution_stats = {
            "total_rules": len(rules),
            "execution_time": 0,
            "max_workers": max_workers,
            "rule_stats": {}
        }
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks
            future_to_rule = {}
            for rule in rules:
                future = executor.submit(self._execute_rule, rule, context)
                future_to_rule[future] = rule
            
            # Collect results
            for future in as_completed(future_to_rule):
                rule = future_to_rule[future]
                try:
                    rule_findings = future.result()
                    all_findings.extend(rule_findings)
                    
                    # Count（，）
                    execution_stats["rule_stats"][rule.metadata.id] = {
                        "execution_success": True,
                        "findings_count": len(rule_findings),
                        "severity_counts": self._count_findings_by_severity(rule_findings)
                    }
                except Exception as e:
                    execution_stats["rule_stats"][rule.metadata.id] = {
                        "execution_success": False,
                        "error": str(e),
                        "findings_count": 0
                    }
        
        execution_stats["execution_time"] = time.time() - start_time
        execution_stats["total_findings"] = len(all_findings)
        
        return all_findings, execution_stats
    
    def _execute_rule(self, rule: Rule, context: RuleContext) -> List[Finding]:
        """Rule"""
        try:
            # Check
            cache_key = self._get_cache_key(rule, context)
            
            with self.cache_lock:
                if cache_key in self.cache:
                    # Return copy of cached result（）
                    return self.cache[cache_key].copy()
            
            # Rule
            findings = rule.check(context)
            
            # Enhance findings (add file path and other metadata)
            enhanced_findings = []
            for finding in findings:
                if not finding.file_path:
                    finding.file_path = context.file_path
                enhanced_findings.append(finding)
            
            # Cache
            with self.cache_lock:
                self.cache[cache_key] = enhanced_findings.copy()
            
            return enhanced_findings
            
        except Exception as e:
            # 
            error_finding = Finding(
                rule_id="rule_engine_error",
                message=f"Rule {rule.metadata.id}: {str(e)[:100]}",
                severity=RuleSeverity.MINOR,
                file_path=context.file_path
            )
            return [error_finding]
    
    def _get_cache_key(self, rule: Rule, context: RuleContext) -> str:
        """Generate cache key"""
        return f"{rule.metadata.id}:{context.file_hash}:{hash(str(rule.metadata))}"
    
    def _count_findings_by_severity(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by severity"""
        counts = {severity.value: 0 for severity in RuleSeverity}
        
        for finding in findings:
            counts[finding.severity.value] += 1
        
        return counts
    
    def clear_cache(self):
        """Clear cache"""
        with self.cache_lock:
            self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache stats"""
        with self.cache_lock:
            return {
                "cache_size": len(self.cache),
                "cache_keys": list(self.cache.keys())[:10]  # Show only first 10
            }
    
    def execute_by_category(self, context: RuleContext, category: str, parallel: bool = False) -> Tuple[List[Finding], Dict[str, Any]]:
        """Execute rules by category"""
        # Convert string to enum
        from .interfaces import RuleCategory
        try:
            rule_category = RuleCategory(category)
        except ValueError:
            # If conversion fails, return empty result
            return [], {"error": f": {category}"}
        
        rules = self.registry.get_rules_by_category(rule_category, enabled_only=True)
        
        if not rules:
            return [], {}
        
        if parallel:
            return self._execute_parallel(context, rules)
        else:
            return self._execute_sequential(context, rules)