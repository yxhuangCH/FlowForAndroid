"""
Configuration file management module
Supports configuration of detection scope, file filtering, and other settings
"""

import os
from pathlib import Path
from typing import List, Set, Optional
import re


class ReviewConfig:
    """Code review configuration class"""
    
    # Default configuration
    DEFAULT_CONFIG = {
        # File extensions to detect
        'file_extensions': ['.kt', '.kts'],  # Kotlin files
        # Directories to detect (relative to project root)
        'scan_directories': ['app/src/main/java', 'app/src/test/java'],
        # Directory patterns to exclude
        'exclude_patterns': ['*/build/*', '*/test/*', '*/debug/*'],
        # Whether to enable semantic analysis (LLM)
        'enable_semantic_review': True,
        # Whether to generate HTML report
        'generate_html_report': True,
        # Minimum score threshold (below this will block PR)
        'min_score_threshold': 70,
        # Language setting (zh_CN/en_US)
        'language': 'zh_CN',
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration
        
        Args:
            config_file: Configuration file path, if None use default configuration
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
        elif os.path.exists('.env'):
            # Try to load configuration from .env file
            self.load_from_env('.env')
    
    def load_config(self, config_file: str):
        """Load configuration from JSON file"""
        try:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                self.config.update(user_config)
        except Exception as e:
            print(f"⚠ Failed to load configuration file {config_file}: {e}")
    
    def load_from_env(self, env_file: str):
        """Load configuration from .env file"""
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            
            # Read configuration from environment variables
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
            
            # Language setting
            language = os.getenv('REVIEW_LANGUAGE')
            if language:
                self.config['language'] = language
            
            # LLM provider settings
            llm_provider = os.getenv('LLM_PROVIDER')
            if llm_provider:
                self.config['llm_provider'] = llm_provider
            
            # LLM model settings
            llm_model = os.getenv('LLM_MODEL')
            if llm_model:
                self.config['llm_model'] = llm_model
                    
        except Exception as e:
            print(f"⚠ Failed to load configuration from environment: {e}")

    def get_llm_provider(self) -> str:
        """Get LLM provider configuration"""
        return self.config.get('llm_provider', 'auto')

    def get_llm_model(self) -> str:
        """Get LLM model configuration"""
        # Get from environment variable or configuration, provide default value based on provider
        model = self.config.get('llm_model')
        if model:
            return model
        
        # Return default model based on provider
        provider = self.get_llm_provider()
        if provider == 'github_copilot':
            return 'gpt-4o-copilot'
        elif provider == 'deepseek':
            return 'deepseek-chat'
        elif provider == 'openai':
            return 'gpt-4o-mini'
        return None

    def get_llm_config(self) -> dict:
        """Get complete LLM configuration"""
        return {
            'provider': self.get_llm_provider(),
            'model': self.get_llm_model(),
        }
    
    def get_file_extensions(self) -> List[str]:
        """Get list of file extensions to detect"""
        return self.config['file_extensions']
    
    def get_scan_directories(self) -> List[str]:
        """Get list of directories to detect"""
        return self.config['scan_directories']
    
    def get_exclude_patterns(self) -> List[str]:
        """Get list of exclusion patterns"""
        return self.config['exclude_patterns']
    
    def should_scan_file(self, file_path: str) -> bool:
        """Determine whether to scan specified file
        
        Args:
            file_path: File path (relative)
            
        Returns:
            Whether the file should be scanned
        """
        # Check file extension
        ext = Path(file_path).suffix.lower()
        if ext not in self.get_file_extensions():
            return False
        
        # Check if in scan directories
        in_scan_dir = False
        for scan_dir in self.get_scan_directories():
            if file_path.startswith(scan_dir):
                in_scan_dir = True
                break
        
        if not in_scan_dir:
            return False
        
        # Check if matches exclusion patterns
        for pattern in self.get_exclude_patterns():
            # Convert glob pattern to regex pattern
            regex_pattern = re.escape(pattern).replace(r'\*', '.*').replace(r'\?', '.')
            if re.match(regex_pattern, file_path):
                return False
        
        return True
    
    def filter_git_diff(self, diff_text: str) -> str:
        """Filter git diff, only keep files that need to be scanned
        
        Args:
            diff_text: Raw git diff output
            
        Returns:
            Filtered git diff containing only files to be scanned
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
            
            # Detect new file start
            if line.startswith('diff --git'):
                # Extract file name
                match = re.search(r'^diff --git a/(.+) b/(.+)$', line)
                if match:
                    old_file = match.group(1)
                    new_file = match.group(2)
                    
                    # Check if this file should be scanned
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
                    # Keep as is
                    filtered_lines.append(line)
                    current_file = None
                    in_file_diff = True
                i += 1
            
            # If not in scan files, skip all lines of this file
            elif not in_file_diff:
                i += 1
                # Skip until next diff --git
                while i < len(lines) and not lines[i].startswith('diff --git'):
                    i += 1
            
            # In scan files, keep all lines
            else:
                filtered_lines.append(line)
                i += 1
        
        return '\n'.join(filtered_lines)
    
    def is_enabled_semantic_review(self) -> bool:
        """Whether semantic analysis is enabled"""
        return self.config['enable_semantic_review']
    
    def should_generate_html_report(self) -> bool:
        """Whether to generate HTML report"""
        return self.config['generate_html_report']
    
    def get_min_score_threshold(self) -> int:
        """Get minimum score threshold"""
        return self.config['min_score_threshold']
    
    def get_language(self) -> str:
        """Get language setting"""
        return self.config.get('language', 'zh_CN')
    
    def get(self, key, default=None):
        """Dictionary-style get method for backward compatibility"""
        # Support nested paths, e.g., "rule_engine.use_new_engine"
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


# Global configuration instance
_config_instance: Optional[ReviewConfig] = None


def get_config() -> ReviewConfig:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        # Find configuration file
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