"""Tests"""
import unittest
from rule_engine.integration.review_runner import ReviewRunner
from rule_engine.registry import RuleRegistry


class TestReviewRunner(unittest.TestCase):
    """Tests"""
    
    def setUp(self):
        """TestRegister"""
        registry = RuleRegistry()
        registry.clear()
    
    def test_initialization(self):
        """Tests"""
        runner = ReviewRunner()
        
        # Initialize
        self.assertFalse(runner._initialized)
        
        # Initialize
        runner.initialize()
        self.assertTrue(runner._initialized)
        
        # Get
        engine_info = runner.get_engine_info()
        self.assertTrue(engine_info["initialized"])
        self.assertGreaterEqual(engine_info["rule_count"], 1)
        
        # Initialize
        runner.initialize()
        self.assertTrue(runner._initialized)
    
    def test_review_code(self):
        """Tests"""
        runner = ReviewRunner()
        runner.initialize()
        
        # TestGlobalScope
        test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("Test")
    }
}
"""
        
        result = runner.review_code(test_code, "test.kt", "kotlin")
        
        self.assertEqual(result["file"], "test.kt")
        self.assertIn("findings", result)
        self.assertIn("score", result)
        self.assertIn("stats", result)
        
        # 
        self.assertGreaterEqual(len(result["findings"]), 1)
        
        # （）
        self.assertLess(result["score"], 100)
        self.assertGreaterEqual(result["score"], 0)
        
        # Verify
        if result["findings"]:
            finding = result["findings"][0]
            self.assertIn("rule", finding)
            self.assertIn("message", finding)
            self.assertIn("severity", finding)
    
    def test_review_file(self):
        """Tests"""
        runner = ReviewRunner()
        runner.initialize()
        
        # Test
        test_code = """
class TestClass {
    // 
    fun emptyFunction() {}
    
    // 
    fun normalFunction() {
        println("")
    }
}
"""
        
        result = runner.review_file("TestClass.kt", test_code, "kotlin")
        
        self.assertEqual(result["file"], "TestClass.kt")
        self.assertIn("findings", result)
        
        # （Rule）
        findings = result["findings"]
        rule_ids = [f["rule"] for f in findings]
        
        # Count
        stats = result["stats"]
        self.assertIn("total_rules", stats)
        self.assertIn("execution_time", stats)
    
    def test_review_diff(self):
        """Tests"""
        runner = ReviewRunner()
        runner.initialize()
        
        # Git diff
        test_diff = """diff --git a/Test.kt b/Test.kt
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/Test.kt
@@ -0,0 +1,7 @@
+class TestClass {
+    // GlobalScope
+    fun testFunction() {
+        GlobalScope.launch {
+            println("Test")
+        }
+    }
+}
"""
        
        results = runner.review_diff(test_diff)
        
        # 
        self.assertGreaterEqual(len(results), 1)
        
        # Verify
        result = results[0]
        self.assertEqual(result["file"], "Test.kt")
        self.assertIn("findings", result)
        self.assertIn("score", result)
    
    def test_with_config(self):
        """Tests"""
        config = {
            "rules": {
                "enabled_categories": ["performance", "correctness"],
                "disabled_rules": ["no_globalscope"],
                "parallel_execution": False
            }
        }
        
        runner = ReviewRunner(config)
        runner.initialize()
        
        # Get
        engine_info = runner.get_engine_info()
        self.assertTrue(engine_info["initialized"])
        
        # Test
        test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("Test")
    }
}
"""
        
        result = runner.review_code(test_code, "test.kt", "kotlin")
        
        # Disableno_globalscopeRule，
        # RuleEnable
        
        self.assertEqual(result["file"], "test.kt")
        self.assertIn("findings", result)
    
    def test_calculate_score(self):
        """Tests"""
        runner = ReviewRunner()
        runner.initialize()
        
        # Test
        clean_code = """
fun cleanFunction() {
    println("")
}
"""
        
        clean_result = runner.review_code(clean_code, "clean.kt", "kotlin")
        self.assertEqual(clean_result["score"], 100)
        
        # Test
        problematic_code = """
fun problematicFunction() {
    GlobalScope.launch {
        println("")
    }
}
"""
        
        problematic_result = runner.review_code(problematic_code, "problematic.kt", "kotlin")
        self.assertLess(problematic_result["score"], 100)
    
    def test_engine_info(self):
        """Tests"""
        runner = ReviewRunner()
        
        # InitializeGet
        info_before = runner.get_engine_info()
        self.assertFalse(info_before["initialized"])
        self.assertEqual(info_before["rule_count"], 0)
        
        # InitializeGet
        runner.initialize()
        info_after = runner.get_engine_info()
        
        self.assertTrue(info_after["initialized"])
        self.assertGreater(info_after["rule_count"], 0)
        
        # VerifyCount
        stats = info_after["statistics"]
        self.assertIn("total_rules", stats)
        self.assertIn("enabled_rules", stats)
        self.assertIn("categories", stats)
        self.assertIn("tags", stats)
        self.assertIn("severities", stats)
        
        # VerifyCount
        cache_stats = info_after["cache_stats"]
        self.assertIn("cache_size", cache_stats)
        self.assertIn("cache_keys", cache_stats)


if __name__ == "__main__":
    unittest.main()