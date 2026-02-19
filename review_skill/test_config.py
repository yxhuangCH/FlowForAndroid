#!/usr/bin/env python3
"""
测试配置功能和文件过滤
"""

import sys
import os
sys.path.append('.')

from config import ReviewConfig, get_config


def test_config_loading():
    """测试配置加载"""
    print("=== 测试配置加载 ===")
    
    # 测试默认配置
    config = ReviewConfig()
    print(f"默认文件扩展名: {config.get_file_extensions()}")
    print(f"默认扫描目录: {config.get_scan_directories()}")
    print(f"默认排除模式: {config.get_exclude_patterns()}")
    print(f"最小分数阈值: {config.get_min_score_threshold()}")
    
    # 测试配置文件加载
    if os.path.exists('review_config.json'):
        config2 = ReviewConfig('review_config.json')
        print(f"\n从配置文件加载的文件扩展名: {config2.get_file_extensions()}")
        print(f"从配置文件加载的扫描目录: {config2.get_scan_directories()}")
    else:
        print("\n未找到配置文件 review_config.json")
    
    print("\n")


def test_file_filtering():
    """测试文件过滤"""
    print("=== 测试文件过滤 ===")
    
    config = get_config()
    
    test_cases = [
        # (文件路径, 期望结果)
        ("app/src/main/java/com/example/MainActivity.kt", True),
        ("app/src/test/java/com/example/MainActivityTest.kt", True),
        ("app/src/androidTest/java/com/example/ExampleInstrumentedTest.kt", True),
        ("app/src/main/java/com/example/TestFile.java", False),  # Java 文件
        ("app/src/main/res/layout/activity_main.xml", False),  # XML 文件
        ("app/build.gradle", False),  # Gradle 文件
        ("app/src/main/java/com/example/build/MainActivity.kt", False),  # 在 build 目录中
        ("app/src/test/java/com/example/MyTest.kt", True),
        ("app/src/test/java/com/example/MyMock.kt", False),  # Mock 文件被排除
        ("app/src/test/java/com/example/MyTestFileTest.kt", False),  # 以 Test 结尾被排除
        ("settings.gradle", False),  # 不在扫描目录
        ("app/src/main/java/com/example/debug/DebugActivity.kt", False),  # 在 debug 目录
    ]
    
    print("文件过滤测试:")
    for file_path, expected in test_cases:
        result = config.should_scan_file(file_path)
        status = "✓" if result == expected else "✗"
        print(f"{status} {file_path:60} 期望: {expected}, 实际: {result}")
    
    print("\n")


def test_git_diff_filtering():
    """测试 git diff 过滤"""
    print("=== 测试 git diff 过滤 ===")
    
    config = get_config()
    
    # 创建一个测试用的 git diff
    test_diff = '''diff --git a/app/src/main/java/com/example/MainActivity.kt b/app/src/main/java/com/example/MainActivity.kt
index abc123..def456 100644
--- a/app/src/main/java/com/example/MainActivity.kt
+++ b/app/src/main/java/com/example/MainActivity.kt
@@ -1,5 +1,5 @@
 package com.example

 class MainActivity : AppCompatActivity() {
-    private val oldCode = "old"
+    private val newCode = "new"
 }

diff --git a/app/build.gradle b/app/build.gradle
index 111111..222222 100644
--- a/app/build.gradle
+++ b/app/build.gradle
@@ -1,3 +1,3 @@
 android {
-    oldVersion = 1.0
+    newVersion = 2.0
 }

diff --git a/app/src/main/res/layout/activity_main.xml b/app/src/main/res/layout/activity_main.xml
index 333333..444444 100644
--- a/app/src/main/res/layout/activity_main.xml
+++ b/app/src/main/res/layout/activity_main.xml
@@ -5,6 +5,6 @@
     <TextView
         android:id="@+id/textView"
         android:layout_width="wrap_content"
-        android:text="Old Text"
+        android:text="New Text"
     />
 </LinearLayout>

diff --git a/app/src/test/java/com/example/MainActivityTest.kt b/app/src/test/java/com/example/MainActivityTest.kt
index 555555..666666 100644
--- a/app/src/test/java/com/example/MainActivityTest.kt
+++ b/app/src/test/java/com/example/MainActivityTest.kt
@@ -10,7 +10,7 @@ class MainActivityTest {
     fun testExample() {
         val activity = MainActivity()
-        assertTrue(activity.isVisible())
+        assertFalse(activity.isVisible())
     }
 }
'''
    
    filtered_diff = config.filter_git_diff(test_diff)
    
    print("原始 diff 行数:", len(test_diff.split('\n')))
    print("过滤后 diff 行数:", len(filtered_diff.split('\n')))
    
    # 检查过滤结果
    expected_files = ['MainActivity.kt', 'MainActivityTest.kt']
    filtered_files = []
    
    for line in filtered_diff.split('\n'):
        if line.startswith('diff --git'):
            import re
            match = re.search(r'^diff --git a/(.+) b/(.+)$', line)
            if match:
                filtered_files.append(os.path.basename(match.group(2)))
    
    print(f"过滤后的文件: {filtered_files}")
    print(f"期望的文件: {expected_files}")
    
    if set(filtered_files) == set(expected_files):
        print("✓ git diff 过滤测试通过")
    else:
        print("✗ git diff 过滤测试失败")
    
    print("\n")


def test_global_config():
    """测试全局配置实例"""
    print("=== 测试全局配置实例 ===")
    
    config1 = get_config()
    config2 = get_config()
    
    # 检查是否是同一个实例
    if config1 is config2:
        print("✓ 全局配置实例是单例")
    else:
        print("✗ 全局配置实例不是单例")
    
    # 检查配置一致性
    if config1.get_file_extensions() == config2.get_file_extensions():
        print("✓ 配置一致性检查通过")
    else:
        print("✗ 配置一致性检查失败")
    
    print("\n")


def test_custom_config():
    """测试自定义配置"""
    print("=== 测试自定义配置 ===")
    
    # 创建一个临时配置文件
    import json
    import tempfile
    
    custom_config = {
        "file_extensions": [".java", ".kt"],
        "scan_directories": ["src/main/java", "src/main/kotlin"],
        "exclude_patterns": ["*/test/*", "*/debug/*"],
        "enable_semantic_review": False,
        "generate_html_report": False,
        "min_score_threshold": 80
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(custom_config, f)
        temp_file = f.name
    
    try:
        config = ReviewConfig(temp_file)
        
        print(f"自定义文件扩展名: {config.get_file_extensions()}")
        print(f"自定义扫描目录: {config.get_scan_directories()}")
        print(f"自定义最小分数阈值: {config.get_min_score_threshold()}")
        print(f"是否启用语义分析: {config.is_enabled_semantic_review()}")
        print(f"是否生成HTML报告: {config.should_generate_html_report()}")
        
        # 验证配置
        assert config.get_file_extensions() == [".java", ".kt"]
        assert config.get_scan_directories() == ["src/main/java", "src/main/kotlin"]
        assert config.get_min_score_threshold() == 80
        assert not config.is_enabled_semantic_review()
        assert not config.should_generate_html_report()
        
        print("✓ 自定义配置测试通过")
    finally:
        os.unlink(temp_file)
    
    print("\n")


if __name__ == "__main__":
    print("开始测试配置模块...\n")
    
    test_config_loading()
    test_file_filtering()
    test_git_diff_filtering()
    test_global_config()
    test_custom_config()
    
    print("所有测试完成！")