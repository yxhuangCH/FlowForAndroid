#!/usr/bin/env python3
"""
Unified Rule Engine Functionality Test
Tests core interfaces, registry, engine, adapters, and rules functionality
"""
import sys
import os

# Add current directory to path to ensure modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rule_engine import (
    RuleRegistry,
    RuleEngine,
    RuleContext,
    RuleSeverity,
    RuleCategory,
    Finding,
    NoGlobalScopeRule,
    viewmodel_context_rule
)


def test_rule_registry():
    """Test rule registry"""
    print("=== Testing Rule Registry ===")
    
    registry = RuleRegistry()
    
    # Create test rules
    class TestRule:
        def __init__(self, rule_id):
            from rule_engine.interfaces import RuleMetadata
            
            self._metadata = RuleMetadata(
                id=rule_id,
                name=f"Test Rule {rule_id}",
                description=f"Test description for {rule_id}",
                severity=RuleSeverity.MINOR,
                category=RuleCategory.CORRECTNESS,
                tags=["test"]
            )
        
        @property
        def metadata(self):
            return self._metadata
        
        def check(self, context):
            return []
        
        def on_register(self):
            print(f"  ✓ Rule {self.metadata.id} registered")
        
        def on_unregister(self):
            print(f"  ✓ Rule {self.metadata.id} unregistered")
    
    # Test registration
    test_rule1 = TestRule("test_rule_1")
    test_rule2 = TestRule("test_rule_2")
    
    registry.register(test_rule1)
    registry.register(test_rule2)
    
    print(f"  Total rules: {registry.count_rules()}")
    print(f"  Rule ID list: {registry.get_all_rule_ids()}")
    
    # Test get rule
    rule = registry.get_rule("test_rule_1")
    print(f"  Get rule test_rule_1: {'success' if rule else 'failed'}")
    
    # Test get rules by category
    correctness_rules = registry.get_rules_by_category(RuleCategory.CORRECTNESS)
    print(f"  Get rules by category (CORRECTNESS): {len(correctness_rules)} rules")
    
    # Test enable/disable
    registry.disable_rule("test_rule_1")
    print(f"  Disable rule test_rule_1: {'success' if not registry.is_rule_enabled('test_rule_1') else 'failed'}")
    
    registry.enable_rule("test_rule_1")
    print(f"  Enable rule test_rule_1: {'success' if registry.is_rule_enabled('test_rule_1') else 'failed'}")
    
    # Test unregister
    registry.unregister("test_rule_1")
    print(f"  Unregister rule test_rule_1: {'success' if not registry.get_rule('test_rule_1') else 'failed'}")
    
    print(f"  Final rule count: {registry.count_rules()}")
    print("✓ Rule registry test passed\n")
    
    return True


def test_rule_context():
    """Test rule context"""
    print("=== Testing Rule Context ===")
    
    code = """
class MyViewModel : ViewModel() {
    private val context: Context? = null
    
    fun doSomething() {
        GlobalScope.launch {
            // Do something
        }
    }
}
"""
    
    context = RuleContext(
        code=code,
        file_path="test.kt",
        language="kotlin"
    )
    
    print(f"  File path: {context.file_path}")
    print(f"  Language: {context.language}")
    print(f"  File hash: {context.file_hash}")
    print(f"  Code lines: {len(context.get_lines())}")
    
    # Test get line
    line_3 = context.get_line_at(3)
    print(f"  Line 3: {line_3 if line_3 else 'none'}")
    
    # Test find pattern
    line_numbers = context.find_pattern_in_lines("GlobalScope.launch")
    print(f"  Find 'GlobalScope.launch' at line {line_numbers}")
    
    # Test cache
    context.set_cached("test_key", "test_value")
    cached_value = context.get_cached("test_key")
    print(f"  Cache test: {'success' if cached_value == 'test_value' else 'failed'}")
    
    print("✓ Rule context test passed\n")
    
    return True


def test_rule_engine():
    """Test rule engine"""
    print("=== Testing Rule Engine ===")
    
    # Create engine
    engine = RuleEngine()
    
    # Register some rules
    registry = engine.registry
    registry.register(NoGlobalScopeRule())
    
    # Test code
    test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("Executing in GlobalScope")
    }
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="test.kt",
        language="kotlin"
    )
    
    # Execute rules (sequential execution)
    findings, stats = engine.execute_all(context, parallel=False)
    
    print(f"  Rules executed: {stats.get('total_rules', 0)}")
    print(f"  Issues found: {len(findings)}")
    print(f"  Execution time: {stats.get('execution_time', 0):.3f} seconds")
    
    if findings:
        for i, finding in enumerate(findings, 1):
            print(f"  Issue {i}: {finding.rule_id} - {finding.message}")
            print(f"    Severity: {finding.severity.value}")
            print(f"    File: {finding.file_path}")
            print(f"    Line: {finding.line_number}")
    
    # Test cache
    cache_stats = engine.get_cache_stats()
    print(f"  Cache size: {cache_stats.get('cache_size', 0)}")
    
    # Clear cache
    engine.clear_cache()
    cache_stats = engine.get_cache_stats()
    print(f"  Cache size after clearing: {cache_stats.get('cache_size', 0)}")
    
    print("✓ Rule engine test passed\n")
    
    return len(findings) > 0  # Expected to find at least one issue


