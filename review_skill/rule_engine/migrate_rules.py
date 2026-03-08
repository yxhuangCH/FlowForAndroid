#!/usr/bin/env python3
"""
规则迁移脚本 - 自动将旧规则迁移到新引擎格式
"""
import os
import sys
import inspect
import json
import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging

# 添加路径以便导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from rule_engine.interfaces import RuleSeverity, RuleCategory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_old_rules() -> Dict[str, Dict[str, Any]]:
    """
    分析旧规则模块，提取规则信息
    
    Returns:
        规则信息字典 {模块名: {规则信息}}
    """
    # 尝试基于脚本位置计算路径
    try:
        rules_dir = Path(__file__).parent.parent / "rules"
    except NameError:
        # 如果__file__不存在，使用当前工作目录
        rules_dir = Path.cwd() / "rules"
    
    if not rules_dir.exists():
        # 尝试相对路径
        rules_dir = Path.cwd() / "rules"
        if not rules_dir.exists():
            logger.error(f"旧规则目录不存在，尝试的路径: {rules_dir}")
            logger.error(f"当前工作目录: {Path.cwd()}")
            return {}
    
    rule_info = {}
    
    for py_file in rules_dir.glob("*.py"):
        module_name = py_file.stem
        full_module_name = f"rules.{module_name}"
        
        try:
            # 使用importlib动态导入模块
            import importlib
            module = importlib.import_module(full_module_name)
            
            # 查找所有以run_开头的函数
            functions = inspect.getmembers(module, inspect.isfunction)
            run_functions = [(name, func) for name, func in functions if name.startswith('run_')]
            
            if not run_functions:
                continue
            
            # 读取文件内容分析
            content = py_file.read_text(encoding='utf-8')
            
            # 提取规则相关信息
            rule_info[module_name] = {
                "module": module,
                "module_path": str(py_file),
                "functions": run_functions,
                "content": content,
                "rules": extract_rules_from_code(content, module_name)
            }
            
            logger.info(f"分析模块 {module_name}: 找到 {len(run_functions)} 个规则函数")
            
        except ImportError as e:
            logger.error(f"导入模块 {full_module_name} 失败: {e}")
        except Exception as e:
            logger.error(f"分析模块 {module_name} 失败: {e}")
    
    return rule_info


def extract_rules_from_code(content: str, module_name: str) -> List[Dict[str, Any]]:
    """
    从代码中提取规则信息
    
    Args:
        content: 代码内容
        module_name: 模块名
        
    Returns:
        规则信息列表
    """
    rules = []
    
    # 查找所有findings.append语句
    pattern = r'findings\.append\(\s*{([^}]+)}\s*\)'
    
    for match in re.finditer(pattern, content, re.DOTALL):
        finding_text = match.group(1)
        
        # 提取规则信息
        rule_match = re.search(r'"rule"\s*:\s*"([^"]+)"', finding_text)
        severity_match = re.search(r'"severity"\s*:\s*"([^"]+)"', finding_text)
        message_match = re.search(r'"message"\s*:\s*"([^"]+)"', finding_text)
        
        if rule_match and severity_match and message_match:
            rule_id = rule_match.group(1)
            severity = severity_match.group(1)
            message = message_match.group(1)
            
            # 根据规则ID推断元数据
            metadata = infer_rule_metadata(rule_id, severity, message, module_name)
            
            rules.append({
                "rule_id": rule_id,
                "severity": severity,
                "message": message,
                "metadata": metadata
            })
    
    return rules


