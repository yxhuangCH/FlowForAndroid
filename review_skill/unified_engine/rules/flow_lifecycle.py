"""
Flow Lifecycle Rules for Unified Engine

Flow 生命周期相关规则 - 使用 FAST 或 HYBRID 模式
"""
from typing import List
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "StateInGlobalScopeRule",
    "ShareInGlobalScopeRule",
    "CollectWithoutRepeatRule",
    "StateInWithoutViewModelScopeRule",
]


class StateInGlobalScopeRule(UnifiedRule):
    """
    StateFlow.stateIn 使用 GlobalScope 检测规则

    在 StateFlow.stateIn() 中使用 GlobalScope 会导致内存泄漏，
    因为 StateFlow 的生命周期与 GlobalScope 绑定，无法自动清理。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="statein_globalscope",
            name="StateFlow.stateIn 使用 GlobalScope",
            description="在 StateFlow.stateIn() 中使用 GlobalScope 会导致内存泄漏，因为 StateFlow 的生命周期与 GlobalScope 绑定，无法自动清理",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "flow", "stateflow", "globalscope", "memory_leak"],
            weight=1.0,
            suggested_fix="使用 viewModelScope 或 lifecycleScope 替代 GlobalScope，确保 StateFlow 在生命周期结束时自动清理",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测 stateIn(GlobalScope)"""
        findings = []

        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "statein(globalscope" in line.lower():
                findings.append(Finding(
                    rule_id=self.metadata.id,
                    message="StateFlow.stateIn() 使用 GlobalScope 会导致内存泄漏",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="使用 viewModelScope 或 lifecycleScope 替代 GlobalScope"
                ))

        return findings


class ShareInGlobalScopeRule(UnifiedRule):
    """
    SharedFlow.shareIn 使用 GlobalScope 检测规则

    在 SharedFlow.shareIn() 中使用 GlobalScope 会导致内存泄漏，
    因为 SharedFlow 的生命周期与 GlobalScope 绑定，无法自动清理。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="sharein_globalscope",
            name="SharedFlow.shareIn 使用 GlobalScope",
            description="在 SharedFlow.shareIn() 中使用 GlobalScope 会导致内存泄漏，因为 SharedFlow 的生命周期与 GlobalScope 绑定，无法自动清理",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "flow", "sharedflow", "globalscope", "memory_leak"],
            weight=1.0,
            suggested_fix="使用 viewModelScope 或 lifecycleScope 替代 GlobalScope，确保 SharedFlow 在生命周期结束时自动清理",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测 shareIn(GlobalScope)"""
        findings = []

        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "sharein(globalscope" in line.lower():
                findings.append(Finding(
                    rule_id=self.metadata.id,
                    message="SharedFlow.shareIn() 使用 GlobalScope 会导致内存泄漏",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="使用 viewModelScope 或 lifecycleScope 替代 GlobalScope"
                ))

        return findings


class CollectWithoutRepeatRule(UnifiedRule):
    """
    UI 层 Flow collect 缺少 repeatOnLifecycle 检测规则

    在 Activity/Fragment/Composable 中直接使用 collect 收集 Flow，
    当应用进入后台时仍会接收事件，可能导致崩溃或资源浪费。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="collect_without_repeat",
            name="UI 层 Flow collect 缺少 repeatOnLifecycle",
            description="在 Activity/Fragment/Composable 中直接使用 collect 收集 Flow，当应用进入后台时仍会接收事件，可能导致崩溃或资源浪费",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "flow", "collect", "lifecycle", "ui"],
            weight=0.9,
            suggested_fix="使用 repeatOnLifecycle 包装 collect，确保只在生命周期处于特定状态时接收事件",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测 collect 缺少 repeatOnLifecycle"""
        findings = []

        lines = context.get_lines()
        in_ui_layer = False
        has_collect = False

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            # 检测是否在 UI 层（Activity/Fragment/Compose）
            if any(keyword in line_lower for keyword in ["activity", "fragment", "composable", "@composable"]):
                in_ui_layer = True

            # 检测 collect
            if "collect {" in line_lower:
                has_collect = True
                if in_ui_layer and "repeatonlifecycle" not in line_lower:
                    # 检查附近是否有 repeatOnLifecycle
                    has_repeat_nearby = False
                    start = max(0, i - 3)
                    end = min(len(lines), i + 1)
                    for j in range(start, end):
                        if j != i and "repeatonlifecycle" in lines[j].lower():
                            has_repeat_nearby = True
                            break

                    if not has_repeat_nearby:
                        findings.append(Finding(
                            rule_id=self.metadata.id,
                            message="UI 层直接使用 collect 收集 Flow，缺少 repeatOnLifecycle",
                            severity=self.metadata.severity,
                            file_path=context.file_path,
                            line_number=i,
                            code_snippet=line,
                            suggestion="使用 repeatOnLifecycle 包装 collect"
                        ))

        return findings


class StateInWithoutViewModelScopeRule(UnifiedRule):
    """
    ViewModel 中 stateIn 未使用 viewModelScope 检测规则

    在 ViewModel 中使用 stateIn 转换 Flow 时，
    应传入 viewModelScope 作为作用域，以确保与 ViewModel 生命周期绑定。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="statein_without_viewmodelscope",
            name="ViewModel 中 stateIn 未使用 viewModelScope",
            description="在 ViewModel 中使用 stateIn 转换 Flow 时，应传入 viewModelScope 作为作用域，以确保与 ViewModel 生命周期绑定",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "flow", "viewmodel", "scope"],
            weight=0.8,
            suggested_fix="在 ViewModel 中使用 stateIn(viewModelScope) 替代其他作用域",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测 ViewModel 中 stateIn 未使用 viewModelScope"""
        findings = []

        lines = context.get_lines()
        in_viewmodel = False

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            # 检测是否在 ViewModel 中
            if "viewmodel" in line_lower or ": viewmodel" in line_lower:
                in_viewmodel = True

            # 检测 stateIn
            if in_viewmodel and "statein(" in line_lower:
                if "viewmodelscope" not in line_lower:
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message="ViewModel 中使用 stateIn 未传入 viewModelScope",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion="使用 stateIn(viewModelScope)"
                    ))

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        StateInGlobalScopeRule(),
        ShareInGlobalScopeRule(),
        CollectWithoutRepeatRule(),
        StateInWithoutViewModelScopeRule(),
    ]
