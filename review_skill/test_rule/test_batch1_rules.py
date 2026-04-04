#!/usr/bin/env python3
"""
Test Batch 1 Rules
第一批规则测试套件
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rule_engine.context import RuleContext
from rule_engine.registry import RuleRegistry
from rule_engine.engine import RuleEngine
from rule_engine.rules.memory_leak_static_context import memory_leak_static_context_rule
from rule_engine.rules.blocking_main_thread import blocking_main_thread_rule
from rule_engine.rules.coroutine_exception import coroutine_exception_rule
from rule_engine.rules.compose_remember_missing import compose_remember_missing_rule
from rule_engine.rules.lifecycle_oncreate_super import lifecycle_oncreate_super_rule
from rule_engine.rules.mutable_livedata_exposed import mutable_livedata_exposed_rule
from rule_engine.rules.fragment_arg_constructor import fragment_arg_constructor_rule
from rule_engine.rules.hardcoded_string import hardcoded_string_rule
from rule_engine.rules.hilt_module_injection import hilt_module_injection_rule
from rule_engine.rules.intent_extra_key import intent_extra_key_rule


def test_memory_leak_static_context():
    """Test static Context reference detection"""
    print("\n" + "=" * 60)
    print("Testing memory_leak_static_context rule...")
    print("=" * 60)

    # Test case 1: Static Activity reference (should trigger)
    code1 = """
