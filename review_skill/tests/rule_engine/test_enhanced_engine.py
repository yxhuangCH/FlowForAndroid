"""
测试增强版规则引擎和配置加载器
"""
import unittest
import tempfile
import os
import json
import time
import sys

# 尝试导入yaml，如果失败则跳过相关测试
YAML_AVAILABLE = True
try:
    import yaml
except ImportError:
    YAML_AVAILABLE = False

# 添加路径以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from rule_engine.engine_enhanced import EnhancedRuleEngine, LRUCache
from rule_engine.integration.config_loader import ConfigLoader
from rule_engine.integration.review_runner import EnhancedReviewRunner
from rule_engine.registry import RuleRegistry
from rule_engine.context import RuleContext
from rule_engine.interfaces import RuleSeverity, RuleCategory, RuleMetadata, Finding
from rule_engine.rules.base_rules import NoGlobalScopeRule


class TestLRUCache(unittest.TestCase):
    """测试LRU缓存"""
    
    def test_basic_cache_operations(self):
        """测试基本缓存操作"""
        cache = LRUCache(max_size=3, ttl=60)
        
        # 测试设置和获取
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        
        # 测试不存在的键
        self.assertIsNone(cache.get("key2"))
        
        # 测试更新值
        cache.set("key1", "value1_updated")
        self.assertEqual(cache.get("key1"), "value1_updated")
        
        # 测试缓存大小
        self.assertEqual(cache.size(), 1)
    
    def test_lru_eviction(self):
        """测试LRU淘汰策略"""
        cache = LRUCache(max_size=3, ttl=3600)
        
        # 添加3个条目
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # 缓存应该满的
        self.assertEqual(cache.size(), 3)
        
        # 访问key1，使其成为最近使用的
        cache.get("key1")
        
        # 添加第4个条目，应该淘汰最旧的key2
        cache.set("key4", "value4")
        
        # key2应该被淘汰
        self.assertIsNone(cache.get("key2"))
        # key1, key3, key4应该还在
        self.assertEqual(cache.get("key1"), "value1")
        self.assertEqual(cache.get("key3"), "value3")
        self.assertEqual(cache.get("key4"), "value4")
    
    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = LRUCache(max_size=10, ttl=1)  # 1秒TTL
        
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        
        # 等待过期
        time.sleep(1.1)
        
        # 应该过期
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.size(), 0)
    
    def test_cache_stats(self):
        """测试缓存统计"""
        cache = LRUCache(max_size=5, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        stats = cache.stats()
        
        self.assertEqual(stats["size"], 2)
        self.assertEqual(stats["max_size"], 5)
        self.assertEqual(stats["ttl"], 60)
        self.assertEqual(stats["expired_count"], 0)
        self.assertIn("key1", stats["keys"])
        self.assertIn("key2", stats["keys"])
    
    def test_cache_clear(self):
        """测试清空缓存"""
        cache = LRUCache(max_size=5, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        self.assertEqual(cache.size(), 2)
        
        cache.clear()
        self.assertEqual(cache.size(), 0)
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))