def infer_rule_metadata(rule_id: str, severity: str, message: str, module_name: str) -> Dict[str, Any]:
    """
    推断规则元数据
    
    Args:
        rule_id: 规则ID
        severity: 严重级别
        message: 消息
        module_name: 模块名
        
    Returns:
        元数据字典
    """
    # 根据模块名推断分类
    category_map = {
        "base_rules": RuleCategory.CORRECTNESS,
        "coroutine_rules": RuleCategory.CONCURRENCY,
        "compose_rules": RuleCategory.CORRECTNESS,
        "flow_rules": RuleCategory.CONCURRENCY,
        "flow_lifecycle_rules": RuleCategory.LIFECYCLE,
        "flow_structure_rules": RuleCategory.CORRECTNESS,
        "hilt_rules": RuleCategory.CORRECTNESS,
        "dagger2_rules": RuleCategory.CORRECTNESS,
    }
    
    category = category_map.get(module_name, RuleCategory.CORRECTNESS)
    
    # 根据规则ID推断名称和标签
    name_map = {
        "no_globalscope": "禁止使用GlobalScope",
        "viewmodel_context": "ViewModel不应持有Context",
        "main_thread_io": "主线程IO操作",
        "unspecified_scope": "未指定协程作用域",
        "launched_effect_unit": "LaunchedEffect(Unit)问题",
        "remember_context": "remember持有Context",
        "flowon_main_dispatcher": "flowOn主线程问题",
        # 添加更多映射...
    }
    
    name = name_map.get(rule_id, rule_id.replace("_", " ").title())
    
    # 推断标签
    tags = [module_name.replace("_rules", "")]
    
    if "coroutine" in rule_id or "scope" in rule_id:
        tags.extend(["coroutine", "android"])
    if "viewmodel" in rule_id:
        tags.extend(["android", "kotlin", "viewmodel"])
    if "compose" in rule_id:
        tags.extend(["android", "compose"])
    if "flow" in rule_id:
        tags.extend(["kotlin", "coroutine", "flow"])
    
    return {
        "name": name,
        "description": message,
        "category": category,
        "tags": tags,
        "suggested_fix": generate_suggested_fix(rule_id)
    }


def generate_suggested_fix(rule_id: str) -> str:
    """
    生成建议修复
    
    Args:
        rule_id: 规则ID
        
    Returns:
        建议修复文本
    """
    fixes = {
        "no_globalscope": "使用viewModelScope、lifecycleScope或自定义CoroutineScope替代GlobalScope",
        "viewmodel_context": "使用Application Context或通过AndroidViewModel获取Context",
        "main_thread_io": "将IO操作移到Dispatchers.IO或后台线程",
        "unspecified_scope": "明确指定协程作用域，如viewModelScope或lifecycleScope",
        "launched_effect_unit": "使用合适的key参数替代Unit，避免不必要的重新组合",
        "remember_context": "避免在remember中持有Context，考虑使用ViewModel或其他方式",
        "flowon_main_dispatcher": "使用Dispatchers.Default或Dispatchers.IO处理上游操作",
    }
    
    return fixes.get(rule_id, "请根据具体情况修复代码问题")


def create_legacy_adapters(rules_info: Dict[str, Dict[str, Any]]) -> List[Any]:
    """
    为旧规则创建适配器（已禁用，legacy_adapter 已移除）

    Args:
        rules_info: 规则信息
        
    Returns:
        空列表
    """
    logger.warning("legacy_adapter 已移除，适配器功能已禁用")
    return []


def generate_migration_report(rules_info: Dict[str, Dict[str, Any]]) -> str:
    """
    生成迁移报告
    
    Args:
        rules_info: 规则信息
        
    Returns:
        报告文本
    """
    report_lines = []
    
    total_rules = 0
    for module_name, module_info in rules_info.items():
        rules = module_info["rules"]
        report_lines.append(f"## 模块: {module_name}")
        report_lines.append(f"文件: {module_info['module_path']}")
        report_lines.append(f"规则数量: {len(rules)}")
        report_lines.append("")
        
        for rule in rules:
            total_rules += 1
            metadata = rule["metadata"]
            report_lines.append(f"### 规则: {rule['rule_id']}")
            report_lines.append(f"- 严重级别: {rule['severity']}")
            report_lines.append(f"- 消息: {rule['message']}")
            report_lines.append(f"- 名称: {metadata['name']}")
            report_lines.append(f"- 分类: {metadata['category'].value}")
            report_lines.append(f"- 标签: {', '.join(metadata['tags'])}")
            report_lines.append(f"- 建议修复: {metadata['suggested_fix']}")
            report_lines.append("")
    
    report_lines.insert(0, f"# 规则迁移报告")
    report_lines.insert(1, f"总计规则数量: {total_rules}")
    report_lines.insert(2, "")
    
    return "\n".join(report_lines)


def migrate_rule_files(rules_info: Dict[str, Dict[str, Any]], output_dir: Path = None) -> Dict[str, str]:
    """
    迁移规则文件到新格式
    
    Args:
        rules_info: 规则信息
        output_dir: 输出目录
        
    Returns:
        生成的文件路径字典
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "rules" / "migrated"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generated_files = {}
    
    # 模板文件头部
    template_header = '''"""
迁移规则 - 从旧格式转换为新格式
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule

