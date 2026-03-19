#!/usr/bin/env python3
"""
Test review skill when .kt file changes are present
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_kt_file():
    """Create a .kt file for testing, containing known issues"""
    test_code = '''package com.example.test

import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import androidx.lifecycle.ViewModel
import android.content.Context

class BadViewModel(val context: Context) : ViewModel() {
    fun doBadThings() {
        // Issue 1: Using GlobalScope
        GlobalScope.launch {
            // Execute IO on main thread
            val file = java.io.File("/tmp/test.txt")
            file.writeText("bad")
        }
        
        // Issue 2: Unspecified coroutine scope
        launch {
            println("unspecified scope")
        }
    }
}

// Issue 3: Empty Composable function
@Composable
fun EmptyComposable() {}
'''
    
    # Create temporary directory and file
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "Test.kt"
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    return str(temp_dir), str(test_file)

def test_with_kt_diff():
    """Test review skill with .kt file changes in git diff"""
    print("=== Testing review skill with .kt file changes ===")
    
    # Create test file
    temp_dir, test_file = create_test_kt_file()
    print(f"Created test file: {test_file}")
    
    try:
        # Create simulated git diff
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Create git diff format changes
        git_diff = f'''diff --git a/{test_file} b/{test_file}
new file mode 100644
index 0000000..abcdef1
--- /dev/null
+++ b/{test_file}
@@ -0,0 +1,31 @@
{content}
'''
        
        print(f"Simulated git diff length: {len(git_diff)} characters")
        
        # Test configuration filtering
        from config import get_config
        config = get_config()
        
        print(f"\nConfiguration info:")
        print(f"  File extensions: {config.get_file_extensions()}")
        print(f"  Scan directories: {config.get_scan_directories()}")
        
        # Since test file is not in configured scan directories, we need to modify config for testing
        # Get file relative path (relative to project root)
        project_root = Path(os.path.dirname(os.path.abspath(__file__))).parent
        relative_path = Path(test_file).relative_to(project_root)
        
        print(f"\nTest file path relative to project root: {relative_path}")
        
        # Check if file should be scanned
        should_scan = config.should_scan_file(str(relative_path))
        print(f"  Should scan with current config: {'✅ Yes' if should_scan else '❌ No'}")
        
        if not should_scan:
            print(f"\n⚠️ Test file is not in configured scan directories")
            print(f"  Current scan directories: {config.get_scan_directories()}")
            print(f"  File path: {relative_path}")
            print(f"  Does file path start with scan directory:")
            for scan_dir in config.get_scan_directories():
                matches = str(relative_path).startswith(scan_dir)
                print(f"    - {scan_dir}: {'✅ Yes' if matches else '❌ No'}")
        
        # Test rule execution (using unified rule engine)
        print(f"\n=== Direct rule execution test ===")
        
        try:
            from rule_engine.integration.review_runner import EnhancedReviewRunner
            runner = EnhancedReviewRunner()
            runner.initialize()
            
            result = runner.review_code(content, "Test.kt")
            findings = result["findings"]
            score = result["score"]
            
            print(f"Total issues found: {len(findings)}")
            print(f"Rule engine info: {runner.get_engine_info()['rule_count']} rules")
            
            if findings:
                print(f"\nDetailed issues:")
                for i, finding in enumerate(findings, 1):
                    print(f"  {i}. [{finding['severity']}] {finding['rule']}: {finding['message']}")
            
            print(f"\nCode quality score: {score}/100")
            
        except ImportError as e:
            print(f"⚠️ Unified rule engine import failed: {e}")
            print("Attempting fallback...")
            try:
                from rules.base_rules import run_base_rules
                from rules.coroutine_rules import run_coroutine_rules
                from rules.compose_rules import run_compose_rules
                from scorer import calculate_score
                
                base_findings = run_base_rules(content)
                coroutine_findings = run_coroutine_rules(content)
                compose_findings = run_compose_rules(content)
                
                all_findings = base_findings + coroutine_findings + compose_findings
                
                print(f"Fallback mode total issues found: {len(all_findings)}")
                print(f"Base rules: {len(base_findings)} issues")
                print(f"Coroutine rules: {len(coroutine_findings)} issues")
                print(f"Compose rules: {len(compose_findings)} issues")
                
                if all_findings:
                    print(f"\nDetailed issues:")
                    for i, finding in enumerate(all_findings, 1):
                        print(f"  {i}. [{finding['severity']}] {finding['rule']}: {finding['message']}")
                
                score = calculate_score(all_findings)
                print(f"\nCode quality score: {score}/100")
                
            except ImportError as e2:
                print(f"❌ Fallback also failed: {e2}")
                print("No rule engine available")
                findings = []
                score = 100
        
        return len(findings) > 0
        
    finally:
        # Clean up temporary directory
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def main():
    """Main function"""
    print("📋 Simulating .kt file changes test\n")
    
    # Check if there are any .kt files in current directory
    project_root = Path(os.path.dirname(os.path.abspath(__file__))).parent
    kt_files = list(project_root.rglob("*.kt"))
    
    print(f"Project root: {project_root}")
    print(f"Number of .kt files found: {len(kt_files)}")
    
    if kt_files:
        print(f"\nFirst 5 .kt files:")
        for kt_file in kt_files[:5]:
            relative_path = kt_file.relative_to(project_root)
            print(f"  - {relative_path}")
    
    # Run test
    success = test_with_kt_diff()
    
    print(f"\n{'='*60}")
    print(f"Test result: {'✅ Passed' if success else '❌ Failed'}")
    
    # Diagnose user issues
    print(f"\n💡 Troubleshooting:")
    print(f"1. User runs `python3 review.py` and sees 'No file changes to scan'")
    print(f"2. Reason: Current git diff has no .kt or .kts file changes")
    print(f"3. Files in current git diff:")
    
    # Get current git diff
    from review import get_git_diff
    diff = get_git_diff()
    lines = diff.split('\n')
    
    diff_files = []
    for line in lines:
        if line.startswith('diff --git'):
            # Extract file name
            parts = line.split()
            if len(parts) >= 3:
                file_a = parts[2][2:]  # Remove 'a/'
                file_b = parts[3][2:]  # Remove 'b/'
                diff_files.append(file_b if file_b != '/dev/null' else file_a)
    
    if diff_files:
        for file in diff_files:
            is_kt = file.endswith('.kt') or file.endswith('.kts')
            print(f"   - {file} {'✅ (.kt file)' if is_kt else '❌ (not .kt file)'}")
    else:
        print(f"   No file changes")
    
    print(f"\n🔧 Solutions:")
    print(f"1. Create or modify a .kt file (e.g., app/src/main/java/.../Test.kt)")
    print(f"2. Run `git add <file>` and `git commit -m 'test changes'`")
    print(f"3. Run `python3 review.py` again")
    print(f"4. Or run test directly: `python3 test_review_functionality.py`")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