class TestEnhancedRuleEngine(unittest.TestCase):
    """测试增强版规则引擎"""
    
    def setUp(self):
        """每个测试前设置"""
        self.registry = RuleRegistry()
        self.registry.clear()
        
        # 注册测试规则
        self.registry.register(NoGlobalScopeRule())
        
        # 创建自定义测试规则
        class TestRule:
            def __init__(self, rule_id):
                self._metadata = RuleMetadata(
                    id=rule_id,
                    name=f"Test Rule {rule_id}",
                    description=f"Test description for {rule_id}",
                    severity=RuleSeverity.MINOR,
                    category=RuleCategory.CORRECTNESS,
                    tags=["test"],
                    weight=1.0
                )
            
            @property
            def metadata(self):
                return self._metadata
            
            def check(self, context):
                findings = []
                if "test_pattern" in context.code:
                    findings.append(Finding(
                        rule_id=self.metadata.id,
                        message="Found test pattern",
                        severity=RuleSeverity.MINOR,
                        file_path=context.file_path
                    ))
                return findings
        
        self.test_rule = TestRule("test_rule_1")
        self.registry.register(self.test_rule)
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        # 默认配置
        engine = EnhancedRuleEngine(self.registry)
        
        self.assertIsNotNone(engine.registry)
        self.assertIsNotNone(engine.config)
        self.assertTrue(engine.parallel_enabled)
        self.assertIsNotNone(engine.max_workers)
        self.assertGreater(engine.max_workers, 0)
        
        # 带配置初始化
        config = {
            "cache": {"enabled": False},
            "parallel": {"enabled": False, "max_workers": 2}
        }
        engine_with_config = EnhancedRuleEngine(self.registry, config)
        self.assertFalse(engine_with_config.cache)
        self.assertFalse(engine_with_config.parallel_enabled)
        self.assertEqual(engine_with_config.max_workers, 2)
    
    def test_execute_all_sequential(self):
        """测试顺序执行"""
        config = {"parallel": {"enabled": False}}
        engine = EnhancedRuleEngine(self.registry, config)
        
        # 测试代码
        test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("测试")
    }
    // test_pattern
}
"""
        
        context = RuleContext(
            code=test_code,
            file_path="test.kt",
            language="kotlin"
        )
        
        findings, stats = engine.execute_all(context)
        
        self.assertGreaterEqual(len(findings), 1)
        self.assertIn("total_rules", stats)
        self.assertIn("execution_time", stats)
        self.assertIn("rule_stats", stats)
        
        # 验证规则统计
        self.assertIn("no_globalscope", stats["rule_stats"])
        self.assertIn("test_rule_1", stats["rule_stats"])
    
    def test_execute_all_parallel(self):
        """测试并行执行"""
        config = {"parallel": {"enabled": True, "max_workers": 2}}
        engine = EnhancedRuleEngine(self.registry, config)
        
        test_code = """
