"""
Test Enhanced AST Rules - 改进的 AST 规则测试

测试从字符串规则迁移到 AST 规则后的精确性提升。
重点验证假阳性减少情况。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ast_engine.parser_v2 import parse_kotlin_ast
from ast_engine.nodes import ASTNode, NodeType
from ast_engine.rules.enhanced_rules import (
    NoGlobalScopeASTRule,
    ViewModelContextASTRule,
    MainThreadIOASTRule,
    UnspecifiedScopeASTRule,
    RememberContextASTRule,
    MissingFlowOnASTRule,
    MutableStateFlowExposedASTRule,
    SingletonActivityASTRule,
    CollectWithoutRepeatASTRule,
    MultipleCollectsASTRule,
)


class TestResult:
    """测试结果记录"""
    def __init__(self, name: str, passed: bool, findings_count: int, expected_count: int, notes: str = ""):
        self.name = name
        self.passed = passed
        self.findings_count = findings_count
        self.expected_count = expected_count
        self.notes = notes


def test_no_globalscope_ast():
    """测试改进的 GlobalScope 检测 - 应排除注释中的匹配"""
    print("\n🧪 测试 NoGlobalScopeASTRule（排除注释匹配）...")

    rule = NoGlobalScopeASTRule()

    # 测试代码：包含实际使用和注释
    code = '''
class TestClass {
    fun actualUsage() {
        // 实际使用 GlobalScope - 应该被检测
        GlobalScope.launch {
            println("bad")
        }
    }

    fun inComment() {
        // 注释中提到的 GlobalScope.launch 不应该被检测
        /* GlobalScope.async { } */
        viewModelScope.launch { }
    }
}
'''

    ast = parse_kotlin_ast(code)
    findings = rule.check(ast, "Test.kt")

    # 应该只检测到一个（实际使用），注释中的不应该被检测
    expected = 1
    passed = len(findings) == expected

    notes = f"发现 {len(findings)} 个问题"
    for f in findings:
        notes += f"\n   - 行{f.line_number}: {f.message[:50]}"

    if not passed:
        notes += f"\n   ❌ 预期 {expected} 个，实际 {len(findings)} 个"
    else:
        notes += "\n   ✅ 正确排除了注释中的 GlobalScope 引用"

    print(notes)
    return TestResult("NoGlobalScope AST", passed, len(findings), expected, notes)


def test_viewmodel_context_ast():
    """测试改进的 ViewModel Context 检测 - 应精确识别类内属性"""
    print("\n🧪 测试 ViewModelContextASTRule（精确类内检测）...")

    rule = ViewModelContextASTRule()

    code = '''
// 普通类持有 Context - 不在 ViewModel 中，不应该被检测
class NormalClass(val context: Context) {
    fun doSomething() {}
}

// 错误的 ViewModel - 持有 Context，应该被检测
class BadViewModel(
    private val context: Context  // 错误
) : ViewModel() {
    val activity: Activity? = null  // 错误
}

// 正确的 ViewModel - 使用 Application
class GoodViewModel(
    application: Application
) : AndroidViewModel(application) {
    private val repository: MyRepository  // 正常依赖
}
'''

    ast = parse_kotlin_ast(code)
    findings = rule.check(ast, "Test.kt")

    # 应该检测到 BadViewModel 中的两个 Context 引用
    expected = 2
    passed = len(findings) == expected

    notes = f"发现 {len(findings)} 个问题"
    for f in findings:
        notes += f"\n   - 行{f.line_number}: {f.message[:40]}"

    if not passed:
        notes += f"\n   ❌ 预期 {expected} 个，实际 {len(findings)} 个"
        if len(findings) > expected:
            notes += "\n   ⚠️ 可能误报了非 ViewModel 类"
        else:
            notes += "\n   ⚠️ 可能漏报了 ViewModel 中的 Context"
    else:
        notes += "\n   ✅ 正确识别 ViewModel 类并检测 Context 持有"

    print(notes)
    return TestResult("ViewModelContext AST", passed, len(findings), expected, notes)


def test_main_thread_io_ast():
    """测试改进的主线程 IO 检测 - 应在同一作用域内检测"""
    print("\n🧪 测试 MainThreadIOASTRule（同一作用域检测）...")

    rule = MainThreadIOASTRule()

    code = '''
class TestClass {
    // 错误：在 Dispatchers.Main 中执行 IO
    fun badFunction() {
        withContext(Dispatchers.Main) {
            val data = File("test.txt").readText()
        }
    }

    // 正确：IO 操作在 IO 调度器中
    fun goodFunction() {
        withContext(Dispatchers.IO) {
            val data = File("test.txt").readText()
        }
    }

    // 文件中有 Dispatchers.Main，但没有 IO 操作
    fun uiOnlyFunction() {
        withContext(Dispatchers.Main) {
            updateUI()
        }
    }
}
'''

    ast = parse_kotlin_ast(code)
    findings = rule.check(ast, "Test.kt")

    # 应该只检测到一个（badFunction）
    expected = 1
    passed = len(findings) == expected

    notes = f"发现 {len(findings)} 个问题"
    for f in findings:
        notes += f"\n   - 行{f.line_number}: {f.message[:40]}"

    if not passed:
        notes += f"\n   ❌ 预期 {expected} 个，实际 {len(findings)} 个"
    else:
        notes += "\n   ✅ 正确区分了作用域内的 IO 操作"

    print(notes)
    return TestResult("MainThreadIO AST", passed, len(findings), expected, notes)


def test_unspecified_scope_ast():
    """测试改进的未指定作用域检测 - 应排除对象方法调用"""
    print("\n🧪 测试 UnspecifiedScopeASTRule（排除对象方法）...")

    rule = UnspecifiedScopeASTRule()

    code = '''
class TestClass {
    // 错误：未指定作用域
    fun badFunction() {
        launch {
            println("bad")
        }
    }

    // 正确：有明确作用域
    fun goodFunction() {
        viewModelScope.launch {
            println("good")
        }
        coroutineScope.launch {
            println("good")
        }
    }

    // 正确：对象方法调用（不应被检测）
    fun objectMethodCall() {
        someObject.launch { }  // 这是对象的 launch 方法，不是协程构建器
    }
}
'''

    ast = parse_kotlin_ast(code)
    findings = rule.check(ast, "Test.kt")

    # 应该只检测到一个（badFunction 中的 launch）
    expected = 1
    passed = len(findings) == expected

    notes = f"发现 {len(findings)} 个问题"
    for f in findings:
        notes += f"\n   - 行{f.line_number}: {f.message[:40]}"

    if not passed:
        notes += f"\n   ❌ 预期 {expected} 个，实际 {len(findings)} 个"
        if len(findings) > expected:
            notes += "\n   ⚠️ 可能将对象方法调用误判为协程构建器"
    else:
        notes += "\n   ✅ 正确排除了对象方法调用"

    print(notes)
    return TestResult("UnspecifiedScope AST", passed, len(findings), expected, notes)


def test_remember_context_ast():
    """测试改进的 remember Context 检测 - 应在 Composable 函数中检测"""
    print("\n🧪 测试 RememberContextASTRule（Composable 内检测）...")

    rule = RememberContextASTRule()

    code = '''
// 普通函数中使用 remember - 不是 Composable，不应该检测（编译错误）
fun normalFunction() {
    val value = remember { 0 }
}

// Composable 函数中正确使用 remember
@Composable
fun GoodComposable() {
    val state = remember { mutableStateOf(0) }
}

// Composable 函数中错误使用 remember 持有 Context
@Composable
fun BadComposable(context: Context) {
    val holder = remember { ContextHolder(context) }  // 错误
}
'''

    ast = parse_kotlin_ast(code)
    findings = rule.check(ast, "Test.kt")

    # 应该只检测到一个（BadComposable）
    expected = 1
    passed = len(findings) == expected

    notes = f"发现 {len(findings)} 个问题"
    for f in findings:
        notes += f"\n   - 行{f.line_number}: {f.message[:40]}"

    if not passed:
        notes += f"\n   ❌ 预期 {expected} 个，实际 {len(findings)} 个"
    else:
        notes += "\n   ✅ 正确识别 Composable 函数中的 remember Context"

    print(notes)
    return TestResult("RememberContext AST", passed, len(findings), expected, notes)


def test_missing_flowon_ast():
    """测试改进的 Flow flowOn 检测 - 应在返回 Flow 的函数中检测"""
    print("\n🧪 测试 MissingFlowOnASTRule（Flow 函数内检测）...")

    rule = MissingFlowOnASTRule()

    code = '''
class Repository {
    // 错误：返回 Flow 的函数中进行 IO 操作但未指定 flowOn
    fun getDataFlow(): Flow<Data> = flow {
        val data = database.query()  // IO 操作
        emit(data)
    }

    // 正确：指定了 flowOn
    fun getDataFlowCorrect(): Flow<Data> = flow {
        val data = database.query()
        emit(data)
    }.flowOn(Dispatchers.IO)

    // 普通函数，不返回 Flow
    fun getData(): Data {
        return database.query()  // 不在 Flow 中，不检测
    }
}
'''

    ast = parse_kotlin_ast(code)
    findings = rule.check(ast, "Test.kt")

    # 应该只检测到一个（getDataFlow）
    expected = 1
    passed = len(findings) == expected

    notes = f"发现 {len(findings)} 个问题"
    for f in findings:
        notes += f"\n   - 行{f.line_number}: {f.message[:40]}"

    if not passed:
        notes += f"\n   ❌ 预期 {expected} 个，实际 {len(findings)} 个"
    else:
        notes += "\n   ✅ 正确识别了需要 flowOn 的 Flow 构建器"

    print(notes)
    return TestResult("MissingFlowOn AST", passed, len(findings), expected, notes)


def test_mutable_stateflow_exposed_ast():
    """测试改进的 MutableStateFlow 暴露检测 - 应检查可见性修饰符"""
    print("\n🧪 测试 MutableStateFlowExposedASTRule（可见性检测）...")

    rule = MutableStateFlowExposedASTRule()

    code = '''
class ViewModel {
    // 错误：公开暴露 MutableStateFlow
    val _state = MutableStateFlow(0)
    val state: StateFlow<Int> = _state

    // 正确：private 修饰
    private val _privateState = MutableStateFlow(0)
    val publicState: StateFlow<Int> = _privateState.asStateFlow()

    // 错误：internal 也是暴露
    internal val _internalState = MutableStateFlow(0)
}
'''

    ast = parse_kotlin_ast(code)
    findings = rule.check(ast, "Test.kt")

    # 应该检测到两个（_state 和 _internalState）
    expected = 2
    passed = len(findings) == expected

    notes = f"发现 {len(findings)} 个问题"
    for f in findings:
        notes += f"\n   - 行{f.line_number}: {f.message[:40]}"

    if not passed:
        notes += f"\n   ❌ 预期 {expected} 个，实际 {len(findings)} 个"
    else:
        notes += "\n   ✅ 正确识别了非 private 的 MutableStateFlow"

    print(notes)
    return TestResult("MutableStateFlowExposed AST", passed, len(findings), expected, notes)


def test_collect_without_repeat_ast():
    """测试改进的 collect 检测 - 应在 Activity/Fragment 中检测"""
    print("\n🧪 测试 CollectWithoutRepeatASTRule（UI 层检测）...")

    rule = CollectWithoutRepeatASTRule()

    code = '''
// ViewModel 中 collect - 不需要 repeatOnLifecycle
class MyViewModel : ViewModel() {
    fun collectData() {
        flow.collect { }  // 不需要检测
    }
}

// Activity 中 collect - 需要 repeatOnLifecycle
class MyActivity : AppCompatActivity() {
    fun setupCollector() {
        lifecycleScope.launch {
            flow.collect { }  // 错误：缺少 repeatOnLifecycle
        }
    }

    fun setupCorrect() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                flow.collect { }  // 正确
            }
        }
    }
}
'''

    ast = parse_kotlin_ast(code)
    findings = rule.check(ast, "Test.kt")

    # 应该只检测到一个（Activity 中的 collect）
    expected = 1
    passed = len(findings) == expected

    notes = f"发现 {len(findings)} 个问题"
    for f in findings:
        notes += f"\n   - 行{f.line_number}: {f.message[:40]}"

    if not passed:
        notes += f"\n   ❌ 预期 {expected} 个，实际 {len(findings)} 个"
        if len(findings) > expected:
            notes += "\n   ⚠️ 可能误报了 ViewModel 中的 collect"
    else:
        notes += "\n   ✅ 正确只在 UI 层检测 collect"

    print(notes)
    return TestResult("CollectWithoutRepeat AST", passed, len(findings), expected, notes)


def test_multiple_collects_ast():
    """测试改进的多次 collect 检测 - 应区分不同 Flow"""
    print("\n🧪 测试 MultipleCollectsASTRule（区分不同 Flow）...")

    rule = MultipleCollectsASTRule()

    code = '''
class TestClass {
    fun collectMultipleTimes() {
        // 同一 Flow 被多次收集 - 应该检测
        dataFlow.collect { }
        dataFlow.collect { }

        // 不同 Flow 被收集 - 不应该检测
        otherFlow.collect { }
    }

    fun collectDifferentFlows() {
        flow1.collect { }
        flow2.collect { }
        flow3.collect { }
    }
}
'''

    ast = parse_kotlin_ast(code)
    findings = rule.check(ast, "Test.kt")

    # 应该只检测到一个（dataFlow 被多次收集）
    expected = 1
    passed = len(findings) == expected

    notes = f"发现 {len(findings)} 个问题"
    for f in findings:
        notes += f"\n   - 行{f.line_number}: {f.message[:40]}"

    if not passed:
        notes += f"\n   ❌ 预期 {expected} 个，实际 {len(findings)} 个"
    else:
        notes += "\n   ✅ 正确区分了同一 Flow 的多次收集和不同 Flow 的收集"

    print(notes)
    return TestResult("MultipleCollects AST", passed, len(findings), expected, notes)


def test_false_positives_reduction():
    """测试假阳性减少情况 - 与原字符串规则对比"""
    print("\n🧪 测试假阳性减少情况...")

    code = '''
class ExampleViewModel : ViewModel() {
    // 1. 注释中的 GlobalScope - 原规则可能误报
    // 不要使用 GlobalScope.launch

    // 2. 私有 MutableStateFlow - 原规则可能误报（private 在不同行）
    private val _state =
        MutableStateFlow(0)

    // 3. 在 ViewModel 中 collect - 原规则可能误报（不需要 repeatOnLifecycle）
    fun init() {
        repository.dataFlow.collect { }
    }
}
'''

    results = []

    # 测试各个规则
    rules_to_test = [
        ("NoGlobalScope", NoGlobalScopeASTRule()),
        ("MutableStateFlow", MutableStateFlowExposedASTRule()),
        ("CollectWithoutRepeat", CollectWithoutRepeatASTRule()),
    ]

    notes = ""
    for name, rule in rules_to_test:
        ast = parse_kotlin_ast(code)
        findings = rule.check(ast, "Test.kt")
        results.append((name, len(findings)))
        notes += f"\n   {name}: {len(findings)} 个问题"

    # 所有规则都应该没有发现问题（都是合法代码）
    total_findings = sum(f for _, f in results)
    passed = total_findings == 0

    if passed:
        notes += "\n   ✅ 所有规则都正确识别了合法代码，无假阳性"
    else:
        notes += f"\n   ❌ 发现 {total_findings} 个假阳性"

    print(notes)
    return TestResult("False Positives Reduction", passed, total_findings, 0, notes)


def main():
    print("=" * 70)
    print("🧪 改进的 AST 规则测试")
    print("=" * 70)
    print("\n本测试验证从字符串规则迁移到 AST 规则后的精确性提升：")
    print("- 排除注释/字符串中的误匹配")
    print("- 精确识别代码结构和作用域")
    print("- 减少假阳性")

    tests = [
        test_no_globalscope_ast,
        test_viewmodel_context_ast,
        test_main_thread_io_ast,
        test_unspecified_scope_ast,
        test_remember_context_ast,
        test_missing_flowon_ast,
        test_mutable_stateflow_exposed_ast,
        test_collect_without_repeat_ast,
        test_multiple_collects_ast,
        test_false_positives_reduction,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            results.append(TestResult(test_func.__name__, False, 0, 0, str(e)))

    # 总结
    print("\n" + "=" * 70)
    print("📊 测试结果总结")
    print("=" * 70)

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)

    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"\n{status} {r.name}")
        print(f"   发现: {r.findings_count} | 预期: {r.expected_count}")

    print(f"\n\n总计: {passed_count}/{total_count} 测试通过")

    # 计算误报率改进（理论值）
    print("\n" + "=" * 70)
    print("📈 规则精确性改进（基于 PLAN_v3.md 分析）")
    print("=" * 70)

    improvements = [
        ("no_globalscope", "15%", "<2%", "排除注释/字符串匹配"),
        ("viewmodel_context", "40%", "<5%", "精确识别 ViewModel 类"),
        ("main_thread_io", "30%", "<5%", "同一作用域检测"),
        ("unspecified_scope", "25%", "<3%", "排除对象方法调用"),
        ("remember_context", "20%", "<3%", "精确 Composable 检测"),
        ("missing_flowon_for_io", "35%", "<5%", "Flow 返回类型检查"),
        ("mutable_stateflow_exposed", "20%", "<2%", "可见性修饰符检查"),
        ("collect_without_repeat", "15%", "<3%", "UI 层精确检测"),
        ("multiple_collects", "20%", "<5%", "Flow 名称区分"),
    ]

    print(f"\n{'规则':<25} {'原误报率':<10} {'目标误报率':<12} {'改进方式'}")
    print("-" * 70)
    for rule, old, new, method in improvements:
        print(f"{rule:<25} {old:<10} {new:<12} {method}")

    print("\n" + "=" * 70)
    if passed_count == total_count:
        print("🎉 所有测试通过！AST 规则迁移成功。")
    else:
        print(f"⚠️ {total_count - passed_count} 个测试需要关注")
    print("=" * 70)

    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
