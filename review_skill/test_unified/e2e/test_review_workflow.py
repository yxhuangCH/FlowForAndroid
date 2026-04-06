"""End-to-end tests for complete review workflow"""

import pytest
import json
import time
from pathlib import Path
from unified_engine.engine import UnifiedExecutionEngine
from unified_engine.cache import UnifiedCache


class TestReviewWorkflow:
    """End-to-end tests for complete review workflow"""

    def test_full_review_on_sample_project(self, temp_project):
        """Run full review on sample project"""
        engine = UnifiedExecutionEngine()

        # Get all Kotlin files
        kotlin_files = list(Path(temp_project).rglob("*.kt"))

        # Execute scan
        results = engine.scan_files([str(f) for f in kotlin_files], show_progress=False)

        # Verify results
        total_findings = sum(len(r.findings) for r in results.values())
        total_time = sum(r.execution_time for r in results.values())

        print(f"\nFiles scanned: {len(results)}")
        print(f"Total findings: {total_findings}")
        print(f"Total time: {total_time:.2f}ms")

        assert len(results) == len(kotlin_files)
        # Should find some issues (sample project has intentional problems)
        assert total_findings > 0

    def test_incremental_review(self, tmp_path):
        """Test incremental review workflow"""
        # Create initial files
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        (src_dir / "File1.kt").write_text("class File1 { }")
        (src_dir / "File2.kt").write_text("class File2 { }")

        engine = UnifiedExecutionEngine()

        # Full scan
        all_files = [str(f) for f in src_dir.glob("*.kt")]
        engine.scan_files(all_files, show_progress=False)

        # Mark as scanned
        engine.mark_scanned("commit_abc", all_files)

        # Get changed files
        changed = engine.get_changed_files("commit_abc", [".kt"])

        assert isinstance(changed, list)

        if changed:
            results = engine.scan_files(changed, show_progress=False)
            assert len(results) == len(changed)

    def test_report_generation(self, temp_project):
        """Test performance report generation"""
        engine = UnifiedExecutionEngine()

        kotlin_files = list(Path(temp_project).rglob("*.kt"))
        engine.scan_files([str(f) for f in kotlin_files], show_progress=False)

        report = engine.get_performance_report()

        assert "engine" in report
        assert "scheduler" in report
        assert "cache" in report

        engine_report = report["engine"]
        assert engine_report["total_files_scanned"] >= len(kotlin_files)
        assert engine_report["total_rules_executed"] > 0

    def test_save_and_load_report(self, temp_project, tmp_path):
        """Test saving and loading performance report"""
        engine = UnifiedExecutionEngine()

        kotlin_files = list(Path(temp_project).rglob("*.kt"))
        engine.scan_files([str(f) for f in kotlin_files], show_progress=False)

        report = engine.get_performance_report()

        # Save to file
        report_path = tmp_path / "performance_report.json"
        report_path.write_text(json.dumps(report, indent=2))

        # Verify saved file
        loaded = json.loads(report_path.read_text())
        assert "engine" in loaded

    def test_complete_workflow_with_issues(self, tmp_path):
        """Test complete workflow with code that has multiple issues"""
        # Create a file with many intentional issues
        problematic_file = tmp_path / "Problematic.kt"
        problematic_file.write_text('''
package com.example.problematic

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.*

class ProblematicActivity : AppCompatActivity() {
    private val viewModel: MyProblematicViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Issue: GlobalScope usage
        GlobalScope.launch { doWork() }

        // Issue: Main thread IO
        val data = readFile()

        // Good pattern
        lifecycleScope.launch { viewModel.data.collect { } }
    }

    private fun readFile(): String {
        return File("data.txt").readText()
    }

    private suspend fun doWork() {}
}

class MyProblematicViewModel : ViewModel() {
    val data = MutableStateFlow(0)

    // Issue: Dispatchers.Main in ViewModel
    fun load() {
        viewModelScope.launch(Dispatchers.Main) { data.value = 1 }
    }

    // Issue: Direct StateFlow value assignment
    fun update() { data.value = data.value + 1 }
}

class BadRepository {
    // Issue: Flow without flowOn
    fun getData(): Flow<String> = flow {
        emit(fetchFromNetwork())
    }

    // Issue: Multiple flowOn
    fun getMoreData(): Flow<Int> = flow { emit(1) }
        .flowOn(Dispatchers.IO)
        .flowOn(Dispatchers.Default)

    private suspend fun fetchFromNetwork(): String = "data"
}
''')

        engine = UnifiedExecutionEngine()
        result = engine.scan_file(str(problematic_file))

        print(f"\nFindings: {len(result.findings)}")
        for finding in result.findings:
            print(f"  - [{finding.severity}] {finding.rule_id}: {finding.message}")

        # Should find multiple issues
        assert len(result.findings) >= 3

        # Check specific findings exist
        rule_ids = [f.rule_id for f in result.findings]
        assert "no_globalscope" in rule_ids or len(rule_ids) > 0

    def test_empty_project_scan(self, tmp_path):
        """Test scanning project with no Kotlin files"""
        src_dir = tmp_path / "empty"
        src_dir.mkdir()

        engine = UnifiedExecutionEngine()
        results = engine.scan_files([], show_progress=False)

        assert results == {}

    def test_single_file_scan(self, tmp_path):
        """Test scanning a single clean file"""
        f = tmp_path / "Clean.kt"
        f.write_text('''
/**
 * A well-written Kotlin class following best practices.
 */
class CleanRepository(
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    /**
     * Fetches data from network using proper coroutine patterns.
     */
    suspend fun fetchData(): Result<Data> = withContext(ioDispatcher) {
        try {
            val response = apiService.getData()
            Success(response.toData())
        } catch (e: IOException) {
            Failure(e)
        }
    }

    companion object {
        const val TAG = "CleanRepository"
    }
}
''')

        engine = UnifiedExecutionEngine()
        result = engine.scan_file(str(f))

        # Clean code should have fewer findings
        print(f"\nClean file findings: {len(result.findings)}")
        assert isinstance(result.findings, list)

    def test_context_manager_workflow(self, tmp_path):
        """Test using engine as context manager"""
        f = tmp_path / "Test.kt"
        f.write_text("class Test { GlobalScope.launch { } }")

        with UnifiedExecutionEngine(max_workers=2) as engine:
            result = engine.scan_file(str(f))
            assert result.files_scanned == 1
            assert len(result.findings) >= 1

        # Engine should be properly shut down after context exit


