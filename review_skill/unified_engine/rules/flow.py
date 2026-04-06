"""
Flow Rules for Unified Engine

Kotlin Flow 相关规则 - 使用 HYBRID 或 FAST 模式
"""
from typing import List
import re
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "FlowOnMainDispatcherRule",
    "MissingFlowOnForIoRule",
    "ChannelFlowUsageRule",
    "EagerSharingDetectedRule",
    "MutableStateFlowExposedRule",
    "MissingFlowOnRule",
    "FlowOnMainThreadRule",
    "MultipleFlowOnRule",
    "FlowExceptionHandlingRule",
    "StateFlowValueAssignmentRule",
]


class MissingFlowOnRule(UnifiedRule):
    """缺失 flowOn 规则 - 兼容测试"""

    execution_mode = ExecutionMode.FAST

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="missing_flow_on",
            name="Missing flowOn operator",
            description="Flow should use flowOn for IO operations",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.PERFORMANCE,
            tags=["android", "kotlin", "flow"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class FlowOnMainThreadRule(UnifiedRule):
    """Flow 在主线程检测规则"""

    execution_mode = ExecutionMode.HYBRID

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="flow_on_main_thread",
            name="Flow on main thread",
            description="Flow operators should not run on main thread",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.PERFORMANCE,
            tags=["android", "kotlin", "flow"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class MultipleFlowOnRule(UnifiedRule):
    """多个 flowOn 检测规则"""

    execution_mode = ExecutionMode.FAST

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="multiple_flow_on",
            name="Multiple flowOn operators",
            description="Multiple flowOn operators may indicate design issue",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["android", "kotlin", "flow"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class FlowExceptionHandlingRule(UnifiedRule):
    """Flow 异常处理规则"""

    execution_mode = ExecutionMode.FAST

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="flow_exception_handling",
            name="Flow exception handling",
            description="Flow should have proper exception handling",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS,
            tags=["android", "kotlin", "flow"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class StateFlowValueAssignmentRule(UnifiedRule):
    """StateFlow 值赋值规则"""

    execution_mode = ExecutionMode.FAST

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="stateflow_value_assignment",
            name="StateFlow value assignment",
            description="StateFlow should use value property for assignment",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS,
            tags=["android", "kotlin", "flow"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class FlowOnMainDispatcherRule(UnifiedRule):
    """
    Flow flowOn 使用主线程调度器检测规则

    flowOn(Dispatchers.Main) 可能导致上游操作在主线程执行。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="flowon_main_dispatcher",
            name="Flow flowOn on Main Thread",
            description="flowOn(Dispatchers.Main) may cause upstream operations to execute on the main thread",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.PERFORMANCE,
            tags=["android", "kotlin", "flow", "coroutine", "main_thread"],
            weight=1.0,
            suggested_fix="Move flowOn to an appropriate dispatcher, such as Dispatchers.IO or Dispatchers.Default",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """Detect flowOn(Dispatchers.Main) usage"""
        findings = []

        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            # Detect flowOn(Dispatchers.Main) pattern
            if "flowon(" in line_lower and "dispatchers.main" in line_lower:
                findings.append(Finding(
                    rule_id=self.metadata.id,
                    message="flowOn(Dispatchers.Main) may cause upstream operations to execute on the main thread",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion=self.metadata.suggested_fix
                ))

        return findings


class MissingFlowOnForIoRule(UnifiedRule):
    """
    Flow IO 操作缺少 flowOn 检测规则

    Flow 执行 IO 操作但没有显式指定 flowOn 调度器。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="missing_flowon_for_io",
            name="Flow IO Operation Missing flowOn",
            description="Flow performs IO operations but does not explicitly specify a flowOn dispatcher",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.PERFORMANCE,
            tags=["android", "kotlin", "flow", "io", "dispatcher"],
            weight=0.9,
            suggested_fix="Explicitly specify flowOn(Dispatchers.IO) for IO operations",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        """Detect Flow performing IO operations but missing flowOn"""
        findings = []

        code = context.code.lower()
        has_flow_builder = "flow {" in code
        has_io_operation = any(keyword in code for keyword in ["repository", "database", "file", "network", "read", "write"])
        has_flowon = "flowon" in code

        if has_flow_builder and has_io_operation and not has_flowon:
            # Find specific line
            lines = context.get_lines()
            for i, line in enumerate(lines, 1):
                line_lower = line.lower()
                if "flow {" in line_lower:
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message="Flow performs IO operations but does not explicitly specify a flowOn dispatcher",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion=self.metadata.suggested_fix
                    ))
                    break

        return findings


class ChannelFlowUsageRule(UnifiedRule):
    """
    channelFlow 使用检测规则

    channelFlow 需要额外注意结构化并发和取消处理。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="channel_flow_usage",
            name="channelFlow Usage Detection",
            description="channelFlow requires extra attention to structured concurrency and cancellation",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CONCURRENCY,
            tags=["android", "kotlin", "flow", "channel", "concurrency"],
            weight=0.8,
            suggested_fix="Verify structured concurrency and cancellation handling for channelFlow",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """Detect channelFlow usage"""
        findings = []

        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "channelflow" in line.lower():
                findings.append(Finding(
                    rule_id=self.metadata.id,
                    message="channelFlow requires extra attention to structured concurrency and cancellation",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion=self.metadata.suggested_fix
                ))

        return findings


class EagerSharingDetectedRule(UnifiedRule):
    """
    热共享检测规则

    SharingStarted.Eagerly 保持上游活动，可能导致资源浪费。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="eager_sharing_detected",
            name="Eager Sharing Detection",
            description="SharingStarted.Eagerly keeps the upstream active, which may lead to resource waste",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.PERFORMANCE,
            tags=["android", "kotlin", "flow", "sharing", "resource"],
            weight=0.8,
            suggested_fix="Consider using SharingStarted.Lazily or SharingStarted.WhileSubscribed",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """Detect SharingStarted.Eagerly usage"""
        findings = []

        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "sharingstarted.eagerly" in line.lower():
                findings.append(Finding(
                    rule_id=self.metadata.id,
                    message="SharingStarted.Eagerly keeps the upstream active, which may lead to resource waste",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion=self.metadata.suggested_fix
                ))

        return findings


class MutableStateFlowExposedRule(UnifiedRule):
    """
    MutableStateFlow 公开暴露检测规则

    MutableStateFlow 不应公开暴露；使用 asStateFlow 暴露只读版本。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="mutable_stateflow_exposed",
            name="MutableStateFlow Exposure Detection",
            description="MutableStateFlow should not be publicly exposed; use asStateFlow to expose a read-only version",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["android", "kotlin", "flow", "stateflow", "encapsulation"],
            weight=0.9,
            suggested_fix="Make MutableStateFlow private and expose a read-only version via asStateFlow",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """Detect publicly exposed MutableStateFlow"""
        findings = []

        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            line_stripped = line.strip()
            # Detect MutableStateFlow assignment that is not private
            if "mutablestateflow" in line_lower and "private" not in line_lower:
                # Check if it's a variable declaration
                if line_stripped.startswith("val ") or line_stripped.startswith("var "):
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message="MutableStateFlow should not be publicly exposed; use asStateFlow to expose a read-only version",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion=self.metadata.suggested_fix
                    ))

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        FlowOnMainDispatcherRule(),
        MissingFlowOnForIoRule(),
        ChannelFlowUsageRule(),
        EagerSharingDetectedRule(),
        MutableStateFlowExposedRule(),
    ]
