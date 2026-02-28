"""
增强版规则执行引擎 - 支持并行处理优化、LRU/TTL缓存、配置支持
"""
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
    """LRU缓存实现，支持TTL"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        初始化LRU缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存生存时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, Tuple[Any, datetime]] = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，如果存在且未过期"""
        with self.lock:
            if key not in self.cache:
                return None
            
            value, timestamp = self.cache[key]
            
            # 检查是否过期
            if self.ttl > 0 and (datetime.now() - timestamp).seconds > self.ttl:
                # 过期，删除
                del self.cache[key]
                logger.debug(f"缓存过期: {key}")
                return None
            
            # 移动到最近使用位置
            self.cache.move_to_end(key)
            return value
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self.lock:
            # 如果键已存在，先删除
            if key in self.cache:
                del self.cache[key]
            
            # 如果达到最大大小，删除最旧的条目
            if len(self.cache) >= self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)
                logger.debug(f"LRU缓存淘汰: {oldest_key}")
            
            # 添加新条目
            self.cache[key] = (value, datetime.now())
    
    def delete(self, key: str):
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            # 统计过期项
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
                "keys": list(self.cache.keys())[:10]  # 只显示前10个
            }


class EnhancedRuleEngine:
    """增强版规则执行引擎"""
    
    def __init__(self, registry: Optional[RuleRegistry] = None, config: Optional[Dict[str, Any]] = None):
        """
        初始化增强版引擎
        
        Args:
            registry: 规则注册表
            config: 配置字典
        """
        self.registry = registry or RuleRegistry()
        self.config = config or {}
        
        # 缓存配置
        cache_config = self.config.get("cache", {})
        cache_enabled = cache_config.get("enabled", True)
        cache_max_size = cache_config.get("max_size", 1000)
        cache_ttl = cache_config.get("ttl", 3600)
        
        if cache_enabled:
            self.cache = LRUCache(max_size=cache_max_size, ttl=cache_ttl)
        else:
            self.cache = None
        
        # 并行执行配置
        parallel_config = self.config.get("parallel", {})
        self.parallel_enabled = parallel_config.get("enabled", True)
        self.max_workers = parallel_config.get("max_workers")
        self.execution_timeout = parallel_config.get("execution_timeout", 30)
        
        # 自动检测CPU核心数
        if self.max_workers is None or self.max_workers <= 0:
            try:
                self.max_workers = os.cpu_count() or 4
                # 留一个核心给其他任务
                self.max_workers = max(1, self.max_workers - 1)
                logger.info(f"自动检测CPU核心数: {os.cpu_count()}, 设置max_workers={self.max_workers}")
            except:
                self.max_workers = 4
        
        # 执行统计
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        self.total_executions = 0
        self.total_findings = 0
        
        logger.info(f"增强版规则引擎初始化完成: cache_enabled={cache_enabled}, max_workers={self.max_workers}")
    
    def execute_all(self, context: RuleContext, parallel: Optional[bool] = None) -> Tuple[List[Finding], Dict[str, Any]]:
        """
        执行所有启用的规则
        
        Args:
            context: 规则上下文
            parallel: 是否并行执行（None表示使用配置）
            
        Returns:
            (发现的问题列表, 执行统计信息)
        """
        rules = self.registry.get_all_rules(enabled_only=True)
        
        if not rules:
            return [], {}
        
        # 确定是否使用并行执行
        if parallel is None:
            parallel = self.parallel_enabled
        
        if parallel:
            return self._execute_parallel_enhanced(context, rules)
        else:
            return self._execute_sequential_enhanced(context, rules)
    
    def _execute_sequential_enhanced(self, context: RuleContext, rules: List[Rule]) -> Tuple[List[Finding], Dict[str, Any]]:
        """增强版顺序执行规则"""
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
            
            # 更新缓存统计
            if cache_hit:
                execution_stats["cache_hits"] += 1
            else:
                execution_stats["cache_misses"] += 1
            
            # 记录规则执行统计
            execution_stats["rule_stats"][rule.metadata.id] = {
                "execution_time": rule_execution_time,
                "findings_count": len(rule_findings),
                "cache_hit": cache_hit,
                "severity_counts": self._count_findings_by_severity(rule_findings),
                "timed_out": False
            }
        
        execution_stats["execution_time"] = time.time() - start_time
        execution_stats["total_findings"] = len(all_findings)
        
        # 更新全局统计
        self.total_executions += 1
        self.total_findings += len(all_findings)
        
        return all_findings, execution_stats
    
    def _execute_parallel_enhanced(self, context: RuleContext, rules: List[Rule]) -> Tuple[List[Finding], Dict[str, Any]]:
        """增强版并行执行规则"""
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
            # 提交任务
            future_to_rule = {}
            for rule in rules:
                future = executor.submit(self._execute_rule_with_timeout, rule, context)
                future_to_rule[future] = rule
            
            # 收集结果
            for future in as_completed(future_to_rule):
                rule = future_to_rule[future]
                try:
                    # 设置超时
                    rule_findings, cache_hit = future.result(timeout=self.execution_timeout)
                    all_findings.extend(rule_findings)
                    
                    # 更新缓存统计
                    if cache_hit:
                        execution_stats["cache_hits"] += 1
                    else:
                        execution_stats["cache_misses"] += 1
                    
                    # 记录规则执行统计
                    execution_stats["rule_stats"][rule.metadata.id] = {
                        "execution_success": True,
                        "findings_count": len(rule_findings),
                        "cache_hit": cache_hit,
                        "severity_counts": self._count_findings_by_severity(rule_findings),
                        "timed_out": False
                    }
                except TimeoutError:
                    # 执行超时
                    execution_stats["timeouts"] += 1
                    execution_stats["rule_stats"][rule.metadata.id] = {
                        "execution_success": False,
                        "error": f"执行超时（{self.execution_timeout}秒）",
                        "findings_count": 0,
                        "timed_out": True
                    }
                    logger.warning(f"规则执行超时: {rule.metadata.id}")
                except Exception as e:
                    execution_stats["rule_stats"][rule.metadata.id] = {
                        "execution_success": False,
                        "error": str(e)[:200],
                        "findings_count": 0,
                        "timed_out": False
                    }
                    logger.error(f"规则执行失败 {rule.metadata.id}: {e}")
        
        execution_stats["execution_time"] = time.time() - start_time
        execution_stats["total_findings"] = len(all_findings)
        
        # 更新全局统计
        self.total_executions += 1
        self.total_findings += len(all_findings)
        
        return all_findings, execution_stats
    
    def _execute_rule_with_timeout(self, rule: Rule, context: RuleContext) -> Tuple[List[Finding], bool]:
        """带超时控制的规则执行"""
        return self._execute_rule_enhanced(rule, context)
    
    def _execute_rule_enhanced(self, rule: Rule, context: RuleContext) -> Tuple[List[Finding], bool]:
        """增强版执行单个规则"""
        cache_hit = False
        
        try:
            # 检查缓存
            cache_key = self._get_cache_key(rule, context)
            
            if self.cache:
                cached_findings = self.cache.get(cache_key)
                if cached_findings is not None:
                    # 返回缓存的副本
                    cache_hit = True
                    return cached_findings.copy(), cache_hit
            
            # 执行规则
            findings = rule.check(context)
            
            # 增强 findings（添加文件路径等元数据）
            enhanced_findings = []
            for finding in findings:
                if not finding.file_path:
                    finding.file_path = context.file_path
                enhanced_findings.append(finding)
            
            # 缓存结果
            if self.cache:
                self.cache.set(cache_key, enhanced_findings.copy())
            
            return enhanced_findings, cache_hit
            
        except Exception as e:
            # 记录错误但不中断整个扫描
            error_finding = Finding(
                rule_id="rule_engine_error",
                message=f"规则执行失败 {rule.metadata.id}: {str(e)[:100]}",
                severity=RuleSeverity.MINOR,
                file_path=context.file_path
            )
            return [error_finding], cache_hit
    
    def _get_cache_key(self, rule: Rule, context: RuleContext) -> str:
        """生成缓存键"""
        # 包含规则ID、文件哈希、规则配置哈希
        rule_config_hash = hashlib.md5(
            str({
                "id": rule.metadata.id,
                "enabled": rule.metadata.enabled,
                "weight": rule.metadata.weight
            }).encode('utf-8')
        ).hexdigest()[:8]
        
        return f"{rule.metadata.id}:{context.file_hash}:{rule_config_hash}"
    
    def _count_findings_by_severity(self, findings: List[Finding]) -> Dict[str, int]:
        """统计不同严重级别的问题数量"""
        counts = {severity.value: 0 for severity in RuleSeverity}
        
        for finding in findings:
            counts[finding.severity.value] += 1
        
        return counts
    
    def clear_cache(self):
        """清空缓存"""
        if self.cache:
            self.cache.clear()
            logger.info("缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        if self.cache:
            return self.cache.stats()
        else:
            return {"enabled": False, "size": 0}
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """获取引擎统计"""
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
        """执行指定分类的规则"""
        # 将字符串转换为枚举
        from .interfaces import RuleCategory
        try:
            rule_category = RuleCategory(category)
        except ValueError:
            # 如果无法转换，返回空结果
            return [], {"error": f"无效的分类: {category}"}
        
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
        按优先级执行规则
        
        Args:
            context: 规则上下文
            high_priority_first: 是否先执行高优先级规则
            
        Returns:
            (发现的问题列表, 执行统计信息)
        """
        rules = self.registry.get_all_rules(enabled_only=True)
        
        if not rules:
            return [], {}
        
        # 按优先级排序
        if high_priority_first:
            # 按严重级别和权重排序
            def rule_priority(rule: Rule) -> tuple:
                # 严重级别权重（越高越优先）
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
        预热缓存
        
        Args:
            contexts: 规则上下文列表
        """
        if not self.cache:
            logger.info("缓存未启用，跳过预热")
            return
        
        logger.info(f"开始预热缓存，共 {len(contexts)} 个上下文")
        
        rules = self.registry.get_all_rules(enabled_only=True)
        if not rules:
            logger.info("没有启用的规则，跳过预热")
            return
        
        start_time = time.time()
        cache_hits = 0
        cache_misses = 0
        
        for context in contexts:
            for rule in rules:
                cache_key = self._get_cache_key(rule, context)
                
                # 尝试从缓存获取
                if self.cache.get(cache_key) is not None:
                    cache_hits += 1
                else:
                    cache_misses += 1
        
        elapsed_time = time.time() - start_time
        logger.info(f"缓存预热完成: 命中 {cache_hits}, 未命中 {cache_misses}, 耗时 {elapsed_time:.2f} 秒")


# 向后兼容的别名
EnhancedRuleEngine = EnhancedRuleEngine


if __name__ == "__main__":
    # 测试增强版引擎
    import sys
    logging.basicConfig(level=logging.INFO)
    
    # 创建测试配置
    config = {
        "cache": {
            "enabled": True,
            "max_size": 100,
            "ttl": 60  # 1分钟
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
    
    # 创建引擎
    registry = RuleRegistry()
    registry.register(NoGlobalScopeRule())
    
    engine = EnhancedRuleEngine(registry, config)
    
    # 测试代码
    test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("测试")
    }
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="test.kt",
        language="kotlin"
    )
    
    # 执行规则
    findings, stats = engine.execute_all(context)
    
    print("增强版规则引擎测试:")
    print(f"执行统计: {stats}")
    print(f"缓存统计: {engine.get_cache_stats()}")
    print(f"引擎统计: {engine.get_engine_stats()}")
    
    if findings:
        print(f"发现的问题 ({len(findings)} 个):")
        for i, finding in enumerate(findings, 1):
            print(f"  {i}. {finding.rule_id}: {finding.message}")