fun testFunction() {
    GlobalScope.launch {
        println("测试")
    }
}
"""
        
        context = RuleContext(
            code=test_code,
            file_path="test.kt",
            language="kotlin"
        )
        
        findings, stats = engine.execute_all(context)
        
        self.assertGreaterEqual(len(findings), 1)
        self.assertIn("total_rules", stats)
        self.assertIn("max_workers", stats)
        self.assertIn("rule_stats", stats)
    
    def test_cache_functionality(self):
        """测试缓存功能"""
        config = {
            "cache": {"enabled": True, "max_size": 10, "ttl": 60}
        }
        engine = EnhancedRuleEngine(self.registry, config)
        
        test_code = "fun test() { GlobalScope.launch {} }"
        context = RuleContext(
            code=test_code,
            file_path="test.kt",
            language="kotlin"
        )
        
        # 第一次执行（应该缓存）
        findings1, stats1 = engine.execute_all(context, parallel=False)
        self.assertIn("cache_hits", stats1)
        self.assertIn("cache_misses", stats1)
        
        # 第二次执行（应该命中缓存）
        findings2, stats2 = engine.execute_all(context, parallel=False)
        
        # 两次结果应该相同
        self.assertEqual(len(findings1), len(findings2))
        
        # 第一次应该没有命中，第二次应该有命中
        self.assertGreater(stats1["cache_misses"], 0)
        
        # 获取缓存统计
        cache_stats = engine.get_cache_stats()
        self.assertTrue(cache_stats["enabled"])
        self.assertGreater(cache_stats["size"], 0)
    
    def test_engine_stats(self):
        """测试引擎统计"""
        engine = EnhancedRuleEngine(self.registry)
        
        stats = engine.get_engine_stats()
        
        self.assertIn("total_executions", stats)
        self.assertIn("total_findings", stats)
        self.assertIn("cache_enabled", stats)
        self.assertIn("parallel_enabled", stats)
        self.assertIn("max_workers", stats)
        self.assertIn("execution_timeout", stats)
        self.assertIn("cache_stats", stats)
    
    def test_execute_by_category(self):
        """测试按分类执行"""
        engine = EnhancedRuleEngine(self.registry)
        
        test_code = "fun test() { GlobalScope.launch {} }"
        context = RuleContext(
            code=test_code,
            file_path="test.kt",
            language="kotlin"
        )
        
        # 执行LIFECYCLE分类的规则
        findings, stats = engine.execute_by_category(context, "lifecycle")
        
        self.assertGreaterEqual(len(findings), 1)
        self.assertIn("total_rules", stats)
        
        # 执行不存在的分类
        findings_empty, stats_empty = engine.execute_by_category(context, "nonexistent")
        self.assertEqual(len(findings_empty), 0)
        self.assertIn("error", stats_empty)
    
    def test_execute_by_priority(self):
        """测试按优先级执行"""
        engine = EnhancedRuleEngine(self.registry)
        
        test_code = "fun test() { GlobalScope.launch {} }"
        context = RuleContext(
            code=test_code,
            file_path="test.kt",
            language="kotlin"
        )
        
        findings, stats = engine.execute_by_priority(context, high_priority_first=True)
        
        self.assertGreaterEqual(len(findings), 1)
        self.assertIn("total_rules", stats)
    
    def test_clear_cache(self):
        """测试清空缓存"""
        config = {
            "cache": {"enabled": True, "max_size": 10, "ttl": 60}
        }
        engine = EnhancedRuleEngine(self.registry, config)
        
        test_code = "fun test() { GlobalScope.launch {} }"
        context = RuleContext(
            code=test_code,
            file_path="test.kt",
            language="kotlin"
        )
        
        # 执行一次以填充缓存
        engine.execute_all(context, parallel=False)
        
        # 清空缓存
        engine.clear_cache()
        
        # 验证缓存已清空
        cache_stats = engine.get_cache_stats()
        self.assertEqual(cache_stats["size"], 0)


class TestConfigLoader(unittest.TestCase):
    """测试配置加载器"""
    
    def test_default_config(self):
        """测试默认配置"""
        loader = ConfigLoader()
        config = loader.load(None)  # 不提供配置文件
        
        self.assertIn("rule_engine", config)
        self.assertIn("integration", config)
        
        engine_config = config["rule_engine"]
        self.assertTrue(engine_config["enabled"])
        self.assertTrue(engine_config["parallel_execution"])
        self.assertIsNone(engine_config["max_workers"])
        self.assertTrue(engine_config["cache_enabled"])
        self.assertEqual(engine_config["cache_max_size"], 1000)
        self.assertEqual(engine_config["cache_ttl"], 3600)
        self.assertEqual(engine_config["execution_timeout"], 30)
    
    def test_json_config_file(self):
        """测试JSON配置文件"""
        # 创建临时JSON配置文件
        json_config = {
            "rule_engine": {
                "enabled": False,
                "parallel_execution": False,
                "max_workers": 2,
                "cache_enabled": False
            },
            "integration": {
                "review": {
                    "min_score_threshold": 80,
                    "block_on_critical": False
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_config, f)
            config_file = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load(config_file)
            
            # 验证配置被正确加载
            engine_config = config["rule_engine"]
            self.assertFalse(engine_config["enabled"])
            self.assertFalse(engine_config["parallel_execution"])
            self.assertEqual(engine_config["max_workers"], 2)
            self.assertFalse(engine_config["cache_enabled"])
            
            # 验证集成配置
            review_config = config["integration"]["review"]
            self.assertEqual(review_config["min_score_threshold"], 80)
            self.assertFalse(review_config["block_on_critical"])
        finally:
            os.unlink(config_file)
    
    def test_yaml_config_file(self):
        """测试YAML配置文件"""
        # 如果yaml不可用，跳过测试
        if not YAML_AVAILABLE:
            self.skipTest("PyYAML未安装，跳过YAML配置测试")
        
        # 创建临时YAML配置文件
        yaml_config = """