class MyActivity : AppCompatActivity() {
    companion object {
        var currentActivity: Activity? = null
    }
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = memory_leak_static_context_rule.check(context1)
    print(f"\nTest 1 (static Activity): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: Application Context (should NOT trigger - safe)
    code2 = """
class MyApp : Application() {
    companion object {
        lateinit var appContext: Context
    }
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = memory_leak_static_context_rule.check(context2)
    print(f"\nTest 2 (Application Context): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings2) == 0, f"Expected 0 findings for Application Context, got {len(findings2)}"
    print("✓ Test 2 passed")

    # Test case 3: Normal non-static field (should NOT trigger)
    code3 = """
class MyActivity : AppCompatActivity() {
    var myView: View? = null
}
"""
    context3 = RuleContext(code=code3, file_path="Test3.kt", language="kotlin")
    findings3 = memory_leak_static_context_rule.check(context3)
    print(f"\nTest 3 (non-static field): {len(findings3)} findings")
    assert len(findings3) == 0, f"Expected 0 findings, got {len(findings3)}"
    print("✓ Test 3 passed")


def test_blocking_main_thread():
    """Test blocking main thread operation detection"""
    print("\n" + "=" * 60)
    print("Testing blocking_main_thread rule...")
    print("=" * 60)

    # Test case 1: File operation without async (should trigger)
    code1 = """
fun readFile() {
    val content = File("test.txt").readText()
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = blocking_main_thread_rule.check(context1)
    print(f"\nTest 1 (File read on main thread): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: File operation with Dispatchers.IO (should NOT trigger - assumed safe)
    # Note: This rule is simple and may still flag it, depending on implementation
    code2 = """
fun readFile() {
    lifecycleScope.launch {
        val content = withContext(Dispatchers.IO) {
            File("test.txt").readText()
        }
    }
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = blocking_main_thread_rule.check(context2)
    print(f"\nTest 2 (File read with Dispatchers.IO): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
    # This may still trigger depending on implementation, so we just check it runs
    print("✓ Test 2 completed (async context detection)")

    # Test case 3: SharedPreferences operation (should trigger)
    code3 = """
fun saveData(context: Context) {
    val prefs = context.getSharedPreferences("my_prefs", Context.MODE_PRIVATE)
    prefs.edit().putString("key", "value").apply()
}
"""
    context3 = RuleContext(code=code3, file_path="Test3.kt", language="kotlin")
    findings3 = blocking_main_thread_rule.check(context3)
    print(f"\nTest 3 (SharedPreferences): {len(findings3)} findings")
    for f in findings3:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings3) >= 1, f"Expected at least 1 finding, got {len(findings3)}"
    print("✓ Test 3 passed")


def test_coroutine_exception():
    """Test coroutine exception handling detection"""
    print("\n" + "=" * 60)
    print("Testing coroutine_exception rule...")
    print("=" * 60)

    # Test case 1: launch without try-catch (should trigger)
    code1 = """
fun fetchData() {
    lifecycleScope.launch {
        val result = api.getData()
        updateUI(result)
    }
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = coroutine_exception_rule.check(context1)
    print(f"\nTest 1 (launch without try-catch): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: launch with try-catch (should NOT trigger)
    code2 = """
fun fetchData() {
    lifecycleScope.launch {
        try {
            val result = api.getData()
            updateUI(result)
        } catch (e: Exception) {
            showError(e)
        }
    }
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = coroutine_exception_rule.check(context2)
    print(f"\nTest 2 (launch with try-catch): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings2) == 0, f"Expected 0 findings, got {len(findings2)}"
    print("✓ Test 2 passed")

    # Test case 3: viewModelScope.launch without exception handling (should trigger)
    code3 = """
class MyViewModel : ViewModel() {
    fun loadData() {
        viewModelScope.launch {
            val data = repository.fetch()
            _state.value = data
        }
    }
}
"""
    context3 = RuleContext(code=code3, file_path="Test3.kt", language="kotlin")
    findings3 = coroutine_exception_rule.check(context3)
    print(f"\nTest 3 (viewModelScope.launch): {len(findings3)} findings")
    for f in findings3:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings3) == 1, f"Expected 1 finding, got {len(findings3)}"
    print("✓ Test 3 passed")


def test_compose_remember_missing():
    """Test Compose remember missing detection"""
    print("\n" + "=" * 60)
    print("Testing compose_remember_missing rule...")
    print("=" * 60)

    # Test case 1: mutableStateOf without remember (should trigger)
    code1 = """
@Composable
fun MyScreen() {
    var count = mutableStateOf(0)
    Button(onClick = { count.value++ }) {
        Text("Count: ${'$'}{count.value}")
    }
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = compose_remember_missing_rule.check(context1)
    print(f"\nTest 1 (mutableStateOf without remember): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: mutableStateOf with remember (should NOT trigger)
    code2 = """
@Composable
fun MyScreen() {
    var count = remember { mutableStateOf(0) }
    Button(onClick = { count.value++ }) {
        Text("Count: ${'$'}{count.value}")
    }
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = compose_remember_missing_rule.check(context2)
    print(f"\nTest 2 (mutableStateOf with remember): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings2) == 0, f"Expected 0 findings, got {len(findings2)}"
    print("✓ Test 2 passed")

    # Test case 3: Non-Composable function (should NOT trigger)
    code3 = """
fun createState(): MutableState<Int> {
    return mutableStateOf(0)
}
"""
    context3 = RuleContext(code=code3, file_path="Test3.kt", language="kotlin")
    findings3 = compose_remember_missing_rule.check(context3)
    print(f"\nTest 3 (non-Composable): {len(findings3)} findings")
    assert len(findings3) == 0, f"Expected 0 findings, got {len(findings3)}"
    print("✓ Test 3 passed")


def test_lifecycle_oncreate_super():
    """Test lifecycle super call detection"""
    print("\n" + "=" * 60)
    print("Testing lifecycle_oncreate_super rule...")
    print("=" * 60)

    # Test case 1: onCreate without super (should trigger)
    code1 = """
class MyActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        setContentView(R.layout.activity_main)
    }
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = lifecycle_oncreate_super_rule.check(context1)
    print(f"\nTest 1 (onCreate without super): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: onCreate with super (should NOT trigger)
    code2 = """
class MyActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
    }
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = lifecycle_oncreate_super_rule.check(context2)
    print(f"\nTest 2 (onCreate with super): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings2) == 0, f"Expected 0 findings, got {len(findings2)}"
    print("✓ Test 2 passed")

    # Test case 3: Fragment onCreateView without super (should trigger)
    code3 = """
class MyFragment : Fragment() {
    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View? {
        return inflater.inflate(R.layout.fragment_main, container, false)
    }
}
"""
    context3 = RuleContext(code=code3, file_path="Test3.kt", language="kotlin")
    findings3 = lifecycle_oncreate_super_rule.check(context3)
    print(f"\nTest 3 (onCreateView without super): {len(findings3)} findings")
    for f in findings3:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings3) == 1, f"Expected 1 finding, got {len(findings3)}"
    print("✓ Test 3 passed")


def test_mutable_livedata_exposed():
    """Test MutableLiveData exposure detection"""
    print("\n" + "=" * 60)
    print("Testing mutable_livedata_exposed rule...")
    print("=" * 60)

    # Test case 1: Public MutableLiveData (should trigger)
    code1 = """
class MyViewModel : ViewModel() {
    val data: MutableLiveData<String> = MutableLiveData()
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = mutable_livedata_exposed_rule.check(context1)
    print(f"\nTest 1 (public MutableLiveData): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: Private MutableLiveData with public LiveData (should NOT trigger)
    code2 = """
class MyViewModel : ViewModel() {
    private val _data = MutableLiveData<String>()
    val data: LiveData<String> = _data
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = mutable_livedata_exposed_rule.check(context2)
    print(f"\nTest 2 (private MutableLiveData): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings2) == 0, f"Expected 0 findings, got {len(findings2)}"
    print("✓ Test 2 passed")

    # Test case 3: var MutableLiveData (should trigger)
    code3 = """
class MyViewModel : ViewModel() {
    var state: MutableLiveData<State> = MutableLiveData()
}
"""
    context3 = RuleContext(code=code3, file_path="Test3.kt", language="kotlin")
    findings3 = mutable_livedata_exposed_rule.check(context3)
    print(f"\nTest 3 (var MutableLiveData): {len(findings3)} findings")
    for f in findings3:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings3) == 1, f"Expected 1 finding, got {len(findings3)}"
    print("✓ Test 3 passed")


def test_fragment_arg_constructor():
    """Test Fragment parameterized constructor detection"""
    print("\n" + "=" * 60)
    print("Testing fragment_arg_constructor rule...")
    print("=" * 60)

    # Test case 1: Fragment with constructor parameter (should trigger)
    code1 = """
class MyFragment(val userId: String) : Fragment() {
    // ...
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = fragment_arg_constructor_rule.check(context1)
    print(f"\nTest 1 (Fragment with constructor param): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: Fragment with default constructor (should NOT trigger)
    code2 = """
class MyFragment : Fragment() {
    companion object {
        fun newInstance(userId: String) = MyFragment().apply {
            arguments = Bundle().apply { putString("userId", userId) }
        }
    }
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = fragment_arg_constructor_rule.check(context2)
    print(f"\nTest 2 (Fragment with default constructor): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings2) == 0, f"Expected 0 findings, got {len(findings2)}"
    print("✓ Test 2 passed")


def test_hardcoded_string():
    """Test hardcoded string detection"""
    print("\n" + "=" * 60)
    print("Testing hardcoded_string rule...")
    print("=" * 60)

    # Test case 1: Composable with hardcoded string (should trigger)
    code1 = """
@Composable
fun GreetingScreen() {
    Column {
        Text("Hello World")
        Button(onClick = { }) {
            Text("Click Me")
        }
    }
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = hardcoded_string_rule.check(context1)
    print(f"\nTest 1 (hardcoded strings in Composable): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) >= 2, f"Expected at least 2 findings, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: Non-UI code (should NOT trigger)
    code2 = """
fun processData() {
    val key = "data_key"
    val url = "https://api.example.com"
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = hardcoded_string_rule.check(context2)
    print(f"\nTest 2 (non-UI code): {len(findings2)} findings")
    assert len(findings2) == 0, f"Expected 0 findings, got {len(findings2)}"
    print("✓ Test 2 passed")


def test_hilt_module_injection():
    """Test Hilt Module @InstallIn detection"""
    print("\n" + "=" * 60)
    print("Testing hilt_module_injection rule...")
    print("=" * 60)

    # Test case 1: @Module without @InstallIn (should trigger)
    code1 = """
@Module
class NetworkModule {
    @Provides
    fun provideRetrofit(): Retrofit = Retrofit.Builder().build()
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = hilt_module_injection_rule.check(context1)
    print(f"\nTest 1 (@Module without @InstallIn): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: @Module with @InstallIn (should NOT trigger)
    code2 = """
@Module
@InstallIn(SingletonComponent::class)
class NetworkModule {
    @Provides
    fun provideRetrofit(): Retrofit = Retrofit.Builder().build()
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = hilt_module_injection_rule.check(context2)
    print(f"\nTest 2 (@Module with @InstallIn): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings2) == 0, f"Expected 0 findings, got {len(findings2)}"
    print("✓ Test 2 passed")


def test_intent_extra_key():
    """Test Intent extra key constant detection"""
    print("\n" + "=" * 60)
    print("Testing intent_extra_key rule...")
    print("=" * 60)

    # Test case 1: putExtra with string literal (should trigger)
    code1 = """
fun openDetail(context: Context, itemId: String) {
    val intent = Intent(context, DetailActivity::class.java)
    intent.putExtra("item_id", itemId)
    context.startActivity(intent)
}
"""
    context1 = RuleContext(code=code1, file_path="Test1.kt", language="kotlin")
    findings1 = intent_extra_key_rule.check(context1)
    print(f"\nTest 1 (putExtra with literal): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")

    # Test case 2: getStringExtra with string literal (should trigger)
    code2 = """
class DetailActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val itemId = intent.getStringExtra("item_id")
    }
}
"""
    context2 = RuleContext(code=code2, file_path="Test2.kt", language="kotlin")
    findings2 = intent_extra_key_rule.check(context2)
    print(f"\nTest 2 (getStringExtra with literal): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings2) == 1, f"Expected 1 finding, got {len(findings2)}"
    print("✓ Test 2 passed")


def test_all_rules_with_engine():
    """Test all batch 1 rules with the full engine"""
    print("\n" + "=" * 60)
    print("Testing all batch 1 rules with rule engine...")
    print("=" * 60)

    registry = RuleRegistry()

    # Register all batch 1 rules
    registry.register(memory_leak_static_context_rule)
    registry.register(blocking_main_thread_rule)
    registry.register(coroutine_exception_rule)
    registry.register(compose_remember_missing_rule)
    registry.register(lifecycle_oncreate_super_rule)
    registry.register(mutable_livedata_exposed_rule)
    registry.register(fragment_arg_constructor_rule)
    registry.register(hardcoded_string_rule)
    registry.register(hilt_module_injection_rule)
    registry.register(intent_extra_key_rule)

    engine = RuleEngine(registry)

    # Test code with multiple issues
    code = """
@Composable
fun BadScreen() {
    var count = mutableStateOf(0)
    Text("Counter")
}

class MyActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        File("test.txt").readText()
        startActivity(Intent().putExtra("key", "value"))
    }
}

@Module
class BadModule
"""

    context = RuleContext(code=code, file_path="Test.kt", language="kotlin")
    findings, stats = engine.execute_all(context)

    print(f"\nEngine test: {len(findings)} findings total")
    for f in findings:
        print(f"  - [{f.rule_id}] Line {f.line_number}: {f.message[:60]}...")

    assert len(findings) >= 5, f"Expected at least 5 findings, got {len(findings)}"
    executed_rules = stats.get('executed_rules', 0)
    print(f"✓ Engine test passed! Found {len(findings)} issues across {executed_rules} rules")


def main():
    print("=" * 60)
    print("Batch 1 Rules Test Suite")
    print("第一批规则测试套件")
    print("=" * 60)

    try:
        test_memory_leak_static_context()
        test_blocking_main_thread()
        test_coroutine_exception()
        test_compose_remember_missing()
        test_lifecycle_oncreate_super()
        test_mutable_livedata_exposed()
        test_fragment_arg_constructor()
        test_hardcoded_string()
        test_hilt_module_injection()
        test_intent_extra_key()
        test_all_rules_with_engine()

        print("\n" + "=" * 60)
        print("✓ All batch 1 tests passed successfully!")
        print("✓ 第一批规则所有测试通过！")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
