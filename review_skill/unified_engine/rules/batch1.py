"""
Batch 1 Rules for Unified Engine

第一批迁移规则 - 使用 HYBRID 或 PRECISE 模式
"""
from typing import List
import re
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "MemoryLeakStaticContextRule",
    "CoroutineMainThreadIoRule",
    "UnspecifiedScopeRule",
    "TodoCommentRule",
    "HardcodedStringRule",
    "LongMethodRule",
]


class MemoryLeakStaticContextRule(UnifiedRule):
    """
    静态字段持有 Context 引用检测规则

    静态字段的生命周期与整个应用程序相同，持有 Activity/View/Context
    引用会阻止垃圾回收，导致内存泄漏。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="memory_leak_static_context",
            name="Static Context reference",
            description="Static fields should not hold Activity, View, or Context references to avoid memory leaks",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "memory-leak", "static"],
            weight=1.5,
            suggested_fix="Remove static modifier or use Application Context instead of Activity/View Context",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []
        lines = context.get_lines()

        # Track if we're inside a companion object
        in_companion_object = False
        companion_brace_depth = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track companion object scope
            if 'companion object' in stripped:
                in_companion_object = True
                companion_brace_depth = stripped.count('{') - stripped.count('}')
                continue

            if in_companion_object:
                companion_brace_depth += stripped.count('{') - stripped.count('}')
                if companion_brace_depth <= 0 and '{' not in stripped:
                    in_companion_object = False

                # Check for Context/Activity/View references in companion object
                if any(keyword in stripped for keyword in ['val ', 'var ', 'lateinit']):
                    if any(type_name in stripped for type_name in ['Context', 'Activity', 'View', 'Fragment']):
                        # Skip Application Context which is safe
                        is_application_context = (
                            'Application' in stripped and 'Context' not in stripped.replace('Application', '')
                        ) or (
                            any(name in stripped for name in ['appContext:', 'applicationContext:', 'appContext ', 'applicationContext '])
                        ) or (
                            re.search(r':\s*Application\b', stripped) is not None
                        )

                        if not is_application_context:
                            findings.append(Finding(
                                rule_id=self.metadata.id,
                                message="Static field should not hold Activity/View/Context reference (causes memory leak)",
                                severity=self.metadata.severity,
                                file_path=context.file_path,
                                line_number=i,
                                code_snippet=line.strip(),
                                suggestion="Use Application Context or remove static modifier, or use WeakReference"
                            ))

            # Check @JvmStatic annotated fields
            if '@JvmStatic' in stripped:
                if i < len(lines):
                    next_line = lines[i].strip()
                    if any(type_name in next_line for type_name in ['Context', 'Activity', 'View', 'Fragment']):
                        if 'Application' not in next_line:
                            findings.append(Finding(
                                rule_id=self.metadata.id,
                                message="@JvmStatic field should not hold Activity/View/Context reference (causes memory leak)",
                                severity=self.metadata.severity,
                                file_path=context.file_path,
                                line_number=i,
                                code_snippet=next_line,
                                suggestion="Use Application Context or remove @JvmStatic, or use WeakReference"
                            ))

        return findings


class CoroutineMainThreadIoRule(UnifiedRule):
    """
    协程主线程 IO 操作检测规则

    在协程的主线程中执行 IO 操作可能导致 ANR。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="coroutine_main_thread_io",
            name="Coroutine main thread IO operation",
            description="Executing IO operations in coroutine main thread may cause ANR (Application Not Responding)",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.PERFORMANCE,
            tags=["android", "kotlin", "coroutine", "io", "anr"],
            weight=1.0,
            suggested_fix="Move IO operations to Dispatchers.IO or background thread",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []

        # Simplified detection: if contains Dispatchers.Main and has IO related operations
        lines = context.get_lines()
        has_main_dispatcher = False
        has_io_operation = False

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if "dispatchers.main" in line_lower:
                has_main_dispatcher = True

            io_keywords = ["read", "write", "file", "network", "database", "sharedpreferences", "repository"]
            if any(keyword in line_lower for keyword in io_keywords):
                has_io_operation = True

                # If found IO operation and main thread dispatcher, record specific location
                if has_main_dispatcher:
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message="Detected risk of executing IO operations in coroutine main thread",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion=self.metadata.suggested_fix
                    ))

        # General detection (if specific line not found)
        if has_main_dispatcher and has_io_operation and not findings:
            findings.append(Finding(
                rule_id=self.metadata.id,
                message="Detected risk of executing IO operations in coroutine main thread",
                severity=self.metadata.severity,
                file_path=context.file_path,
                suggestion=self.metadata.suggested_fix
            ))

        return findings


