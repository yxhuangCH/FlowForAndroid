"""
测试集成功能
"""
import unittest
from rule_engine.integration.review_runner import ReviewRunner
from rule_engine.registry import RuleRegistry


class TestReviewRunner(unittest.TestCase):
    """测试审查运行器"""
    
    def setUp(self):
        """每个测试前清理注册表"""
        registry = RuleRegistry()
        registry.clear()
    
    def test_initialization(self):
        """测试初始化"""
        runner = ReviewRunner()
        
        # 初始状态未初始化
        self.assertFalse(runner._initialized)
        
        # 初始化
        runner.initialize()
        self.assertTrue(runner._initialized)
        
        # 获取引擎信息
        engine_info = runner.get_engine_info()
        self.assertTrue(engine_info["initialized"])
        self.assertGreaterEqual(engine_info["rule_count"], 1)
        
        # 再次初始化应该不会有问题
        runner.initialize()
        self.assertTrue(runner._initialized)
    
    def test_review_code(self):
        """测试审查代码"""
        runner = ReviewRunner()
        runner.initialize()
        
        # 测试代码包含GlobalScope
        test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("测试")
    }
}
"""
        
        result = runner.review_code(test_code, "test.kt", "kotlin")
        
        self.assertEqual(result["file"], "test.kt")
        self.assertIn("findings", result)
        self.assertIn("score", result)
        self.assertIn("stats", result)
        
        # 应该找到至少一个问题
        self.assertGreaterEqual(len(result["findings"]), 1)
        
        # 分数应该在合理范围内（因为有问题会扣分）
        self.assertLess(result["score"], 100)
        self.assertGreaterEqual(result["score"], 0)
        
        # 验证问题内容
        if result["findings"]:
            finding = result["findings"][0]
            self.assertIn("rule", finding)
            self.assertIn("message", finding)
            self.assertIn("severity", finding)
    
    def test_review_file(self):
        """测试审查文件"""
        runner = ReviewRunner()
        runner.initialize()
        
        # 测试代码包含空函数
        test_code = """
class TestClass {
    // 空函数
    fun emptyFunction() {}
    
    // 正常函数
    fun normalFunction() {
        println("正常")
    }
}
"""
        
        result = runner.review_file("TestClass.kt", test_code, "kotlin")
        
        self.assertEqual(result["file"], "TestClass.kt")
        self.assertIn("findings", result)
        
        # 应该找到空函数问题（如果有空函数检测规则）
        findings = result["findings"]
        rule_ids = [f["rule"] for f in findings]
        
        # 至少应该有一些统计信息
        stats = result["stats"]
        self.assertIn("total_rules", stats)
        self.assertIn("execution_time", stats)
    
    def test_review_diff(self):
        """测试审查Git diff"""
        runner = ReviewRunner()
        runner.initialize()
        
        # 模拟Git diff
        test_diff = """diff --git a/Test.kt b/Test.kt
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/Test.kt
@@ -0,0 +1,7 @@
+class TestClass {
+    // 使用GlobalScope
+    fun testFunction() {
+        GlobalScope.launch {
+            println("测试")
+        }
+    }
+}
"""
        
        results = runner.review_diff(test_diff)
        
        # 应该至少有一个结果
        self.assertGreaterEqual(len(results), 1)
        
        # 验证结果结构
        result = results[0]
        self.assertEqual(result["file"], "Test.kt")
        self.assertIn("findings", result)
        self.assertIn("score", result)
    
    def test_with_config(self):
        """测试带配置的审查"""
        config = {
            "rules": {
                "enabled_categories": ["performance", "correctness"],
                "disabled_rules": ["no_globalscope"],
                "parallel_execution": False
            }
        }
        
        runner = ReviewRunner(config)
        runner.initialize()
        
        # 获取引擎信息
        engine_info = runner.get_engine_info()
        self.assertTrue(engine_info["initialized"])
        
        # 测试代码
        test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("测试")
    }
}
"""
        
        result = runner.review_code(test_code, "test.kt", "kotlin")
        
        # 由于禁用了no_globalscope规则，可能找不到问题
        # 这取决于哪些规则被启用
        
        self.assertEqual(result["file"], "test.kt")
        self.assertIn("findings", result)
    
    def test_calculate_score(self):
        """测试分数计算"""
        runner = ReviewRunner()
        runner.initialize()
        
        # 测试无问题的代码
        clean_code = """
fun cleanFunction() {
    println("干净的代码")
}
"""
        
        clean_result = runner.review_code(clean_code, "clean.kt", "kotlin")
        self.assertEqual(clean_result["score"], 100)
        
        # 测试有问题的代码
        problematic_code = """
fun problematicFunction() {
    GlobalScope.launch {
        println("有问题的代码")
    }
}
"""
        
        problematic_result = runner.review_code(problematic_code, "problematic.kt", "kotlin")
        self.assertLess(problematic_result["score"], 100)
    
    def test_engine_info(self):
        """测试引擎信息"""
        runner = ReviewRunner()
        
        # 初始化前获取信息
        info_before = runner.get_engine_info()
        self.assertFalse(info_before["initialized"])
        self.assertEqual(info_before["rule_count"], 0)
        
        # 初始化后获取信息
        runner.initialize()
        info_after = runner.get_engine_info()
        
        self.assertTrue(info_after["initialized"])
        self.assertGreater(info_after["rule_count"], 0)
        
        # 验证统计信息
        stats = info_after["statistics"]
        self.assertIn("total_rules", stats)
        self.assertIn("enabled_rules", stats)
        self.assertIn("categories", stats)
        self.assertIn("tags", stats)
        self.assertIn("severities", stats)
        
        # 验证缓存统计
        cache_stats = info_after["cache_stats"]
        self.assertIn("cache_size", cache_stats)
        self.assertIn("cache_keys", cache_stats)


if __name__ == "__main__":
    unittest.main()