"""
Rule: hilt_module_injection
Detection: @Module classes missing @InstallIn annotation
"""
from typing import List
from ..interfaces import RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="hilt_module_injection",
    name="Hilt Module missing @InstallIn",
    description="@Module classes must have @InstallIn to specify which Hilt component to install in",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.CORRECTNESS,
    tags=["android", "kotlin", "hilt", "di", "dagger"],
    suggested_fix="Add @InstallIn annotation: @InstallIn(SingletonComponent::class) or @InstallIn(ActivityComponent::class)",
    weight=1.0
)
def hilt_module_injection_rule(context: RuleContext) -> List[Finding]:
    """
    Detect @Module classes that are missing @InstallIn annotation.

    Hilt requires @InstallIn to know which component to install the module in.
    Missing @InstallIn means the module won't be used.
    """
    findings = []
    lines = context.get_lines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Find @Module annotation
        if '@Module' in stripped and '@InstallIn' not in stripped:
            # Check next few lines for @InstallIn
            has_installin = False
            for j in range(i + 1, min(i + 5, len(lines) + 1)):
                if '@InstallIn' in lines[j - 1]:
                    has_installin = True
                    break
                # If we hit the class declaration, stop looking
                if 'class ' in lines[j - 1]:
                    break

            if not has_installin:
                findings.append(Finding(
                    rule_id="hilt_module_injection",
                    message="@Module class missing @InstallIn annotation - module will not be installed",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion="Add @InstallIn(SingletonComponent::class) for app-wide dependencies or @InstallIn(ActivityComponent::class) for activity-scoped"
                ))

    return findings
