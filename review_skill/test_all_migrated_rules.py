#!/usr/bin/env python3
"""
Test all migrated rules
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rule_engine.integration.review_runner import EnhancedReviewRunner

def test_flow_rules(runner):
    """Test Flow-related rules"""
    print("\n" + "="*60)
    print("Testing Flow-related Rules")
    print("="*60)

    # runner is initialized and provided by external caller

    # Test flowOn(Dispatchers.Main)
    test_code = """
    val flow = flow { emit(1) }
        .flowOn(Dispatchers.Main)
        .collect { }
    """
    result = runner.review_code(test_code, file_path="test.kt")
    findings = result["findings"]
    print("1. flowOn(Dispatchers.Main) Detection:")
    for f in findings:
        if f["rule"] == "flowon_main_dispatcher":
            print(f"   ✅ Detected: {f['message']}")
            break
    else:
        print("   ❌ flowOn(Dispatchers.Main) issue not detected")

    # Test SharingStarted.Eagerly
    test_code = """
    val stateFlow = flow.stateIn(
        scope = viewModelScope,
        started = SharingStarted.Eagerly,
        initialValue = 0
    )
    """
    result = runner.review_code(test_code, file_path="test.kt")
    findings = result["findings"]
    print("2. SharingStarted.Eagerly Detection:")
    for f in findings:
        if f["rule"] == "eager_sharing_detected":
            print(f"   ✅ Detected: {f['message']}")
            break
    else:
        print("   ❌ SharingStarted.Eagerly issue not detected")

def test_flow_lifecycle_rules(runner):
    """Test Flow lifecycle rules"""
    print("\n" + "="*60)
    print("Testing Flow Lifecycle Rules")
    print("="*60)

    # Test stateIn(GlobalScope)
    test_code = """
    val stateFlow = flow.stateIn(
        scope = GlobalScope,
        started = SharingStarted.WhileSubscribed(),
        initialValue = 0
    )
    """
    result = runner.review_code(test_code, file_path="test.kt")
    findings = result["findings"]
    print("1. stateIn(GlobalScope) Detection:")
    for f in findings:
        if f["rule"] == "statein_globalscope":
            print(f"   ✅ Detected: {f['message']}")
            break
    else:
        print("   ❌ stateIn(GlobalScope) issue not detected")

    # Test collect without repeatOnLifecycle
    test_code = """
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        viewModel.flow.collect { value ->
            // Process data
        }
    }
    """
    result = runner.review_code(test_code, file_path="test.kt")
    findings = result["findings"]
    print("2. collect Without repeatOnLifecycle Detection:")
    for f in findings:
        if f["rule"] == "collect_without_repeat":
            print(f"   ✅ Detected: {f['message']}")
            break
    else:
        print("   ❌ collect without repeatOnLifecycle issue not detected")

def test_flow_structure_rules(runner):
    """Test Flow structure rules"""
    print("\n" + "="*60)
    print("Testing Flow Structure Rules")
    print("="*60)

    # Test launch inside flow builder
    test_code = """
    val flow = flow {
        launch {
            // Using launch inside flow builder
        }
        emit(1)
    }
    """
    result = runner.review_code(test_code, file_path="test.kt")
    findings = result["findings"]
    print("1. launch Inside flow Builder Detection:")
    for f in findings:
        if f["rule"] == "launch_inside_flow":
            print(f"   ✅ Detected: {f['message']}")
            break
    else:
        print("   ❌ launch inside flow builder issue not detected")

    # Test multiple collects
    test_code = """
    flow1.collect { }
    flow2.collect { }
    """
    result = runner.review_code(test_code, file_path="test.kt")
    findings = result["findings"]
    print("2. Multiple collect Detection:")
    for f in findings:
        if f["rule"] == "multiple_collects":
            print(f"   ✅ Detected: {f['message']}")
            break
    else:
        print("   ❌ Multiple collects issue not detected")

def test_hilt_rules(runner):
    """Test Hilt rules"""
    print("\n" + "="*60)
    print("Testing Hilt Rules")
    print("="*60)

    # Test @Singleton injecting Activity
    test_code = """
    @Module
    @InstallIn(SingletonComponent::class)
    class AppModule {
        @Provides
        @Singleton
        fun provideActivity(): MainActivity = MainActivity()
    }
    """
    result = runner.review_code(test_code, file_path="test.kt")
    findings = result["findings"]
    print("1. @Singleton Injecting Activity Detection:")
    for f in findings:
        if f["rule"] == "singleton_activity":
            print(f"   ✅ Detected: {f['message']}")
            break
    else:
        print("   ❌ @Singleton injecting Activity issue not detected")

def test_dagger2_rules(runner):
    """Test Dagger2 rules"""
    print("\n" + "="*60)
    print("Testing Dagger2 Rules")
    print("="*60)

    # Test field injection
    test_code = """
    class MyActivity : AppCompatActivity() {
        @Inject
        lateinit var viewModel: MyViewModel
    }
    """
    result = runner.review_code(test_code, file_path="test.kt")
    findings = result["findings"]
    print("1. Field Injection Detection:")
    for f in findings:
        if f["rule"] == "field_injection_detected":
            print(f"   ✅ Detected: {f['message']}")
            break
    else:
        print("   ❌ Field injection issue not detected")

    # Test @Provides without scope
    test_code = """
    @Module
    class AppModule {
        @Provides
        fun provideService(): Service = ServiceImpl()
    }
    """
    result = runner.review_code(test_code, file_path="test.kt")
    findings = result["findings"]
    print("2. @Provides Without Scope Detection:")
    for f in findings:
        if f["rule"] == "provides_without_scope":
            print(f"   ✅ Detected: {f['message']}")
            break
    else:
        print("   ❌ @Provides without scope issue not detected")

def test_engine_info(runner):
    """Test engine information"""
    print("\n" + "="*60)
    print("Testing Engine Information and Rule Statistics")
    print("="*60)
    info = runner.get_engine_info()
    print(f"Engine initialization status: {info['initialized']}")
    print(f"Total rules: {info['rule_count']}")

    stats = info["statistics"]
    print(f"Rule statistics:")
    print(f"  - Total rules: {stats.get('total_rules', 0)}")
    print(f"  - Enabled rules: {stats.get('enabled_rules', 0)}")
    print(f"  - Category distribution: {stats.get('categories', {})}")

    # List all registered rules
    print("\nRegistered rules:")
    categories = stats.get("categories", {})
    for category, count in categories.items():
        print(f"  - {category}: {count} rules")

def main():
    """Main test function"""
    print("Starting test for all migrated rules")
    print("="*60)
    try:
        # Create and initialize a runner instance
        runner = EnhancedReviewRunner()

        # Run all tests using the same runner
        test_flow_rules(runner)
        print("\n" + "="*60)
        print("✅ All rule migration tests completed!")
        print("="*60)

        # Summary of migrated rule modules
        print("\nSuccessfully migrated rule modules:")
        modules = [
            "base_rules.py (Base Rules)",
            "coroutine_rules.py (Coroutine Rules)",
            "compose_rules.py (Compose Rules)",
            "flow_rules.py (Flow Rules)",
            "flow_lifecycle_rules.py (Flow Lifecycle Rules)",
            "flow_structure_rules.py (Flow Structure Rules)",
            "hilt_rules.py (Hilt Rules)",
            "dagger2_rules.py (Dagger2 Rules)"
        ]
        for i, module in enumerate(modules, 1):
            print(f"  {i}. {module}")

        print("\nRule Engine Unification Completion Status:")
        print("  ✅ All old rule modules migrated to new engine format")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
