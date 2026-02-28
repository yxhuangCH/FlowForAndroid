"""
配置加载器 - 支持YAML/JSON配置，配置验证和默认值处理
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
    """配置加载器，支持多种配置格式和环境变量覆盖"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "rule_engine": {
            "enabled": True,
            "parallel_execution": True,
            "max_workers": None,  # None表示自动检测CPU核心数
            "cache_enabled": True,
            "cache_max_size": 1000,  # 最大缓存条目数
            "cache_ttl": 3600,  # 缓存生存时间（秒）
            "execution_timeout": 30,  # 规则执行超时（秒）
            "rules": {
                "enabled_categories": [],  # 空列表表示启用所有分类
                "disabled_rules": [],
                "enabled_rules": [],  # 空列表表示启用所有规则
                "rule_weights": {}  # 规则权重覆盖
            },
            "logging": {
                "level": "INFO",
                "file": None,  # None表示只输出到控制台
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
        加载配置文件
        
        Args:
            config_path: 配置文件路径，如果为None则尝试自动查找
            
        Returns:
            配置字典
        """
        # 尝试自动查找配置文件
        if config_path is None:
            config_path = self._find_config_file()
        
        if config_path and os.path.exists(config_path):
            self.config_file = config_path
            self.config_file_mtime = os.path.getmtime(config_path)
            
            # 根据文件扩展名选择加载器
            ext = Path(config_path).suffix.lower()
            if ext in ['.yaml', '.yml']:
                user_config = self._load_yaml(config_path)
            elif ext == '.json':
                user_config = self._load_json(config_path)
            else:
                # 默认尝试JSON
                try:
                    user_config = self._load_json(config_path)
                except json.JSONDecodeError:
                    # 尝试YAML
                    user_config = self._load_yaml(config_path)
            
            # 深度合并配置
            self._deep_merge(self.config, user_config)
            
            logger.info(f"已加载配置文件: {config_path}")
        
        # 应用环境变量覆盖
        self._apply_env_overrides()
        
        # 验证配置
        self._validate_config()
        
        # 处理默认值
        self._apply_defaults()
        
        return self.config
    
    def _find_config_file(self) -> Optional[str]:
        """自动查找配置文件"""
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
        """加载YAML配置文件"""
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            logger.warning("PyYAML未安装，无法加载YAML配置")
            return {}
        except Exception as e:
            logger.error(f"加载YAML配置文件失败 {config_path}: {e}")
            return {}
    
    def _load_json(self, config_path: str) -> Dict[str, Any]:
        """加载JSON配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON配置文件解析失败 {config_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载JSON配置文件失败 {config_path}: {e}")
            return {}
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        # 规则引擎配置
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
                # 解析配置路径
                if len(config_path) == 3:
                    section, key, type_func = config_path
                    self._set_config_value([section, key], env_value, type_func)
                elif len(config_path) == 4:
                    section, subsection, key, type_func = config_path
                    self._set_config_value([section, subsection, key], env_value, type_func)
    
    def _set_config_value(self, path: List[str], value: str, type_func):
        """设置配置值"""
        config = self.config
        for i, key in enumerate(path[:-1]):
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 转换类型
        try:
            if type_func == bool:
                converted_value = value.lower() in ['true', '1', 'yes', 'on']
            else:
                converted_value = type_func(value)
            
            config[path[-1]] = converted_value
            logger.debug(f"环境变量覆盖配置: {'.'.join(path)} = {converted_value}")
        except (ValueError, TypeError) as e:
            logger.warning(f"环境变量转换失败 {'.'.join(path)}={value}: {e}")
    
    def _validate_config(self):
        """验证配置"""
        # 验证规则引擎配置
        engine_config = self.config.get("rule_engine", {})
        
        # 验证max_workers
        max_workers = engine_config.get("max_workers")
        if max_workers is not None and max_workers <= 0:
            logger.warning(f"无效的max_workers配置: {max_workers}，使用默认值")
            engine_config["max_workers"] = None
        
        # 验证缓存配置
        cache_max_size = engine_config.get("cache_max_size", 1000)
        if cache_max_size < 0:
            logger.warning(f"无效的cache_max_size配置: {cache_max_size}，使用默认值")
            engine_config["cache_max_size"] = 1000
        
        cache_ttl = engine_config.get("cache_ttl", 3600)
        if cache_ttl < 0:
            logger.warning(f"无效的cache_ttl配置: {cache_ttl}，使用默认值")
            engine_config["cache_ttl"] = 3600
        
        # 验证执行超时
        timeout = engine_config.get("execution_timeout", 30)
        if timeout <= 0:
            logger.warning(f"无效的execution_timeout配置: {timeout}，使用默认值")
            engine_config["execution_timeout"] = 30
        
        # 验证集成配置
        integration_config = self.config.get("integration", {})
        review_config = integration_config.get("review", {})
        
        min_score = review_config.get("min_score_threshold", 70)
        if min_score < 0 or min_score > 100:
            logger.warning(f"无效的min_score_threshold配置: {min_score}，使用默认值")
            review_config["min_score_threshold"] = 70
    
    def _apply_defaults(self):
        """应用默认值"""
        # 确保所有必需的字段都存在
        if "rule_engine" not in self.config:
            self.config["rule_engine"] = {}
        
        if "integration" not in self.config:
            self.config["integration"] = {}
        
        # 确保子配置存在
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
        检查并热重载配置（如果配置文件已修改）
        
        Returns:
            是否重新加载了配置
        """
        if self.config_file and os.path.exists(self.config_file):
            current_mtime = os.path.getmtime(self.config_file)
            if current_mtime != self.config_file_mtime:
                logger.info(f"配置文件已修改，重新加载: {self.config_file}")
                old_config = self.config.copy()
                self.config = self.DEFAULT_CONFIG.copy()
                self.load(self.config_file)
                
                # 检查配置是否实际改变
                if old_config != self.config:
                    logger.info("配置已更新")
                    return True
        
        return False
    
    def get_engine_config(self) -> Dict[str, Any]:
        """获取规则引擎配置"""
        return self.config.get("rule_engine", {})
    
    def get_integration_config(self) -> Dict[str, Any]:
        """获取集成配置"""
        return self.config.get("integration", {})
    
    def get_rule_config(self) -> Dict[str, Any]:
        """获取规则配置"""
        engine_config = self.config.get("rule_engine", {})
        return engine_config.get("rules", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        engine_config = self.config.get("rule_engine", {})
        return engine_config.get("logging", {})
    
    def get_review_config(self) -> Dict[str, Any]:
        """获取审查配置"""
        integration_config = self.config.get("integration", {})
        return integration_config.get("review", {})
    
    def get_diff_parser_config(self) -> Dict[str, Any]:
        """获取diff解析器配置"""
        integration_config = self.config.get("integration", {})
        return integration_config.get("diff_parser", {})


# 全局配置加载器实例
_config_loader_instance: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """获取全局配置加载器实例"""
    global _config_loader_instance
    if _config_loader_instance is None:
        _config_loader_instance = ConfigLoader()
        _config_loader_instance.load()
    
    return _config_loader_instance


def get_config() -> Dict[str, Any]:
    """获取当前配置"""
    return get_config_loader().config


if __name__ == "__main__":
    # 测试配置加载器
    import sys
    logging.basicConfig(level=logging.INFO)
    
    loader = ConfigLoader()
    config = loader.load()
    
    print("配置加载测试:")
    print(json.dumps(config, indent=2, ensure_ascii=False))