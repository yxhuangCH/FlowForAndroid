"""
AST Engine Performance Benchmark - AST引擎性能基准测试

测试AST引擎和旧引擎的性能对比。
"""

import os
import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def generate_test_code(num_classes: int = 10) -> str:
    """生成测试代码"""
    code = """
package com.test.performance

import kotlinx.coroutines.*
import androidx.lifecycle.ViewModel
import androidx.compose.runtime.*
import android.content.Context

"""
    
    for i in range(num_classes):
        code += f"""
class TestClass{i} {{
    private val scope = CoroutineScope(Dispatchers.Default)
    
    fun method{i}a() {{
        // 正确用法
        scope.launch {{
            println("Method {{i}}a")
        }}
    }}
    
    fun method{i}b() {{
        // 可能的问题
        launch {{
            println("Method {{i}}b")
        }}
    }}
}}

class TestViewModel{i}(
    private val context: Context  // 问题：持有Context
) : ViewModel() {{
    fun test{i}() {{
        GlobalScope.launch {{  // 问题：GlobalScope
            delay(1000)
        }}
    }}
}}

@Composable
fun TestComposable{i}() {{
    var state by mutableStateOf("")  // 问题：应该用remember
    LaunchedEffect(Unit) {{
        // 只执行一次
    }}
}}
"""
    
    return code


def benchmark_ast_engine():
    """测试AST引擎性能"""
    from ast_engine.integration import ASTEngine
    
    print("\n" + "=" * 60)
    print("🚀 AST Engine Performance Benchmark")
    print("=" * 60)
    
    # 创建引擎
    engine = ASTEngine()
    info = engine.get_engine_info()
    print(f"Engine: {info['type']} v{info['version']}")
    print(f"Rules loaded: {info['rules_count']}")
    
    # 测试不同规模的代码
    test_sizes = [10, 50, 100]
    results = []
    
    for num_classes in test_sizes:
        code = generate_test_code(num_classes)
        code_lines = code.count('\n')
        
        # 预热
        _ = engine.review_code(code, "warmup.kt")
        
        # 计时
        start_time = time.time()
        iterations = 5
        
        for _ in range(iterations):
            findings = engine.review_code(code, f"test_{num_classes}.kt")
        
        elapsed = (time.time() - start_time) / iterations
        
        result = {
            "classes": num_classes,
            "lines": code_lines,
            "time": elapsed,
            "findings": len(findings),
            "lines_per_second": code_lines / elapsed if elapsed > 0 else 0
        }
        results.append(result)
        
        print(f"\n📊 Test: {num_classes} classes ({code_lines} lines)")
        print(f"   Time: {elapsed:.4f}s")
        print(f"   Findings: {len(findings)}")
        print(f"   Performance: {code_lines / elapsed:.0f} lines/sec")
    
    return results


def benchmark_rule_engine():
    """测试旧规则引擎性能"""
    try:
        from rule_engine.integration.review_runner import ReviewRunner
        
        print("\n" + "=" * 60)
        print("🔧 Rule Engine Performance Benchmark")
        print("=" * 60)
        
        # 创建runner
        config = {
            "rules": {
                "enabled_categories": ["lifecycle", "concurrency", "correctness"],
                "parallel_execution": False
            }
        }
        runner = ReviewRunner(config)
        runner.initialize()
        
        # 测试不同规模的代码
        test_sizes = [10, 50, 100]
        results = []
        
        for num_classes in test_sizes:
            code = generate_test_code(num_classes)
            code_lines = code.count('\n')
            
            # 创建模拟diff
            diff = f"""diff --git a/test_{num_classes}.kt b/test_{num_classes}.kt
--- a/test_{num_classes}.kt
+++ b/test_{num_classes}.kt
@@ -0,0 +1,{code_lines} @@
{code}
"""
            
            # 预热
            _ = runner.review_diff(diff)
            
            # 计时
            start_time = time.time()
            iterations = 5
            
            for _ in range(iterations):
                review_results = runner.review_diff(diff)
            
            elapsed = (time.time() - start_time) / iterations
            
            # 计算findings数量
            findings_count = sum(len(r.get("findings", [])) for r in review_results)
            
            result = {
                "classes": num_classes,
                "lines": code_lines,
                "time": elapsed,
                "findings": findings_count,
                "lines_per_second": code_lines / elapsed if elapsed > 0 else 0
            }
            results.append(result)
            
            print(f"\n📊 Test: {num_classes} classes ({code_lines} lines)")
            print(f"   Time: {elapsed:.4f}s")
            print(f"   Findings: {findings_count}")
            print(f"   Performance: {code_lines / elapsed:.0f} lines/sec")
        
        return results
    except Exception as e:
        print(f"⚠ Rule engine benchmark failed: {e}")
        return []


def compare_results(ast_results, rule_results):
    """对比两个引擎的结果"""
    if not ast_results or not rule_results:
        print("\n⚠ 无法对比，缺少测试结果")
        return
    
    print("\n" + "=" * 60)
    print("📈 Performance Comparison")
    print("=" * 60)
    
    print(f"\n{'Classes':<10} {'Lines':<10} {'AST Engine':<15} {'Rule Engine':<15} {'Speedup':<10}")
    print("-" * 60)
    
    for ast, rule in zip(ast_results, rule_results):
        speedup = rule["time"] / ast["time"] if ast["time"] > 0 else 0
        print(f"{ast['classes']:<10} {ast['lines']:<10} {ast['time']:.4f}s{'':<8} {rule['time']:.4f}s{'':<8} {speedup:.2f}x")
    
    # 总结
    avg_speedup = sum(
        r["time"] / a["time"] if a["time"] > 0 else 0 
        for a, r in zip(ast_results, rule_results)
    ) / len(ast_results)
    
    print(f"\n✅ Average speedup: {avg_speedup:.2f}x")


def main():
    print("=" * 60)
    print("📋 AST Engine Performance Benchmark Suite")
    print("=" * 60)
    
    # 测试AST引擎
    ast_results = benchmark_ast_engine()
    
    # 测试规则引擎
    rule_results = benchmark_rule_engine()
    
    # 对比结果
    compare_results(ast_results, rule_results)
    
    # 保存报告
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ast_engine": ast_results,
        "rule_engine": rule_results
    }
    
    import json
    report_path = Path(__file__).parent / 'report' / 'benchmark_report.json'
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Benchmark report saved to: {report_path}")


if __name__ == "__main__":
    main()