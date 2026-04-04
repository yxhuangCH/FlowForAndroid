"""
Rule: intent_extra_key
Detection: Intent extra keys as string literals instead of constants
"""
from typing import List
import re
from ..interfaces import RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="intent_extra_key",
    name="Intent extra key not defined as constant",
    description="Intent extra keys should be defined as constants to prevent typos and enable refactoring",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "intent", "constants"],
    suggested_fix="Define keys as companion object constants: companion object { const val EXTRA_KEY = \"extra_key\" }",
    weight=0.9
)
def intent_extra_key_rule(context: RuleContext) -> List[Finding]:
    """
    Detect string literal keys in Intent putExtra/getExtra calls.

    Using string literals for Intent keys is error-prone.
    Should use constants to prevent typos and enable IDE refactoring.
    """
    findings = []
    lines = context.get_lines()

    # Pattern for Intent extra operations with string literals
    intent_patterns = [
        (r'\.putExtra\s*\(\s*"([^"]+)"', "putExtra"),
        (r'\.getStringExtra\s*\(\s*"([^"]+)"', "getStringExtra"),
        (r'\.getIntExtra\s*\(\s*"([^"]+)"', "getIntExtra"),
        (r'\.getBooleanExtra\s*\(\s*"([^"]+)"', "getBooleanExtra"),
        (r'\.getLongExtra\s*\(\s*"([^"]+)"', "getLongExtra"),
        (r'\.getParcelableExtra\s*\(\s*"([^"]+)"', "getParcelableExtra"),
        (r'\.getSerializableExtra\s*\(\s*"([^"]+)"', "getSerializableExtra"),
        (r'\.getBundleExtra\s*\(\s*"([^"]+)"', "getBundleExtra"),
        (r'\.hasExtra\s*\(\s*"([^"]+)"', "hasExtra"),
        (r'\.removeExtra\s*\(\s*"([^"]+)"', "removeExtra"),
    ]

    # Common safe keys (Android framework keys)
    safe_keys = {'android.', 'androidx.', 'com.android.'}

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        for pattern, operation in intent_patterns:
            match = re.search(pattern, stripped)
            if match:
                key = match.group(1)

                # Skip if it's already a constant reference
                if not key:
                    continue

                # Skip Android framework keys
                if any(key.startswith(prefix) for prefix in safe_keys):
                    continue

                findings.append(Finding(
                    rule_id="intent_extra_key",
                    message=f"Intent extra key \"{key}\" should be defined as constant",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion=f"Define constant: companion object {{ const val EXTRA_{key.upper().replace('.', '_')} = \"{key}\" }}"
                ))
                break

    return findings
