"""
Rule: memory_leak_static_context
Detection: Static fields holding Activity/View/Context references
"""
from typing import List
import re
from ..interfaces import RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="memory_leak_static_context",
    name="Static Context reference",
    description="Static fields should not hold Activity, View, or Context references to avoid memory leaks",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "memory-leak", "static"],
    suggested_fix="Remove static modifier or use Application Context instead of Activity/View Context",
    weight=1.5
)
def memory_leak_static_context_rule(context: RuleContext) -> List[Finding]:
    """
    Detect static fields that hold Context, Activity, or View references.

    Static fields live for the entire application lifecycle, holding Activity/View
    references prevents garbage collection and causes memory leaks.
    """
    findings = []
    lines = context.get_lines()

    # Track if we're inside a companion object
    in_companion_object = False
    companion_brace_depth = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track companion object scope
        if 'companion object' in stripped:
            in_companion_object = True
            companion_brace_depth = stripped.count('{') - stripped.count('}')
            continue

        if in_companion_object:
            companion_brace_depth += stripped.count('{') - stripped.count('}')
            if companion_brace_depth <= 0 and '{' not in stripped:
                in_companion_object = False

            # Check for Context/Activity/View references in companion object
            if any(keyword in stripped for keyword in ['val ', 'var ', 'lateinit']):
                if any(type_name in stripped for type_name in ['Context', 'Activity', 'View', 'Fragment']):
                    # Skip Application Context which is safe
                    is_application_context = (
                        'Application' in stripped and 'Context' not in stripped.replace('Application', '')
                    ) or (
                        any(name in stripped for name in ['appContext:', 'applicationContext:', 'appContext ', 'applicationContext '])
                    ) or (
                        re.search(r':\s*Application\b', stripped) is not None
                    )

                    if not is_application_context:
                        findings.append(Finding(
                            rule_id="memory_leak_static_context",
                            message="Static field should not hold Activity/View/Context reference (causes memory leak)",
                            severity=RuleSeverity.CRITICAL,
                            file_path=context.file_path,
                            line_number=i,
                            code_snippet=line.strip(),
                            suggestion="Use Application Context or remove static modifier, or use WeakReference"
                        ))

        # Check @JvmStatic annotated fields
        if '@JvmStatic' in stripped:
            if i < len(lines):
                next_line = lines[i].strip()
                if any(type_name in next_line for type_name in ['Context', 'Activity', 'View', 'Fragment']):
                    if 'Application' not in next_line:
                        findings.append(Finding(
                            rule_id="memory_leak_static_context",
                            message="@JvmStatic field should not hold Activity/View/Context reference (causes memory leak)",
                            severity=RuleSeverity.CRITICAL,
                            file_path=context.file_path,
                            line_number=i,
                            code_snippet=next_line,
                            suggestion="Use Application Context or remove @JvmStatic, or use WeakReference"
                        ))

    return findings
