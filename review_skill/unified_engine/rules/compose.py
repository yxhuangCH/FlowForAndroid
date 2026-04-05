"""
Compose Rules for Unified Engine

Jetpack Compose 相关规则 - 使用 HYBRID 模式
"""
from typing import List
import re
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "ComposeRememberMissingRule",
]


class ComposeRememberMissingRule(UnifiedRule):
    """
    Compose 中缺少 remember 包装检测规则

    mutableStateOf 和其他状态创建器应该被 remember 包装，
    以防止重组循环。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="compose_remember_missing",
            name="Missing remember in Composable",
            description="mutableStateOf and other state creators should be wrapped in remember to prevent recomposition loops",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.PERFORMANCE,
            tags=["android", "kotlin", "compose", "recomposition", "performance"],
            weight=1.3,
            suggested_fix="Wrap state creation in remember: val state = remember { mutableStateOf(initialValue) }",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        """
        Detect mutableStateOf and state creators not wrapped in remember.

        Creating state outside remember causes recomposition on every render,
        leading to performance issues and potential infinite recomposition loops.
        """
        findings = []
        lines = context.get_lines()

        # Check if this is a Composable function
        is_composable = any('@Composable' in line for line in lines[:10])
        if not is_composable:
            return findings

        # State creators that should be remembered
        state_patterns = [
            (r'\bval\s+\w+\s*=\s*mutableStateOf\(', "mutableStateOf"),
            (r'\bvar\s+\w+\s*=\s*mutableStateOf\(', "mutableStateOf"),
            (r'\bval\s+\w+\s*=\s*mutableIntStateOf\(', "mutableIntStateOf"),
            (r'\bval\s+\w+\s*=\s*mutableLongStateOf\(', "mutableLongStateOf"),
            (r'\bval\s+\w+\s*=\s*mutableFloatStateOf\(', "mutableFloatStateOf"),
            (r'\bval\s+\w+\s*=\s*mutableDoubleStateOf\(', "mutableDoubleStateOf"),
            (r'\bval\s+\w+\s*=\s*mutableBooleanStateOf\(', "mutableBooleanStateOf"),
            (r'\bval\s+\w+\s*=\s*derivedStateOf\(', "derivedStateOf"),
        ]

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip if already wrapped in remember
            if 'remember {' in stripped or 'remember(' in stripped:
                continue
            if 'rememberSaveable' in stripped:
                continue

            # Check for direct state creation without remember
            for pattern, state_type in state_patterns:
                if re.search(pattern, stripped):
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message=f"{state_type} should be wrapped in remember to prevent recomposition loops",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion=f"Use remember: val state = remember {{ {state_type}(initialValue) }}"
                    ))
                    break

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        ComposeRememberMissingRule(),
    ]
