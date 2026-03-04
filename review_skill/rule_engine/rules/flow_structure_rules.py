"""
Flow结构相关规则 - 迁移到新引擎格式
"""
import re
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="nested_launch_in_collect",
    name="collectLatest内部嵌套launch",
    description="collectLatest内部嵌套launch可能破坏结构化并发",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.CONCURRENCY,
    tags=["android", "kotlin", "flow", "collect", "launch", "concurrency"],
    suggested_fix="避免在collectLatest内部直接使用launch，考虑使用流操作符",
    weight=0.8
)
def nested_launch_in_collect_rule(context: RuleContext) -> List[Finding]:
    """检测collectLatest内部嵌套launch"""
    findings = []
    
    lines = context.get_lines()
    in_collect_latest = False
    collect_start_line = 0
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # 检测collectLatest开始
        if "collectlatest" in line_lower and "{" in line_lower:
            in_collect_latest = True
            collect_start_line = i
        
        # 如果在collectLatest块内
        if in_collect_latest:
            # 检测嵌套的launch
            if "launch" in line_lower and "{" in line_lower:
                # 检查是否为非嵌套的简单launch
                if not any(op in line_lower for op in ["viewmodelscope.launch", "lifecyclescope.launch", "globalscope.launch"]):
                    findings.append(Finding(
                        rule_id="nested_launch_in_collect",
                        message="collectLatest内部嵌套launch可能破坏结构化并发",
                        severity=RuleSeverity.MAJOR,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion="避免在collectLatest内部直接使用launch，考虑使用流操作符"
                    ))
            
            # 检测collectLatest块结束
            if line.strip() == "}" and in_collect_latest:
                # 简单的块结束检测
                in_collect_latest = False
    
    return findings


@rule(
    rule_id="launch_inside_flow",
    name="flow builder内部使用launch",
    description="flow builder内部使用launch会破坏结构化并发",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.CONCURRENCY,
    tags=["android", "kotlin", "flow", "launch", "concurrency", "builder"],
    suggested_fix="使用callbackFlow或channelFlow替代，或重构逻辑",
    weight=1.0
)
def launch_inside_flow_rule(context: RuleContext) -> List[Finding]:
    """检测flow builder内部使用launch"""
    findings = []
    
    lines = context.get_lines()
    in_flow_builder = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # 检测flow builder开始
        if "flow {" in line_lower:
            in_flow_builder = True
        
        # 如果在flow builder内部
        if in_flow_builder:
            # 检测launch
            if "launch" in line_lower and "{" in line_lower:
                findings.append(Finding(
                    rule_id="launch_inside_flow",
                    message="flow builder内部使用launch会破坏结构化并发",
                    severity=RuleSeverity.CRITICAL,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="使用callbackFlow或channelFlow替代，或重构逻辑"
                ))
            
            # 检测flow builder结束
            if line.strip() == "}" and in_flow_builder:
                in_flow_builder = False
    
    return findings


@rule(
    rule_id="multiple_collects",
    name="多次collect同一Flow",
    description="多次collect同一Flow可能导致冷流行为问题",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "flow", "collect", "cold_flow"],
    suggested_fix="使用shareIn或stateIn转换为热流，或重构为单一collect",
    weight=0.5
)
def multiple_collects_rule(context: RuleContext) -> List[Finding]:
    """检测多次collect同一Flow"""
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
        # 如果同一个文件中有多个collect
        findings.append(Finding(
            rule_id="multiple_collects",
            message=f"检测到{collect_count}次collect调用，可能导致冷流行为问题",
            severity=RuleSeverity.MINOR,
            file_path=context.file_path,
            line_number=collect_lines[0],
            code_snippet=f"文件中有{collect_count}处collect调用",
            suggestion="使用shareIn或stateIn转换为热流，或重构为单一collect"
        ))
    
    return findings


@rule(
    rule_id="channel_flow_no_awaitclose",
    name="channelFlow缺少awaitClose",
    description="channelFlow未使用awaitClose可能导致资源泄漏",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "flow", "channel", "resource", "leak"],
    suggested_fix="在channelFlow末尾添加awaitClose { }",
    weight=0.9
)
def channel_flow_no_awaitclose_rule(context: RuleContext) -> List[Finding]:
    """检测channelFlow缺少awaitClose"""
    findings = []
    
    lines = context.get_lines()
    in_channel_flow = False
    channel_start_line = 0
    has_awaitclose = False
    
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # 检测channelFlow开始
        if "channelflow {" in line_lower:
            in_channel_flow = True
            channel_start_line = i
            has_awaitclose = False
        
        # 如果在channelFlow内部
        if in_channel_flow:
            # 检测awaitClose
            if "awaitclose" in line_lower:
                has_awaitclose = True
            
            # 检测channelFlow结束
            if line.strip() == "}" and in_channel_flow:
                if not has_awaitclose:
                    findings.append(Finding(
                        rule_id="channel_flow_no_awaitclose",
                        message="channelFlow未使用awaitClose可能导致资源泄漏",
                        severity=RuleSeverity.MAJOR,
                        file_path=context.file_path,
                        line_number=channel_start_line,
                        code_snippet=f"从第{channel_start_line}行开始的channelFlow",
                        suggestion="在channelFlow末尾添加awaitClose { }"
                    ))
                in_channel_flow = False
    
    return findings


__all__ = [
    "nested_launch_in_collect_rule",
    "launch_inside_flow_rule",
    "multiple_collects_rule",
    "channel_flow_no_awaitclose_rule"
]