"""
Internationalization (i18n) Support Module
Supports bilingual switching between Chinese and English
"""
import gettext
import os
import locale as system_locale

# Default language
DEFAULT_LANGUAGE = 'zh_CN'

# Supported languages list
SUPPORTED_LANGUAGES = ['zh_CN', 'en_US']

def get_language_from_env():
    """Get language settings from environment variable"""
    lang = os.environ.get('REVIEW_LANGUAGE', '')
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return None

def get_language_from_config(config=None):
    """Get language settings from configuration"""
    if config and 'language' in config:
        lang = config['language']
        if lang in SUPPORTED_LANGUAGES:
            return lang
    return None

def get_system_language():
    """Get system language"""
    try:
        system_lang = system_locale.getdefaultlocale()[0]
        if system_lang and 'zh' in system_lang.lower():
            return 'zh_CN'
    except:
        pass
    return 'en_US'

def get_language(config=None):
    """
    Determine which language to use (priority: environment variable > config > system default > default Chinese)
    """
    # 1. Check environment variable
    lang = get_language_from_env()
    if lang:
        return lang
    
    # 2. Check configuration
    lang = get_language_from_config(config)
    if lang:
        return lang
    
    # 3. Use system language (if Chinese)
    system_lang = get_system_language()
    if system_lang == 'zh_CN':
        return 'zh_CN'
    
    # 4. Default Chinese
    return DEFAULT_LANGUAGE

def setup_i18n(language=None, config=None):
    """
    Set up internationalization
    
    Args:
        language: Language code (zh_CN/en_US), None for auto-detection
        config: Configuration dictionary for reading language settings
        
    Returns:
        gettext translation function
    """
    if language is None:
        language = get_language(config)
    
    # Ensure language is in supported list
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    # Get locale directory path
    locale_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locale')
    
    try:
        # Load translation
        translation = gettext.translation(
            'messages',
            locale_dir,
            languages=[language],
            fallback=True
        )
        return translation.gettext
    except Exception:
        # If loading fails, return original string
        return lambda x: x

# Global translation function (lazy initialization)
_ = None

def init_i18n(language=None, config=None):
    """
    Initialize internationalization, set global _ function
    
    Usage example:
        from i18n import init_i18n, _
        init_i18n()  # or init_i18n('en_US')
        print(_("Hello World"))
    """
    global _
    _ = setup_i18n(language, config)
    return _

# Default initialization (Chinese)
_ = setup_i18n(DEFAULT_LANGUAGE)