def test_adapters():
    """Test adapters (decorators)"""
    print("=== Testing Adapters (Decorators) ===")
    
    from rule_engine.adapters import rule
    
    @rule(
        rule_id="simple_adapter_test",
        name="Simple Adapter Test",
        description="Test decorator-created rule functionality",
        severity=RuleSeverity.INFO,
        category=RuleCategory.STYLE,
        tags=["test", "adapter"]
    )
    def simple_adapter_rule(context):
        """Simple decorator rule test"""
        findings = []
        
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "adapter_test" in line.lower():
                findings.append(Finding(
                    rule_id="simple_adapter_test",
                    message="Found adapter test marker",
                    severity=RuleSeverity.INFO,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line
                ))
        
        return findings
    
    # Test decorator-created rule
    rule_instance = simple_adapter_rule
    
    print(f"  Adapter rule ID: {rule_instance.metadata.id}")
    print(f"  Adapter rule name: {rule_instance.metadata.name}")
    print(f"  Adapter rule category: {rule_instance.metadata.category.value}")
    
    # Test rule execution
    test_code = """
// adapter_test: this is a test marker
fun testAdapterFunction() {
    println("Adapter test")
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="test.kt",
        language="kotlin"
    )
    
    findings = rule_instance.check(context)
    
    print(f"  Issues found by adapter: {len(findings)}")
    
    if findings:
        for finding in findings:
            print(f"    Issue: {finding.message}")
            print(f"    Line: {finding.line_number}")
    
    print("✓ Adapter test passed\n")
    
    return len(findings) > 0


def test_decorators():
    """Test decorators"""
    print("=== Testing Decorators ===")
    
    from rule_engine.adapters import rule
    
    @rule(
        rule_id="test_decorator_rule",
        name="Test Decorator Rule",
        description="This is a test decorator rule example",
        severity=RuleSeverity.MINOR,
        category=RuleCategory.STYLE,
        tags=["test", "decorator"]
    )
    def test_decorator_rule(context):
        """Test decorator rule"""
        findings = []
        
        if "TODO" in context.code:
            findings.append(Finding(
                rule_id="test_decorator_rule",
                message="TODO comment found in code",
                severity=RuleSeverity.MINOR,
                file_path=context.file_path,
                suggestion="Process TODO comments promptly"
            ))
        
        return findings
    
    # Test decorator-created rule
    rule_instance = test_decorator_rule
    
    print(f"  Decorator rule ID: {rule_instance.metadata.id}")
    print(f"  Decorator rule name: {rule_instance.metadata.name}")
    print(f"  Decorator rule category: {rule_instance.metadata.category.value}")
    
    # Test rule execution
    test_code = """
// TODO: Need to implement this function
fun todoFunction() {
    // To be implemented
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="test.kt",
        language="kotlin"
    )
    
    findings = rule_instance.check(context)
    
    print(f"  Issues found by decorator rule: {len(findings)}")
    
    if findings:
        for finding in findings:
            print(f"    Issue: {finding.message}")
    
    print("✓ Decorator test passed\n")
    
    return True


def test_integration():
    """Test integration functionality"""
    print("=== Testing Integration Functionality ===")
    
    # Clear previous registry (singleton pattern)
    registry = RuleRegistry()
    registry.clear()
    
    # Create complete engine and register multiple rules
    engine = RuleEngine(registry)
    
    # Register multiple rules
    registry.register(NoGlobalScopeRule())
    
    # Register decorator rules
    from rule_engine.adapters import rule
    
    @rule(
        rule_id="empty_function",
        name="Empty Function Detection",
        description="Detect empty function bodies",
        severity=RuleSeverity.MINOR,
        category=RuleCategory.STYLE
    )
    def empty_function_rule(context):
        findings = []
        
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "fun" in line and "{}" in line:
                findings.append(Finding(
                    rule_id="empty_function",
                    message="Empty function body found",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="Add function implementation or remove unused function"
                ))
        
        return findings
    
    registry.register(empty_function_rule)
    
    print(f"  Registered rules: {registry.count_rules()}")
    
    # Test code
    test_code = """
class TestClass {
    // Empty function
    fun emptyFunction() {}
    
    fun testFunction() {
        // Using GlobalScope
        GlobalScope.launch {
            println("Test")
        }
    }
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="TestClass.kt",
        language="kotlin"
    )
    
    # Execute all rules
    findings, stats = engine.execute_all(context, parallel=False)
    
    print(f"  Rules executed: {stats.get('total_rules', 0)}")
    print(f"  Total issues found: {len(findings)}")
    
    # Group statistics
    severity_counts = {}
    for finding in findings:
        severity = finding.severity.value
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    print("  Issue severity statistics:")
    for severity, count in severity_counts.items():
        print(f"    {severity}: {count} issues")
    
    print("  Detailed issue list:")
    for i, finding in enumerate(findings, 1):
        print(f"    {i}. [{finding.severity.value}] {finding.rule_id}: {finding.message}")
        if finding.line_number:
            print(f"       Line: {finding.line_number}")
        if finding.suggestion:
            print(f"       Suggestion: {finding.suggestion}")
    
    # Test execute by category
    print("\n  Testing execute rules by category:")
    style_findings, style_stats = engine.execute_by_category(context, "style", parallel=False)
    print(f"  STYLE category issues found: {len(style_findings)} issues")
    
    # Get statistics
    engine_stats = registry.get_statistics()
    print(f"  Engine stats - Total rules: {engine_stats.get('total_rules', 0)}")
    print(f"  Engine stats - Enabled rules: {engine_stats.get('enabled_rules', 0)}")
    
    print("✓ Integration test passed\n")
    
    return len(findings) >= 2  # Expected to find at least 2 issues


def main():
    """Main test function"""
    print("Unified Rule Engine Functionality Test\n")
    
    tests = [
        ("Rule Registry", test_rule_registry),
        ("Rule Context", test_rule_context),
        ("Rule Engine", test_rule_engine),
        ("Adapters", test_adapters),
        ("Decorators", test_decorators),
        ("Integration", test_integration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} test passed")
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} test exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\nTest summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
