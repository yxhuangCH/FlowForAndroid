"""
审查运行器，集成新旧系统 - 增强版
"""
import json
import time
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..interfaces import Finding, RuleSeverity, RuleCategory
from ..context import RuleContext
from ..registry import RuleRegistry
from ..engine import RuleEngine
from .config_loader import get_config_loader

# 所有规则已迁移到新引擎，不再需要导入旧规则
OLD_RULES_AVAILABLE = False

logger = logging.getLogger(__name__)


class EnhancedReviewRunner:
    """增强版审查运行器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 如果没有配置，从配置加载器获取
        if not self.config:
            config_loader = get_config_loader()
            engine_config = config_loader.get_engine_config()
            self.config = {
                "cache": {
                    "enabled": engine_config.get("cache_enabled", True),
                    "max_size": engine_config.get("cache_max_size", 1000),
                    "ttl": engine_config.get("cache_ttl", 3600)
                },
                "parallel": {
                    "enabled": engine_config.get("parallel_execution", True),
                    "max_workers": engine_config.get("max_workers"),
                    "execution_timeout": engine_config.get("execution_timeout", 30)
                },
                "rules": engine_config.get("rules", {})
            }
        
        self.registry = RuleRegistry()
        self.engine = RuleEngine(self.registry, self.config)
        self._initialized = False
    
    def initialize(self):
        """初始化规则引擎"""
        if self._initialized:
            return
        
        # 注册新规则
        self._register_new_rules()
        
        # 注册旧规则适配器（如果可用）- 已禁用，所有规则已迁移到新引擎
        # if OLD_RULES_AVAILABLE:
        #     self._register_legacy_rules()
        
        # 按配置启用/禁用规则
        self._configure_rules()
        
        self._initialized = True
    
    def _register_new_rules(self):
        """注册新规则"""
        from ..rules import base_rules
        
        # 注册基础规则
        self.registry.register(base_rules.NoGlobalScopeRule())
        
        # 注册装饰器规则（装饰器返回的是规则实例，不是函数）
        from ..rules.base_rules import viewmodel_context_rule, main_thread_io_rule
        self.registry.register(viewmodel_context_rule)
        self.registry.register(main_thread_io_rule)
        
        # 注册迁移的协程规则
        try:
            from ..rules.coroutine_rules import coroutine_main_thread_io_rule, unspecified_scope_rule
            self.registry.register(coroutine_main_thread_io_rule)
            self.registry.register(unspecified_scope_rule)
        except ImportError as e:
            logger.warning(f"协程规则导入失败: {e}")

        # 注册迁移的Compose规则
        try:
            from ..rules.compose_rules import launched_effect_unit_rule, remember_context_rule
            self.registry.register(launched_effect_unit_rule)
            self.registry.register(remember_context_rule)
        except ImportError as e:
            logger.warning(f"Compose规则导入失败: {e}")

        # 注册迁移的Flow规则
        try:
            from ..rules.flow_rules import (
                flowon_main_dispatcher_rule,
                missing_flowon_for_io_rule,
                channel_flow_usage_rule,
                eager_sharing_detected_rule,
                mutable_stateflow_exposed_rule
            )
            self.registry.register(flowon_main_dispatcher_rule)
            self.registry.register(missing_flowon_for_io_rule)
            self.registry.register(channel_flow_usage_rule)
            self.registry.register(eager_sharing_detected_rule)
            self.registry.register(mutable_stateflow_exposed_rule)
        except ImportError as e:
            logger.warning(f"Flow规则导入失败: {e}")

        # 注册迁移的Flow生命周期规则
        try:
            from ..rules.flow_lifecycle_rules import (
                statein_globalscope_rule,
                sharein_globalscope_rule,
                collect_without_repeat_rule,
                statein_without_viewmodelscope_rule
            )
            self.registry.register(statein_globalscope_rule)
            self.registry.register(sharein_globalscope_rule)
            self.registry.register(collect_without_repeat_rule)
            self.registry.register(statein_without_viewmodelscope_rule)
        except ImportError as e:
            logger.warning(f"Flow生命周期规则导入失败: {e}")

        # 注册迁移的Flow结构规则
        try:
            from ..rules.flow_structure_rules import (
                nested_launch_in_collect_rule,
                launch_inside_flow_rule,
                multiple_collects_rule,
                channel_flow_no_awaitclose_rule
            )
            self.registry.register(nested_launch_in_collect_rule)
            self.registry.register(launch_inside_flow_rule)
            self.registry.register(multiple_collects_rule)
            self.registry.register(channel_flow_no_awaitclose_rule)
        except ImportError as e:
            logger.warning(f"Flow结构规则导入失败: {e}")

        # 注册迁移的Hilt规则
        try:
            from ..rules.hilt_rules import singleton_activity_rule
            self.registry.register(singleton_activity_rule)
        except ImportError as e:
            logger.warning(f"Hilt规则导入失败: {e}")

        # 注册迁移的Dagger2规则
        try:
            from ..rules.dagger2_rules import (
                singleton_component_inject_activity_rule,
                field_injection_detected_rule,
                provides_without_scope_rule
            )
            self.registry.register(singleton_component_inject_activity_rule)
            self.registry.register(field_injection_detected_rule)
            self.registry.register(provides_without_scope_rule)
        except ImportError as e:
            logger.warning(f"Dagger2规则导入失败: {e}")
    
    def _register_legacy_rules(self):
        """注册旧规则适配器（已禁用，legacy_adapter 已移除）"""
        logger.warning("legacy_adapter 已移除，旧规则适配器功能已禁用")
        # 此功能已不再需要，所有规则已迁移到新引擎格式
    
    def _configure_rules(self):
        """根据配置启用/禁用规则"""
        # 从配置读取规则设置
        rule_config = self.config.get("rules", {})
        
        # 启用/禁用特定规则
        enabled_rules = rule_config.get("enabled_rules", [])
        disabled_rules = rule_config.get("disabled_rules", [])
        
        for rule_id in enabled_rules:
            self.registry.enable_rule(rule_id)
        
        for rule_id in disabled_rules:
            self.registry.disable_rule(rule_id)
        
        # 按分类启用/禁用
        enabled_categories = rule_config.get("enabled_categories", [])
        if enabled_categories:
            # 禁用所有规则，然后启用指定分类的规则
            for rule in self.registry.get_all_rules(enabled_only=False):
                rule.metadata.enabled = False
            
            for category_str in enabled_categories:
                try:
                    category = RuleCategory(category_str)
                    rules = self.registry.get_rules_by_category(category, enabled_only=False)
                    for rule in rules:
                        rule.metadata.enabled = True
                except ValueError:
                    # 忽略无效的分类
                    pass
    
    def review_file(self, file_path: str, code: str, language: str = "kotlin") -> Dict[str, Any]:
        """
        审查单个文件
        
        Args:
            file_path: 文件路径
            code: 代码内容
            language: 编程语言
            
        Returns:
            审查结果
        """
        # 确保已初始化
        if not self._initialized:
            self.initialize()
        
        # 创建上下文
        context = RuleContext(
            code=code,
            file_path=file_path,
            language=language,
            config=self.config
        )
        
        # 执行规则（使用并行执行）
        parallel = self.config.get("parallel_execution", True)
        findings, stats = self.engine.execute_all(context, parallel=parallel)
        
        # 计算分数
        score = self._calculate_score(findings)
        
        # 转换为旧格式（兼容性）
        legacy_findings = [f.to_dict() for f in findings]
        
        return {
            "file": file_path,
            "findings": legacy_findings,
            "score": score,
            "stats": stats,
            "engine_stats": self.registry.get_statistics()
        }
    
    def _calculate_score(self, findings: List[Finding]) -> int:
        """
        计算代码质量分数
        
        Args:
            findings: 发现的问题列表
            
        Returns:
            分数（0-100）
        """
        if not findings:
            return 100
        
        score = 100
        
        for finding in findings:
            # 获取对应的规则
            rule = self.registry.get_rule(finding.rule_id)
            if rule:
                deduction = rule.get_score_deduction(finding.severity)
                score -= deduction
            else:
                # 默认扣分
                default_deduction = {
                    "info": 0,
                    "minor": 5,
                    "major": 10,
                    "critical": 20,
                    "blocker": 100
                }.get(finding.severity.value, 5)
                score -= default_deduction
        
        # 确保分数在0-100之间
        return max(0, min(100, score))
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            "initialized": self._initialized,
            "rule_count": self.registry.count_rules(),
            "statistics": self.registry.get_statistics(),
            "cache_stats": self.engine.get_cache_stats()
        }
    
    def review_code(self, code: str, file_path: str = "unknown.kt", language: str = "kotlin") -> Dict[str, Any]:
        """
        审查代码片段
        
        Args:
            code: 代码内容
            file_path: 文件路径（默认unknown.kt）
            language: 编程语言
            
        Returns:
            审查结果
        """
        return self.review_file(file_path, code, language)
    
    def review_diff(self, diff: str) -> List[Dict[str, Any]]:
        """
        审查Git diff
        
        Args:
            diff: Git diff文本
            
        Returns:
            审查结果列表（每个文件一个结果）
        """
        if not self._initialized:
            self.initialize()
        
        results = []
        
        # 简单解析diff（实际实现需要更复杂的解析）
        lines = diff.split('\n')
        current_file = None
        current_code = []
        
        for line in lines:
            if line.startswith('diff --git'):
                # 处理上一个文件
                if current_file and current_code:
                    file_result = self.review_file(
                        file_path=current_file,
                        code='\n'.join(current_code),
                        language="kotlin"
                    )
                    results.append(file_result)
                
                # 开始新文件
                # 提取文件名：diff --git a/path/to/file b/path/to/file
                parts = line.split()
                if len(parts) >= 4:
                    # 取b侧的文件名，去掉b/前缀
                    b_file = parts[3]
                    if b_file.startswith('b/'):
                        current_file = b_file[2:]
                    else:
                        current_file = b_file
                else:
                    current_file = "unknown"
                current_code = []
            elif line.startswith('+') and not line.startswith('+++'):
                # 新增行
                current_code.append(line[1:])
            elif line.startswith(' ') and not line.startswith('---'):
                # 未变更行
                current_code.append(line[1:])
        
        # 处理最后一个文件
        if current_file and current_code:
            file_result = self.review_file(
                file_path=current_file,
                code='\n'.join(current_code),
                language="kotlin"
            )
            results.append(file_result)
        
        return results


# 向后兼容别名
ReviewRunner = EnhancedReviewRunner
