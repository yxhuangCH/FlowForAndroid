#!/usr/bin/env python3
"""
Demo of Enhanced Rule Engine Features
Demonstrates parallel processing, LRU/TTL cache, configuration support, and other advanced features
"""
import os
import sys
import json
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rule_engine.engine import RuleEngine, LRUCache
from rule_engine.integration.config_loader import ConfigLoader
from rule_engine.integration.review_runner import EnhancedReviewRunner
from rule_engine.registry import RuleRegistry
from rule_engine.context import RuleContext
from rule_engine.rules.base_rules import NoGlobalScopeRule


def demo_lru_cache():
    """Demo LRU cache functionality"""
    print("=" * 60)
    print("Demo: LRU/TTL Cache")
    print("=" * 60)
    
    # Create cache
    cache = LRUCache(max_size=5, ttl=2)  # Max 5 entries, 2 seconds TTL
    
    # Add data
    for i in range(5):
        cache.set(f"key_{i}", f"value_{i}")
    
    print(f"Initial cache size: {cache.size()}")
    print(f"Get key_2: {cache.get('key_2')}")
    print(f"Get non-existent key_10: {cache.get('key_10')}")
    
    # Test LRU eviction
    print("\nTesting LRU eviction strategy:")
    cache.get("key_0")  # Access key_0 to make it most recently used
    cache.set("key_5", "value_5")  # Add 6th entry
    
    print(f"Cache size after adding key_5: {cache.size()}")
    print(f"key_1 should be evicted: {'key_1' not in [k for k, _ in cache.cache.items()]}")
    print(f"key_0 should still exist: {cache.get('key_0') is not None}")
    
    # Test TTL expiration
    print("\nTesting TTL expiration strategy:")
    cache.set("expiring_key", "expiring_value")
    print(f"Set expiring_key: {cache.get('expiring_key')}")
    
    time.sleep(2.1)  # Wait for expiration
    print(f"Get expiring_key after 2.1s: {cache.get('expiring_key')}")
    
    # Display cache statistics
    stats = cache.stats()
    print(f"\nCache Statistics:")
    print(f"  Size: {stats['size']}/{stats['max_size']}")
    print(f"  TTL: {stats['ttl']}s")
    print(f"  Expired entries: {stats['expired_count']}")
    print(f"  First few keys: {stats['keys'][:3]}...")


