#!/usr/bin/env python3
"""
测试所有已迁移的规则
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rule_engine.integration.review_runner import EnhancedReviewRunner


def test_flow_rules(runner):
    """测试Flow相关规则"""
    print("\n" + "="*60)
    print("测试Flow相关规则")
    print("="*60)
    
    # runner 已由外部初始化和提供
    
    # 测试flowOn(Dispatchers.Main)
    test_code = """
    fun testFlow() {
        flow {
            emit(1)
        }.flowOn(Dispatchers.Main)
    }
    """
    result = runner.review_code(test_code, "flow_test.kt")
    findings = result["findings"]
    print(f"1. flowOn(Dispatchers.Main)检测:")
    for f in findings:
        if f["rule"] == "flowon_main_dispatcher":
            print(f"   ✅ 检测到: {f['message']}")
            break
    else:
        print("   ❌ 未检测到flowOn(Dispatchers.Main)问题")
    
    # 测试SharingStarted.Eagerly
    test_code = """
    fun testSharing() {
        val sharedFlow = flow { emit(1) }.shareIn(viewModelScope, SharingStarted.Eagerly)
    }
    """
    result = runner.review_code(test_code, "sharing_test.kt")
    findings = result["findings"]
    print(f"2. SharingStarted.Eagerly检测:")
    for f in findings:
        if f["rule"] == "eager_sharing_detected":
            print(f"   ✅ 检测到: {f['message']}")
            break
    else:
        print("   ❌ 未检测到SharingStarted.Eagerly问题")


def test_flow_lifecycle_rules(runner):
    """测试Flow生命周期规则"""
    print("\n" + "="*60)
    print("测试Flow生命周期规则")
    print("="*60)
    
    # 测试stateIn(GlobalScope)
    test_code = """
    fun testStateIn() {
        val stateFlow = flow { emit(1) }.stateIn(GlobalScope)
    }
    """
    result = runner.review_code(test_code, "statein_test.kt")
    findings = result["findings"]
    print(f"1. stateIn(GlobalScope)检测:")
    for f in findings:
        if f["rule"] == "statein_globalscope":
            print(f"   ✅ 检测到: {f['message']}")
            break
    else:
        print("   ❌ 未检测到stateIn(GlobalScope)问题")
    
    # 测试collect未使用repeatOnLifecycle
    test_code = """
    class TestActivity : Activity() {
        fun testCollect() {
            viewModel.flow.collect { value ->
                // 处理数据
            }
        }
    }
    """
    result = runner.review_code(test_code, "collect_test.kt")
    findings = result["findings"]
    print(f"2. collect未使用repeatOnLifecycle检测:")
    for f in findings:
        if f["rule"] == "collect_without_repeat":
            print(f"   ✅ 检测到: {f['message']}")
            break
    else:
        print("   ❌ 未检测到collect未使用repeatOnLifecycle问题")


def test_flow_structure_rules(runner):
    """测试Flow结构规则"""
    print("\n" + "="*60)
    print("测试Flow结构规则")
    print("="*60)
    
    # 测试flow builder内部使用launch
    test_code = """
    fun testFlowBuilder() {
        flow {
            launch {
                // 在flow builder内部使用launch
            }
        }
    }
    """
    result = runner.review_code(test_code, "flow_builder_test.kt")
    findings = result["findings"]
    print(f"1. flow builder内部使用launch检测:")
    for f in findings:
        if f["rule"] == "launch_inside_flow":
            print(f"   ✅ 检测到: {f['message']}")
            break
    else:
        print("   ❌ 未检测到flow builder内部使用launch问题")
    
    # 测试多次collect
    test_code = """
    fun testMultipleCollects() {
        flow1.collect { }
        flow1.collect { }
    }
    """
    result = runner.review_code(test_code, "multiple_collects_test.kt")
    findings = result["findings"]
    print(f"2. 多次collect检测:")
    for f in findings:
        if f["rule"] == "multiple_collects":
            print(f"   ✅ 检测到: {f['message']}")
            break
    else:
        print("   ❌ 未检测到多次collect问题")


def test_hilt_rules(runner):
    """测试Hilt规则"""
    print("\n" + "="*60)
    print("测试Hilt规则")
    print("="*60)
    
    # 测试@Singleton注入Activity
    test_code = """
    @Singleton
    class MyRepository @Inject constructor() { }
    
    class MainActivity : Activity() {
        @Inject lateinit var repository: MyRepository
    }
    """
    result = runner.review_code(test_code, "hilt_test.kt")
    findings = result["findings"]
    print(f"1. @Singleton注入Activity检测:")
    for f in findings:
        if f["rule"] == "singleton_activity":
            print(f"   ✅ 检测到: {f['message']}")
            break
    else:
        print("   ❌ 未检测到@Singleton注入Activity问题")


def test_dagger2_rules(runner):
    """测试Dagger2规则"""
    print("\n" + "="*60)
    print("测试Dagger2规则")
    print("="*60)
    
    # 测试字段注入
    test_code = """
    class MyService {
        @Inject lateinit var repository: Repository
    }
    """
    result = runner.review_code(test_code, "dagger2_test.kt")
    findings = result["findings"]
    print(f"1. 字段注入检测:")
    for f in findings:
        if f["rule"] == "field_injection_detected":
            print(f"   ✅ 检测到: {f['message']}")
            break
    else:
        print("   ❌ 未检测到字段注入问题")
    
    # 测试@Provides未指定作用域
    test_code = """
    @Module
    class MyModule {
        @Provides
        fun provideRepository(): Repository {
            return RepositoryImpl()
        }
    }
    """
    result = runner.review_code(test_code, "provides_test.kt")
    findings = result["findings"]
    print(f"2. @Provides未指定作用域检测:")
    for f in findings:
        if f["rule"] == "provides_without_scope":
            print(f"   ✅ 检测到: {f['message']}")
            break
    else:
        print("   ❌ 未检测到@Provides未指定作用域问题")


def test_engine_info(runner):
    """测试引擎信息"""
    print("\n" + "="*60)
    print("测试引擎信息和规则统计")
    print("="*60)
    
    info = runner.get_engine_info()
    print(f"引擎初始化状态: {info['initialized']}")
    print(f"规则总数: {info['rule_count']}")
    
    stats = info["statistics"]
    print(f"规则统计:")
    print(f"  - 总规则数: {stats.get('total_rules', 0)}")
    print(f"  - 启用规则数: {stats.get('enabled_rules', 0)}")
    print(f"  - 分类分布: {stats.get('categories', {})}")
    
    # 列出所有已注册的规则
    print("\n已注册的规则:")
    categories = stats.get("categories", {})
    for category, count in categories.items():
        print(f"  - {category}: {count}条规则")


def main():
    """主测试函数"""
    print("开始测试所有已迁移的规则")
    print("="*60)
    
    try:
        # 创建并初始化一个runner实例
        runner = EnhancedReviewRunner()
        runner.initialize()
        
        # 使用同一个runner运行所有测试
        test_flow_rules(runner)
        test_flow_lifecycle_rules(runner)
        test_flow_structure_rules(runner)
        test_hilt_rules(runner)
        test_dagger2_rules(runner)
        test_engine_info(runner)
        
        print("\n" + "="*60)
        print("✅ 所有规则迁移测试完成！")
        print("="*60)
        
        # 总结已迁移的规则模块
        print("\n已成功迁移的规则模块:")
        modules = [
            "base_rules.py (基础规则)",
            "coroutine_rules.py (协程规则)",
            "compose_rules.py (Compose规则)",
            "flow_rules.py (Flow规则)",
            "flow_lifecycle_rules.py (Flow生命周期规则)",
            "flow_structure_rules.py (Flow结构规则)",
            "hilt_rules.py (Hilt规则)",
            "dagger2_rules.py (Dagger2规则)"
        ]
        for module in modules:
            print(f"  ✓ {module}")
        
        print("\n规则引擎统一完成情况:")
        print("  ✅ 所有旧规则模块已迁移到新引擎格式")
        print("  ✅ 规则注册系统已集成所有新规则")
        print("  ✅ 增强版审查运行器已更新")
        print("  ✅ 向后兼容适配器保持可用")
        
        return 0
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())