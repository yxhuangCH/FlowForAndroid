#!/usr/bin/env python3
"""
Test Android-specific rules
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rule_engine.context import RuleContext
from rule_engine.registry import RuleRegistry
from rule_engine.engine import RuleEngine
from rule_engine.rules.android_rules import startactivity_without_trycatch_rule, _find_try_catch_ranges


def test_find_try_catch():
    """Debug test for try-catch detection"""
    print("\n" + "=" * 60)
    print("Debugging try-catch detection")
    print("=" * 60)
    
    code2 = """fun testIntent(context: Context) {
    try {
        context.startActivity(Intent(), Bundle())
    } catch (e: ActivityNotFoundException) {
        // Handle error
    }
}"""
    lines = code2.split('\n')
    print("\nTest code lines:")
    for i, line in enumerate(lines, 1):
        print(f"  {i}: {repr(line)}")
    
    ranges = _find_try_catch_ranges(lines)
    print(f"\nFound try-catch ranges: {ranges}")
    
    # Check line 3 (startActivity is on line 3)
    line_with_startactivity = 3
    in_range = any(start <= line_with_startactivity <= end for start, end in ranges)
    print(f"Line {line_with_startactivity} in try-catch range: {in_range}")


def test_startactivity_without_trycatch():
    """Test startActivity without try-catch detection"""
    print("\n" + "=" * 60)
    print("Testing startactivity_without_trycatch rule...")
    print("=" * 60)
    
    # Test case 1: startActivity without try-catch (should trigger)
    code1 = """
fun testIntent(context: Context) {
    context.startActivity(
        Intent(), Bundle()
    )
}
"""
    context1 = RuleContext(
        code=code1,
        file_path="Test1.kt",
        language="kotlin"
    )
    findings1 = startactivity_without_trycatch_rule.check(context1)
    print(f"\nTest 1 (no try-catch): {len(findings1)} findings")
    for f in findings1:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings1) == 1, f"Expected 1 finding, got {len(findings1)}"
    print("✓ Test 1 passed")
    
    # Test case 2: startActivity with try-catch (should NOT trigger)
    code2 = """fun testIntent(context: Context) {
    try {
        context.startActivity(Intent(), Bundle())
    } catch (e: ActivityNotFoundException) {
        // Handle error
    }
}"""
    context2 = RuleContext(
        code=code2,
        file_path="Test2.kt",
        language="kotlin"
    )
    findings2 = startactivity_without_trycatch_rule.check(context2)
    print(f"\nTest 2 (with try-catch): {len(findings2)} findings")
    for f in findings2:
        print(f"  - Line {f.line_number}: {f.message}")
        print(f"    Code: {f.code_snippet}")
    assert len(findings2) == 0, f"Expected 0 findings, got {len(findings2)}"
    print("✓ Test 2 passed")
    
    # Test case 3: Multiple startActivity calls, one protected, one not
    code3 = """fun testMultiple(context: Context) {
    context.startActivity(Intent())
    
    try {
        context.startActivity(Intent(), Bundle())
    } catch (e: ActivityNotFoundException) {
        // Handle error
    }
    
    context.startActivity(Intent())
}"""
    context3 = RuleContext(
        code=code3,
        file_path="Test3.kt",
        language="kotlin"
    )
    findings3 = startactivity_without_trycatch_rule.check(context3)
    print(f"\nTest 3 (multiple calls): {len(findings3)} findings")
    for f in findings3:
        print(f"  - Line {f.line_number}: {f.message}")
    # Should find 2 unprotected calls (line 2 and line 10)
    assert len(findings3) == 2, f"Expected 2 findings, got {len(findings3)}"
    print("✓ Test 3 passed")
    
    # Test case 4: startActivity with @Throws annotation (should NOT trigger)
    code4 = """
@Throws(ActivityNotFoundException::class)
fun testIntent(context: Context) {
    context.startActivity(Intent())
}
"""
    context4 = RuleContext(
        code=code4,
        file_path="Test4.kt",
        language="kotlin"
    )
    findings4 = startactivity_without_trycatch_rule.check(context4)
    print(f"\nTest 4 (with @Throws): {len(findings4)} findings")
    for f in findings4:
        print(f"  - Line {f.line_number}: {f.message}")
    assert len(findings4) == 0, f"Expected 0 findings for @Throws, got {len(findings4)}"
    print("✓ Test 4 passed")
    
    print("\nAll tests passed!")


def test_with_real_mainactivity():
    """Test with the real MainActivity.kt file"""
    print("\n" + "=" * 60)
    print("Testing with real MainActivity.kt...")
    print("=" * 60)
    
    # Read the actual MainActivity.kt file
    mainactivity_path = "app/src/main/java/com/yxhuang/flowforandroid/MainActivity.kt"
    try:
        with open(mainactivity_path, 'r') as f:
            code = f.read()
        
        context = RuleContext(
            code=code,
            file_path=mainactivity_path,
            language="kotlin"
        )
        
        findings = startactivity_without_trycatch_rule.check(context)
        print(f"MainActivity.kt: {len(findings)} findings")
        for f in findings:
            print(f"  - Line {f.line_number}: {f.message}")
            print(f"    Code: {f.code_snippet}")
        
        # Should detect the testIntent function
        assert len(findings) >= 1, "Expected at least 1 finding in MainActivity.kt"
        print("✓ Real file test passed!")
        
    except FileNotFoundError:
        print(f"⚠ File not found: {mainactivity_path}")


def test_with_engine():
    """Test with full rule engine"""
    print("\n" + "=" * 60)
    print("Testing with full rule engine...")
    print("=" * 60)
    
    # Create registry and engine
    registry = RuleRegistry()
    registry.register(startactivity_without_trycatch_rule)
    
    from rule_engine.engine import RuleEngine
    engine = RuleEngine(registry)
    
    # Test code
    code = """
package com.example

fun testIntent(context: Context) {
    context.startActivity(Intent())
}
"""
    
    context = RuleContext(
        code=code,
        file_path="Test.kt",
        language="kotlin"
    )
    
    findings, stats = engine.execute_all(context)
    print(f"Engine test: {len(findings)} findings")
    for f in findings:
        print(f"  - Line {f.line_number}: {f.message}")
    
    assert len(findings) == 1, f"Expected 1 finding, got {len(findings)}"
    print("✓ Engine test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Android Rules Test Suite")
    print("=" * 60)
    
    try:
        test_find_try_catch()
        test_startactivity_without_trycatch()
        test_with_real_mainactivity()
        test_with_engine()
        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
