"""
Rule: fragment_arg_constructor
Detection: Fragment with parameterized constructors
"""
from typing import List
import re
from ..interfaces import RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="fragment_arg_constructor",
    name="Fragment has parameterized constructor",
    description="Fragment should have only default constructor to prevent crashes on configuration changes",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE,
    tags=["android", "kotlin", "fragment", "configuration-change"],
    suggested_fix="Remove constructor parameters, use arguments Bundle with Fragment.setArguments() and Fragment.getArguments() instead",
    weight=1.3
)
def fragment_arg_constructor_rule(context: RuleContext) -> List[Finding]:
    """
    Detect Fragments with parameterized constructors.

    When Android recreates a Fragment (configuration change, process death),
    it uses the default constructor. Parameterized constructors cause crashes.
    """
    findings = []
    lines = context.get_lines()

    # Check if this is a Fragment class
    is_fragment = any('class' in line and 'Fragment' in line for line in lines[:5])
    if not is_fragment:
        return findings

    # Pattern to detect class with constructor parameters
    # Matches: class MyFragment(val param: String) : Fragment()
    # Or: class MyFragment constructor(val param: String) : Fragment()
    constructor_pattern = re.compile(
        r'class\s+(\w+)\s*(?:constructor\s*)?\(([^)]*val\s+[^)]+)\)',
        re.IGNORECASE
    )

    for i, line in enumerate(lines, 1):
        match = constructor_pattern.search(line)
        if match:
            class_name = match.group(1)

            findings.append(Finding(
                rule_id="fragment_arg_constructor",
                message=f"Fragment '{class_name}' has parameterized constructor - will crash on configuration change",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line.strip(),
                suggestion="Use arguments Bundle: class MyFragment : Fragment() { companion object { fun newInstance(arg: String) = MyFragment().apply { arguments = Bundle().apply { putString('key', arg) } } } }"
            ))

    return findings
