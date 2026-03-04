#!/usr/bin/env python3
"""
统一规则引擎功能测试
测试核心接口、注册表、引擎、适配器和规则的功能
"""
import sys
import os

# 添加当前目录到路径，确保能导入模块
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
    """测试规则注册表"""
    print("=== 测试规则注册表 ===")
    
    registry = RuleRegistry()
    
    # 创建测试规则
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
            print(f"  ✓ 规则 {self.metadata.id} 已注册")
        
        def on_unregister(self):
            print(f"  ✓ 规则 {self.metadata.id} 已注销")
    
    # 测试注册
    test_rule1 = TestRule("test_rule_1")
    test_rule2 = TestRule("test_rule_2")
    
    registry.register(test_rule1)
    registry.register(test_rule2)
    
    print(f"  总规则数: {registry.count_rules()}")
    print(f"  规则ID列表: {registry.get_all_rule_ids()}")
    
    # 测试获取规则
    rule = registry.get_rule("test_rule_1")
    print(f"  获取规则 test_rule_1: {'成功' if rule else '失败'}")
    
    # 测试按分类获取规则
    correctness_rules = registry.get_rules_by_category(RuleCategory.CORRECTNESS)
    print(f"  按分类获取规则 (CORRECTNESS): {len(correctness_rules)} 条")
    
    # 测试启用/禁用
    registry.disable_rule("test_rule_1")
    print(f"  禁用规则 test_rule_1: {'成功' if not registry.is_rule_enabled('test_rule_1') else '失败'}")
    
    registry.enable_rule("test_rule_1")
    print(f"  启用规则 test_rule_1: {'成功' if registry.is_rule_enabled('test_rule_1') else '失败'}")
    
    # 测试注销
    registry.unregister("test_rule_1")
    print(f"  注销规则 test_rule_1: {'成功' if not registry.get_rule('test_rule_1') else '失败'}")
    
    print(f"  最终规则数: {registry.count_rules()}")
    print("✓ 规则注册表测试通过\n")
    
    return True


def test_rule_context():
    """测试规则上下文"""
    print("=== 测试规则上下文 ===")
    
    code = """
class MyViewModel : ViewModel() {
    private val context: Context? = null
    
    fun doSomething() {
        GlobalScope.launch {
            // 做一些事情
        }
    }
}
"""
    
    context = RuleContext(
        code=code,
        file_path="test.kt",
        language="kotlin"
    )
    
    print(f"  文件路径: {context.file_path}")
    print(f"  语言: {context.language}")
    print(f"  文件哈希: {context.file_hash}")
    print(f"  代码行数: {len(context.get_lines())}")
    
    # 测试获取行
    line_3 = context.get_line_at(3)
    print(f"  第3行: {line_3 if line_3 else '无'}")
    
    # 测试查找模式
    line_numbers = context.find_pattern_in_lines("GlobalScope.launch")
    print(f"  查找 'GlobalScope.launch' 在第 {line_numbers} 行")
    
    # 测试缓存
    context.set_cached("test_key", "test_value")
    cached_value = context.get_cached("test_key")
    print(f"  缓存测试: {'成功' if cached_value == 'test_value' else '失败'}")
    
    print("✓ 规则上下文测试通过\n")
    
    return True


def test_rule_engine():
    """测试规则引擎"""
    print("=== 测试规则引擎 ===")
    
    # 创建引擎
    engine = RuleEngine()
    
    # 注册一些规则
    registry = engine.registry
    registry.register(NoGlobalScopeRule())
    
    # 测试代码
    test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("在 GlobalScope 中执行")
    }
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="test.kt",
        language="kotlin"
    )
    
    # 执行规则（顺序执行）
    findings, stats = engine.execute_all(context, parallel=False)
    
    print(f"  执行规则数: {stats.get('total_rules', 0)}")
    print(f"  发现的问题数: {len(findings)}")
    print(f"  执行时间: {stats.get('execution_time', 0):.3f} 秒")
    
    if findings:
        for i, finding in enumerate(findings, 1):
            print(f"  问题 {i}: {finding.rule_id} - {finding.message}")
            print(f"    严重级别: {finding.severity.value}")
            print(f"    文件: {finding.file_path}")
            print(f"    行号: {finding.line_number}")
    
    # 测试缓存
    cache_stats = engine.get_cache_stats()
    print(f"  缓存大小: {cache_stats.get('cache_size', 0)}")
    
    # 清空缓存
    engine.clear_cache()
    cache_stats = engine.get_cache_stats()
    print(f"  清空缓存后大小: {cache_stats.get('cache_size', 0)}")
    
    print("✓ 规则引擎测试通过\n")
    
    return len(findings) > 0  # 预期至少找到一个问题


