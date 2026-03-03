"""
规则执行引擎
"""
import threading
import time
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from .interfaces import Rule, Finding, RuleSeverity
from .context import RuleContext
from .registry import RuleRegistry


class RuleEngine:
    """规则执行引擎"""
    
    def __init__(self, registry: Optional[RuleRegistry] = None):
        self.registry = registry or RuleRegistry()
        self.cache: Dict[str, List[Finding]] = {}  # 缓存：cache_key -> findings
        self.cache_lock = threading.Lock()
        self.execution_stats: Dict[str, Dict[str, Any]] = {}  # 执行统计
    
    def execute_all(self, context: RuleContext, parallel: bool = False) -> Tuple[List[Finding], Dict[str, Any]]:
        """
        执行所有启用的规则
        
        Args:
            context: 规则上下文
            parallel: 是否并行执行
            
        Returns:
            (发现的问题列表, 执行统计信息)
        """
        rules = self.registry.get_all_rules(enabled_only=True)
        
        if not rules:
            return [], {}
        
        if parallel:
            return self._execute_parallel(context, rules)
        else:
            return self._execute_sequential(context, rules)
    
    def _execute_sequential(self, context: RuleContext, rules: List[Rule]) -> Tuple[List[Finding], Dict[str, Any]]:
        """顺序执行规则"""
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
            
            # 记录规则执行统计
            execution_stats["rule_stats"][rule.metadata.id] = {
                "execution_time": rule_execution_time,
                "findings_count": len(rule_findings),
                "severity_counts": self._count_findings_by_severity(rule_findings)
            }
        
        execution_stats["execution_time"] = time.time() - start_time
        execution_stats["total_findings"] = len(all_findings)
        
        return all_findings, execution_stats
    
    def _execute_parallel(self, context: RuleContext, rules: List[Rule], max_workers: int = 4) -> Tuple[List[Finding], Dict[str, Any]]:
        """并行执行规则"""
        all_findings = []
        execution_stats = {
            "total_rules": len(rules),
            "execution_time": 0,
            "max_workers": max_workers,
            "rule_stats": {}
        }
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_rule = {}
            for rule in rules:
                future = executor.submit(self._execute_rule, rule, context)
                future_to_rule[future] = rule
            
            # 收集结果
            for future in as_completed(future_to_rule):
                rule = future_to_rule[future]
                try:
                    rule_findings = future.result()
                    all_findings.extend(rule_findings)
                    
                    # 记录统计（并行执行时间不准确，只记录是否执行成功）
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
        """执行单个规则"""
        try:
            # 检查缓存
            cache_key = self._get_cache_key(rule, context)
            
            with self.cache_lock:
                if cache_key in self.cache:
                    # 返回缓存的副本（避免修改）
                    return self.cache[cache_key].copy()
            
            # 执行规则
            findings = rule.check(context)
            
            # 增强 findings（添加文件路径等元数据）
            enhanced_findings = []
            for finding in findings:
                if not finding.file_path:
                    finding.file_path = context.file_path
                enhanced_findings.append(finding)
            
            # 缓存结果
            with self.cache_lock:
                self.cache[cache_key] = enhanced_findings.copy()
            
            return enhanced_findings
            
        except Exception as e:
            # 记录错误但不中断整个扫描
            error_finding = Finding(
                rule_id="rule_engine_error",
                message=f"规则执行失败 {rule.metadata.id}: {str(e)[:100]}",
                severity=RuleSeverity.MINOR,
                file_path=context.file_path
            )
            return [error_finding]
    
    def _get_cache_key(self, rule: Rule, context: RuleContext) -> str:
        """生成缓存键"""
        return f"{rule.metadata.id}:{context.file_hash}:{hash(str(rule.metadata))}"
    
    def _count_findings_by_severity(self, findings: List[Finding]) -> Dict[str, int]:
        """统计不同严重级别的问题数量"""
        counts = {severity.value: 0 for severity in RuleSeverity}
        
        for finding in findings:
            counts[finding.severity.value] += 1
        
        return counts
    
    def clear_cache(self):
        """清空缓存"""
        with self.cache_lock:
            self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.cache_lock:
            return {
                "cache_size": len(self.cache),
                "cache_keys": list(self.cache.keys())[:10]  # 只显示前10个
            }
    
    def execute_by_category(self, context: RuleContext, category: str, parallel: bool = False) -> Tuple[List[Finding], Dict[str, Any]]:
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
        
        if parallel:
            return self._execute_parallel(context, rules)
        else:
            return self._execute_sequential(context, rules)