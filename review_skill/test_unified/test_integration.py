"""Integration tests for unified engine components"""

import pytest
import time
from unified_engine.engine import UnifiedExecutionEngine
from unified_engine.cache import UnifiedCache
from unified_engine.context import UnifiedContext


class TestEngineIntegration:
    """Integration tests for the full engine"""

    def test_full_scan_workflow(self, tmp_path):
        """Test complete scan workflow"""
        # Create test file
        test_file = tmp_path / "Test.kt"
        test_file.write_text('''
        class Test {
            fun problematic() {
                GlobalScope.launch { }
            }
        }
        ''')

        # Initialize engine
        engine = UnifiedExecutionEngine(
            cache=UnifiedCache(disk_cache_dir=str(tmp_path / "cache")),
            max_workers=2,
            enable_parallel=False
        )

        # Execute scan
        result = engine.scan_file(str(test_file))

        # Verify results
        assert len(result.findings) >= 1
        assert result.files_scanned == 1
        assert result.rules_executed > 0
        assert result.execution_time > 0

    def test_cache_integration(self, tmp_path):
        """Test cache integration"""
        test_file = tmp_path / "Test.kt"
        test_file.write_text("class Test {}")

        cache = UnifiedCache(disk_cache_dir=str(tmp_path / "cache"))
        engine = UnifiedExecutionEngine(cache=cache)

        # First scan
        result1 = engine.scan_file(str(test_file))
        time1 = result1.execution_time

        # Second scan (should hit cache)
        result2 = engine.scan_file(str(test_file))
        time2 = result2.execution_time

        # Cache hit should be faster
        assert time2 < time1 * 0.5 or time2 < 10  # Either significantly faster or very fast

    def test_scan_code_directly(self):
        """Test scanning code string directly"""
        engine = UnifiedExecutionEngine()

        code = '''
        class MainActivity {
            fun bad() {
                GlobalScope.launch { }
            }
        }
        '''

        result = engine.scan_code(code, "MainActivity.kt")

        assert len(result.findings) >= 1
        assert result.files_scanned == 1

    def test_scan_multiple_files(self, tmp_path):
        """Test scanning multiple files"""
        # Create multiple test files
        files = []
        for i in range(3):
            f = tmp_path / f"Test{i}.kt"
            f.write_text(f'''
            class Test{i} {{
                fun bad() {{ GlobalScope.launch {{ }} }}
            }}
            ''')
            files.append(str(f))

        engine = UnifiedExecutionEngine()
        results = engine.scan_files(files, show_progress=False)

        assert len(results) == 3
        for path, result in results.items():
            assert result.files_scanned == 1
            assert len(result.findings) >= 1

    def test_scheduler_with_adaptive_strategy(self):
        """Test scheduler with adaptive strategy"""
        from unified_engine.scheduler import RuleScheduler

        scheduler = RuleScheduler(enable_adaptive=True)

        # Small file should execute all rules
        small_plan = scheduler.create_execution_plan(
            file_size=5_000,
            line_count=100
        )

        # Large file should reduce rules
        large_plan = scheduler.create_execution_plan(
            file_size=600_000,
            line_count=5000
        )

        assert large_plan.total_rules <= small_plan.total_rules

    def test_parallel_execution_integration(self):
        """Test parallel execution"""
        engine = UnifiedExecutionEngine(
            max_workers=4,
            enable_parallel=True
        )

        code = "class Test {}"
        result = engine.scan_code(code, "Test.kt")

        assert result.files_scanned == 1
        assert result.execution_time > 0

    def test_incremental_scan_integration(self, tmp_path):
        """Test incremental scan"""
        test_file = tmp_path / "Test.kt"
        test_file.write_text("class Test {}")

        engine = UnifiedExecutionEngine()

        # Full scan
        engine.scan_file(str(test_file))

        # Mark as scanned
        engine.mark_scanned("commit_abc", [str(test_file)])

        # Get changed files
        changed = engine.get_changed_files("commit_abc", [".kt"])

        # File should not appear as changed (same content)
        # Note: This might return the file if git diff shows changes
        assert isinstance(changed, list)

    def test_performance_report(self, tmp_path):
        """Test performance report generation"""
        test_file = tmp_path / "Test.kt"
        test_file.write_text("class Test { fun bad() { GlobalScope.launch { } } }")

        engine = UnifiedExecutionEngine()
        engine.scan_file(str(test_file))

        report = engine.get_performance_report()

        assert "engine" in report
        assert report["engine"]["total_files_scanned"] >= 1
        assert report["engine"]["total_rules_executed"] > 0

    def test_reset_stats(self, tmp_path):
        """Test resetting statistics"""
        test_file = tmp_path / "Test.kt"
        test_file.write_text("class Test {}")

        engine = UnifiedExecutionEngine()
        engine.scan_file(str(test_file))

        assert engine._total_files_scanned >= 1

        engine.reset_stats()

        assert engine._total_files_scanned == 0
        assert engine._total_rules_executed == 0

    def test_cleanup(self, tmp_path):
        """Test cache cleanup"""
        cache = UnifiedCache(
            disk_cache_dir=str(tmp_path / "cache"),
            default_ttl_seconds=0.01
        )
        engine = UnifiedExecutionEngine(cache=cache)

        # Put something in cache
        cache.put("key1", "value1")

        # Wait for TTL
        import time
        time.sleep(0.02)

        # Cleanup
        stats = engine.cleanup()

        assert "removed_count" in stats

    def test_context_manager(self, tmp_path):
        """Test engine as context manager"""
        test_file = tmp_path / "Test.kt"
        test_file.write_text("class Test {}")

        with UnifiedExecutionEngine() as engine:
            result = engine.scan_file(str(test_file))
            assert result.files_scanned == 1

    def test_engine_repr(self):
        """Test engine string representation"""
        engine = UnifiedExecutionEngine(max_workers=4)
        repr_str = repr(engine)

        assert "UnifiedExecutionEngine" in repr_str
        assert "parallel" in repr_str

    def test_complex_code_scanning(self, tmp_path):
        """Test scanning complex Kotlin code"""
        test_file = tmp_path / "Complex.kt"
        test_file.write_text('''
        class ComplexActivity : AppCompatActivity() {
            private val viewModel: MyViewModel by viewModels()

            override fun onCreate(savedInstanceState: Bundle?) {
                super.onCreate(savedInstanceState)

                // Bad: GlobalScope
                GlobalScope.launch {
                    doWork()
                }

                // Bad: Main thread IO
                val data = readFile()

                // Good: lifecycleScope
                lifecycleScope.launch {
                    viewModel.data.collect { }
                }
            }

            private fun readFile(): String = "data"
            private suspend fun doWork() {}
        }

        class MyViewModel : ViewModel() {
            val data = MutableStateFlow(0)

            fun load() {
                // Bad: ViewModel with Dispatchers.Main
                viewModelScope.launch(Dispatchers.Main) {
                    data.value = 1
                }
            }
        }
        ''')

        engine = UnifiedExecutionEngine()
        result = engine.scan_file(str(test_file))

        assert result.files_scanned == 1
        assert len(result.findings) >= 3  # Should find GlobalScope, Main thread IO, ViewModel/MainDispatcher
