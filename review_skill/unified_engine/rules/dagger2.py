"""
Dagger2 Rules for Unified Engine

Dagger2 依赖注入相关规则 - 使用 FAST 或 HYBRID 模式
"""
import re
from typing import List
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "SingletonComponentInjectActivityRule",
    "FieldInjectionDetectedRule",
    "ProvidesWithoutScopeRule",
]


class SingletonComponentInjectActivityRule(UnifiedRule):
    """
    @Singleton 与 ComponentActivity 生命周期不匹配检测规则

    使用 @Singleton 作用域注入 Component/Activity 会导致生命周期不匹配，
    单例对象持有 Activity 引用会造成内存泄漏。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="singleton_component_inject_activity",
            name="@Singleton 与 ComponentActivity 生命周期不匹配",
            description="使用 @Singleton 作用域注入 Component/Activity 会导致生命周期不匹配，单例对象持有 Activity 引用会造成内存泄漏",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "dagger2", "di", "singleton", "component", "activity", "lifecycle"],
            weight=0.9,
            suggested_fix="使用 @ActivityScoped 或 @FragmentScoped 替代 @Singleton 来注入 Activity",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测 @Singleton 注入 ComponentActivity"""
        findings = []

        lines = context.get_lines()
        has_singleton_component = False
        has_activity = False
        singleton_component_line = 0

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            # 检测 @Singleton 和 @Component
            if "@singleton" in line_lower and "@component" in line_lower:
                has_singleton_component = True
                singleton_component_line = i

            # 检测 Activity
            if "activity" in line_lower and ("class " in line_lower or ": activity" in line_lower):
                has_activity = True

            # 检测 @Singleton @Component 与 Activity
            if has_singleton_component and has_activity:
                findings.append(Finding(
                    rule_id=self.metadata.id,
                    message="@Singleton 作用域注入 Activity 会导致生命周期不匹配",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=singleton_component_line,
                    code_snippet=line,
                    suggestion=self.metadata.suggested_fix
                ))
                break

        return findings


class FieldInjectionDetectedRule(UnifiedRule):
    """
    字段注入检测规则

    使用 @Inject lateinit var 进行字段注入不利于测试和维护，
    推荐使用构造函数注入。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="field_injection_detected",
            name="检测到字段注入",
            description="使用 @Inject lateinit var 进行字段注入不利于测试和维护，推荐使用构造函数注入",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["android", "kotlin", "dagger2", "di", "field_injection", "constructor_injection"],
            weight=0.7,
            suggested_fix="将字段注入改为构造函数注入，提高可测试性和代码清晰度",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测字段注入"""
        findings = []

        lines = context.get_lines()

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            # 检测 @Inject lateinit var
            if "@inject" in line_lower and "lateinit" in line_lower and "var" in line_lower:
                pattern = r"@Inject\s+lateinit\s+var"
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message="检测到字段注入（@Inject lateinit var），建议使用构造函数注入",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion=self.metadata.suggested_fix
                    ))

        return findings


class ProvidesWithoutScopeRule(UnifiedRule):
    """
    @Provides 方法缺少作用域检测规则

    @Provides 方法未指定作用域（如 @Singleton），每次注入都会创建新实例，
    可能导致不必要的对象创建。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="provides_without_scope",
            name="@Provides 方法缺少作用域",
            description="@Provides 方法未指定作用域（如 @Singleton），每次注入都会创建新实例，可能导致不必要的对象创建",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["android", "kotlin", "dagger2", "di", "provides", "scope"],
            weight=0.6,
            suggested_fix="为 @Provides 方法添加合适的作用域注解，如 @Singleton、@ActivityScoped 等",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        """检测 @Provides 缺少作用域"""
        findings = []

        lines = context.get_lines()
        provides_line = 0
        in_provides_method = False

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            # 检测 @Provides
            if "@provides" in line_lower:
                in_provides_method = True
                provides_line = i

            # 在 @Provides 方法中
            if in_provides_method:
                # 检测方法定义（fun）
                if "fun " in line_lower or "def " in line_lower:
                    # 检查是否有作用域（@Singleton, @ActivityScoped, etc.）
                    has_scope = any(scope in line_lower for scope in ["@singleton", "@activityscoped", "@fragmentscoped", "@viewmodelscoped"])

                    if not has_scope:
                        # 检查附近是否有作用域
                        has_scope_nearby = False
                        start = max(0, i - 3)
                        for j in range(start, i):
                            if any(scope in lines[j].lower() for scope in ["@singleton", "@activityscoped", "@fragmentscoped", "@viewmodelscoped"]):
                                has_scope_nearby = True
                                break

                        if not has_scope_nearby:
                            findings.append(Finding(
                                rule_id=self.metadata.id,
                                message="@Provides 方法缺少作用域注解",
                                severity=self.metadata.severity,
                                file_path=context.file_path,
                                line_number=provides_line,
                                code_snippet=line,
                                suggestion="为 @Provides 添加作用域注解，如 @Singleton"
                            ))

                    in_provides_method = False

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        SingletonComponentInjectActivityRule(),
        FieldInjectionDetectedRule(),
        ProvidesWithoutScopeRule(),
    ]
