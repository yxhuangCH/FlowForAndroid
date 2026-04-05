"""
Base Rules for Unified Engine

基础规则集 - 使用 FAST 模式执行
"""
from typing import List
import re
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "NoGlobalScopeRule",
    "ViewModelContextRule",
    "MainThreadIoRule",
]


class NoGlobalScopeRule(UnifiedRule):
    """
    禁止使用 GlobalScope 规则

    GlobalScope 的生命周期与整个应用程序相同，使用它启动协程
    可能导致内存泄漏。应该使用生命周期感知的协程作用域。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="no_globalscope",
            name="Prohibit GlobalScope usage",
            description="GlobalScope.launch may cause memory leaks, should use lifecycle-aware coroutine scopes",
            severity=RuleSeverity.BLOCKER,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "coroutine", "lifecycle"],
            weight=1.5,
            suggested_fix="Use viewModelScope, lifecycleScope or custom CoroutineScope instead of GlobalScope",
            reference_url="https://developer.android.com/kotlin/coroutines/coroutines-best-practices"
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []

        # FAST 模式：仅使用正则匹配
        line_matches = context.find_pattern_with_lines(r"GlobalScope\.(launch|async)", case_sensitive=False)

        for match in line_matches:
            findings.append(Finding(
                rule_id=self.metadata.id,
                message=self.metadata.description,
                severity=self.metadata.severity,
                file_path=context.file_path,
                line_number=match.line_number,
                code_snippet=match.line_content.strip(),
                suggestion=self.metadata.suggested_fix
            ))

        return findings


class ViewModelContextRule(UnifiedRule):
    """
    ViewModel 不应持有 Context 规则

    ViewModel 的生命周期可能比 Activity/Fragment 更长，
    直接持有 Context 可能导致内存泄漏。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="viewmodel_context",
            name="ViewModel should not hold Context",
            description="ViewModel should not directly hold Android Context, which may cause memory leaks",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "viewmodel", "context"],
            weight=1.2,
            suggested_fix="Use Application Context or get Context through AndroidViewModel",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []

        # Phase 1: Fast - 快速筛选 ViewModel 类
        lines = context.get_lines()
        in_viewmodel = False
        viewmodel_brace_depth = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # 检测 ViewModel 类定义
            if not in_viewmodel:
                if re.search(r"class\s+\w+.*ViewModel", stripped):
                    in_viewmodel = True
                    viewmodel_brace_depth = stripped.count("{") - stripped.count("}")
                    continue
            else:
                # 跟踪类体内的花括号深度
                viewmodel_brace_depth += stripped.count("{") - stripped.count("}")

                if viewmodel_brace_depth <= 0:
                    in_viewmodel = False
                    continue

                # Phase 2: 检测是否持有 Context
                if re.search(r"(val|var|lateinit)\s+\w+.*:\s*Context", stripped):
                    # 排除 Application Context（安全）
                    if "Application" not in stripped:
                        findings.append(Finding(
                            rule_id=self.metadata.id,
                            message=self.metadata.description,
                            severity=self.metadata.severity,
                            file_path=context.file_path,
                            line_number=i,
                            code_snippet=stripped,
                            suggestion=self.metadata.suggested_fix
                        ))

        return findings


class MainThreadIoRule(UnifiedRule):
    """
    主线程 IO 操作检测规则

    在主线程执行 IO 操作可能导致 ANR（应用程序无响应）。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="main_thread_io",
            name="Main thread IO operation",
            description="Executing IO operations on main thread may cause ANR (Application Not Responding)",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.PERFORMANCE,
            tags=["android", "kotlin", "coroutine", "io", "anr"],
            weight=1.0,
            suggested_fix="Move IO operations to Dispatchers.IO or background thread",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []

        # Phase 1: Fast - 检查是否有主线程调度器和 IO 操作
        has_main_dispatcher = context.contains_pattern(r"Dispatchers\.Main", case_sensitive=False)

        if not has_main_dispatcher:
            return findings

        # 检测 IO 相关操作
        io_keywords = ["read", "write", "file", "network", "database", "sharedpreferences", "repository"]

        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            for keyword in io_keywords:
                if keyword in line_lower:
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message=f"Detected risk of executing IO operations on main thread (keyword: {keyword})",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion=self.metadata.suggested_fix
                    ))
                    break  # 每行只报告一次

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        NoGlobalScopeRule(),
        ViewModelContextRule(),
        MainThreadIoRule(),
    ]
