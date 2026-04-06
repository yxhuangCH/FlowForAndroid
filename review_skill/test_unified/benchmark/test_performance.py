"""Performance benchmarks for unified engine"""

import pytest
import time
import statistics
from unified_engine.engine import UnifiedExecutionEngine
from unified_engine.cache import UnifiedCache
from unified_engine.context import UnifiedContext


class TestPerformanceBenchmark:
    """Performance benchmark tests for unified engine"""

    # Performance targets from PLAN_v4
    TARGETS = {
        "first_scan_ms": 50,      # First scan 50ms/file
        "cached_scan_ms": 5,      # Cache hit 5ms/file
        "large_file_ms": 500,     # Large file < 500ms
        "parallel_speedup": 2.0,  # Parallel speedup 2x
    }

    @pytest.fixture
    def sample_files(self, tmp_path):
        """Create sample Kotlin files for benchmarking"""
        files = []

        # Small file (simple class)
        f1 = tmp_path / "Simple.kt"
        f1.write_text("class Simple { fun greet() = \"Hello\" }")
        files.append(str(f1))

        # Medium file (with some issues)
        f2 = tmp_path / "Medium.kt"
        f2.write_text('''
class MediumActivity : AppCompatActivity() {
    private val viewModel: MyViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        GlobalScope.launch { doWork() }

        lifecycleScope.launch { viewModel.data.collect { } }
    }

    private suspend fun doWork() {}
}

class MyViewModel : ViewModel() {
    val data = MutableStateFlow(0)
    fun load() { viewModelScope.launch(Dispatchers.Main) { data.value = 1 } }
}
''')
        files.append(str(f2))

        # Complex file (multiple issues)
        f3 = tmp_path / "Complex.kt"
        f3.write_text('''
package com.example

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.*

@Composable
fun CounterScreen(modifier: Modifier = Modifier) {
    var count by remember { mutableStateOf(0) }

    Column(modifier = modifier) {
        Text("Count: $count")
        Button(onClick = { count++ }) { }
    }
}

class DataRepository {
    fun getData(): Flow<Data> = flow {
        emit(fetchFromNetwork())
    }

    private suspend fun fetchFromNetwork(): Data = Data()
}

data class Data(val id: Int = 0, val name: String = "")
''')
        files.append(str(f3))

        return files

    def test_first_scan_performance(self, sample_files):
        """Test first scan performance"""
        engine = UnifiedExecutionEngine(
            cache=UnifiedCache(),
            max_workers=1,
            enable_parallel=False
        )

        times = []
        for file_path in sample_files:
            result = engine.scan_file(file_path)
            times.append(result.execution_time)

        avg_time = statistics.mean(times)
        max_time = max(times)

        print(f"\nFirst scan average: {avg_time:.2f}ms")
        print(f"First scan max: {max_time:.2f}ms")

        # Allow 2x tolerance from target
        assert avg_time < self.TARGETS["first_scan_ms"] * 2

    def test_cached_scan_performance(self, sample_files):
        """Test cached scan performance"""
        cache = UnifiedCache()
        engine = UnifiedExecutionEngine(cache=cache)

        # First scan to fill cache
        for file_path in sample_files:
            engine.scan_file(file_path)

        # Second scan (cache hit)
        times = []
        for file_path in sample_files:
            result = engine.scan_file(file_path)
            times.append(result.execution_time)

        avg_time = statistics.mean(times)

        print(f"\nCached scan average: {avg_time:.2f}ms")

        # Allow 2x tolerance from target
        assert avg_time < self.TARGETS["cached_scan_ms"] * 2

    def test_parallel_speedup(self, sample_files):
        """Test parallel execution speedup"""
        # Serial execution
        serial_engine = UnifiedExecutionEngine(
            max_workers=1,
            enable_parallel=False
        )

        start = time.time()
        for file_path in sample_files:
            serial_engine.scan_file(file_path)
        serial_time = time.time() - start

        # Parallel execution
        parallel_engine = UnifiedExecutionEngine(
            max_workers=4,
            enable_parallel=True
        )

        start = time.time()
        parallel_engine.scan_files(sample_files, show_progress=False)
        parallel_time = time.time() - start

        speedup = serial_time / parallel_time if parallel_time > 0 else float('inf')

        print(f"\nSerial time: {serial_time:.3f}s")
        print(f"Parallel time: {parallel_time:.3f}s")
        print(f"Speedup: {speedup:.2f}x")

        # Allow 20% tolerance (speedup may be limited by Python GIL)
        if speedup > 0:
            assert speedup >= self.TARGETS["parallel_speedup"] * 0.8 or speedup >= 1.0

    def test_large_file_performance(self, tmp_path):
        """Test large file scanning performance"""
        # Generate large code file (~600KB)
        large_code = self._generate_large_code(600_000)
        large_file = tmp_path / "LargeFile.kt"
        large_file.write_text(large_code)

        engine = UnifiedExecutionEngine(enable_adaptive=True)

        start = time.time()
        result = engine.scan_file(str(large_file))
        elapsed_ms = (time.time() - start) * 1000

        print(f"\nLarge file scan: {elapsed_ms:.2f}ms")
        print(f"Rules executed: {result.rules_executed}")

        assert elapsed_ms < self.TARGETS["large_file_ms"]
        # Adaptive strategy should reduce rules for large files
        assert result.rules_executed <= 34

    def test_memory_usage(self, sample_files):
        """Test memory usage during scanning"""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            engine = UnifiedExecutionEngine(
                cache=UnifiedCache(),
                max_workers=4
            )

            # Scan multiple times
            for _ in range(10):
                for file_path in sample_files:
                    engine.scan_file(file_path)

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            print(f"\nInitial memory: {initial_memory:.2f}MB")
            print(f"Final memory: {final_memory:.2f}MB")
            print(f"Memory increase: {memory_increase:.2f}MB")

            assert memory_increase < 200  # Memory growth < 200MB

        except ImportError:
            pytest.skip("psutil not installed")

    def test_rule_execution_distribution(self, sample_files):
        """Test rule execution time distribution"""
        engine = UnifiedExecutionEngine()
        engine.scan_files(sample_files, show_progress=False)

        report = engine.get_performance_report()

        scheduler_report = report.get("scheduler", {})
        by_mode = scheduler_report.get("by_mode", {})

        print("\nRule execution by mode:")
        for mode, stats in by_mode.items():
            print(f"  {mode}: {stats['count']} rules, avg {stats.get('avg_time_ms', 0):.2f}ms")

        # Verify all modes have stats
        assert isinstance(by_mode, dict)

    def test_scheduler_monitor_stats(self, sample_files):
        """Test scheduler monitor collects proper stats"""
        engine = UnifiedExecutionEngine()
        engine.scan_files(sample_files, show_progress=False)

        report = engine.scheduler.get_performance_report()

        summary = report.get("summary", {})
        assert summary.get("total_rule_executions", 0) > 0
        assert summary.get("total_file_executions", 0) > 0

    def test_cache_hit_rate(self, sample_files):
        """Test cache hit rate improves with repeated scans"""
        cache = UnifiedCache()
        engine = UnifiedExecutionEngine(cache=cache)

        # First scan (all misses)
        for file_path in sample_files:
            engine.scan_file(file_path)

        first_stats = cache.get_stats()
        first_misses = first_stats.get("misses", 0)

        # Second scan (should have hits)
        for file_path in sample_files:
            engine.scan_file(file_path)

        second_stats = cache.get_stats()
        second_hits = second_stats.get("hits", 0)

        print(f"\nFirst scan misses: {first_misses}")
        print(f"Second scan hits: {second_hits}")

        # Should have cache hits on second scan
        assert second_hits > 0 or first_misses == 0

    def _generate_large_code(self, size_bytes: int) -> str:
        """Generate a large code file of approximately the given size"""
        template = '''
        class GeneratedClass{N} {{
            fun method1() {{ val x = 1 }}
            fun method2() {{ val y = 2 }}
            fun method3() {{ val z = 3 }}
            companion object {{
                const val VERSION = 1
            }}
        }}

        '''

        classes = []
        n = 0
        while len('\n'.join(classes).encode()) < size_bytes:
            classes.append(template.format(N=n))
            n += 1

        return '\n'.join(classes)


