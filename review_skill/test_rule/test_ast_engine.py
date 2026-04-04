"""
Test AST Engine - 测试AST引擎基础架构
"""

import sys
sys.path.insert(0, '/Users/yxhuang/code/AndroidDemo/flowforandroid/review_skill')

from ast_engine.parser import KotlinASTParser
from ast_engine.rules.base_ast_rule import RuleRegistry
from ast_engine.rules.coroutine_rules import (
    GlobalScopeRule, UnspecifiedScopeRule, MainThreadIORule, ViewModelContextRule
)
from ast_engine.rules.compose_rules import (
    ComposeRememberRule, ComposeLaunchedEffectRule
)


def test_parser():
    """测试解析器"""
    print("=" * 60)
    print("Testing Kotlin AST Parser")
    print("=" * 60)
    
    code = """
package com.example.test

import kotlinx.coroutines.*

class TestViewModel {
    val context: Context? = null
    
    suspend fun fetchData() {
        GlobalScope.launch {
            println("Hello")
        }
    }
}

fun test() {
    launch {
        delay(1000)
    }
}
"""
    
    parser = KotlinASTParser()
    ast = parser.parse(code)
    
    print(f"✓ Parsed successfully")
    print(f"  - Node type: {ast.node_type.value}")
    print(f"  - Children count: {len(ast.children)}")
    print(f"  - Line count: {code.count(chr(10)) + 1}")
    
    # 测试查找功能
    calls = ast.find_all(type(ast.children[0]).__class__)
    print(f"  - Found declarations: {len(ast.children)}")
    
    return True


def test_rules():
    """测试规则系统"""
    print("\n" + "=" * 60)
    print("Testing Rule System")
    print("=" * 60)
    
    # 清空并重新注册规则
    RuleRegistry.clear()
    
    # 注册规则
    from ast_engine.rules import coroutine_rules, compose_rules
    
    # 获取所有已注册规则
    rules = RuleRegistry.get_all_rules()
    print(f"✓ Registered {len(rules)} rules:")
    
    for rule in rules:
        print(f"  - {rule.rule_id}: {rule.rule_name} ({rule.severity.value})")
    
    return True


def test_coroutine_rules():
    """测试协程规则"""
    print("\n" + "=" * 60)
    print("Testing Coroutine Rules")
    print("=" * 60)
    
    code = """
class BadViewModel {
    val activityContext: Context? = null
    
    fun badPractice() {
        GlobalScope.launch {
            // Bad!
        }
        
        launch {
            // No scope specified
        }
        
        withContext(Dispatchers.Main) {
            file.readText() // IO on main thread
        }
    }
}
"""
    
    parser = KotlinASTParser()
    ast = parser.parse(code)
    
    # 运行所有协程规则
    from ast_engine.rules import coroutine_rules
    rules = [
        GlobalScopeRule(),
        UnspecifiedScopeRule(),
        MainThreadIORule(),
        ViewModelContextRule(),
    ]
    
    all_findings = []
    for rule in rules:
        findings = rule.check(ast, "Test.kt")
        all_findings.extend(findings)
    
    print(f"✓ Found {len(all_findings)} issues:")
    for finding in all_findings:
        print(f"  [{finding.severity.value.upper()}] Line {finding.line_number}: {finding.message[:60]}...")
    
    return True


def test_compose_rules():
    """测试Compose规则"""
    print("\n" + "=" * 60)
    print("Testing Compose Rules")
    print("=" * 60)
    
    code = """
@Composable
fun TestScreen() {
    val state = remember { mutableStateOf(0) }
    
    LaunchedEffect(Unit) {
        // Runs once
    }
    
    val list = items.filter { it.active }
    
    Box(
        modifier = Modifier
            .padding(16.dp)
            .size(100.dp)
    )
}
"""
    
    parser = KotlinASTParser()
    ast = parser.parse(code)
    
    # 运行Compose规则
    rules = [
        ComposeRememberRule(),
        ComposeLaunchedEffectRule(),
    ]
    
    all_findings = []
    for rule in rules:
        findings = rule.check(ast, "TestCompose.kt")
        all_findings.extend(findings)
    
    print(f"✓ Found {len(all_findings)} issues:")
    for finding in all_findings:
        print(f"  [{finding.severity.value.upper()}] Line {finding.line_number}: {finding.message[:60]}...")
    
    return True


if __name__ == "__main__":
    print("\n" + "🚀" * 30)
    print("AST Engine Architecture Test Suite")
    print("🚀" * 30 + "\n")
    
    tests = [
        ("Parser", test_parser),
        ("Rule System", test_rules),
        ("Coroutine Rules", test_coroutine_rules),
        ("Compose Rules", test_compose_rules),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