'''
    
    for module_name, module_info in rules_info.items():
        output_file = output_dir / f"{module_name}_migrated.py"
        
        # 生成新规则代码
        code_lines = [template_header]
        
        for rule in module_info["rules"]:
            rule_id = rule["rule_id"]
            metadata = rule["metadata"]
            severity_str = rule["severity"]
            
            # 生成规则类或装饰器
            if len(module_info["rules"]) == 1:
                # 单个规则，生成类
                class_code = generate_rule_class(rule_id, metadata, severity_str)
                code_lines.append(class_code)
            else:
                # 多个规则，生成装饰器函数
                func_code = generate_rule_function(rule_id, metadata, severity_str)
                code_lines.append(func_code)
            
            code_lines.append("\n\n")
        
        # 写入文件
        output_file.write_text("".join(code_lines), encoding='utf-8')
        generated_files[module_name] = str(output_file)
        logger.info(f"生成新规则文件: {output_file}")
    
    return generated_files


def generate_rule_class(rule_id: str, metadata: Dict[str, Any], severity_str: str) -> str:
    """
    生成规则类代码
    
    Args:
        rule_id: 规则ID
        metadata: 元数据
        severity_str: 严重级别字符串
        
    Returns:
        类代码
    """
    try:
        severity = RuleSeverity(severity_str)
    except ValueError:
        severity = RuleSeverity.MINOR
    
    class_name = f"{rule_id.title().replace('_', '')}Rule"
    
    code = f'''class {class_name}(Rule):
    """{metadata['name']}"""
    
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="{rule_id}",
            name="{metadata['name']}",
            description="{metadata['description']}",
            severity=RuleSeverity.{severity.name},
            category=RuleCategory.{metadata['category'].name},
            tags={metadata['tags']},
            suggested_fix="{metadata['suggested_fix']}",
            weight=1.0
        )
    
    def check(self, context: RuleContext) -> List[Finding]:
        findings = []
        
        # TODO: 实现规则检测逻辑
        # 基于旧规则逻辑实现
        
        return findings'''
    
    return code


def generate_rule_function(rule_id: str, metadata: Dict[str, Any], severity_str: str) -> str:
    """
    生成规则函数代码
    
    Args:
        rule_id: 规则ID
        metadata: 元数据
        severity_str: 严重级别字符串
        
    Returns:
        函数代码
    """
    try:
        severity = RuleSeverity(severity_str)
    except ValueError:
        severity = RuleSeverity.MINOR
    
    code = f'''@rule(
    rule_id="{rule_id}",
    name="{metadata['name']}",
    description="{metadata['description']}",
    severity=RuleSeverity.{severity.name},
    category=RuleCategory.{metadata['category'].name},
    tags={metadata['tags']},
    suggested_fix="{metadata['suggested_fix']}",
    weight=1.0
)
def {rule_id}_rule(context: RuleContext) -> List[Finding]:
    """{metadata['name']}"""
    findings = []
    
    # TODO: 实现规则检测逻辑
    # 基于旧规则逻辑实现
    
    return findings'''
    
    return code


def main():
    """主函数"""
    print("=== 规则迁移工具 ===")
    print()
    
    # 分析旧规则
    print("1. 分析旧规则模块...")
    rules_info = analyze_old_rules()
    
    if not rules_info:
        print("未找到旧规则模块")
        return
    
    print(f"分析完成，找到 {len(rules_info)} 个模块")
    print()
    
    # 生成报告
    print("2. 生成迁移报告...")
    report = generate_migration_report(rules_info)
    
    report_file = Path(__file__).parent / "migration_report.md"
    report_file.write_text(report, encoding='utf-8')
    print(f"报告已保存到: {report_file}")
    print()
    
    # 创建适配器
    print("3. 创建适配器...")
    adapters = create_legacy_adapters(rules_info)
    print(f"创建了 {len(adapters)} 个适配器")
    print()
    
    # 生成新规则文件
    print("4. 生成新规则文件...")
    output_dir = Path(__file__).parent.parent / "rules" / "migrated"
    generated_files = migrate_rule_files(rules_info, output_dir)
    
    print(f"生成 {len(generated_files)} 个新规则文件到: {output_dir}")
    print()
    
    # 提供下一步指导
    print("=== 迁移完成 ===")
    print()
    print("下一步操作:")
    print("1. 检查生成的适配器是否正确")
    print("2. 实现新规则文件中的TODO逻辑")
    print("3. 更新review_runner.py中的规则注册逻辑")
    print("4. 运行测试验证迁移效果")
    print()
    print(f"详细报告: {report_file}")
    
    return adapters


if __name__ == "__main__":
    main()