rule_engine:
  enabled: false
  parallel_execution: false
  max_workers: 4
  cache_enabled: true
  cache_max_size: 500
  cache_ttl: 1800
  
integration:
  review:
    min_score_threshold: 60
    generate_html_report: false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_config)
            config_file = f.name
        
        try:
            loader = ConfigLoader()
            config = loader.load(config_file)
            
            # 验证配置被正确加载
            engine_config = config["rule_engine"]
            self.assertFalse(engine_config["enabled"])
            self.assertFalse(engine_config["parallel_execution"])
            self.assertEqual(engine_config["max_workers"], 4)
            self.assertTrue(engine_config["cache_enabled"])
            self.assertEqual(engine_config["cache_max_size"], 500)
            self.assertEqual(engine_config["cache_ttl"], 1800)
            
            # 验证集成配置
            review_config = config["integration"]["review"]
            self.assertEqual(review_config["min_score_threshold"], 60)
            self.assertFalse(review_config["generate_html_report"])
        finally:
            os.unlink(config_file)
    
    def test_env_overrides(self):
        """测试环境变量覆盖"""
        # 设置环境变量
        os.environ["RULE_ENGINE_ENABLED"] = "false"
        os.environ["RULE_ENGINE_PARALLEL"] = "false"
        os.environ["RULE_ENGINE_MAX_WORKERS"] = "3"
        os.environ["REVIEW_MIN_SCORE"] = "75"
        
        try:
            loader = ConfigLoader()
            config = loader.load(None)
            
            # 验证环境变量被正确应用
            engine_config = config["rule_engine"]
            self.assertFalse(engine_config["enabled"])
            self.assertFalse(engine_config["parallel_execution"])
            self.assertEqual(engine_config["max_workers"], 3)
            
            # 验证集成配置
            review_config = config["integration"]["review"]
            self.assertEqual(review_config["min_score_threshold"], 75)
        finally:
            # 清理环境变量
            del os.environ["RULE_ENGINE_ENABLED"]
            del os.environ["RULE_ENGINE_PARALLEL"]
            del os.environ["RULE_ENGINE_MAX_WORKERS"]
            del os.environ["REVIEW_MIN_SCORE"]
    
    def test_config_validation(self):
        """测试配置验证"""
        loader = ConfigLoader()
        
        # 测试无效配置
        invalid_config = {
            "rule_engine": {
                "max_workers": -1,  # 无效
                "cache_max_size": -100,  # 无效
                "cache_ttl": -50,  # 无效
                "execution_timeout": -10  # 无效
            },
            "integration": {
                "review": {
                    "min_score_threshold": 150  # 无效，应该大于100
                }
            }
        }
        
        # 手动设置配置并验证
        loader.config = loader.DEFAULT_CONFIG.copy()
        loader._deep_merge(loader.config, invalid_config)
        loader._validate_config()
        
        # 验证无效值被修正
        engine_config = loader.config["rule_engine"]
        self.assertIsNone(engine_config["max_workers"])  # 应该被设为None
        self.assertEqual(engine_config["cache_max_size"], 1000)  # 应该被设为默认值
        self.assertEqual(engine_config["cache_ttl"], 3600)  # 应该被设为默认值
        self.assertEqual(engine_config["execution_timeout"], 30)  # 应该被设为默认值
        
        # 验证集成配置
        review_config = loader.config["integration"]["review"]
        self.assertEqual(review_config["min_score_threshold"], 70)  # 应该被设为默认值
    
    def test_config_methods(self):
        """测试配置方法"""
        loader = ConfigLoader()
        config = loader.load(None)
        
        # 测试各种获取方法
        engine_config = loader.get_engine_config()
        self.assertIn("enabled", engine_config)
        
        integration_config = loader.get_integration_config()
        self.assertIn("review", integration_config)
        
        rule_config = loader.get_rule_config()
        self.assertIn("enabled_categories", rule_config)
        
        logging_config = loader.get_logging_config()
        self.assertIn("level", logging_config)
        
        review_config = loader.get_review_config()
        self.assertIn("min_score_threshold", review_config)
        
        diff_parser_config = loader.get_diff_parser_config()
        self.assertIn("enabled", diff_parser_config)


