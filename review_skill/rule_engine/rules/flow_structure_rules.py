"""
FlowRule - 
"""
import re
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="nested_launch_in_collect",
    name="collectLatest 内部嵌套 launch",
    description="在 collectLatest 回调内部使用 launch 会导致并发问题，collectLatest 的取消语义可能无法正确传递",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.CONCURRENCY,
    tags=["android", "kotlin", "flow", "collect", "launch", "concurrency"],
    suggested_fix="避免在 collectLatest 内部使用 launch，直接使用 collectLatest 的挂起特性处理异步操作",
    weight=0.8
)
def nested_launch_in_collect_rule(context: RuleContext) -> List[Finding]:
    """collectLatestlaunch"""
    findings = []
    
    lines = context.get_lines()
    in_collect_latest = False
    collect_start_line = 0
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # collectLatest
        if "collectlatest" in line_lower and "{" in line_lower:
            in_collect_latest = True
            collect_start_line = i
        
        # collectLatest
        if in_collect_latest:
            # launch
            if "launch" in line_lower and "{" in line_lower:
                # Checklaunch
                if not any(op in line_lower for op in ["viewmodelscope.launch", "lifecyclescope.launch", "globalscope.launch"]):
                    findings.append(Finding(
                        rule_id="nested_launch_in_collect",
                        message="collectLatestlaunch",
                        severity=RuleSeverity.MAJOR,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion="collectLatestlaunch，"
                    ))
            
            # collectLatest
            if line.strip() == "}" and in_collect_latest:
                # 
                in_collect_latest = False
    
    return findings


@rule(
    rule_id="launch_inside_flow",
    name="flow {} 构建器中使用 launch",
    description="在 flow { } 构建器中使用 launch 会破坏流的可组合性和背压处理，应该使用 callbackFlow 或 channelFlow",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.CONCURRENCY,
    tags=["android", "kotlin", "flow", "launch", "concurrency", "builder"],
    suggested_fix="使用 callbackFlow 或 channelFlow 替代 flow { } 构建器中的 launch",
    weight=1.0
)
def launch_inside_flow_rule(context: RuleContext) -> List[Finding]:
    """flow builderlaunch"""
    findings = []
    
    lines = context.get_lines()
    in_flow_builder = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # flow builder
        if "flow {" in line_lower:
            in_flow_builder = True
        
        # flow builder
        if in_flow_builder:
            # launch
            if "launch" in line_lower and "{" in line_lower:
                findings.append(Finding(
                    rule_id="launch_inside_flow",
                    message="flow builderlaunch",
                    severity=RuleSeverity.CRITICAL,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="callbackFlowchannelFlow，"
                ))
            
            # flow builder
            if line.strip() == "}" and in_flow_builder:
                in_flow_builder = False
    
    return findings


@rule(
    rule_id="multiple_collects",
    name="多次收集同一个 Cold Flow",
    description="多个地方收集同一个 Cold Flow 会导致重复执行上游操作，浪费资源",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "flow", "collect", "cold_flow"],
    suggested_fix="使用 shareIn 或 stateIn 将 Cold Flow 转换为 Hot Flow，避免重复执行",
    weight=0.5
)
def multiple_collects_rule(context: RuleContext) -> List[Finding]:
    """collectFlow"""
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
        # collect
        findings.append(Finding(
            rule_id="multiple_collects",
            message=f"{collect_count}collect，",
            severity=RuleSeverity.MINOR,
            file_path=context.file_path,
            line_number=collect_lines[0],
            code_snippet=f"{collect_count}collect",
            suggestion="shareInstateInConvert，collect"
        ))
    
    return findings


@rule(
    rule_id="channel_flow_no_awaitclose",
    name="channelFlow 缺少 awaitClose",
    description="使用 channelFlow 但未调用 awaitClose，当 Flow 取消时无法正确清理资源，可能导致内存泄漏",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "channel", "resource", "leak"],
    suggested_fix="在 channelFlow 中添加 awaitClose { } 块，确保在 Flow 取消时清理资源",
    weight=0.9
)
def channel_flow_no_awaitclose_rule(context: RuleContext) -> List[Finding]:
    """channelFlowawaitClose"""
    findings = []
    
    lines = context.get_lines()
    in_channel_flow = False
    channel_start_line = 0
    has_awaitclose = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # channelFlow
        if "channelflow {" in line_lower:
            in_channel_flow = True
            channel_start_line = i
            has_awaitclose = False
        
        # channelFlow
        if in_channel_flow:
            # awaitClose
            if "awaitclose" in line_lower:
                has_awaitclose = True
            
            # channelFlow
            if line.strip() == "}" and in_channel_flow:
                if not has_awaitclose:
                    findings.append(Finding(
                        rule_id="channel_flow_no_awaitclose",
                        message="channelFlowawaitClose",
                        severity=RuleSeverity.MAJOR,
                        file_path=context.file_path,
                        line_number=channel_start_line,
                        code_snippet=f"{channel_start_line}channelFlow",
                        suggestion="channelFlowAddawaitClose { }"
                    ))
                in_channel_flow = False
    
    return findings


__all__ = [
    "nested_launch_in_collect_rule",
    "launch_inside_flow_rule",
    "multiple_collects_rule",
    "channel_flow_no_awaitclose_rule"
]