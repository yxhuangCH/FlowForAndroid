#!/usr/bin/env python3
"""
测试 review skill 功能
这个脚本用于验证 review skill 是否能正确检测代码问题
"""
import os
import sys
import tempfile
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 测试代码：包含已知问题的代码
TEST_CODE = '''
package com.example.test

import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

class TestViewModel(val context: android.content.Context) {
    fun doSomething() {
        GlobalScope.launch {
            // 在 GlobalScope 中执行
            println("测试")
        }
    }
    
    fun doIO() {
        // 在主线程执行 IO 操作
        val file = java.io.File("/path/to/file")
        file.readText()
    }
}
'''

def test_git_diff_logic():
    """测试 git diff 获取逻辑"""
    from review import get_git_diff
    
    print("=== 测试 git diff 获取逻辑 ===")
    
    # 测试获取 git diff
    diff = get_git_diff()
    
    if diff:
        print("✅ 成功获取 git diff")
        print(f"  长度: {len(diff)} 字符")
        print(f"  内容前100字符: {diff[:100]}...")
    else:
        print("⚠️ 未获取到 git diff")
        print("  可能原因:")
        print("  1. 没有未提交的更改")
        print("  2. 没有相对于远程分支的更改")
        print("  3. git 配置问题")
    
    return bool(diff)

def test_config_filtering():
    """测试配置过滤功能"""
    from config import get_config
    
    print("\n=== 测试配置过滤功能 ===")
    
    config = get_config()
    
    print(f"配置的文件扩展名: {config.get_file_extensions()}")
    print(f"配置的扫描目录: {config.get_scan_directories()}")
    print(f"配置的排除模式: {config.get_exclude_patterns()}")
    
    # 测试文件过滤
    test_files = [
        "app/src/main/java/com/example/Test.kt",
        "app/src/test/java/com/example/Test.kt", 
        "app/build/generated/Test.kt",
        "app/src/main/java/com/example/Test.java"
    ]
    
    print("\n文件过滤测试:")
    for file_path in test_files:
        should_scan = config.should_scan_file(file_path)
        print(f"  {file_path}: {'✅ 应该扫描' if should_scan else '❌ 不应该扫描'}")
    
    return True

def test_rule_execution():
    """测试规则执行"""
    print("\n=== 测试规则执行 ===")
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.kt', delete=False) as f:
        f.write(TEST_CODE)
        temp_file = f.name
    
    try:
        # 读取文件内容
        with open(temp_file, 'r') as f:
            code = f.read()
        
        print(f"测试代码长度: {len(code)} 字符")
        print(f"测试文件: {temp_file}")
        
        # 测试基础规则
        from rules.base_rules import run_base_rules
        base_findings = run_base_rules(code)
        
        print(f"\n基础规则发现的问题数: {len(base_findings)}")
        for i, finding in enumerate(base_findings, 1):
            print(f"  问题 {i}: [{finding['severity']}] {finding['rule']} - {finding['message']}")
        
        # 测试其他规则
        from rules.coroutine_rules import run_coroutine_rules
        coroutine_findings = run_coroutine_rules(code)
        
        print(f"\n协程规则发现的问题数: {len(coroutine_findings)}")
        for i, finding in enumerate(coroutine_findings, 1):
            print(f"  问题 {i}: [{finding['severity']}] {finding['rule']} - {finding['message']}")
        
        # 测试评分
        from scorer import calculate_score
        all_findings = base_findings + coroutine_findings
        score = calculate_score(all_findings)
        
        print(f"\n总分数: {score}/100")
        print(f"总问题数: {len(all_findings)}")
        
        return len(all_findings) > 0
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.unlink(temp_file)

def test_rule_engine():
    """测试新规则引擎"""
    print("\n=== 测试新规则引擎 ===")
    
    try:
        from rule_engine import (
            RuleEngine,
            RuleContext,
            RuleRegistry,
            NoGlobalScopeRule,
            viewmodel_context_rule
        )
        
        # 创建引擎
        engine = RuleEngine()
        
        # 注册规则
        registry = engine.registry
        registry.register(NoGlobalScopeRule())
        registry.register(viewmodel_context_rule)
        
        # 创建上下文
        context = RuleContext(
            code=TEST_CODE,
            file_path="Test.kt",
            language="kotlin"
        )
        
        # 执行规则
        findings, stats = engine.execute_all(context, parallel=False)
        
        print(f"新规则引擎发现的问题数: {len(findings)}")
        print(f"执行的规则数: {stats.get('total_rules', 0)}")
        print(f"执行时间: {stats.get('execution_time', 0):.3f} 秒")
        
        for i, finding in enumerate(findings, 1):
            print(f"  问题 {i}: [{finding.severity.value}] {finding.rule_id} - {finding.message}")
            if finding.suggestion:
                print(f"      建议: {finding.suggestion}")
        
        return len(findings) > 0
        
    except ImportError as e:
        print(f"❌ 导入规则引擎失败: {e}")
        print("  注意: 新规则引擎可能还没有完全集成")
        return False
    except Exception as e:
        print(f"❌ 规则引擎测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_review_integration():
    """测试 review.py 集成"""
    print("\n=== 测试 review.py 集成 ===")
    
    # 创建临时测试目录和文件
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "Test.kt")
    
    with open(test_file, 'w') as f:
        f.write(TEST_CODE)
    
    try:
        # 创建临时代码变更（模拟 git diff）
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
+            // 在 GlobalScope 中执行
+            println("测试")
+        }}
+    }}
+    
+    fun doIO() {{
+        // 在主线程执行 IO 操作
+        val file = java.io.File("/path/to/file")
+        file.readText()
+    }}
+}}
+'''
        
        # 测试配置过滤
        from config import get_config
        config = get_config()
        
        filtered_diff = config.filter_git_diff(git_diff_content)
        
        print(f"原始 git diff 长度: {len(git_diff_content)}")
        print(f"过滤后 git diff 长度: {len(filtered_diff)}")
        
        if filtered_diff:
            print("✅ 配置过滤功能正常")
            return True
        else:
            print("❌ 配置过滤后没有内容")
            print("  可能原因: 测试文件路径不在配置的扫描目录中")
            return False
            
    finally:
        # 清理临时目录
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def main():
    """主测试函数"""
    print("📋 review skill 功能测试\n")
    
    tests = [
        ("git diff 获取逻辑", test_git_diff_logic),
        ("配置过滤功能", test_config_filtering),
        ("规则执行", test_rule_execution),
        ("新规则引擎", test_rule_engine),
        ("review.py 集成", test_review_integration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            if test_func():
                print(f"✅ {test_name}测试通过")
                passed += 1
            else:
                print(f"❌ {test_name}测试失败")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"测试总结: {passed} 通过, {failed} 失败")
    
    # 提供建议
    if failed > 0:
        print("\n💡 建议:")
        print("1. 检查 review skill 配置文件 (review_config.json)")
        print("2. 确保有代码变更可供审查")
        print("3. 查看具体失败的测试以了解问题原因")
        print("4. 运行 python3 review.py 查看原始输出")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())