class TestEnhancedReviewRunner(unittest.TestCase):
    """测试增强版审查运行器"""
    
    def setUp(self):
        """每个测试前清理注册表"""
        registry = RuleRegistry()
        registry.clear()
    
    def test_initialization_with_config(self):
        """测试带配置的初始化"""
        config = {
            "cache": {
                "enabled": True,
                "max_size": 500,
                "ttl": 1800
            },
            "parallel": {
                "enabled": False,
                "max_workers": 2
            },
            "rules": {
                "enabled_categories": ["lifecycle", "performance"]
            }
        }
        
        runner = EnhancedReviewRunner(config)
        
        # 验证配置被正确应用
        self.assertIn("cache", runner.config)
        self.assertIn("parallel", runner.config)
        self.assertIn("rules", runner.config)
        
        # 初始化
        runner.initialize()
        self.assertTrue(runner._initialized)
        
        # 获取引擎信息
        engine_info = runner.get_engine_info()
        self.assertTrue(engine_info["initialized"])
        self.assertGreaterEqual(engine_info["rule_count"], 1)
    
    def test_initialization_without_config(self):
        """测试无配置的初始化（使用配置加载器）"""
        runner = EnhancedReviewRunner()  # 不提供配置
        
        # 应该使用配置加载器的默认配置
        self.assertIn("cache", runner.config)
        self.assertIn("parallel", runner.config)
        self.assertIn("rules", runner.config)
        
        runner.initialize()
        self.assertTrue(runner._initialized)
    
    def test_review_with_enhanced_engine(self):
        """测试使用增强版引擎进行审查"""
        runner = EnhancedReviewRunner()
        runner.initialize()
        
        # 测试代码
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
        self.assertIn("engine_stats", result)
        
        # 应该找到至少一个问题
        self.assertGreaterEqual(len(result["findings"]), 1)
        
        # 验证统计信息包含增强版引擎特有的字段
        stats = result["stats"]
        self.assertIn("cache_hits", stats)
        self.assertIn("cache_misses", stats)
    
    def test_enhanced_engine_stats(self):
        """测试增强版引擎统计"""
        runner = EnhancedReviewRunner()
        runner.initialize()
        
        engine_info = runner.get_engine_info()
        
        self.assertTrue(engine_info["initialized"])
        self.assertGreaterEqual(engine_info["rule_count"], 1)
        
        # 验证统计信息
        stats = engine_info["statistics"]
        self.assertIn("total_rules", stats)
        self.assertIn("enabled_rules", stats)
        
        # 验证缓存统计
        cache_stats = engine_info["cache_stats"]
        self.assertIn("enabled", cache_stats)
        self.assertIn("size", cache_stats)
    
    def test_review_diff_with_enhanced_runner(self):
        """测试使用增强版运行器审查diff"""
        runner = EnhancedReviewRunner()
        runner.initialize()
        
        # 模拟Git diff
        test_diff = """diff --git a/Test.kt b/Test.kt
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/Test.kt
@@ -0,0 +1,7 @@
+class TestClass {
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
        
        # 应该找到GlobalScope问题
        if result["findings"]:
            rule_ids = [f["rule"] for f in result["findings"]]
            self.assertIn("no_globalscope", rule_ids)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTest(unittest.makeSuite(TestLRUCache))
    suite.addTest(unittest.makeSuite(TestEnhancedRuleEngine))
    suite.addTest(unittest.makeSuite(TestConfigLoader))
    suite.addTest(unittest.makeSuite(TestEnhancedReviewRunner))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("运行增强版规则引擎测试...")
    success = run_tests()
    
    if success:
        print("🎉 所有测试通过!")
    else:
        print("⚠️ 部分测试失败")
    
    sys.exit(0 if success else 1)