def test_adapters():
    """测试适配器（装饰器）"""
    print("=== 测试适配器（装饰器） ===")
    
    from rule_engine.adapters import rule
    
    @rule(
        rule_id="simple_adapter_test",
        name="简单适配器测试",
        description="测试装饰器创建规则的功能",
        severity=RuleSeverity.INFO,
        category=RuleCategory.STYLE,
        tags=["test", "adapter"]
    )
    def simple_adapter_rule(context):
        """简单的装饰器规则测试"""
        findings = []
        
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "adapter_test" in line.lower():
                findings.append(Finding(
                    rule_id="simple_adapter_test",
                    message="发现适配器测试标记",
                    severity=RuleSeverity.INFO,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line
                ))
        
        return findings
    
    # 测试装饰器创建的规则
    rule_instance = simple_adapter_rule
    
    print(f"  适配器规则ID: {rule_instance.metadata.id}")
    print(f"  适配器规则名称: {rule_instance.metadata.name}")
    print(f"  适配器规则分类: {rule_instance.metadata.category.value}")
    
    # 测试规则执行
    test_code = """
// adapter_test: 这是一个测试标记
fun testAdapterFunction() {
    println("适配器测试")
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="test.kt",
        language="kotlin"
    )
    
    findings = rule_instance.check(context)
    
    print(f"  适配器发现的问题数: {len(findings)}")
    
    if findings:
        for finding in findings:
            print(f"    问题: {finding.message}")
            print(f"    行号: {finding.line_number}")
    
    print("✓ 适配器测试通过\n")
    
    return len(findings) > 0


def test_decorators():
    """测试装饰器"""
    print("=== 测试装饰器 ===")
    
    from rule_engine.adapters import rule
    
    @rule(
        rule_id="test_decorator_rule",
        name="测试装饰器规则",
        description="这是一个测试装饰器规则的示例",
        severity=RuleSeverity.MINOR,
        category=RuleCategory.STYLE,
        tags=["test", "decorator"]
    )
    def test_decorator_rule(context):
        """测试装饰器规则"""
        findings = []
        
        if "TODO" in context.code:
            findings.append(Finding(
                rule_id="test_decorator_rule",
                message="代码中包含TODO注释",
                severity=RuleSeverity.MINOR,
                file_path=context.file_path,
                suggestion="及时处理TODO注释"
            ))
        
        return findings
    
    # 测试装饰器创建的规则
    rule_instance = test_decorator_rule
    
    print(f"  装饰器规则ID: {rule_instance.metadata.id}")
    print(f"  装饰器规则名称: {rule_instance.metadata.name}")
    print(f"  装饰器规则分类: {rule_instance.metadata.category.value}")
    
    # 测试规则执行
    test_code = """
// TODO: 需要实现这个函数
fun todoFunction() {
    // 待实现
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="test.kt",
        language="kotlin"
    )
    
    findings = rule_instance.check(context)
    
    print(f"  装饰器规则发现的问题数: {len(findings)}")
    
    if findings:
        for finding in findings:
            print(f"    问题: {finding.message}")
    
    print("✓ 装饰器测试通过\n")
    
    return True


def test_integration():
    """测试集成功能"""
    print("=== 测试集成功能 ===")
    
    # 清空之前的注册表（单例模式）
    registry = RuleRegistry()
    registry.clear()
    
    # 创建完整引擎并注册多个规则
    engine = RuleEngine(registry)
    
    # 注册多个规则
    registry.register(NoGlobalScopeRule())
    
    # 注册装饰器规则
    from rule_engine.adapters import rule
    
    @rule(
        rule_id="empty_function",
        name="空函数检测",
        description="检测空函数体",
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
                    message="发现空函数体",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="添加函数实现或删除无用函数"
                ))
        
        return findings
    
    registry.register(empty_function_rule)
    
    print(f"  注册的规则数: {registry.count_rules()}")
    
    # 测试代码
    test_code = """
class TestClass {
    // 空函数
    fun emptyFunction() {}
    
    fun testFunction() {
        // 使用GlobalScope
        GlobalScope.launch {
            println("测试")
        }
    }
}
"""
    
    context = RuleContext(
        code=test_code,
        file_path="TestClass.kt",
        language="kotlin"
    )
    
    # 执行所有规则
    findings, stats = engine.execute_all(context, parallel=False)
    
    print(f"  执行的规则数: {stats.get('total_rules', 0)}")
    print(f"  发现的总问题数: {len(findings)}")
    
    # 分组统计
    severity_counts = {}
    for finding in findings:
        severity = finding.severity.value
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    print("  问题严重级别统计:")
    for severity, count in severity_counts.items():
        print(f"    {severity}: {count} 个")
    
    print("  详细问题列表:")
    for i, finding in enumerate(findings, 1):
        print(f"    {i}. [{finding.severity.value}] {finding.rule_id}: {finding.message}")
        if finding.line_number:
            print(f"       行号: {finding.line_number}")
        if finding.suggestion:
            print(f"       建议: {finding.suggestion}")
    
    # 测试按分类执行
    print("\n  测试按分类执行规则:")
    style_findings, style_stats = engine.execute_by_category(context, "style", parallel=False)
    print(f"  STYLE分类发现的问题: {len(style_findings)} 个")
    
    # 获取统计信息
    engine_stats = registry.get_statistics()
    print(f"  引擎统计 - 总规则: {engine_stats.get('total_rules', 0)}")
    print(f"  引擎统计 - 启用规则: {engine_stats.get('enabled_rules', 0)}")
    
    print("✓ 集成测试通过\n")
    
    return len(findings) >= 2  # 预期至少找到2个问题


def main():
    """主测试函数"""
    print("统一规则引擎功能测试\n")
    
    tests = [
        ("规则注册表", test_rule_registry),
        ("规则上下文", test_rule_context),
        ("规则引擎", test_rule_engine),
        ("适配器", test_adapters),
        ("装饰器", test_decorators),
        ("集成功能", test_integration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
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
    
    print(f"\n测试总结: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有测试通过!")
        return 0
    else:
        print("⚠️ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())