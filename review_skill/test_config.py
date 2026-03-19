#!/usr/bin/env python3
"""
Test Configuration Module

This script tests the configuration loading and file filtering functionality
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ReviewConfig
from config import get_config

def test_config_loading():
    """Test configuration loading"""
    print("=== Testing Configuration Loading ===")

    # Test default configuration
    config = ReviewConfig()

    print(f"Default file extensions: {config.get_file_extensions()}")
    print(f"Default scan directories: {config.get_scan_directories()}")
    print(f"Default exclude patterns: {config.get_exclude_patterns()}")
    print(f"Minimum score threshold: {config.get_min_score_threshold()}")

    # Test configuration file loading
    if os.path.exists('review_config.json'):
        config2 = ReviewConfig('review_config.json')

        print(f"\nFile extensions loaded from config file: {config2.get_file_extensions()}")
        print(f"Scan directories loaded from config file: {config2.get_scan_directories()}")
    else:
        print("\nConfiguration file review_config.json not found")

def test_file_filtering():
    """Test file filtering"""
    print("=== Testing File Filtering ===")

    config = ReviewConfig()

    test_cases = [
        # (file path, expected result)
        ("app/src/main/java/com/example/MainActivity.kt", True),
        ("app/src/androidTest/java/com/example/ExampleInstrumentedTest.kt", True),
        ("app/src/main/java/com/example/TestFile.java", False),  # Java file
        ("app/src/main/res/layout/activity_main.xml", False),  # XML file
        ("app/build.gradle", False),  # Gradle file
        ("app/src/main/java/com/example/build/MainActivity.kt", False),  # In build directory
        ("app/src/test/java/com/example/MyTest.kt", True),
        ("app/src/test/java/com/example/MyMock.kt", False),  # Mock file excluded
        ("app/src/test/java/com/example/MyTestFileTest.kt", False),  # Ends with Test excluded
        ("settings.gradle", False),  # Not in scan directories
        ("app/src/main/java/com/example/debug/DebugActivity.kt", False),  # In debug directory
    ]

    print("File filtering tests:")
    for file_path, expected in test_cases:
        result = config.should_scan_file(file_path)
        status = "✓" if result == expected else "✗"
        print(f"{status} {file_path:60} Expected: {expected}, Actual: {result}")

def test_git_diff_filtering():
    """Test git diff filtering"""
    print("=== Testing Git Diff Filtering ===")

    config = ReviewConfig()

    # Create a test git diff
    test_diff = '''diff --git a/app/src/main/java/com/example/MainActivity.kt b/app/src/main/java/com/example/MainActivity.kt
--- a/app/src/main/java/com/example/MainActivity.kt
+++ b/app/src/main/java/com/example/MainActivity.kt
@@ -10,5 +10,6 @@ class MainActivity : AppCompatActivity() {
     override fun onCreate(savedInstanceState: Bundle?) {
         super.onCreate(savedInstanceState)
         setContentView(R.layout.activity_main)
+        println("Test")
     }
 }

diff --git a/app/src/test/java/com/example/MainActivityTest.kt b/app/src/test/java/com/example/MainActivityTest.kt
--- a/app/src/test/java/com/example/MainActivityTest.kt
+++ b/app/src/test/java/com/example/MainActivityTest.kt
@@ -5,4 +5,5 @@ class MainActivityTest {
     @Test
     fun testExample() {
+        println("Test")
     }
 }

diff --git a/build.gradle b/build.gradle
--- a/build.gradle
+++ b/build.gradle
@@ -1,4 +1,4 @@
 // Build script
-version = "1.0"
+version = "2.0"
'''

    filtered_diff = config.filter_diff_by_config(test_diff)

    print(f"Original diff line count: {len(test_diff.split(chr(10)))}")
    print(f"Filtered diff line count: {len(filtered_diff.split(chr(10)))}")

    # Check filtering result
    expected_files = ['MainActivity.kt', 'MainActivityTest.kt']

    import re
    filtered_files = re.findall(r'b/(.*?\.kt)', filtered_diff)

    print(f"Filtered files: {filtered_files}")
    print(f"Expected files: {expected_files}")

    if set(filtered_files) == set(expected_files):
        print("✓ Git diff filtering test passed")
    else:
        print("✗ Git diff filtering test failed")

def test_global_config():
    """Test global configuration instance"""
    print("=== Testing Global Configuration Instance ===")

    config1 = get_config()
    config2 = get_config()

    # Check if it's the same instance
    if config1 is config2:
        print("✓ Global configuration instance is singleton")
    else:
        print("✗ Global configuration instance is not singleton")

    # Check configuration consistency
    if config1.get_file_extensions() == config2.get_file_extensions():
        print("✓ Configuration consistency check passed")
    else:
        print("✗ Configuration consistency check failed")

def test_custom_config():
    """Test custom configuration"""
    print("=== Testing Custom Configuration ===")

    # Create a temporary configuration file
    import json

    temp_config = {
        "file_extensions": [".java", ".kt"],
        "scan_directories": ["src/main", "src/test"],
        "min_score_threshold": 70,
        "semantic_review": True,
        "generate_html_report": True
    }

    temp_file = "/tmp/test_review_config.json"
    with open(temp_file, 'w') as f:
        json.dump(temp_config, f)

    try:
        config = ReviewConfig(temp_file)

        print(f"Custom file extensions: {config.get_file_extensions()}")
        print(f"Custom scan directories: {config.get_scan_directories()}")
        print(f"Custom minimum score threshold: {config.get_min_score_threshold()}")
        print(f"Semantic analysis enabled: {config.is_enabled_semantic_review()}")
        print(f"Generate HTML report: {config.should_generate_html_report()}")

        # Verify configuration
        assert config.get_file_extensions() == [".java", ".kt"]

        print("✓ Custom configuration test passed")
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    print("Starting configuration module tests...\n")

    test_config_loading()
    print()

    test_file_filtering()
    print()

    test_git_diff_filtering()
    print()

    test_global_config()
    print()

    test_custom_config()
    print()

    print("All tests completed!")
