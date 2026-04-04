"""
Rule: mutable_livedata_exposed
Detection: Public MutableLiveData fields that should be private
"""
from typing import List
import re
from ..interfaces import RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="mutable_livedata_exposed",
    name="MutableLiveData exposed publicly",
    description="MutableLiveData should be private, expose immutable LiveData to observers",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.CORRECTNESS,
    tags=["android", "kotlin", "livedata", "architecture", "encapsulation"],
    suggested_fix="Make MutableLiveData private and expose LiveData: private val _data = MutableLiveData<T>(); val data: LiveData<T> = _data",
    weight=1.2
)
def mutable_livedata_exposed_rule(context: RuleContext) -> List[Finding]:
    """
    Detect public MutableLiveData fields.

    Exposing MutableLiveData allows external modification, breaking encapsulation.
    Should use private MutableLiveData with public LiveData backing property.
    """
    findings = []
    lines = context.get_lines()

    # Pattern for public MutableLiveData declarations
    public_mutable_pattern = re.compile(
        r'^(\s*)(val|var|lateinit\s+var)\s+(\w+)\s*(:\s*MutableLiveData|\s*=\s*MutableLiveData)',
        re.IGNORECASE
    )

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip if private
        if 'private' in stripped:
            continue

        # Skip if internal/protected with underscore prefix (convention for backing fields)
        if re.match(r'.*_(\w+)', stripped):
            continue

        match = public_mutable_pattern.search(stripped)
        if match:
            field_name = match.group(3)

            # Skip if it follows the underscore convention (_data)
            if field_name.startswith('_'):
                continue

            findings.append(Finding(
                rule_id="mutable_livedata_exposed",
                message=f"MutableLiveData field '{field_name}' should be private",
                severity=RuleSeverity.MAJOR,
                file_path=context.file_path,
                line_number=i,
                code_snippet=line.strip(),
                suggestion=f"Use: private val _{field_name} = MutableLiveData<T>(); val {field_name}: LiveData<T> = _{field_name}"
            ))

    return findings
