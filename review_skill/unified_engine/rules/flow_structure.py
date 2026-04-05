"""
Flow Structure Rules for Unified Engine

Flow 结构相关规则 - 使用 FAST 或 HYBRID 模式
"""
from typing import List
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "NestedLaunchInCollectRule",
    "LaunchInsideFlowRule",
    "MultipleCollectsRule",
    "ChannelFlowNoAwaitCloseRule",
]


class NestedLaunchInCollectRule(UnifiedRule):
    """
    collectLatest 内部嵌套 launch 检测规则

    在 collectLatest 回调内部使用 launch 会导致并发问题，
    collectLatest 的取消语义可能无法正确传递。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="nested_launch_in_collect",
            name="collectLatest 内部嵌套 launch",
            description="在 collectLatest 回调内部使用 launch 会导致并发问题，collectLatest 的取消语义可能无法正确传递",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CONCURRENCY,
            tags=["android", "kotlin", "flow", "collect", "launch", "concurrency"],
            weight=0.8,
            suggested_fix="避免在 collectLatest 内部使用 launch，直接使用 collectLatest 的挂起特性处理异步操作",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测 collectLatest 内嵌 launch"""
        findings = []

        lines = context.get_lines()
        in_collect_latest = False
        collect_start_line = 0

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            # 检测 collectLatest 开始
            if "collectlatest" in line_lower and "{" in line_lower:
                in_collect_latest = True
                collect_start_line = i

            # 在 collectLatest 内部
            if in_collect_latest:
                # 检测 launch
                if "launch" in line_lower and "{" in line_lower:
                    # 检查是否是直接调用 launch（没有 scope 前缀）
                    if not any(op in line_lower for op in ["viewmodelscope.launch", "lifecyclescope.launch", "globalscope.launch"]):
                        findings.append(Finding(
                            rule_id=self.metadata.id,
                            message="collectLatest 内部嵌套 launch 可能导致并发问题",
                            severity=self.metadata.severity,
                            file_path=context.file_path,
                            line_number=i,
                            code_snippet=line,
                            suggestion="避免在 collectLatest 内部使用 launch"
                        ))

                # 检测 collectLatest 结束
                if line.strip() == "}" and in_collect_latest:
                    # 简单检测结束，可能有嵌套情况
                    in_collect_latest = False

        return findings


class LaunchInsideFlowRule(UnifiedRule):
    """
    flow {} 构建器中使用 launch 检测规则

    在 flow { } 构建器中使用 launch 会破坏流的可组合性和背压处理，
    应该使用 callbackFlow 或 channelFlow。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="launch_inside_flow",
            name="flow {} 构建器中使用 launch",
            description="在 flow { } 构建器中使用 launch 会破坏流的可组合性和背压处理，应该使用 callbackFlow 或 channelFlow",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.CONCURRENCY,
            tags=["android", "kotlin", "flow", "launch", "concurrency", "builder"],
            weight=1.0,
            suggested_fix="使用 callbackFlow 或 channelFlow 替代 flow { } 构建器中的 launch",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测 flow builder 中的 launch"""
        findings = []

        lines = context.get_lines()
        in_flow_builder = False

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            # 检测 flow builder 开始
            if "flow {" in line_lower:
                in_flow_builder = True

            # 在 flow builder 内部
            if in_flow_builder:
                # 检测 launch
                if "launch" in line_lower and "{" in line_lower:
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message="flow builder 中使用 launch 会破坏流的特性",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion="使用 callbackFlow 或 channelFlow"
                    ))

                # 检测 flow builder 结束（简化处理）
                if line.strip() == "}" and in_flow_builder:
                    in_flow_builder = False

        return findings


class MultipleCollectsRule(UnifiedRule):
    """
    多次收集同一个 Cold Flow 检测规则

    多个地方收集同一个 Cold Flow 会导致重复执行上游操作，浪费资源。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="multiple_collects",
            name="多次收集同一个 Cold Flow",
            description="多个地方收集同一个 Cold Flow 会导致重复执行上游操作，浪费资源",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["android", "kotlin", "flow", "collect", "cold_flow"],
            weight=0.5,
            suggested_fix="使用 shareIn 或 stateIn 将 Cold Flow 转换为 Hot Flow，避免重复执行",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测多次 collect"""
        findings = []

        collect_count = 0
        lines = context.get_lines()
        collect_lines = []

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if ".collect" in line_lower or "collect {" in line_lower:
                collect_count += 1
                collect_lines.append(i)

        if collect_count > 1:
            # 报告多次 collect
            findings.append(Finding(
                rule_id=self.metadata.id,
                message=f"检测到 {collect_count} 处 collect，可能多次收集 Cold Flow",
                severity=self.metadata.severity,
                file_path=context.file_path,
                line_number=collect_lines[0],
                code_snippet=f"共 {collect_count} 处 collect",
                suggestion="使用 shareIn 或 stateIn 转换为 Hot Flow"
            ))

        return findings


class ChannelFlowNoAwaitCloseRule(UnifiedRule):
    """
    channelFlow 缺少 awaitClose 检测规则

    使用 channelFlow 但未调用 awaitClose，当 Flow 取消时无法正确清理资源，
    可能导致内存泄漏。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="channel_flow_no_awaitclose",
            name="channelFlow 缺少 awaitClose",
            description="使用 channelFlow 但未调用 awaitClose，当 Flow 取消时无法正确清理资源，可能导致内存泄漏",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "flow", "channel", "resource", "leak"],
            weight=0.9,
            suggested_fix="在 channelFlow 中添加 awaitClose { } 块，确保在 Flow 取消时清理资源",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测 channelFlow 缺少 awaitClose"""
        findings = []

        lines = context.get_lines()
        in_channel_flow = False
        channel_start_line = 0
        has_awaitclose = False

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            # 检测 channelFlow 开始
            if "channelflow {" in line_lower:
                in_channel_flow = True
                channel_start_line = i
                has_awaitclose = False

            # 在 channelFlow 内部
            if in_channel_flow:
                # 检测 awaitClose
                if "awaitclose" in line_lower:
                    has_awaitclose = True

                # 检测 channelFlow 结束（简化处理）
                if line.strip() == "}" and in_channel_flow:
                    if not has_awaitclose:
                        findings.append(Finding(
                            rule_id=self.metadata.id,
                            message="channelFlow 缺少 awaitClose",
                            severity=self.metadata.severity,
                            file_path=context.file_path,
                            line_number=channel_start_line,
                            code_snippet=f"第 {channel_start_line} 行 channelFlow",
                            suggestion="添加 awaitClose { } 块"
                        ))
                    in_channel_flow = False

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        NestedLaunchInCollectRule(),
        LaunchInsideFlowRule(),
        MultipleCollectsRule(),
        ChannelFlowNoAwaitCloseRule(),
    ]
