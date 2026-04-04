"""
Rule: hardcoded_string
Detection: Hardcoded strings in UI code that should be in resources
"""
from typing import List
import re
from ..interfaces import RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="hardcoded_string",
    name="Hardcoded string in UI code",
    description="UI strings should be defined in resources for internationalization",
    severity=RuleSeverity.MINOR,
    category=RuleCategory.BEST_PRACTICE,
    tags=["android", "kotlin", "i18n", "resources"],
    suggested_fix="Move string to res/values/strings.xml and reference with R.string.name",
    weight=0.8
)
def hardcoded_string_rule(context: RuleContext) -> List[Finding]:
    """
    Detect hardcoded strings in UI-related code.

    Hardcoded strings make internationalization difficult.
    Should use string resources instead.
    """
    findings = []
    lines = context.get_lines()

    # Check if this is UI code
    is_ui_code = any(keyword in ' '.join(lines[:30]) for keyword in
                     ['@Composable', 'Text(', 'Button(', 'setContentView', 'LayoutInflater'])

    if not is_ui_code:
        return findings

    # Pattern for hardcoded strings (double quotes with content)
    string_pattern = re.compile(r'"([^"]{3,})"')  # At least 3 chars to avoid noise

    excluded_patterns = [
        r'Log\.[vdiew]\s*\(',
        r'Timber\.[vdiew]\s*\(',
        r'//',
        r'println\s*\(',
        r'import\s+',
        r'package\s+',
        r'tag\s*=',
        r'BuildConfig\.',
    ]

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip excluded lines
        if any(re.search(pattern, stripped) for pattern in excluded_patterns):
            continue

        # Skip string resources access
        if 'R.string.' in stripped or 'stringResource(' in stripped:
            continue

        matches = string_pattern.findall(stripped)
        for match in matches:
            # Filter out non-text strings (URLs, file paths, keys, etc.)
            if _is_likely_ui_string(match):
                findings.append(Finding(
                    rule_id="hardcoded_string",
                    message=f"Hardcoded string should be in resources: \"{match[:30]}{'...' if len(match) > 30 else ''}\"",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line.strip()[:100],
                    suggestion=f"Add to strings.xml: <string name=\"text_name\">{match}</string>"
                ))
                break  # One finding per line is enough

    return findings


def _is_likely_ui_string(text: str) -> bool:
    """Check if a string is likely a UI text (not URL, path, key, etc.)."""
    # Exclude URLs
    if text.startswith('http://') or text.startswith('https://'):
        return False
    # Exclude file paths
    if '/' in text and '.' in text:
        return False
    # Exclude JSON keys or similar
    if text.islower() and '_' in text:
        return False
    # Exclude single words that look like constants
    if text.isupper() and '_' in text:
        return False
    # Exclude camelCase keys
    if not text[0].isupper() and any(c.isupper() for c in text[1:]):
        return False
    # Should have some letters
    if not any(c.isalpha() for c in text):
        return False
    return True
