"""
Best Practice Rules for Unified Engine

最佳实践规则 - 使用 FAST 或 HYBRID 模式
"""
from typing import List
import re
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "MutableLiveDataExposedRule",
    "IntentExtraKeyRule",
    "HiltModuleInjectionRule",
]


class MutableLiveDataExposedRule(UnifiedRule):
    """
    MutableLiveData 公开暴露检测规则

    公开暴露 MutableLiveData 允许外部修改，破坏了封装性。
    应该使用私有的 MutableLiveData 配合公开的 LiveData 支持属性。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="mutable_livedata_exposed",
            name="MutableLiveData exposed publicly",
            description="MutableLiveData should be private, expose immutable LiveData to observers",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS,
            tags=["android", "kotlin", "livedata", "architecture", "encapsulation"],
            weight=1.2,
            suggested_fix="Make MutableLiveData private and expose LiveData: private val _data = MutableLiveData<T>(); val data: LiveData<T> = _data",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
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
                    rule_id=self.metadata.id,
                    message=f"MutableLiveData field '{field_name}' should be private",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion=f"Use: private val _{field_name} = MutableLiveData<T>(); val {field_name}: LiveData<T> = _{field_name}"
                ))

        return findings


class IntentExtraKeyRule(UnifiedRule):
    """
    Intent extra key 未定义为常量检测规则

    使用字符串字面量作为 Intent key 容易出错。
    应该使用常量来防止拼写错误并支持 IDE 重构。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="intent_extra_key",
            name="Intent extra key not defined as constant",
            description="Intent extra keys should be defined as constants to prevent typos and enable refactoring",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["android", "kotlin", "intent", "constants"],
            weight=0.9,
            suggested_fix="Define keys as companion object constants: companion object { const val EXTRA_KEY = \"extra_key\" }",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
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
                        rule_id=self.metadata.id,
                        message=f"Intent extra key \"{key}\" should be defined as constant",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion=f"Define constant: companion object {{ const val EXTRA_{key.upper().replace('.', '_')} = \"{key}\" }}"
                    ))
                    break

        return findings


class HiltModuleInjectionRule(UnifiedRule):
    """
    Hilt Module 缺少 @InstallIn 注解检测规则

    Hilt 需要 @InstallIn 来知道将模块安装到哪个组件中。
    缺少 @InstallIn 意味着该模块不会被使用。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="hilt_module_injection",
            name="Hilt Module missing @InstallIn",
            description="@Module classes must have @InstallIn to specify which Hilt component to install in",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.CORRECTNESS,
            tags=["android", "kotlin", "hilt", "di", "dagger"],
            weight=1.0,
            suggested_fix="Add @InstallIn annotation: @InstallIn(SingletonComponent::class) or @InstallIn(ActivityComponent::class)",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
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
                        rule_id=self.metadata.id,
                        message="@Module class missing @InstallIn annotation - module will not be installed",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="Add @InstallIn(SingletonComponent::class) for app-wide dependencies or @InstallIn(ActivityComponent::class) for activity-scoped"
                    ))

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        MutableLiveDataExposedRule(),
        IntentExtraKeyRule(),
        HiltModuleInjectionRule(),
    ]
