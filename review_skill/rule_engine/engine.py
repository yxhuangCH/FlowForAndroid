"""Rule Execution Engine"""
import threading
import time
import os
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import hashlib
from datetime import datetime, timedelta
from collections import OrderedDict
import logging

from .interfaces import Rule, Finding, RuleSeverity
from .context import RuleContext
from .registry import RuleRegistry

logger = logging.getLogger(__name__)


class LRUCache:
    """LRU Cache implementation, supports TTL"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Initialize LRU cache
        
        Args:
            max_size: max cache entries
            ttl: cache TTL in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, Tuple[Any, datetime]] = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value, if exists and not expired"""
        with self.lock:
            if key not in self.cache:
                return None
            
            value, timestamp = self.cache[key]
            
            # Check if expired
            if self.ttl > 0 and (datetime.now() - timestamp).seconds > self.ttl:
                # Expired, delete
                del self.cache[key]
                logger.debug(f"Cache expired: {key}")
                return None
            
            # Move to most recently used position
            self.cache.move_to_end(key)
            return value
    
    def set(self, key: str, value: Any):
        """Set cache value"""
        with self.lock:
            # If key exists, delete first
            if key in self.cache:
                del self.cache[key]
            
            # If max size reached, delete oldest entry
            if len(self.cache) >= self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)
                logger.debug(f"LRU cache evicted: {oldest_key}")
            
            # Add new entry
            self.cache[key] = (value, datetime.now())
    
    def delete(self, key: str):
        """Delete cache item"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """Clear cache"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """Get cache size"""
        with self.lock:
            return len(self.cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache stats"""
        with self.lock:
            # Count expired items
            expired_count = 0
            now = datetime.now()
            for _, timestamp in self.cache.values():
                if self.ttl > 0 and (now - timestamp).seconds > self.ttl:
                    expired_count += 1
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "expired_count": expired_count,
                "keys": list(self.cache.keys())[:10]  # Show only first 10
            }


