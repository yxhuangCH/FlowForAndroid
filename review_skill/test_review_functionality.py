#!/usr/bin/env python3
"""
Test Review Skill Functionality

This script verifies that the review skill can correctly detect code issues
"""
import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test code: contains known issues
TEST_CODE = '''
package com.example.test

import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

class TestViewModel(val context: android.content.Context) {
    fun doSomething() {
        GlobalScope.launch {
            // Execute in GlobalScope
            println("Test")
        }
    }
    
    fun doIO() {
        // Execute IO operation on main thread
        val file = java.io.File("/path/to/file")
        file.readText()
    }
}
'''

def test_git_diff_logic():
    """Test git diff retrieval logic"""
    from review import get_git_diff
    
    print("=== Testing Git Diff Retrieval Logic ===")
    
    # Test getting git diff
    diff = get_git_diff()
    
    if diff:
        print("✅ Successfully retrieved git diff")
        print(f"  Length: {len(diff)} characters")
        print(f"  First 100 characters: {diff[:100]}...")
    else:
        print("⚠️ No git diff retrieved")
        print("  Possible reasons:")
        print("  1. No uncommitted changes")
        print("  2. No changes relative to remote branch")
        print("  3. Git configuration issues")
    
    return bool(diff)

def test_config_filtering():
    """Test configuration filtering"""
    from config import get_config
    
    print("\n=== Testing Configuration Filtering ===")
    
    config = get_config()
    
    print(f"Configured file extensions: {config.get_file_extensions()}")
    print(f"Configured scan directories: {config.get_scan_directories()}")
    print(f"Configured exclude patterns: {config.get_exclude_patterns()}")
    
    # Test file filtering
    test_files = [
        "app/src/main/java/com/example/Test.kt",
        "app/src/test/java/com/example/Test.kt", 
        "app/build/generated/Test.kt",
        "app/src/main/java/com/example/Test.java"
    ]
    
    print("\nFile filtering tests:")
    for file_path in test_files:
        should_scan = config.should_scan_file(file_path)
        print(f"  {file_path}: {'✅ Should scan' if should_scan else '❌ Should not scan'}")
    
    return True

def test_rule_execution():
    """Test rule execution"""
    print("\n=== Testing Rule Execution ===")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.kt', delete=False) as f:
        f.write(TEST_CODE)
        temp_file = f.name
    
    try:
        # Read file content
        with open(temp_file, 'r') as f:
            code = f.read()
        
        print(f"Test code length: {len(code)} characters")
        print(f"Test file: {temp_file}")
        
        # Test new rule engine
        try:
            from rule_engine.integration.review_runner import EnhancedReviewRunner
            runner = EnhancedReviewRunner()
            runner.initialize()
            
            result = runner.review_code(code, "Test.kt")
            findings = result["findings"]
            score = result["score"]
            
            print(f"\nUnified rule engine findings: {len(findings)}")
            for i, finding in enumerate(findings, 1):
                print(f"  Issue {i}: [{finding['severity']}] {finding['rule']} - {finding['message']}")
            
            print(f"\nTotal score: {score}/100")
            print(f"Total issues: {len(findings)}")
            
            # Check engine info
            info = runner.get_engine_info()
            print(f"Rule engine stats: {info['rule_count']} rules")
            
            return len(findings) > 0
            
        except ImportError as e:
            print(f"❌ Failed to import rule engine: {e}")
            print("  Attempting fallback...")
            # Fallback to old rule system (if available)
            try:
                from rules.base_rules import run_base_rules
                from rules.coroutine_rules import run_coroutine_rules
                from scorer import calculate_score
                
                base_findings = run_base_rules(code)
                coroutine_findings = run_coroutine_rules(code)
                all_findings = base_findings + coroutine_findings
                score = calculate_score(all_findings)
                
                print(f"\nFallback mode: Issues found: {len(all_findings)}")
                print(f"Total score: {score}/100")
                
                return len(all_findings) > 0
            except ImportError as e2:
                print(f"❌ Fallback also failed: {e2}")
                return False
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.unlink(temp_file)

def test_rule_engine():
    """Test new rule engine"""
    print("\n=== Testing New Rule Engine ===")
    
    try:
        from rule_engine import (
            RuleEngine,
            RuleContext,
            RuleRegistry,
            NoGlobalScopeRule,
            viewmodel_context_rule
        )
        
        # Create engine
        engine = RuleEngine()
        
        # Register rules
        registry = engine.registry
        registry.register(NoGlobalScopeRule())
        registry.register(viewmodel_context_rule)
        
        # Create context
        context = RuleContext(
            code=TEST_CODE,
            file_path="Test.kt",
            language="kotlin"
        )
        
        # Execute rules
        findings, stats = engine.execute_all(context, parallel=False)
        
        print(f"New rule engine findings: {len(findings)}")
        print(f"Rules executed: {stats.get('total_rules', 0)}")
        print(f"Execution time: {stats.get('execution_time', 0):.3f} seconds")
        
        for i, finding in enumerate(findings, 1):
            print(f"  Issue {i}: [{finding.severity.value}] {finding.rule_id} - {finding.message}")
            if finding.suggestion:
                print(f"      Suggestion: {finding.suggestion}")
        
        return len(findings) > 0
        
    except ImportError as e:
        print(f"❌ Failed to import rule engine: {e}")
        print("  Note: New rule engine may not be fully integrated yet")
        return False
    except Exception as e:
        print(f"❌ Rule engine test exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_review_integration():
    """Test review.py integration"""
    print("\n=== Testing review.py Integration ===")
    
    # Create temporary test directory and file
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "Test.kt")
    
    with open(test_file, 'w') as f:
        f.write(TEST_CODE)
    
    try:
        # Create temporary code changes (simulate git diff)
        git_diff_content = f'''diff --git a/{test_file} b/{test_file}
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/{test_file}
@@ -0,0 +1,22 @@
+package com.example.test
+
+import kotlinx.coroutines.GlobalScope
+import kotlinx.coroutines.launch
+
+class TestViewModel(val context: android.content.Context) {{
+    fun doSomething() {{
+        GlobalScope.launch {{
+            // Execute in GlobalScope
+            println("Test")
+        }}
+    }}
+    
+    fun doIO() {{
+        // Execute IO operation on main thread
+        val file = java.io.File("/path/to/file")
+        file.readText()
+    }}
+}}
+'''
        
        # Test configuration filtering
        from config import get_config
        config = get_config()
        
        filtered_diff = config.filter_git_diff(git_diff_content)
        
        print(f"Original git diff length: {len(git_diff_content)}")
        print(f"Filtered git diff length: {len(filtered_diff)}")
        
        if filtered_diff:
            print("✅ Configuration filtering working")
            return True
        else:
            print("❌ No content after filtering")
            print("  Possible reason: Test file path not in configured scan directories")
            return False
            
    finally:
        # Clean up temporary directory
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def main():
    """Main test function"""
    print("📋 Review Skill Functionality Test\n")
    
    tests = [
        ("Git diff retrieval logic", test_git_diff_logic),
        ("Configuration filtering", test_config_filtering),
        ("Rule execution", test_rule_execution),
        ("New rule engine", test_rule_engine),
        ("review.py integration", test_review_integration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
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
    
    print(f"\n{'='*60}")
    print(f"Test summary: {passed} passed, {failed} failed")
    
    # Provide suggestions
    if failed > 0:
        print("\n💡 Suggestions:")
        print("1. Check review skill configuration file (review_config.json)")
        print("2. Ensure there are code changes available for review")
        print("3. Check specific failed tests to understand the issue")
        print("4. Run python3 review.py to see raw output")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
