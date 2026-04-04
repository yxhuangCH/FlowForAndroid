"""
Rule: blocking_main_thread
Detection: IO operations that may block the main thread
"""
from typing import List
import re
from ..interfaces import RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="blocking_main_thread",
    name="Blocking operation on main thread",
    description="IO operations on main thread can cause ANR (Application Not Responding)",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.PERFORMANCE,
    tags=["android", "kotlin", "performance", "anr", "main-thread"],
    suggested_fix="Move blocking operations to background thread using coroutines (Dispatchers.IO), AsyncTask, or WorkManager",
    weight=1.4
)
def blocking_main_thread_rule(context: RuleContext) -> List[Finding]:
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
                is_in_async = _is_in_async_context(lines, i)

                if not is_in_async:
                    findings.append(Finding(
                        rule_id="blocking_main_thread",
                        message=f"{operation_type} on main thread may cause ANR",
                        severity=RuleSeverity.CRITICAL,
                        file_path=context.file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion=f"Wrap {operation_type} in withContext(Dispatchers.IO) or use coroutines"
                    ))
                break

    return findings


def _is_in_async_context(lines: List[str], line_number: int) -> bool:
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