def demo_enhanced_engine():
    """Demo enhanced rule engine"""
    print("\n" + "=" * 60)
    print("Demo: Enhanced Rule Engine")
    print("=" * 60)
    
    # Create registry and register rules
    registry = RuleRegistry()
    registry.clear()
    registry.register(NoGlobalScopeRule())
    
    # Create test code
    test_code = """
fun testFunction1() {
    GlobalScope.launch {
        println("Test 1")
    }
}

fun testFunction2() {
    GlobalScope.launch {
        println("Test 2")
    }
}
"""
    
    # Create context
    context = RuleContext(
        code=test_code,
        file_path="Demo.kt",
        language="kotlin"
    )
    
    print("Test code:")
    print(test_code)
    print("\n1. Test sequential execution (cache disabled):")
    config_no_cache = {
        "cache": {"enabled": False},
        "parallel": {"enabled": False}
    }
    engine_no_cache = RuleEngine(registry, config_no_cache)
    
    start_time = time.time()
    findings1, stats1 = engine_no_cache.execute_all(context)
    exec_time1 = time.time() - start_time
    
    print(f"  Execution time: {exec_time1:.4f}s")
    print(f"  Findings count: {len(findings1)}")
    print(f"  Cache hits: {stats1.get('cache_hits', 0)}, Cache misses: {stats1.get('cache_misses', 0)}")
    
    print("\n2. Test cache functionality (cache enabled):")
    config_with_cache = {
        "cache": {"enabled": True, "max_size": 100, "ttl": 10},
        "parallel": {"enabled": False}
    }
    engine_with_cache = RuleEngine(registry, config_with_cache)
    
    # First execution (populate cache)
    start_time = time.time()
    findings2, stats2 = engine_with_cache.execute_all(context)
    exec_time2 = time.time() - start_time
    
    print(f"  First execution time: {exec_time2:.4f}s")
    print(f"  Cache hits: {stats2.get('cache_hits', 0)}, Cache misses: {stats2.get('cache_misses', 0)}")
    
    # Second execution (should hit cache)
    start_time = time.time()
    findings3, stats3 = engine_with_cache.execute_all(context)
    exec_time3 = time.time() - start_time
    
    print(f"  Second execution time: {exec_time3:.4f}s")
    print(f"  Cache hits: {stats3.get('cache_hits', 0)}, Cache misses: {stats3.get('cache_misses', 0)}")
    print(f"  Performance improvement: {(exec_time2 - exec_time3)/exec_time2*100:.1f}%")
    
    print("\n3. Test parallel execution:")
    config_parallel = {
        "cache": {"enabled": True},
        "parallel": {"enabled": True, "max_workers": 2}
    }
    engine_parallel = RuleEngine(registry, config_parallel)
    
    start_time = time.time()
    findings4, stats4 = engine_parallel.execute_all(context)
    exec_time4 = time.time() - start_time
    
    print(f"  Parallel execution time: {exec_time4:.4f}s")
    print(f"  Max workers: {stats4.get('max_workers', 1)}")
    print(f"  Timeouts: {stats4.get('timeouts', 0)}")
    
    # Display engine statistics
    engine_stats = engine_parallel.get_engine_stats()
    print(f"\nEngine Statistics:")
    print(f"  Total executions: {engine_stats['total_executions']}")
    print(f"  Total findings: {engine_stats['total_findings']}")
    print(f"  Cache enabled: {engine_stats['cache_enabled']}")
    print(f"  Parallel enabled: {engine_stats['parallel_enabled']}")
    print(f"  Max workers: {engine_stats['max_workers']}")
    print(f"  Execution timeout: {engine_stats['execution_timeout']}s")
    
    # Display cache statistics
    cache_stats = engine_parallel.get_cache_stats()
    print(f"  Cache Statistics:")
    for key, value in cache_stats.items():
        print(f"    {key}: {value}")


def demo_config_loader():
    """Demo config loader"""
    print("\n" + "=" * 60)
    print("Demo: Config Loader")
    print("=" * 60)
    
    # Create config loader
    loader = ConfigLoader()
    
    print("1. Load default config:")
    default_config = loader.load(None)
    
    engine_config = default_config["rule_engine"]
    print(f"  Rule engine enabled: {engine_config['enabled']}")
    print(f"  Parallel execution: {engine_config['parallel_execution']}")
    print(f"  Max workers: {engine_config['max_workers']}")
    print(f"  Cache enabled: {engine_config['cache_enabled']}")
    print(f"  Cache max size: {engine_config['cache_max_size']}")
    print(f"  Cache TTL: {engine_config['cache_ttl']}s")
    print(f"  Execution timeout: {engine_config['execution_timeout']}s")
    
    print("\n2. Test config methods:")
    print(f"  Get rule config: {loader.get_rule_config()}")
    print(f"  Get logging config: {loader.get_logging_config()}")
    print(f"  Get review config: {loader.get_review_config()}")
    
    print("\n3. Test environment variable overrides:")
    # Set environment variables
    os.environ["RULE_ENGINE_MAX_WORKERS"] = "8"
    os.environ["RULE_ENGINE_CACHE_ENABLED"] = "false"
    os.environ["REVIEW_MIN_SCORE"] = "85"
    
    try:
        loader2 = ConfigLoader()
        env_config = loader2.load(None)
        
        env_engine_config = env_config["rule_engine"]
        print(f"  After environment variable overrides:")
        print(f"    Max workers: {env_engine_config['max_workers']}")
        print(f"    Cache enabled: {env_engine_config['cache_enabled']}")
        print(f"    Review min score: {env_config['integration']['review']['min_score_threshold']}")
    finally:
        # Clean up environment variables
        del os.environ["RULE_ENGINE_MAX_WORKERS"]
        del os.environ["RULE_ENGINE_CACHE_ENABLED"]
        del os.environ["REVIEW_MIN_SCORE"]


