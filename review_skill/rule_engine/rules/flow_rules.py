"""
Flow-related rules - Migrated to new engine format
"""
import re
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="flowon_main_dispatcher",
    name="Flow flowOn on Main Thread",
    description="flowOn(Dispatchers.Main) may cause upstream operations to execute on the main thread",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "flow", "coroutine", "main_thread"],
    suggested_fix="Move flowOn to an appropriate dispatcher, such as Dispatchers.IO or Dispatchers.Default",
    weight=1.0
)
def flowon_main_dispatcher_rule(context: RuleContext) -> List[Finding]:
    """Detect flowOn(Dispatchers.Main) usage"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()
        # Detect flowOn(Dispatchers.Main) pattern
        if "flowon(" in line_lower and "dispatchers.main" in line_lower:
            findings.append(Finding(
                rule_id="flowon_main_dispatcher",
                message="flowOn(Dispatchers.Main) may cause upstream operations to execute on the main thread",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="Move flowOn to an appropriate dispatcher, such as Dispatchers.IO or Dispatchers.Default"
            ))
    
    return findings


@rule(
    rule_id="missing_flowon_for_io",
    name="Flow IO Operation Missing flowOn",
    description="Flow performs IO operations but does not explicitly specify a flowOn dispatcher",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "flow", "io", "dispatcher"],
    suggested_fix="Explicitly specify flowOn(Dispatchers.IO) for IO operations",
    weight=0.9
)
def missing_flowon_for_io_rule(context: RuleContext) -> List[Finding]:
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
                    rule_id="missing_flowon_for_io",
                    message="Flow performs IO operations but does not explicitly specify a flowOn dispatcher",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="Explicitly specify flowOn(Dispatchers.IO) for IO operations"
                ))
                break
    
    return findings


@rule(
    rule_id="channel_flow_usage",
    name="channelFlow Usage Detection",
    description="channelFlow requires extra attention to structured concurrency and cancellation",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.CONCURRENCY,
    tags=["android", "kotlin", "flow", "channel", "concurrency"],
    suggested_fix="Verify structured concurrency and cancellation handling for channelFlow",
    weight=0.8
)
def channel_flow_usage_rule(context: RuleContext) -> List[Finding]:
    """Detect channelFlow usage"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "channelflow" in line.lower():
            findings.append(Finding(
                rule_id="channel_flow_usage",
                message="channelFlow requires extra attention to structured concurrency and cancellation",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="Verify structured concurrency and cancellation handling for channelFlow"
            ))
    
    return findings


@rule(
    rule_id="eager_sharing_detected",
    name="Eager Sharing Detection",
    description="SharingStarted.Eagerly keeps the upstream active, which may lead to resource waste",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "flow", "sharing", "resource"],
    suggested_fix="Consider using SharingStarted.Lazily or SharingStarted.WhileSubscribed",
    weight=0.8
)
def eager_sharing_detected_rule(context: RuleContext) -> List[Finding]:
    """Detect SharingStarted.Eagerly usage"""
    findings = []
    
    lines = context.get_lines()
    for i, line in enumerate(lines, 1):
        if "sharingstarted.eagerly" in line.lower():
            findings.append(Finding(
                rule_id="eager_sharing_detected",
                message="SharingStarted.Eagerly keeps the upstream active, which may lead to resource waste",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line,
                suggestion="Consider using SharingStarted.Lazily or SharingStarted.WhileSubscribed"
            ))
    
    return findings


@rule(
    rule_id="mutable_stateflow_exposed",
    name="MutableStateFlow Exposure Detection",
    description="MutableStateFlow should not be publicly exposed; use asStateFlow to expose a read-only version",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "flow", "stateflow", "encapsulation"],
    suggested_fix="Make MutableStateFlow private and expose a read-only version via asStateFlow",
    weight=0.9
)
def mutable_stateflow_exposed_rule(context: RuleContext) -> List[Finding]:
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
                    rule_id="mutable_stateflow_exposed",
                    message="MutableStateFlow should not be publicly exposed; use asStateFlow to expose a read-only version",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="Make MutableStateFlow private and expose a read-only version via asStateFlow"
                ))
    
    return findings


__all__ = [
    "flowon_main_dispatcher_rule",
    "missing_flowon_for_io_rule",
    "channel_flow_usage_rule",
    "eager_sharing_detected_rule",
    "mutable_stateflow_exposed_rule"
]
