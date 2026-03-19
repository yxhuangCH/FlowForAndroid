"""Config Loader - YAML/JSON，Process
"""
import os
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Config Loader，"""
    
    # 
    DEFAULT_CONFIG = {
        "rule_engine": {
            "enabled": True,
            "parallel_execution": True,
            "max_workers": None,  # NoneCPU
            "cache_enabled": True,
            "cache_max_size": 1000,  # 
            "cache_ttl": 3600,  # Cache（）
            "execution_timeout": 30,  # Rule（）
            "rules": {
                "enabled_categories": [],  # Enable
                "disabled_rules": [],
                "enabled_rules": [],  # EnableRule
                "rule_weights": {}  # Rule weight
            },
            "logging": {
                "level": "INFO",
                "file": None,  # None
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "integration": {
            "diff_parser": {
                "enabled": True,
                "max_file_size": 1024 * 1024,  # 1MB
                "skip_binary_files": True
            },
            "review": {
                "min_score_threshold": 70,
                "block_on_critical": True,
                "generate_html_report": True,
                "report_output_dir": "./reports"
            }
        }
    }
    
    def __init__(self):
        self.config = self.DEFAULT_CONFIG.copy()
        self.config_file = None
        self.config_file_mtime = None
    
    def load(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load
        
        Args:
            config_path: file path，None
            
        Returns:
            
        """
        # 
        if config_path is None:
            config_path = self._find_config_file()
        
        if config_path and os.path.exists(config_path):
            self.config_file = config_path
            self.config_file_mtime = os.path.getmtime(config_path)
            
            # Load
            ext = Path(config_path).suffix.lower()
            if ext in ['.yaml', '.yml']:
                user_config = self._load_yaml(config_path)
            elif ext == '.json':
                user_config = self._load_json(config_path)
            else:
                # JSON
                try:
                    user_config = self._load_json(config_path)
                except json.JSONDecodeError:
                    # YAML
                    user_config = self._load_yaml(config_path)
            
            # 
            self._deep_merge(self.config, user_config)
            
            logger.info(f"Load: {config_path}")
        
        # 
        self._apply_env_overrides()
        
        # Verify
        self._validate_config()
        
        # Process
        self._apply_defaults()
        
        return self.config
    
    def _find_config_file(self) -> Optional[str]:
        """"""
        search_paths = [
            "review_config.yaml",
            "review_config.yml",
            "review_config.json",
            ".review_config.yaml",
            ".review_config.yml",
            ".review_config.json",
            os.path.join(os.path.dirname(__file__), "../../review_config.yaml"),
            os.path.join(os.path.dirname(__file__), "../../review_config.yml"),
            os.path.join(os.path.dirname(__file__), "../../review_config.json"),
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _load_yaml(self, config_path: str) -> Dict[str, Any]:
        """LoadYAML"""
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            logger.warning("PyYAML，LoadYAML")
            return {}
        except Exception as e:
            logger.error(f"LoadYAML {config_path}: {e}")
            return {}
    
    def _load_json(self, config_path: str) -> Dict[str, Any]:
        """LoadJSON"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON {config_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"LoadJSON {config_path}: {e}")
            return {}
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]):
        """"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _apply_env_overrides(self):
        """"""
        # Rule engine
        env_mappings = {
            "RULE_ENGINE_ENABLED": ("rule_engine", "enabled", bool),
            "RULE_ENGINE_PARALLEL": ("rule_engine", "parallel_execution", bool),
            "RULE_ENGINE_MAX_WORKERS": ("rule_engine", "max_workers", int),
            "RULE_ENGINE_CACHE_ENABLED": ("rule_engine", "cache_enabled", bool),
            "RULE_ENGINE_CACHE_MAX_SIZE": ("rule_engine", "cache_max_size", int),
            "RULE_ENGINE_CACHE_TTL": ("rule_engine", "cache_ttl", int),
            "RULE_ENGINE_TIMEOUT": ("rule_engine", "execution_timeout", int),
            "REVIEW_MIN_SCORE": ("integration", "review", "min_score_threshold", int),
            "REVIEW_BLOCK_CRITICAL": ("integration", "review", "block_on_critical", bool),
            "REVIEW_GENERATE_HTML": ("integration", "review", "generate_html_report", bool),
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # 
                if len(config_path) == 3:
                    section, key, type_func = config_path
                    self._set_config_value([section, key], env_value, type_func)
                elif len(config_path) == 4:
                    section, subsection, key, type_func = config_path
                    self._set_config_value([section, subsection, key], env_value, type_func)
    
    def _set_config_value(self, path: List[str], value: str, type_func):
        """Set"""
        config = self.config
        for i, key in enumerate(path[:-1]):
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Convert
        try:
            if type_func == bool:
                converted_value = value.lower() in ['true', '1', 'yes', 'on']
            else:
                converted_value = type_func(value)
            
            config[path[-1]] = converted_value
            logger.debug(f": {'.'.join(path)} = {converted_value}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Convert {'.'.join(path)}={value}: {e}")
    
    def _validate_config(self):
        """"""
        # VerifyRule Engine
        engine_config = self.config.get("rule_engine", {})
        
        # Verifymax_workers
        max_workers = engine_config.get("max_workers")
        if max_workers is not None and max_workers <= 0:
            logger.warning(f"max_workers: {max_workers}，")
            engine_config["max_workers"] = None
        
        # Verify
        cache_max_size = engine_config.get("cache_max_size", 1000)
        if cache_max_size < 0:
            logger.warning(f"cache_max_size: {cache_max_size}，")
            engine_config["cache_max_size"] = 1000
        
        cache_ttl = engine_config.get("cache_ttl", 3600)
        if cache_ttl < 0:
            logger.warning(f"cache_ttl: {cache_ttl}，")
            engine_config["cache_ttl"] = 3600
        
        # Verify
        timeout = engine_config.get("execution_timeout", 30)
        if timeout <= 0:
            logger.warning(f"execution_timeout: {timeout}，")
            engine_config["execution_timeout"] = 30
        
        # Verify
        integration_config = self.config.get("integration", {})
        review_config = integration_config.get("review", {})
        
        min_score = review_config.get("min_score_threshold", 70)
        if min_score < 0 or min_score > 100:
            logger.warning(f"min_score_threshold: {min_score}，")
            review_config["min_score_threshold"] = 70
    
    def _apply_defaults(self):
        """"""
        # 
        if "rule_engine" not in self.config:
            self.config["rule_engine"] = {}
        
        if "integration" not in self.config:
            self.config["integration"] = {}
        
        # 
        engine_config = self.config["rule_engine"]
        if "rules" not in engine_config:
            engine_config["rules"] = {}
        if "logging" not in engine_config:
            engine_config["logging"] = {}
        
        integration_config = self.config["integration"]
        if "diff_parser" not in integration_config:
            integration_config["diff_parser"] = {}
        if "review" not in integration_config:
            integration_config["review"] = {}
    
    def hot_reload_if_needed(self) -> bool:
        """
        Check（）
        
        Returns:
            Load
        """
        if self.config_file and os.path.exists(self.config_file):
            current_mtime = os.path.getmtime(self.config_file)
            if current_mtime != self.config_file_mtime:
                logger.info(f"，Load: {self.config_file}")
                old_config = self.config.copy()
                self.config = self.DEFAULT_CONFIG.copy()
                self.load(self.config_file)
                
                # Check
                if old_config != self.config:
                    logger.info("Update")
                    return True
        
        return False
    
    def get_engine_config(self) -> Dict[str, Any]:
        """GetRule Engine"""
        return self.config.get("rule_engine", {})
    
    def get_integration_config(self) -> Dict[str, Any]:
        """Get"""
        return self.config.get("integration", {})
    
    def get_rule_config(self) -> Dict[str, Any]:
        """GetRule Configuration"""
        engine_config = self.config.get("rule_engine", {})
        return engine_config.get("rules", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get"""
        engine_config = self.config.get("rule_engine", {})
        return engine_config.get("logging", {})
    
    def get_review_config(self) -> Dict[str, Any]:
        """Get"""
        integration_config = self.config.get("integration", {})
        return integration_config.get("review", {})
    
    def get_diff_parser_config(self) -> Dict[str, Any]:
        """Getdiff"""
        integration_config = self.config.get("integration", {})
        return integration_config.get("diff_parser", {})


# Load
_config_loader_instance: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """GetLoad"""
    global _config_loader_instance
    if _config_loader_instance is None:
        _config_loader_instance = ConfigLoader()
        _config_loader_instance.load()
    
    return _config_loader_instance


def get_config() -> Dict[str, Any]:
    """Get"""
    return get_config_loader().config


if __name__ == "__main__":
    # TestLoad
    import sys
    logging.basicConfig(level=logging.INFO)
    
    loader = ConfigLoader()
    config = loader.load()
    
    print("LoadTest:")
    print(json.dumps(config, indent=2, ensure_ascii=False))