def demo_enhanced_review_runner():
    """Demo enhanced review runner"""
    print("\n" + "=" * 60)
    print("Demo: Enhanced Review Runner")
    print("=" * 60)
    
    # Create runner with config
    config = {
        "cache": {
            "enabled": True,
            "max_size": 100,
            "ttl": 60
        },
        "parallel": {
            "enabled": True,
            "max_workers": 2,
            "execution_timeout": 10
        },
        "rules": {
            "enabled_categories": ["lifecycle", "performance"],
            "disabled_rules": []
        }
    }
    
    runner = EnhancedReviewRunner(config)
    
    print("1. Initialize runner:")
    runner.initialize()
    
    engine_info = runner.get_engine_info()
    print(f"  Initialized: {engine_info['initialized']}")
    print(f"  Rule count: {engine_info['rule_count']}")
    
    stats = engine_info["statistics"]
    print(f"  Rule statistics:")
    print(f"    Total rules: {stats['total_rules']}")
    print(f"    Enabled rules: {stats['enabled_rules']}")
    
    print("\n2. Review code:")
    test_code = """
class DemoViewModel : ViewModel() {
    fun processData() {
        // Using GlobalScope (issue)
        GlobalScope.launch {
            // IO operation on main thread (issue)
            readFileOnMainThread()
        }
    }
    
    private fun readFileOnMainThread() {
        // Simulate IO operation
        Thread.sleep(100)
    }
}
"""
    
    print("Test code:")
    print(test_code)
    
    result = runner.review_code(test_code, "DemoViewModel.kt", "kotlin")
    
    print(f"\nReview result:")
    print(f"  File: {result['file']}")
    print(f"  Score: {result['score']}/100")
    print(f"  Findings count: {len(result['findings'])}")
    
    if result['findings']:
        print("\n  Findings:")
        for i, finding in enumerate(result['findings'], 1):
            print(f"    {i}. [{finding['severity'].upper()}] {finding['rule']}")
            print(f"        Message: {finding['message']}")
            if finding.get('suggestion'):
                print(f"        Suggestion: {finding['suggestion']}")
            if finding.get('line_number'):
                print(f"        Line number: {finding['line_number']}")
    
    print("\n3. Execution statistics:")
    stats = result['stats']
    print(f"  Total rules: {stats['total_rules']}")
    print(f"  Execution time: {stats['execution_time']:.4f}s")
    print(f"  Cache hits: {stats.get('cache_hits', 0)}")
    print(f"  Cache misses: {stats.get('cache_misses', 0)}")
    
    print("\n4. Engine statistics:")
    engine_stats = runner.get_engine_info()
    print(f"  Cache statistics: {engine_stats['cache_stats']}")