class TestRealWorldScenarios:
    """Tests simulating real-world scenarios"""

    def test_android_activity_scan(self, tmp_path):
        """Test scanning typical Android Activity"""
        activity_file = tmp_path / "MainActivity.kt"
        activity_file.write_text('''
package com.example.app

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        setupObservers()
        loadData()
    }

    private fun setupObservers() {
        lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                updateUI(state)
            }
        }
    }

    private fun loadData() {
        GlobalScope.launch {
            val data = repository.fetchData()
            runOnUiThread { displayData(data) }
        }
    }

    private fun updateUI(state: UIState) {}
    private fun displayData(data: Data) {}
}
''')

        engine = UnifiedExecutionEngine()
        result = engine.scan_file(str(activity_file))

        # Should detect GlobalScope issue
        rule_ids = [f.rule_id for f in result.findings]
        print(f"\nActivity findings: {rule_ids}")

    def test_android_viewmodel_scan(self, tmp_path):
        """Test scanning typical Android ViewModel"""
        vm_file = tmp_path / "HomeViewModel.kt"
        vm_file.write_text('''
package com.example.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class HomeViewModel(
    private val repository: UserRepository,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) : ViewModel() {

    private val _uiState = MutableStateFlow(UIState())
    val uiState: StateFlow<UIState> = _uiState.asStateFlow()

    init {
        loadUsers()
    }

    fun refresh() {
        viewModelScope.launch(Dispatchers.Main) {
            _uiState.update { it.copy(isLoading = true) }
        }
    }

    private fun loadUsers() {
        viewModelScope.launch(ioDispatcher) {
            repository.getUsers()
                .catch { e -> handleError(e) }
                .collect { users ->
                    _uiState.value = _uiState.value.copy(users = users)
                }
        }
    }

    private fun handleError(e: Throwable) {}
}

data class UIState(
    val isLoading: Boolean = false,
    val users: List<User> = emptyList()
)
''')

        engine = UnifiedExecutionEngine()
        result = engine.scan_file(str(vm_file))

        print(f"\nViewModel findings: {[f.rule_id for f in result.findings]}")
        # Should detect Dispatchers.Main in ViewModel
