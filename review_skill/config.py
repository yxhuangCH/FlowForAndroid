"""
配置文件管理模块
支持配置检测范围、文件过滤等设置
"""

import os
from pathlib import Path
from typing import List, Set, Optional
import re


class ReviewConfig:
    """代码审查配置类"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        # 要检测的文件扩展名
        'file_extensions': ['.kt', '.kts'],  # Kotlin 文件
        # 要检测的目录（相对于项目根目录）
        'scan_directories': ['app/src/main/java', 'app/src/test/java'],
        # 要排除的目录模式
        'exclude_patterns': ['*/build/*', '*/test/*', '*/debug/*'],
        # 是否启用语义分析（LLM）
        'enable_semantic_review': True,
        # 是否生成HTML报告
        'generate_html_report': True,
        # 最小分数阈值（低于此分数会阻塞PR）
        'min_score_threshold': 70,
        # 语言设置 (zh_CN/en_US)
        'language': 'zh_CN',
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """初始化配置
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认配置
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
        elif os.path.exists('.env'):
            # 尝试从.env文件加载配置
            self.load_from_env('.env')
    
    def load_config(self, config_file: str):
        """从JSON配置文件加载配置"""
        try:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                self.config.update(user_config)
        except Exception as e:
            print(f"⚠ 加载配置文件失败 {config_file}: {e}")
    
    def load_from_env(self, env_file: str):
        """从.env文件加载配置"""
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            
            # 从环境变量读取配置
            extensions = os.getenv('REVIEW_FILE_EXTENSIONS')
            if extensions:
                self.config['file_extensions'] = [ext.strip() for ext in extensions.split(',')]
            
            scan_dirs = os.getenv('REVIEW_SCAN_DIRECTORIES')
            if scan_dirs:
                self.config['scan_directories'] = [dir.strip() for dir in scan_dirs.split(',')]
            
            exclude_patterns = os.getenv('REVIEW_EXCLUDE_PATTERNS')
            if exclude_patterns:
                self.config['exclude_patterns'] = [pattern.strip() for pattern in exclude_patterns.split(',')]
            
            enable_semantic = os.getenv('REVIEW_ENABLE_SEMANTIC')
            if enable_semantic:
                self.config['enable_semantic_review'] = enable_semantic.lower() == 'true'
            
            generate_html = os.getenv('REVIEW_GENERATE_HTML')
            if generate_html:
                self.config['generate_html_report'] = generate_html.lower() == 'true'
            
            min_score = os.getenv('REVIEW_MIN_SCORE_THRESHOLD')
            if min_score:
                try:
                    self.config['min_score_threshold'] = int(min_score)
                except ValueError:
                    pass
            
            # 语言设置
            language = os.getenv('REVIEW_LANGUAGE')
            if language:
                self.config['language'] = language
            
            # LLM 提供商设置
            llm_provider = os.getenv('LLM_PROVIDER')
            if llm_provider:
                self.config['llm_provider'] = llm_provider
            
            # LLM 模型设置
            llm_model = os.getenv('LLM_MODEL')
            if llm_model:
                self.config['llm_model'] = llm_model
                    
        except Exception as e:
            from i18n import _
            print(_("⚠ Failed to load configuration from environment: {error}").format(error=e))

    def get_llm_provider(self) -> str:
        """获取LLM提供商配置"""
        return self.config.get('llm_provider', 'auto')

    def get_llm_model(self) -> str:
        """获取LLM模型配置"""
        # 从环境变量或配置中获取，根据提供商提供默认值
        model = self.config.get('llm_model')
        if model:
            return model
        
        # 根据提供商返回默认模型
        provider = self.get_llm_provider()
        if provider == 'github_copilot':
            return 'gpt-4o-copilot'
        elif provider == 'deepseek':
            return 'deepseek-chat'
        elif provider == 'openai':
            return 'gpt-4o-mini'
        return None

    def get_llm_config(self) -> dict:
        """获取LLM完整配置"""
        return {
            'provider': self.get_llm_provider(),
            'model': self.get_llm_model(),
        }
    
    def get_file_extensions(self) -> List[str]:
        """获取要检测的文件扩展名列表"""
        return self.config['file_extensions']
    
    def get_scan_directories(self) -> List[str]:
        """获取要检测的目录列表"""
        return self.config['scan_directories']
    
    def get_exclude_patterns(self) -> List[str]:
        """获取排除模式列表"""
        return self.config['exclude_patterns']
    
    def should_scan_file(self, file_path: str) -> bool:
        """判断是否应该扫描指定文件
        
        Args:
            file_path: 文件路径（相对路径）
            
        Returns:
            是否应该扫描该文件
        """
        # 检查文件扩展名
        ext = Path(file_path).suffix.lower()
        if ext not in self.get_file_extensions():
            return False
        
        # 检查是否在扫描目录中
        in_scan_dir = False
        for scan_dir in self.get_scan_directories():
            if file_path.startswith(scan_dir):
                in_scan_dir = True
                break
        
        if not in_scan_dir:
            return False
        
        # 检查是否匹配排除模式
        for pattern in self.get_exclude_patterns():
            # 将 glob 模式转换为正则表达式
            regex_pattern = re.escape(pattern).replace(r'\*', '.*').replace(r'\?', '.')
            if re.match(regex_pattern, file_path):
                return False
        
        return True
    
    def filter_git_diff(self, diff_text: str) -> str:
        """过滤git diff，只保留需要扫描的文件
        
        Args:
            diff_text: 原始的git diff输出
            
        Returns:
            过滤后的git diff，只包含需要扫描的文件
        """
        if not diff_text.strip():
            return diff_text
        
        lines = diff_text.split('\n')
        filtered_lines = []
        i = 0
        current_file = None
        in_file_diff = False
        
        while i < len(lines):
            line = lines[i]
            
            # 检测新文件开始
            if line.startswith('diff --git'):
                # 提取文件名
                match = re.search(r'^diff --git a/(.+) b/(.+)$', line)
                if match:
                    old_file = match.group(1)
                    new_file = match.group(2)
                    
                    # 检查是否应该扫描此文件
                    should_scan = (self.should_scan_file(old_file) or 
                                 self.should_scan_file(new_file))
                    
                    if should_scan:
                        current_file = new_file
                        in_file_diff = True
                        filtered_lines.append(line)
                    else:
                        current_file = None
                        in_file_diff = False
                else:
                    # 保持原样
                    filtered_lines.append(line)
                    current_file = None
                    in_file_diff = True
                i += 1
            
            # 如果不在扫描文件中，跳过该文件的所有行
            elif not in_file_diff:
                i += 1
                # 跳过直到下一个 diff --git
                while i < len(lines) and not lines[i].startswith('diff --git'):
                    i += 1
            
            # 在扫描文件中，保留所有行
            else:
                filtered_lines.append(line)
                i += 1
        
        return '\n'.join(filtered_lines)
    
    def is_enabled_semantic_review(self) -> bool:
        """是否启用语义分析"""
        return self.config['enable_semantic_review']
    
    def should_generate_html_report(self) -> bool:
        """是否生成HTML报告"""
        return self.config['generate_html_report']
    
    def get_min_score_threshold(self) -> int:
        """获取最小分数阈值"""
        return self.config['min_score_threshold']
    
    def get_language(self) -> str:
        """获取语言设置"""
        return self.config.get('language', 'zh_CN')
    
    def get(self, key, default=None):
        """字典风格的get方法，用于兼容旧代码"""
        # 支持嵌套路径，如 "rule_engine.use_new_engine"
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


# 全局配置实例
_config_instance: Optional[ReviewConfig] = None


def get_config() -> ReviewConfig:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        # 查找配置文件
        config_file = None
        possible_configs = [
            'review_config.json',
            '.review_config.json',
            os.path.join(os.path.dirname(__file__), 'review_config.json'),
        ]
        
        for cfg in possible_configs:
            if os.path.exists(cfg):
                config_file = cfg
                break
        
        _config_instance = ReviewConfig(config_file)
    
    return _config_instance