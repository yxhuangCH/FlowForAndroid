"""
pytest fixtures for unified engine tests
"""

import pytest
import tempfile
from pathlib import Path

from unified_engine.context import UnifiedContext
from unified_engine.scheduler import RuleScheduler
from unified_engine.cache import UnifiedCache
from unified_engine.registry import UnifiedRegistry
from unified_engine.rules import get_all_rules
from unified_engine.interfaces import ExecutionMode


@pytest.fixture(scope="session")
def registered_registry():
    """
    Session-scoped fixture that registers all rules in the global registry.
    This ensures all tests have access to registered rules.
    """
    registry = UnifiedRegistry()
    # Clear any existing rules first (in case of test re-runs)
    registry.clear()

    # Register all rules
    rules = get_all_rules()
    for rule in rules:
        try:
            if not registry.has_rule(rule.metadata.id):
                registry.register(rule)
        except ValueError:
            pass  # Already registered

    return registry


@pytest.fixture
def sample_rules(registered_registry):
    """Provide all available rules for testing"""
    return get_all_rules()


@pytest.fixture
def scheduler(registered_registry):
    """Provide a default scheduler instance for testing"""
    return RuleScheduler(
        registry=registered_registry,
        max_workers=2,
        enable_parallel=False  # Disable parallel for easier debugging
    )


@pytest.fixture
def cache(tmp_path):
    """Provide a temporary cache instance for testing"""
    return UnifiedCache(
        memory_size=100,
        disk_cache_dir=str(tmp_path / "cache")
    )


@pytest.fixture
def fast_rules(sample_rules):
    """Provide only FAST mode rules"""
    return [r for r in sample_rules if r.execution_mode == ExecutionMode.FAST]


@pytest.fixture
def hybrid_rules(sample_rules):
    """Provide only HYBRID mode rules"""
    return [r for r in sample_rules if r.execution_mode == ExecutionMode.HYBRID]


@pytest.fixture
def precise_rules(sample_rules):
    """Provide only PRECISE mode rules"""
    return [r for r in sample_rules if r.execution_mode == ExecutionMode.PRECISE]


@pytest.fixture
def sample_kotlin_code():
    """Provide various Kotlin code samples for testing"""
    return {
        "simple_class": """
            class Simple {
                fun greet() = "Hello"
            }
        """,
        "coroutine_globalscope": """
            class Test {
                fun test() {
                    GlobalScope.launch { }
                }
            }
        """,
        "coroutine_correct": """
            class Test {
                fun test() {
                    lifecycleScope.launch { }
                }
            }
        """,
        "flow_usage": """
            class ViewModel {
                val flow = flow { emit(1) }
                    .flowOn(Dispatchers.IO)
            }
        """,
        "viewmodel_mainthread": """
            class MyViewModel : ViewModel() {
                fun load() {
                    viewModelScope.launch(Dispatchers.Main) { }
                }
            }
        """,
        "comment_only": """
            // This is a comment
            /* Multi-line comment
               with GlobalScope.launch mentioned */
        """,
        "empty": "",
        "whitespace": "   \n\n   ",
    }


@pytest.fixture
def sample_kt_file(tmp_path, sample_kotlin_code):
    """Create a temporary Kotlin file with problematic code"""
    file_path = tmp_path / "Test.kt"
    file_path.write_text(sample_kotlin_code["coroutine_globalscope"])
    return str(file_path)


@pytest.fixture
def empty_context():
    """Provide an empty context for testing"""
    return UnifiedContext("", "Test.kt")


@pytest.fixture
def sample_context(sample_kotlin_code):
    """Provide a context with sample code"""
    return UnifiedContext(sample_kotlin_code["simple_class"], "Test.kt")


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure for testing"""
    # Create source files
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "MainActivity.kt").write_text('''
        class MainActivity : AppCompatActivity() {
            fun bad() {
                GlobalScope.launch { }
            }
        }
    ''')

    (src_dir / "ViewModel.kt").write_text('''
        class MyViewModel : ViewModel() {
            fun load() {
                viewModelScope.launch(Dispatchers.Main) { }
            }
        }
    ''')

    (src_dir / "Repository.kt").write_text('''
        class Repository {
            suspend fun fetch() = withContext(Dispatchers.IO) { }
        }
    ''')

    return str(tmp_path)


@pytest.fixture
def small_file_size():
    """Small file size (5KB) for testing"""
    return 5_000


@pytest.fixture
def medium_file_size():
    """Medium file size (50KB) for testing"""
    return 50_000


@pytest.fixture
def large_file_size():
    """Large file size (600KB) for testing"""
    return 600_000
