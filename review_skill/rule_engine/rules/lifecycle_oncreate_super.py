"""
Rule: lifecycle_oncreate_super
Detection: Lifecycle methods missing super calls
"""
from typing import List
import re
from ..interfaces import RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="lifecycle_oncreate_super",
    name="Missing super call in lifecycle method",
    description="Lifecycle methods like onCreate, onResume should call super method",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.CORRECTNESS,
    tags=["android", "kotlin", "lifecycle", "super-call"],
    suggested_fix="Add super.onCreate(savedInstanceState) / super.onResume() etc. at the beginning of the method",
    weight=1.2
)
def lifecycle_oncreate_super_rule(context: RuleContext) -> List[Finding]:
    """
    Detect lifecycle methods that don't call super.

    Android lifecycle methods require super calls for proper framework operation.
    Missing super calls can cause crashes or unexpected behavior.
    """
    findings = []
    lines = context.get_lines()

    # Lifecycle methods that require super calls
    lifecycle_methods = {
        'onCreate': 'super.onCreate',
        'onResume': 'super.onResume',
        'onPause': 'super.onPause',
        'onStop': 'super.onStop',
        'onDestroy': 'super.onDestroy',
        'onStart': 'super.onStart',
        'onRestart': 'super.onRestart',
        'onSaveInstanceState': 'super.onSaveInstanceState',
        'onRestoreInstanceState': 'super.onRestoreInstanceState',
        'onActivityResult': 'super.onActivityResult',
        'onRequestPermissionsResult': 'super.onRequestPermissionsResult',
        'onAttach': 'super.onAttach',
        'onDetach': 'super.onDetach',
        'onCreateView': 'super.onCreateView',
        'onViewCreated': 'super.onViewCreated',
        'onDestroyView': 'super.onDestroyView',
    }

    # Track method ranges
    in_lifecycle_method = None
    method_start_line = 0
    brace_depth = 0
    found_super_call = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Detect lifecycle method start
        for method_name, super_call in lifecycle_methods.items():
            # Match: override fun onCreate(savedInstanceState: Bundle?)
            pattern = rf'override\s+fun\s+{method_name}\s*\('
            if re.search(pattern, stripped):
                in_lifecycle_method = method_name
                method_start_line = i
                brace_depth = stripped.count('{') - stripped.count('}')
                found_super_call = False
                break

        if in_lifecycle_method:
            # Check for super call
            if lifecycle_methods[in_lifecycle_method] in stripped:
                found_super_call = True

            # Track braces
            brace_depth += stripped.count('{') - stripped.count('}')

            # Method ended
            if brace_depth <= 0 and i > method_start_line:
                if not found_super_call:
                    findings.append(Finding(
                        rule_id="lifecycle_oncreate_super",
                        message=f"{in_lifecycle_method}() must call {lifecycle_methods[in_lifecycle_method]}()",
                        severity=RuleSeverity.MAJOR,
                        file_path=context.file_path,
                        line_number=method_start_line,
                        code_snippet=lines[method_start_line - 1].strip(),
                        suggestion=f"Add {lifecycle_methods[in_lifecycle_method]}(...) as the first statement"
                    ))
                in_lifecycle_method = None

    return findings
