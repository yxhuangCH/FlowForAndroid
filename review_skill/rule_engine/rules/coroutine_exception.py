"""
Rule: coroutine_exception
Detection: Coroutine launches without exception handling
"""
from typing import List
import re
from ..interfaces import RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="coroutine_exception",
    name="Missing coroutine exception handling",
    description="Top-level coroutine launch should have exception handling to prevent silent failures",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.CORRECTNESS,
    tags=["android", "kotlin", "coroutine", "exception-handling"],
    suggested_fix="Add try-catch block or CoroutineExceptionHandler to handle exceptions",
    weight=1.2
)
def coroutine_exception_rule(context: RuleContext) -> List[Finding]:
    """
    Detect coroutine launches without proper exception handling.

    Top-level launch blocks without try-catch or CoroutineExceptionHandler
    may fail silently and make debugging difficult.
    """
    findings = []
    lines = context.get_lines()

    # Find all launch/async blocks
    launch_pattern = re.compile(r'(lifecycleScope|viewModelScope|GlobalScope|coroutineScope)\.(launch|async)\s*\{')

    for i, line in enumerate(lines, 1):
        match = launch_pattern.search(line)
        if match:
            scope_type = match.group(1)
            launch_type = match.group(2)

            # Check if this line or nearby lines have exception handling
            has_exception_handling = _has_exception_handling(lines, i)

            if not has_exception_handling:
                findings.append(Finding(
                    rule_id="coroutine_exception",
                    message=f"{scope_type}.{launch_type} should have exception handling",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion=f"Add try-catch block or CoroutineExceptionHandler: {scope_type}.launch {{ try {{ ... }} catch(e: Exception) {{ /* handle */ }} }}"
                ))

    return findings


def _has_exception_handling(lines: List[str], line_number: int) -> bool:
    """Check if coroutine at line_number has exception handling."""
    # Check same line for handler
    line = lines[line_number - 1]
    if 'CoroutineExceptionHandler' in line or 'try' in line:
        return True

    # Look ahead a few lines for try block
    for i in range(line_number, min(len(lines), line_number + 3)):
        if 'try' in lines[i - 1]:
            return True

    return False
