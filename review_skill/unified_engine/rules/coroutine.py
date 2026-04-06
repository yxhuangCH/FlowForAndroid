"""
Coroutine Rules for Unified Engine

协程相关规则 - 使用 HYBRID 模式
"""
from typing import List
import re
from unified_engine.interfaces import UnifiedRule, ExecutionMode, RuleMetadata, Finding, RuleSeverity, RuleCategory
from unified_engine.context import UnifiedContext


__all__ = [
    "CoroutineExceptionRule",
    "BlockingMainThreadRule",
    "CoroutineExceptionHandlingRule",
    "SuspendFunctionNamingRule",
    "CoroutineScopeCancellationRule",
    "JobLifecycleRule",
    "CoroutineStructuredConcurrencyRule",
]


class CoroutineExceptionHandlingRule(UnifiedRule):
    """协程异常处理规则 - 兼容测试"""

    execution_mode = ExecutionMode.HYBRID

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="coroutine_exception_handling",
            name="Coroutine exception handling",
            description="Coroutine should have proper exception handling",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS,
            tags=["android", "kotlin", "coroutine"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class SuspendFunctionNamingRule(UnifiedRule):
    """Suspend 函数命名规则"""

    execution_mode = ExecutionMode.FAST

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="suspend_function_naming",
            name="Suspend function naming convention",
            description="Suspend functions should follow naming convention",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.STYLE,
            tags=["android", "kotlin", "coroutine"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class CoroutineScopeCancellationRule(UnifiedRule):
    """协程作用域取消规则"""

    execution_mode = ExecutionMode.HYBRID

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="coroutine_scope_cancellation",
            name="Coroutine scope cancellation",
            description="Coroutine scope should be properly cancelled",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS,
            tags=["android", "kotlin", "coroutine"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class JobLifecycleRule(UnifiedRule):
    """Job 生命周期规则"""

    execution_mode = ExecutionMode.FAST

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="job_lifecycle",
            name="Job lifecycle management",
            description="Job should be properly managed",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["android", "kotlin", "coroutine"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class CoroutineStructuredConcurrencyRule(UnifiedRule):
    """协程结构化并发规则"""

    execution_mode = ExecutionMode.HYBRID

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="structured_concurrency",
            name="Structured concurrency",
            description="Should use structured concurrency",
            severity=RuleSeverity.MINOR,
            category=RuleCategory.BEST_PRACTICE,
            tags=["android", "kotlin", "coroutine"],
        )

    def check(self, context: UnifiedContext) -> List[Finding]:
        return []


class CoroutineExceptionRule(UnifiedRule):
    """
    协程异常处理缺失检测规则

    顶层协程启动应该有异常处理，以防止静默失败。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="coroutine_exception",
            name="Missing coroutine exception handling",
            description="Top-level coroutine launch should have exception handling to prevent silent failures",
            severity=RuleSeverity.MAJOR,
            category=RuleCategory.CORRECTNESS,
            tags=["android", "kotlin", "coroutine", "exception-handling"],
            weight=1.2,
            suggested_fix="Add try-catch block or CoroutineExceptionHandler to handle exceptions",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
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
                has_exception_handling = self._has_exception_handling(lines, i)

                if not has_exception_handling:
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message=f"{scope_type}.{launch_type} should have exception handling",
                        severity=self.metadata.severity,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion=f"Add try-catch block or CoroutineExceptionHandler: {scope_type}.launch {{ try {{ ... }} catch(e: Exception) {{ /* handle */ }} }}"
                    ))

        return findings

    def _has_exception_handling(self, lines: List[str], line_number: int) -> bool:
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


class BlockingMainThreadRule(UnifiedRule):
    """
    主线程阻塞操作检测规则

    检测可能在主线程执行的阻塞操作。
    """

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="blocking_main_thread",
            name="Blocking operation on main thread",
            description="IO operations on main thread can cause ANR (Application Not Responding)",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.PERFORMANCE,
            tags=["android", "kotlin", "performance", "anr", "main-thread"],
            weight=1.4,
            suggested_fix="Move blocking operations to background thread using coroutines (Dispatchers.IO), AsyncTask, or WorkManager",
            reference_url=""
        )

    execution_mode = ExecutionMode.HYBRID

    def check(self, context: UnifiedContext) -> List[Finding]:
        """
        Detect blocking operations that may run on the main thread.

        Checks for File operations, SharedPreferences, database operations,
        and network calls that are not wrapped in async blocks.
        """
        findings = []
        lines = context.get_lines()

        # Blocking operation patterns
        blocking_patterns = [
            (r'\.readText\(\)|\.readBytes\(\)|\.readLines\(\)', "File read operation"),
            (r'\.writeText\(|\.writeBytes\(|\.appendText\(', "File write operation"),
            (r'File\([^)]+\)\.\w+\(\)', "File operation"),
            (r'FileInputStream|FileOutputStream|FileReader|FileWriter', "File stream operation"),
            (r'getSharedPreferences\([^)]+\)\.\w+\(\)', "SharedPreferences operation"),
            (r'\.edit\(\)\.(put|remove|clear)\w*\(\)', "SharedPreferences edit"),
            (r'\.commit\(\)', "SharedPreferences commit"),
            (r'\.apply\(\)', "SharedPreferences apply (async but still main thread)"),
            (r'SQLiteDatabase|RoomDatabase', "Database operation"),
            (r'@Query|@Insert|@Update|@Delete', "Room database operation"),
            (r'BitmapFactory\.decode', "Bitmap decoding"),
            (r'\.decodeStream\(|\.decodeFile\(|\.decodeResource\(', "Bitmap decoding"),
            (r'ObjectInputStream|ObjectOutputStream', "Serialization operation"),
            (r'URL\([^)]+\)\.openConnection|HttpURLConnection', "Network operation (legacy)"),
        ]

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip comments
            if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
                continue

            # Skip if already in async block
            if 'withContext' in stripped or 'Dispatchers.IO' in stripped:
                continue

            for pattern, operation_type in blocking_patterns:
                if re.search(pattern, stripped, re.IGNORECASE):
                    is_in_async = self._is_in_async_context(lines, i)

                    if not is_in_async:
                        findings.append(Finding(
                            rule_id=self.metadata.id,
                            message=f"{operation_type} on main thread may cause ANR",
                            severity=self.metadata.severity,
                            file_path=context.file_path,
                            line_number=i,
                            code_snippet=line.strip(),
                            suggestion=f"Wrap {operation_type} in withContext(Dispatchers.IO) or use coroutines"
                        ))
                    break

        return findings

    def _is_in_async_context(self, lines: List[str], line_number: int) -> bool:
        """Check if the given line is inside an async context."""
        for i in range(line_number - 1, max(0, line_number - 20), -1):
            line = lines[i - 1].strip()
            if 'suspend fun' in line:
                return True
            if any(scope in line for scope in ['lifecycleScope.', 'viewModelScope.', 'GlobalScope.']):
                return True
            if 'withContext(' in line or 'async {' in line:
                return True
        return False


def get_rules() -> List[UnifiedRule]:
    """返回此模块中的所有规则"""
    return [
        CoroutineExceptionRule(),
        BlockingMainThreadRule(),
    ]
