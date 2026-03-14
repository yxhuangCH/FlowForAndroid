"""
国际化 (i18n) 支持模块
支持中英文双语切换
"""
import gettext
import os
import locale as system_locale

# 默认语言
DEFAULT_LANGUAGE = 'zh_CN'

# 支持的语言列表
SUPPORTED_LANGUAGES = ['zh_CN', 'en_US']

def get_language_from_env():
    """从环境变量获取语言设置"""
    lang = os.environ.get('REVIEW_LANGUAGE', '')
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return None

def get_language_from_config(config=None):
    """从配置获取语言设置"""
    if config and 'language' in config:
        lang = config['language']
        if lang in SUPPORTED_LANGUAGES:
            return lang
    return None

def get_system_language():
    """获取系统语言"""
    try:
        system_lang = system_locale.getdefaultlocale()[0]
        if system_lang and 'zh' in system_lang.lower():
            return 'zh_CN'
    except:
        pass
    return 'en_US'

def get_language(config=None):
    """
    确定使用哪种语言（优先级：环境变量 > 配置 > 系统默认 > 默认中文）
    """
    # 1. 检查环境变量
    lang = get_language_from_env()
    if lang:
        return lang
    
    # 2. 检查配置
    lang = get_language_from_config(config)
    if lang:
        return lang
    
    # 3. 使用系统语言（如果是中文）
    system_lang = get_system_language()
    if system_lang == 'zh_CN':
        return 'zh_CN'
    
    # 4. 默认中文
    return DEFAULT_LANGUAGE

def setup_i18n(language=None, config=None):
    """
    设置国际化
    
    Args:
        language: 指定语言代码 (zh_CN/en_US)，None则自动检测
        config: 配置字典，用于从中读取语言设置
        
    Returns:
        gettext 翻译函数
    """
    if language is None:
        language = get_language(config)
    
    # 确保语言在支持列表中
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    # 获取 locale 目录路径
    locale_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locale')
    
    try:
        # 加载翻译
        translation = gettext.translation(
            'messages',
            locale_dir,
            languages=[language],
            fallback=True
        )
        return translation.gettext
    except Exception:
        # 如果加载失败，返回原字符串
        return lambda x: x

# 全局翻译函数（延迟初始化）
_ = None

def init_i18n(language=None, config=None):
    """
    初始化国际化，设置全局 _ 函数
    
    使用示例:
        from i18n import init_i18n, _
        init_i18n()  # 或 init_i18n('en_US')
        print(_("Hello World"))
    """
    global _
    _ = setup_i18n(language, config)
    return _

# 默认初始化（中文）
_ = setup_i18n(DEFAULT_LANGUAGE)
