"""
Review runner, integrates old and new systems - Enhanced version
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

# All rules have been migrated to the new engine, no need to import old rules
OLD_RULES_AVAILABLE = False

logger = logging.getLogger(__name__)


class EnhancedReviewRunner:
    """Enhanced review runner"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # If no config provided, get from config loader
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
        """Initialize rule engine"""
        if self._initialized:
            return
        
        # Register new rules
        self._register_new_rules()
        
        # Register old rule adapters (if available) - Disabled, all rules migrated to new engine
        # if OLD_RULES_AVAILABLE:
        #     self._register_legacy_rules()
        
        # Enable/disable rules according to configuration
        self._configure_rules()
        
        self._initialized = True
    
    def _register_new_rules(self):
        """Register new rules"""
        from ..rules import base_rules
        
        # Register base rules
        self.registry.register(base_rules.NoGlobalScopeRule())
        
        # Register decorator rules (decorators return rule instances, not functions)
        from ..rules.base_rules import viewmodel_context_rule, main_thread_io_rule
        self.registry.register(viewmodel_context_rule)
        self.registry.register(main_thread_io_rule)
        
        # Register migrated coroutine rules
        try:
            from ..rules.coroutine_rules import coroutine_main_thread_io_rule, unspecified_scope_rule
            self.registry.register(coroutine_main_thread_io_rule)
            self.registry.register(unspecified_scope_rule)
        except ImportError as e:
            logger.warning(f"Coroutine rules import failed: {e}")

        # Register migrated Compose rules
        try:
            from ..rules.compose_rules import launched_effect_unit_rule, remember_context_rule
            self.registry.register(launched_effect_unit_rule)
            self.registry.register(remember_context_rule)
        except ImportError as e:
            logger.warning(f"Compose rules import failed: {e}")

        # Register migrated Flow rules
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
            logger.warning(f"Flow rules import failed: {e}")

        # Register migrated Flow lifecycle rules
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
            logger.warning(f"Flow lifecycle rules import failed: {e}")

        # Register migrated Flow structure rules
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
            logger.warning(f"Flow structure rules import failed: {e}")

        # Register migrated Hilt rules
        try:
            from ..rules.hilt_rules import singleton_activity_rule
            self.registry.register(singleton_activity_rule)
        except ImportError as e:
            logger.warning(f"Hilt rules import failed: {e}")

        # Register migrated Dagger2 rules
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
            logger.warning(f"Dagger2 rules import failed: {e}")

        # Register Android-specific rules
        try:
            from ..rules.android_rules import startactivity_without_trycatch_rule
            self.registry.register(startactivity_without_trycatch_rule)
        except ImportError as e:
            logger.warning(f"Android rules import failed: {e}")
    
    def _register_legacy_rules(self):
        """Register old rule adapters (disabled, legacy_adapter removed)"""
        logger.warning("legacy_adapter removed, old rule adapters disabled")
        # This feature is no longer needed, all rules migrated to new engine format
    
    def _configure_rules(self):
        """Enable/disable rules according to configuration"""
        # Read rule settings from configuration
        rule_config = self.config.get("rules", {})
        
        # Enable/disable specific rules
        enabled_rules = rule_config.get("enabled_rules", [])
        disabled_rules = rule_config.get("disabled_rules", [])
        
        for rule_id in enabled_rules:
            self.registry.enable_rule(rule_id)
        
        for rule_id in disabled_rules:
            self.registry.disable_rule(rule_id)
        
        # Enable/disable by category
        enabled_categories = rule_config.get("enabled_categories", [])
        if enabled_categories:
            # Disable all rules, then enable rules in specified categories
            for rule in self.registry.get_all_rules(enabled_only=False):
                rule.metadata.enabled = False
            
            for category_str in enabled_categories:
                try:
                    category = RuleCategory(category_str)
                    rules = self.registry.get_rules_by_category(category, enabled_only=False)
                    for rule in rules:
                        rule.metadata.enabled = True
                except ValueError:
                    # Ignore invalid categories
                    pass
    
    def review_file(self, file_path: str, code: str, language: str = "kotlin") -> Dict[str, Any]:
        """
        Review a single file
        
        Args:
            file_path: File path
            code: Code content
            language: Programming language
            
        Returns:
            Review result
        """
        # Ensure initialized
        if not self._initialized:
            self.initialize()
        
        # Create context
        context = RuleContext(
            code=code,
            file_path=file_path,
            language=language,
            config=self.config
        )
        
        # Execute rules (use parallel execution)
        parallel = self.config.get("parallel_execution", True)
        findings, stats = self.engine.execute_all(context, parallel=parallel)
        
        # Calculate score
        score = self._calculate_score(findings)
        
        # Convert to old format (compatibility)
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
        Calculate code quality score
        
        Args:
            findings: List of findings
            
        Returns:
            Score (0-100)
        """
        if not findings:
            return 100
        
        score = 100
        
        for finding in findings:
            # Get corresponding rule
            rule = self.registry.get_rule(finding.rule_id)
            if rule:
                deduction = rule.get_score_deduction(finding.severity)
                score -= deduction
            else:
                # Default deduction
                default_deduction = {
                    "info": 0,
                    "minor": 5,
                    "major": 10,
                    "critical": 20,
                    "blocker": 100
                }.get(finding.severity.value, 5)
                score -= default_deduction
        
        # Ensure score is between 0-100
        return max(0, min(100, score))
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get engine info"""
        return {
            "initialized": self._initialized,
            "rule_count": self.registry.count_rules(),
            "statistics": self.registry.get_statistics(),
            "cache_stats": self.engine.get_cache_stats()
        }
    
    def review_code(self, code: str, file_path: str = "unknown.kt", language: str = "kotlin") -> Dict[str, Any]:
        """
        Review code snippet
        
        Args:
            code: Code content
            file_path: File path (default unknown.kt)
            language: Programming language
            
        Returns:
            Review result
        """
        return self.review_file(file_path, code, language)
    
    def review_diff(self, diff: str) -> List[Dict[str, Any]]:
        """
        Review Git diff
        
        Args:
            diff: Git diff text
            
        Returns:
            List of review results (one per file)
        """
        if not self._initialized:
            self.initialize()
        
        results = []
        
        # Simple diff parsing (actual implementation needs more complex parsing)
        lines = diff.split('\n')
        current_file = None
        current_code = []
        
        for line in lines:
            if line.startswith('diff --git'):
                # Process previous file
                if current_file and current_code:
                    file_result = self.review_file(
                        file_path=current_file,
                        code='\n'.join(current_code),
                        language="kotlin"
                    )
                    results.append(file_result)
                
                # Start new file
                # Extract filename: diff --git a/path/to/file b/path/to/file
                parts = line.split()
                if len(parts) >= 4:
                    # Take filename from b side, remove b/ prefix
                    b_file = parts[3]
                    if b_file.startswith('b/'):
                        current_file = b_file[2:]
                    else:
                        current_file = b_file
                else:
                    current_file = "unknown"
                current_code = []
            elif line.startswith('+') and not line.startswith('+++'):
                # Added lines
                current_code.append(line[1:])
            elif line.startswith(' ') and not line.startswith('---'):
                # Unchanged lines
                current_code.append(line[1:])
        
        # Process last file
        if current_file and current_code:
            file_result = self.review_file(
                file_path=current_file,
                code='\n'.join(current_code),
                language="kotlin"
            )
            results.append(file_result)
        
        return results


# Backward compatible alias
ReviewRunner = EnhancedReviewRunner