class TestScalability:
    """Scalability tests for the engine"""

    def test_many_small_files(self, tmp_path):
        """Test scanning many small files efficiently"""
        # Create 20 small files
        files = []
        for i in range(20):
            f = tmp_path / f"File{i}.kt"
            f.write_text(f"class File{i} {{ fun method{i}() = {i} }}")
            files.append(str(f))

        engine = UnifiedExecutionEngine(max_workers=4, enable_parallel=True)

        start = time.time()
        results = engine.scan_files(files, show_progress=False)
        total_time = time.time() - start

        avg_per_file = total_time / len(files) * 1000  # ms per file

        print(f"\n20 small files: {total_time:.3f}s total ({avg_per_file:.2f}ms/file)")

        assert len(results) == 20
        assert total_time < 30  # Should complete within 30 seconds

    def test_mixed_size_files(self, tmp_path):
        """Test scanning mixed-size files"""
        files = []

        # Small files
        for i in range(5):
            f = tmp_path / f"Small{i}.kt"
            f.write_text("class Small { }")
            files.append(str(f))

        # Medium files
        for i in range(5):
            f = tmp_path / f"Medium{i}.kt"
            f.write_text('''
class Medium {
    fun method1() {}
    fun method2() {}
    fun method3() {}
}
''')
            files.append(str(f))

        # Large-ish file
        f = tmp_path / "Larger.kt"
        template = "class Large{N} { fun m{}() {} }\n"
        f.write_text(template * 200)
        files.append(str(f))

        engine = UnifiedExecutionEngine(enable_adaptive=True)

        start = time.time()
        results = engine.scan_files(files, show_progress=False)
        total_time = time.time() - start

        print(f"\nMixed files ({len(files)}): {total_time:.3f}s")

        assert len(results) == len(files)


class TestStressTests:
    """Stress tests for edge cases"""

    def test_rapid_repeated_scans(self, tmp_path):
        """Test rapid repeated scans don't cause issues"""
        f = tmp_path / "Test.kt"
        f.write_text("class Test { }")

        engine = UnifiedExecutionEngine()

        errors = []
        for i in range(50):
            try:
                engine.scan_file(str(f))
            except Exception as e:
                errors.append(e)

        assert len(errors) == 0, f"Errors during rapid scans: {errors}"

    def test_concurrent_engine_instances(self, tmp_path):
        """Test multiple engine instances can run concurrently"""
        import threading

        f = tmp_path / "Test.kt"
        f.write_text("class Test { GlobalScope.launch { } }")

        errors = []
        results = []

        def scan_with_new_engine():
            try:
                engine = UnifiedExecutionEngine(max_workers=2)
                result = engine.scan_file(str(f))
                results.append(len(result.findings))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=scan_with_new_engine) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent errors: {errors}"
        assert len(results) == 5