class UnspecifiedScopeRule(UnifiedRule):
    """
    未指定协程作用域检测规则

    协程启动时应该显式指定生命周期作用域。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="unspecified_scope",
            name="Unspecified coroutine scope",
            description="Coroutine launch without specifying lifecycle scope",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "coroutine", "lifecycle"],
            weight=0.8,
            suggested_fix="Explicitly specify coroutine scope, such as viewModelScope or lifecycleScope",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []

        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Check if contains launch { but no scope specified
            if "launch {" in line_stripped or line_stripped.startswith("launch {") or "launch(" in line_stripped:
                # Check if explicit scope exists
                if not any(scope in line_stripped for scope in ["viewModelScope", "lifecycleScope", "GlobalScope", "coroutineScope"]):
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message="Coroutine launch without specifying lifecycle scope",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line,
                        suggestion=self.metadata.suggested_fix
                    ))

        return findings


class TodoCommentRule(UnifiedRule):
    """
    TODO/FIXME 注释检测规则

    检测代码中的 TODO 和 FIXME 注释。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="todo_comment",
            name="TODO/FIXME comment",
            description="Code contains TODO or FIXME comments that need attention",
            severity=RuleSeverity.INFO,
            category=RuleCategory.BEST_PRACTICE,
            tags=["kotlin", "documentation"],
            weight=0.3,
            suggested_fix="Address the TODO/FIXME or remove the comment if resolved",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []

        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check for TODO or FIXME in comments
            if re.search(r"(//|/\*|\*)\s*(TODO|FIXME)", stripped, re.IGNORECASE):
                findings.append(Finding(
                    rule_id=self.metadata.id,
                    message=f"Found {self.metadata.name}: {stripped[:50]}",
                    severity=self.metadata.severity,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=stripped,
                    suggestion=self.metadata.suggested_fix
                ))

        return findings


class HardcodedStringRule(UnifiedRule):
    """
    硬编码字符串检测规则

    检测代码中可能应该提取为资源的硬编码字符串。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="hardcoded_string",
            name="Hardcoded string",
            description="Hardcoded strings should be extracted to resources for internationalization",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["android", "kotlin", "i18n"],
            weight=0.5,
            suggested_fix="Extract string to strings.xml and use stringResource() or getString()",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []

        # Pattern for hardcoded strings (not in comments, not empty, not just symbols)
        # Skip: comments, log messages, test files, urls, package names
        string_pattern = r'"([^"]{3,})"'

        line_matches = context.find_pattern_with_lines(string_pattern)

        for match in line_matches:
            line_content = match.line_content.strip()

            # Skip comments
            if line_content.startswith("//") or line_content.startswith("*"):
                continue

            # Skip log statements
            if re.search(r"(Log\.|println|print\(| Timber\.)", line_content):
                continue

            # Skip URLs
            if re.search(r"https?://", line_content):
                continue

            # Skip package declarations and imports
            if line_content.startswith("package ") or line_content.startswith("import "):
                continue

            # Skip annotations
            if line_content.startswith("@"):
                continue

            # Extract the string content
            str_match = match.match
            string_content = str_match.group(1)

            # Skip strings that are just symbols/numbers/paths
            if re.match(r"^[\d\s\W_]+$", string_content):
                continue

            findings.append(Finding(
                rule_id=self.metadata.id,
                message=f"Hardcoded string: \"{string_content[:30]}...\" should be extracted to resources",
                severity=self.metadata.severity,
                file_path=context.file_path,
                line_number=match.line_number,
                code_snippet=line_content,
                suggestion=self.metadata.suggested_fix
            ))

        return findings


class LongMethodRule(UnifiedRule):
    """
    长方法检测规则

    检测代码行数过多的方法。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="long_method",
            name="Long method",
            description="Method is too long and should be refactored into smaller methods",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.MAINTAINABILITY,
            tags=["kotlin", "readability"],
            weight=0.5,
            suggested_fix="Refactor the method by extracting smaller, focused methods",
            reference_url=""
        )

    execution_mode = ExecutionMode.FAST

    def __init__(self, max_lines: int = 50):
        super().__init__()
        self.max_lines = max_lines

    def check(self, context: UnifiedContext) -> List[Finding]:
        findings = []

        lines = context.get_lines()
        in_function = False
        function_start_line = 0
        function_signature = ""
        brace_depth = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if not in_function:
                # Detect function definition
                # Match patterns like: fun name(), suspend fun name(), private fun name(), etc.
                if re.match(r"^(\s*)(suspend\s+)?(private\s+|public\s+|protected\s+|internal\s+)?(fun\s+\w+)", stripped):
                    in_function = True
                    function_start_line = i
                    function_signature = stripped
                    brace_depth = stripped.count("{") - stripped.count("}")
            else:
                brace_depth += stripped.count("{") - stripped.count("}")

                if brace_depth <= 0 and "{" not in stripped:
                    # Function ended
                    function_end_line = i
                    function_length = function_end_line - function_start_line + 1

                    if function_length > self.max_lines:
                        findings.append(Finding(
                            rule_id=self.metadata.id,
                            message=f"Method is too long ({function_length} lines, max {self.max_lines})",
                            severity=self.metadata.severity,
                            file_path=context.file_path,
                            line_number=function_start_line,
                            code_snippet=function_signature[:100],
                            suggestion=self.metadata.suggested_fix
                        ))

                    in_function = False
                    function_signature = ""

        return findings


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        MemoryLeakStaticContextRule(),
        CoroutineMainThreadIoRule(),
        UnspecifiedScopeRule(),
        TodoCommentRule(),
        HardcodedStringRule(),
        LongMethodRule(),
    ]
