"""
配置转换器 - 将旧版配置转换为新版统一配置格式
"""
import json
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def convert_old_to_unified_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    将旧版配置转换为新版统一配置
    
    旧版配置结构:
    {
        "rule_engine": {
            "use_new_engine": true,
            "new_engine_config": {
                "enabled_categories": [...],
                "disabled_rules": [],
                "parallel_execution": true,
                "cache_enabled": true,
                "max_workers": 4
            }
        },
        ...其他配置
    }
    
    新版统一配置结构:
    {
        "rule_engine": {
            "enabled": true,
            "parallel_execution": true,
            "max_workers": null,  # 自动检测
            "cache_enabled": true,
            "cache_max_size": 1000,
            "cache_ttl": 3600,
            "execution_timeout": 30,
            "rules": {
                "enabled_categories": [...],
                "disabled_rules": [],
                "enabled_rules": [],
                "rule_weights": {}
            }
        },
        "integration": {
            "review": {
                "min_score_threshold": 70,
                "block_on_critical": true,
                "generate_html_report": true
            }
        }
    }
    """
    unified_config = {
        "rule_engine": {
            "enabled": True,
            "parallel_execution": True,
            "max_workers": None,  # 自动检测
            "cache_enabled": True,
            "cache_max_size": 1000,
            "cache_ttl": 3600,
            "execution_timeout": 30,
            "rules": {
                "enabled_categories": [],
                "disabled_rules": [],
                "enabled_rules": [],
                "rule_weights": {}
            }
        },
        "integration": {
            "review": {
                "min_score_threshold": 70,
                "block_on_critical": True,
                "generate_html_report": True
            }
        }
    }
    
    # 如果旧配置有rule_engine配置
    if "rule_engine" in old_config:
        old_engine_config = old_config["rule_engine"]
        
        # 转换新引擎配置
        if "new_engine_config" in old_engine_config:
            new_engine_config = old_engine_config["new_engine_config"]
            
            # 并行执行配置
            if "parallel_execution" in new_engine_config:
                unified_config["rule_engine"]["parallel_execution"] = new_engine_config["parallel_execution"]
            
            # 最大工作线程数
            if "max_workers" in new_engine_config:
                unified_config["rule_engine"]["max_workers"] = new_engine_config["max_workers"]
            
            # 缓存配置
            if "cache_enabled" in new_engine_config:
                unified_config["rule_engine"]["cache_enabled"] = new_engine_config["cache_enabled"]
            
            # 规则配置
            if "enabled_categories" in new_engine_config:
                unified_config["rule_engine"]["rules"]["enabled_categories"] = new_engine_config["enabled_categories"]
            
            if "disabled_rules" in new_engine_config:
                unified_config["rule_engine"]["rules"]["disabled_rules"] = new_engine_config["disabled_rules"]
    
    # 保留其他配置（如文件扩展名、扫描目录等）
    # 这些配置在ReviewConfig类中处理，不需要转换
    for key, value in old_config.items():
        if key != "rule_engine":
            unified_config[key] = value
    
    return unified_config


def migrate_config_file(old_config_path: str, new_config_path: str = None) -> str:
    """
    迁移配置文件
    
    Args:
        old_config_path: 旧配置文件路径
        new_config_path: 新配置文件路径（默认为原路径，添加_unified后缀）
    
    Returns:
        新配置文件路径
    """
    if not os.path.exists(old_config_path):
        raise FileNotFoundError(f"配置文件不存在: {old_config_path}")
    
    # 读取旧配置
    with open(old_config_path, 'r', encoding='utf-8') as f:
        old_config = json.load(f)
    
    # 转换为新配置
    unified_config = convert_old_to_unified_config(old_config)
    
    # 确定新文件路径
    if new_config_path is None:
        base, ext = os.path.splitext(old_config_path)
        new_config_path = f"{base}_unified{ext}"
    
    # 写入新配置
    with open(new_config_path, 'w', encoding='utf-8') as f:
        json.dump(unified_config, f, indent=2, ensure_ascii=False)
    
    logger.info(f"配置文件已迁移: {old_config_path} -> {new_config_path}")
    return new_config_path


def get_unified_runner_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    从配置字典获取统一运行器配置
    
    Args:
        config_dict: 配置字典（可以是旧版或新版）
    
    Returns:
        统一运行器配置
    """
    # 检查是否为旧版配置
    if "rule_engine" in config_dict:
        rule_engine_config = config_dict["rule_engine"]
        
        # 如果是旧版配置且有new_engine_config，转换为新版
        if "new_engine_config" in rule_engine_config:
            unified_config = convert_old_to_unified_config(config_dict)
            rule_engine_config = unified_config["rule_engine"]
    else:
        # 如果没有rule_engine配置，使用默认配置
        rule_engine_config = convert_old_to_unified_config({})["rule_engine"]
    
    # 构建运行器配置
    runner_config = {
        "cache": {
            "enabled": rule_engine_config.get("cache_enabled", True),
            "max_size": rule_engine_config.get("cache_max_size", 1000),
            "ttl": rule_engine_config.get("cache_ttl", 3600)
        },
        "parallel": {
            "enabled": rule_engine_config.get("parallel_execution", True),
            "max_workers": rule_engine_config.get("max_workers"),
            "execution_timeout": rule_engine_config.get("execution_timeout", 30)
        },
        "rules": rule_engine_config.get("rules", {})
    }
    
    return runner_config


if __name__ == "__main__":
    # 测试配置转换
    import sys
    logging.basicConfig(level=logging.INFO)
    
    # 测试数据
    test_old_config = {
        "file_extensions": [".kt", ".kts"],
        "scan_directories": ["app/src/main/java", "app/src/test/java"],
        "exclude_patterns": ["*/build/*", "*/.gradle/*"],
        "enable_semantic_review": True,
        "generate_html_report": True,
        "min_score_threshold": 70,
        "rule_engine": {
            "use_new_engine": True,
            "new_engine_config": {
                "enabled_categories": ["security", "performance", "correctness"],
                "disabled_rules": [],
                "parallel_execution": True,
                "cache_enabled": True,
                "max_workers": 4
            }
        }
    }
    
    print("旧版配置:")
    print(json.dumps(test_old_config, indent=2, ensure_ascii=False))
    print("\n" + "="*60 + "\n")
    
    unified_config = convert_old_to_unified_config(test_old_config)
    print("转换后的统一配置:")
    print(json.dumps(unified_config, indent=2, ensure_ascii=False))
    print("\n" + "="*60 + "\n")
    
    runner_config = get_unified_runner_config(test_old_config)
    print("运行器配置:")
    print(json.dumps(runner_config, indent=2, ensure_ascii=False))