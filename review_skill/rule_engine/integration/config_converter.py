"""Config Converter - Convert
"""
import json
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def convert_old_to_unified_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert
    
    :
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
        ...
    }
    
    :
    {
        "rule_engine": {
            "enabled": true,
            "parallel_execution": true,
            "max_workers": null,  # 
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
            "max_workers": None,  # 
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
    
    # rule_engine
    if "rule_engine" in old_config:
        old_engine_config = old_config["rule_engine"]
        
        # Convert
        if "new_engine_config" in old_engine_config:
            new_engine_config = old_engine_config["new_engine_config"]
            
            # Parallel execution config
            if "parallel_execution" in new_engine_config:
                unified_config["rule_engine"]["parallel_execution"] = new_engine_config["parallel_execution"]
            
            # 
            if "max_workers" in new_engine_config:
                unified_config["rule_engine"]["max_workers"] = new_engine_config["max_workers"]
            
            # Cache config
            if "cache_enabled" in new_engine_config:
                unified_config["rule_engine"]["cache_enabled"] = new_engine_config["cache_enabled"]
            
            # Rule config
            if "enabled_categories" in new_engine_config:
                unified_config["rule_engine"]["rules"]["enabled_categories"] = new_engine_config["enabled_categories"]
            
            if "disabled_rules" in new_engine_config:
                unified_config["rule_engine"]["rules"]["disabled_rules"] = new_engine_config["disabled_rules"]
    
    # （、, etc.)
    # ReviewConfigProcess，Convert
    for key, value in old_config.items():
        if key != "rule_engine":
            unified_config[key] = value
    
    return unified_config


def migrate_config_file(old_config_path: str, new_config_path: str = None) -> str:
    """
    
    
    Args:
        old_config_path: file path
        new_config_path: (default，Add_unified）
    
    Returns:
        
    """
    if not os.path.exists(old_config_path):
        raise FileNotFoundError(f": {old_config_path}")
    
    # 
    with open(old_config_path, 'r', encoding='utf-8') as f:
        old_config = json.load(f)
    
    # Convert
    unified_config = convert_old_to_unified_config(old_config)
    
    # 
    if new_config_path is None:
        base, ext = os.path.splitext(old_config_path)
        new_config_path = f"{base}_unified{ext}"
    
    # 
    with open(new_config_path, 'w', encoding='utf-8') as f:
        json.dump(unified_config, f, indent=2, ensure_ascii=False)
    
    logger.info(f": {old_config_path} -> {new_config_path}")
    return new_config_path


def get_unified_runner_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get
    
    Args:
        config_dict: config dictionary（）
    
    Returns:
        
    """
    # Check
    if "rule_engine" in config_dict:
        rule_engine_config = config_dict["rule_engine"]
        
        # new_engine_config，Convert
        if "new_engine_config" in rule_engine_config:
            unified_config = convert_old_to_unified_config(config_dict)
            rule_engine_config = unified_config["rule_engine"]
    else:
        # rule_engine，
        rule_engine_config = convert_old_to_unified_config({})["rule_engine"]
    
    # 
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
    # TestConvert
    import sys
    logging.basicConfig(level=logging.INFO)
    
    # Test
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
    
    print(":")
    print(json.dumps(test_old_config, indent=2, ensure_ascii=False))
    print("\n" + "="*60 + "\n")
    
    unified_config = convert_old_to_unified_config(test_old_config)
    print("Convert:")
    print(json.dumps(unified_config, indent=2, ensure_ascii=False))
    print("\n" + "="*60 + "\n")
    
    runner_config = get_unified_runner_config(test_old_config)
    print(":")
    print(json.dumps(runner_config, indent=2, ensure_ascii=False))