def performance_comparison():
    """Performance comparison demo"""
    print("\n" + "=" * 60)
    print("Demo: Performance Comparison")
    print("=" * 60)
    
    # Create registry
    registry = RuleRegistry()
    registry.clear()
    registry.register(NoGlobalScopeRule())
    
    # Create large test code
    code_lines = []
    for i in range(20):
        code_lines.append(f"fun testFunction{i}() {{")
        code_lines.append(f"    GlobalScope.launch {{")
        code_lines.append(f"        println(\"Test {i}\")")
        code_lines.append(f"    }}")
        code_lines.append(f"}}")
    
    large_test_code = "\n".join(code_lines)
    
    context = RuleContext(
        code=large_test_code,
        file_path="LargeDemo.kt",
        language="kotlin"
    )
    
    print(f"Test code size: {len(large_test_code)} characters")
    lines = large_test_code.split('\n')
    print(f"Lines of code: {len(lines)}")
    
    # Test sequential execution (no cache)
    print("\n1. Sequential execution (no cache):")
    config_sequential = {
        "cache": {"enabled": False},
        "parallel": {"enabled": False}
    }
    engine_sequential = RuleEngine(registry, config_sequential)
    
    start_time = time.time()
    findings_seq, stats_seq = engine_sequential.execute_all(context)
    time_seq = time.time() - start_time
    
    print(f"  Execution time: {time_seq:.4f}s")
    print(f"  Findings count: {len(findings_seq)}")
    
    # Test parallel execution (no cache)
    print("\n2. Parallel execution (no cache):")
    config_parallel = {
        "cache": {"enabled": False},
        "parallel": {"enabled": True, "max_workers": 4}
    }
    engine_parallel = RuleEngine(registry, config_parallel)
    
    start_time = time.time()
    findings_par, stats_par = engine_parallel.execute_all(context)
    time_par = time.time() - start_time
    
    print(f"  Execution time: {time_par:.4f}s")
    print(f"  Findings count: {len(findings_par)}")
    print(f"  Performance improvement: {(time_seq - time_par)/time_seq*100:.1f}%")
    
    # Test parallel execution (with cache)
    print("\n3. Parallel execution (with cache):")
    config_cached = {
        "cache": {"enabled": True, "max_size": 100, "ttl": 60},
        "parallel": {"enabled": True, "max_workers": 4}
    }
    engine_cached = RuleEngine(registry, config_cached)
    
    # First execution (populate cache)
    start_time = time.time()
    findings_cached1, stats_cached1 = engine_cached.execute_all(context)
    time_cached1 = time.time() - start_time
    
    # Second execution (hit cache)
    start_time = time.time()
    findings_cached2, stats_cached2 = engine_cached.execute_all(context)
    time_cached2 = time.time() - start_time
    
    print(f"  First execution time: {time_cached1:.4f}s")
    print(f"  Second execution time: {time_cached2:.4f}s")
    print(f"  Cache performance improvement: {(time_cached1 - time_cached2)/time_cached1*100:.1f}%")
    
    print(f"\nSummary:")
    print(f"  Sequential: {time_seq:.4f}s")
    print(f"  Parallel: {time_par:.4f}s (improved {((time_seq - time_par)/time_seq*100):.1f}%)")
    print(f"  Cached: {time_cached2:.4f}s (improved {((time_seq - time_cached2)/time_seq*100):.1f}%)")


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("Unified Rule Engine Phase 3: Advanced Features and Optimization")
    print("=" * 60)
    print("Features include:")
    print("1. Parallel processing optimization (auto-detect CPU cores, priority queue)")
    print("2. LRU/TTL cache mechanism (multi-level cache support)")
    print("3. Complete configuration support (YAML/JSON, environment variable override)")
    print("=" * 60 + "\n")
    
    try:
        demo_lru_cache()
        demo_enhanced_engine()
        demo_config_loader()
        demo_enhanced_review_runner()
        performance_comparison()
        
        print("\n" + "=" * 60)
        print("Demo completed!")
        print("=" * 60)
        print("\nKey Features Summary:")
        print("✅ Parallel Processing: Auto-detect CPU cores, support priority queue")
        print("✅ LRU Cache: Support TTL expiration, max entry limit")
        print("✅ Config Management: Support YAML/JSON, environment variable override, config validation")
        print("✅ Hot Reload: Auto reload when config file changes")
        print("✅ Statistics Monitoring: Cache hit rate, execution time, rule statistics")
        print("✅ Backward Compatible: Support old rule adapters")
        
    except Exception as e:
        print(f"\n⚠️ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
