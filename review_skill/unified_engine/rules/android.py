"""
Android Rules for Unified Engine

Android 框架相关规则 - 使用 HYBRID 模式
"""
from typing import List
import re
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "LifecycleOnCreateSuperRule",
    "FragmentArgConstructorRule",
]


class LifecycleOnCreateSuperRule(UnifiedRule):
    """
    生命周期方法缺少 super 调用检测规则

    Android 生命周期方法需要调用 super 方法以确保框架正常工作。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="lifecycle_oncreate_super",
            name="Missing super call in lifecycle method",
            description="Lifecycle methods like onCreate, onResume should call super method",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS,
            tags=["android", "kotlin", "lifecycle", "super-call"],
            weight=1.2,
            suggested_fix="Add super.onCreate(savedInstanceState) / super.onResume() etc. at the beginning of the method",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
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
                            rule_id=self.metadata.id,
                            message=f"{in_lifecycle_method}() must call {lifecycle_methods[in_lifecycle_method]}()",
                            severity=self.metadata.severity,
                            file_path=context.file_path,
                            line_number=method_start_line,
                            code_snippet=lines[method_start_line - 1].strip(),
                            suggestion=f"Add {lifecycle_methods[in_lifecycle_method]}(...) as the first statement"
                        ))
                    in_lifecycle_method = None

        return findings


class FragmentArgConstructorRule(UnifiedRule):
    """
    Fragment 带参数构造函数检测规则

    当 Android 重新创建 Fragment（配置更改、进程死亡）时，
    它使用默认构造函数。带参数的构造函数会导致崩溃。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="fragment_arg_constructor",
            name="Fragment has parameterized constructor",
            description="Fragment should have only default constructor to prevent crashes on configuration changes",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "fragment", "configuration-change"],
            weight=1.3,
            suggested_fix="Remove constructor parameters, use arguments Bundle with Fragment.setArguments() and Fragment.getArguments() instead",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
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
                    rule_id=self.metadata.id,
                    message=f"Fragment '{class_name}' has parameterized constructor - will crash on configuration change",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion="Use arguments Bundle: class MyFragment : Fragment() { companion object { fun newInstance(arg: String) = MyFragment().apply { arguments = Bundle().apply { putString('key', arg) } } } }"
                ))

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        LifecycleOnCreateSuperRule(),
        FragmentArgConstructorRule(),
    ]
