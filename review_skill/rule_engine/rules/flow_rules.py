"""
Flow相关规则 - 迁移到新引擎格式
"""
import re
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="flowon_main_dispatcher",
    name="Flow在主线程flowOn",
    description="flowOn(Dispatchers.Main)可能导致上游操作在主线程执行",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "flow", "coroutine", "main_thread"],
    suggested_fix="将flowOn移到适当的调度器，如Dispatchers.IO或Dispatchers.Default",
    weight=1.0
)
def flowon_main_dispatcher_rule(context: RuleContext) -> List[Finding]:
    """检测flowOn(Dispatchers.Main)使用"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        # 检测flowOn(Dispatchers.Main)模式
        if "flowon(" in line_lower and "dispatchers.main" in line_lower:
            findings.append(Finding(
                rule_id="flowon_main_dispatcher",
                message="flowOn(Dispatchers.Main)可能导致上游操作在主线程执行",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="将flowOn移到适当的调度器，如Dispatchers.IO或Dispatchers.Default"
            ))
    
    return findings


@rule(
    rule_id="missing_flowon_for_io",
    name="Flow执行IO操作未指定flowOn",
    description="Flow执行IO操作但未明确指定flowOn调度器",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "flow", "io", "dispatcher"],
    suggested_fix="为IO操作明确指定flowOn(Dispatchers.IO)",
    weight=0.9
)
def missing_flowon_for_io_rule(context: RuleContext) -> List[Finding]:
    """检测Flow执行IO操作但缺少flowOn"""
    findings = []
    
    code = context.code.lower()
    has_flow_builder = "flow {" in code
    has_io_operation = any(keyword in code for keyword in ["repository", "database", "file", "network", "read", "write"])
    has_flowon = "flowon" in code
    
    if has_flow_builder and has_io_operation and not has_flowon:
        # 找到具体行
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if "flow {" in line_lower:
                findings.append(Finding(
                    rule_id="missing_flowon_for_io",
                    message="Flow执行IO操作但未明确指定flowOn调度器",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="为IO操作明确指定flowOn(Dispatchers.IO)"
                ))
                break
    
    return findings


@rule(
    rule_id="channel_flow_usage",
    name="channelFlow使用检测",
    description="channelFlow需要额外关注结构化并发和取消",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.CONCURRENCY,
    tags=["android", "kotlin", "flow", "channel", "concurrency"],
    suggested_fix="验证channelFlow的结构化并发和取消处理",
    weight=0.8
)
def channel_flow_usage_rule(context: RuleContext) -> List[Finding]:
    """检测channelFlow使用"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "channelflow" in line.lower():
            findings.append(Finding(
                rule_id="channel_flow_usage",
                message="channelFlow需要额外关注结构化并发和取消",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="验证channelFlow的结构化并发和取消处理"
            ))
    
    return findings


@rule(
    rule_id="eager_sharing_detected",
    name="Eager共享检测",
    description="SharingStarted.Eagerly会保持上游活跃，可能导致资源浪费",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "flow", "sharing", "resource"],
    suggested_fix="考虑使用SharingStarted.Lazily或SharingStarted.WhileSubscribed",
    weight=0.8
)
def eager_sharing_detected_rule(context: RuleContext) -> List[Finding]:
    """检测SharingStarted.Eagerly使用"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "sharingstarted.eagerly" in line.lower():
            findings.append(Finding(
                rule_id="eager_sharing_detected",
                message="SharingStarted.Eagerly会保持上游活跃，可能导致资源浪费",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="考虑使用SharingStarted.Lazily或SharingStarted.WhileSubscribed"
            ))
    
    return findings


@rule(
    rule_id="mutable_stateflow_exposed",
    name="MutableStateFlow暴露检测",
    description="MutableStateFlow不应公开暴露，应通过asStateFlow转换为只读版本",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "flow", "stateflow", "encapsulation"],
    suggested_fix="将MutableStateFlow设为private，通过asStateFlow暴露只读版本",
    weight=0.9
)
def mutable_stateflow_exposed_rule(context: RuleContext) -> List[Finding]:
    """检测公开暴露的MutableStateFlow"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        line_stripped = line.strip()
        # 检测MutableStateFlow赋值且不是private
        if "mutablestateflow" in line_lower and "private" not in line_lower:
            # 检查是否是变量声明
            if line_stripped.startswith("val ") or line_stripped.startswith("var "):
                findings.append(Finding(
                    rule_id="mutable_stateflow_exposed",
                    message="MutableStateFlow不应公开暴露，应通过asStateFlow转换为只读版本",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="将MutableStateFlow设为private，通过asStateFlow暴露只读版本"
                ))
    
    return findings


__all__ = [
    "flowon_main_dispatcher_rule",
    "missing_flowon_for_io_rule",
    "channel_flow_usage_rule",
    "eager_sharing_detected_rule",
    "mutable_stateflow_exposed_rule"
]