class RuleEngine:
    """Enhanced Rule Execution Engine"""
    
    def __init__(self, registry: Optional[RuleRegistry] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize enhanced engine
        
        Args:
            registry: rule registry
            config: config dictionary
        """
        self.registry = registry or RuleRegistry()
        self.config = config or {}
        
        # Cache config
        cache_config = self.config.get("cache", {})
        cache_enabled = cache_config.get("enabled", True)
        cache_max_size = cache_config.get("max_size", 1000)
        cache_ttl = cache_config.get("ttl", 3600)
        
        if cache_enabled:
            self.cache = LRUCache(max_size=cache_max_size, ttl=cache_ttl)
        else:
            self.cache = None
        
        # Parallel execution config
        parallel_config = self.config.get("parallel", {})
        self.parallel_enabled = parallel_config.get("enabled", True)
        self.max_workers = parallel_config.get("max_workers")
        self.execution_timeout = parallel_config.get("execution_timeout", 30)
        
        # Auto-detect CPU cores
        if self.max_workers is None or self.max_workers <= 0:
            try:
                self.max_workers = os.cpu_count() or 4
                # Reserve one core for other tasks
                self.max_workers = max(1, self.max_workers - 1)
                logger.info(f"Auto-detected CPU cores: {os.cpu_count()}, set max_workers={self.max_workers}")
            except:
                self.max_workers = 4
        
        # Execution stats
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        self.total_executions = 0
        self.total_findings = 0
        
        logger.info(f"Enhanced rule engine initialized: cache_enabled={cache_enabled}, max_workers={self.max_workers}")
    
    def execute_all(self, context: RuleContext, parallel: Optional[bool] = None) -> Tuple[List[Finding], Dict[str, Any]]:
        """
        Execute all enabled rules
        
        Args:
            context: rule context
            parallel: whether to execute in parallel (None means use config)
            
        Returns:
            (list of findings, execution statistics)
        """
        rules = self.registry.get_all_rules(enabled_only=True)
        
        if not rules:
            return [], {}
        
        # Determine whether to use parallel execution
        if parallel is None:
            parallel = self.parallel_enabled
        
        if parallel:
            return self._execute_parallel_enhanced(context, rules)
        else:
            return self._execute_sequential_enhanced(context, rules)
    
    def _execute_sequential_enhanced(self, context: RuleContext, rules: List[Rule]) -> Tuple[List[Finding], Dict[str, Any]]:
        """Enhanced sequential execution"""
        all_findings = []
        execution_stats = {
            "total_rules": len(rules),
            "execution_time": 0,
            "rule_stats": {},
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        start_time = time.time()
        
        for rule in rules:
            rule_start_time = time.time()
            rule_findings, cache_hit = self._execute_rule_enhanced(rule, context)
            rule_execution_time = time.time() - rule_start_time
            
            all_findings.extend(rule_findings)
            
            # Update cache stats
            if cache_hit:
                execution_stats["cache_hits"] += 1
            else:
                execution_stats["cache_misses"] += 1
            
            # Record rule execution stats
            execution_stats["rule_stats"][rule.metadata.id] = {
                "execution_time": rule_execution_time,
                "findings_count": len(rule_findings),
                "cache_hit": cache_hit,
                "severity_counts": self._count_findings_by_severity(rule_findings),
                "timed_out": False
            }
        
        execution_stats["execution_time"] = time.time() - start_time
        execution_stats["total_findings"] = len(all_findings)
        
        # Update global stats
        self.total_executions += 1
        self.total_findings += len(all_findings)
        
        return all_findings, execution_stats
    
    def _execute_parallel_enhanced(self, context: RuleContext, rules: List[Rule]) -> Tuple[List[Finding], Dict[str, Any]]:
        """Enhanced parallel execution"""
        all_findings = []
        execution_stats = {
            "total_rules": len(rules),
            "execution_time": 0,
            "max_workers": self.max_workers,
            "rule_stats": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "timeouts": 0
        }
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            future_to_rule = {}
            for rule in rules:
                future = executor.submit(self._execute_rule_with_timeout, rule, context)
                future_to_rule[future] = rule
            
            # Collect results
            for future in as_completed(future_to_rule):
                rule = future_to_rule[future]
                try:
                    # Set timeout
                    rule_findings, cache_hit = future.result(timeout=self.execution_timeout)
                    all_findings.extend(rule_findings)
                    
                    # Update cache stats
                    if cache_hit:
                        execution_stats["cache_hits"] += 1
                    else:
                        execution_stats["cache_misses"] += 1
                    
                    # Record rule execution stats
                    execution_stats["rule_stats"][rule.metadata.id] = {
                        "execution_success": True,
                        "findings_count": len(rule_findings),
                        "cache_hit": cache_hit,
                        "severity_counts": self._count_findings_by_severity(rule_findings),
                        "timed_out": False
                    }
                except TimeoutError:
                    # Execution timeout
                    execution_stats["timeouts"] += 1
                    execution_stats["rule_stats"][rule.metadata.id] = {
                        "execution_success": False,
                        "error": f"Execution timeout ({self.execution_timeout}s)",
                        "findings_count": 0,
                        "timed_out": True
                    }
                    logger.warning(f"Rule execution timeout: {rule.metadata.id}")
                except Exception as e:
                    execution_stats["rule_stats"][rule.metadata.id] = {
                        "execution_success": False,
                        "error": str(e)[:200],
                        "findings_count": 0,
                        "timed_out": False
                    }
                    logger.error(f"Rule execution failed {rule.metadata.id}: {e}")
        
        execution_stats["execution_time"] = time.time() - start_time
        execution_stats["total_findings"] = len(all_findings)
        
        # Update global stats
        self.total_executions += 1
        self.total_findings += len(all_findings)
        
        return all_findings, execution_stats
    
    def _execute_rule_with_timeout(self, rule: Rule, context: RuleContext) -> Tuple[List[Finding], bool]:
        """Rule execution with timeout"""
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._execute_rule_enhanced, rule, context)
            try:
                return future.result(timeout=self.execution_timeout)
            except FutureTimeoutError:
                logger.warning(f"Rule execution timeout: {rule.metadata.id} (>{self.execution_timeout}s)")
                raise TimeoutError(f"Rule {rule.metadata.id} exceeded {self.execution_timeout}s timeout")
    
    def _execute_rule_enhanced(self, rule: Rule, context: RuleContext) -> Tuple[List[Finding], bool]:
        """Enhanced single rule execution"""
        cache_hit = False
        
        try:
            # Check cache
            cache_key = self._get_cache_key(rule, context)
            
            if self.cache:
                cached_findings = self.cache.get(cache_key)
                if cached_findings is not None:
                    # Return copy of cached result
                    cache_hit = True
                    return cached_findings.copy(), cache_hit
            
            # Execute rule
            findings = rule.check(context)
            
            # Enhance findings (add file path and other metadata)
            enhanced_findings = []
            for finding in findings:
                if not finding.file_path:
                    finding.file_path = context.file_path
                enhanced_findings.append(finding)
            
            # Cache result
            if self.cache:
                self.cache.set(cache_key, enhanced_findings.copy())
            
            return enhanced_findings, cache_hit
            
        except Exception as e:
            # Log error but don't interrupt the whole scan
            error_finding = Finding(
                rule_id="rule_engine_error",
                message=f"Rule execution failed {rule.metadata.id}: {str(e)[:100]}",
                severity=RuleSeverity.MINOR,
                file_path=context.file_path
            )
            return [error_finding], cache_hit
    
    def _get_cache_key(self, rule: Rule, context: RuleContext) -> str:
        """Generate cache key"""
        # Include rule ID, file hash, rule config hash
        rule_config_hash = hashlib.md5(
            str({
                "id": rule.metadata.id,
                "enabled": rule.metadata.enabled,
                "weight": rule.metadata.weight
            }).encode('utf-8')
        ).hexdigest()[:8]
        
        return f"{rule.metadata.id}:{context.file_hash}:{rule_config_hash}"
    
    def _count_findings_by_severity(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by severity"""
        counts = {severity.value: 0 for severity in RuleSeverity}
        
        for finding in findings:
            counts[finding.severity.value] += 1
        
        return counts
    
    def clear_cache(self):
        """Clear cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache stats"""
        if self.cache:
            return self.cache.stats()
        else:
            return {"enabled": False, "size": 0}
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine stats"""
        return {
            "total_executions": self.total_executions,
            "total_findings": self.total_findings,
            "cache_enabled": self.cache is not None,
            "parallel_enabled": self.parallel_enabled,
            "max_workers": self.max_workers,
            "execution_timeout": self.execution_timeout,
            "cache_stats": self.get_cache_stats() if self.cache else {}
        }
    
    def execute_by_category(self, context: RuleContext, category: str, parallel: Optional[bool] = None) -> Tuple[List[Finding], Dict[str, Any]]:
        """Execute rules by category"""
        # Convert string to enum
        from .interfaces import RuleCategory
        try:
            rule_category = RuleCategory(category)
        except ValueError:
            # If conversion fails, return empty result
            return [], {"error": f"Invalid category: {category}"}
        
        rules = self.registry.get_rules_by_category(rule_category, enabled_only=True)
        
        if not rules:
            return [], {}
        
        if parallel is None:
            parallel = self.parallel_enabled
        
        if parallel:
            return self._execute_parallel_enhanced(context, rules)
        else:
            return self._execute_sequential_enhanced(context, rules)
    
    def execute_by_priority(self, context: RuleContext, high_priority_first: bool = True) -> Tuple[List[Finding], Dict[str, Any]]:
        """
        Execute rules by priority
        
        Args:
            context: rule context
            high_priority_first: whether to execute high priority rules first
            
        Returns:
            (list of findings, execution statistics)
        """
        rules = self.registry.get_all_rules(enabled_only=True)
        
        if not rules:
            return [], {}
        
        # Sort by priority
        if high_priority_first:
            # Sort by severity and weight
            def rule_priority(rule: Rule) -> tuple:
                # Severity weight (higher = more priority)
                severity_weight = {
                    RuleSeverity.BLOCKER: 5,
                    RuleSeverity.CRITICAL: 4,
                    RuleSeverity.MAJOR: 3,
                    RuleSeverity.MINOR: 2,
                    RuleSeverity.INFO: 1
                }.get(rule.metadata.severity, 0)
                
                return (-severity_weight, -rule.metadata.weight)
            
            rules = sorted(rules, key=rule_priority)
        
        return self._execute_sequential_enhanced(context, rules)
    
    def warmup_cache(self, contexts: List[RuleContext]):
        """
        Warmup cache
        
        Args:
            contexts: list of rule contexts
        """
        if not self.cache:
            logger.info("Cache not enabled, skip warmup")
            return
        
        logger.info(f"Starting cache warmup, total {len(contexts)} contexts")
        
        rules = self.registry.get_all_rules(enabled_only=True)
        if not rules:
            logger.info("No enabled rules, skip warmup")
            return
        
        start_time = time.time()
        cache_hits = 0
        cache_misses = 0
        
        for context in contexts:
            for rule in rules:
                cache_key = self._get_cache_key(rule, context)
                
                # Try to get from cache
                if self.cache.get(cache_key) is not None:
                    cache_hits += 1
                else:
                    cache_misses += 1
        
        elapsed_time = time.time() - start_time
        logger.info(f"Cache warmup complete: hits {cache_hits}, misses {cache_misses}, time elapsed {elapsed_time:.2f} seconds")


# Backward compatible alias
EnhancedRuleEngine = RuleEngine


if __name__ == "__main__":
    # Test enhanced engine
    import sys
    logging.basicConfig(level=logging.INFO)
    
    # Create test config
    config = {
        "cache": {
            "enabled": True,
            "max_size": 100,
            "ttl": 60  # 1
        },
        "parallel": {
            "enabled": True,
            "max_workers": 2,
            "execution_timeout": 5
        }
    }
    
    from rule_engine.registry import RuleRegistry
    from rule_engine.context import RuleContext
    from rule_engine.rules.base_rules import NoGlobalScopeRule
    
    # Create engine
    registry = RuleRegistry()
    registry.register(NoGlobalScopeRule())
    
    engine = RuleEngine(registry, config)
    
    # Test code
    test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("test")
    }
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="test.kt",
        language="kotlin"
    )
    
    # Execute rules
    findings, stats = engine.execute_all(context)
    
    print("Enhanced rule engine test:")
    print(f"Execution stats: {stats}")
    print(f"Cache stats: {engine.get_cache_stats()}")
    print(f"Engine stats: {engine.get_engine_stats()}")
    
    if findings:
        print(f"Findings ({len(findings)}):")
        for i, finding in enumerate(findings, 1):
            print(f"  {i}. {finding.rule_id}: {finding.message}")