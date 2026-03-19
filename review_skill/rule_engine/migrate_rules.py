#!/usr/bin/env python3
"""
Rule Migration - Rule Migration
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

# Add
sys.path.insert(0, str(Path(__file__).parent.parent))

from rule_engine.interfaces import RuleSeverity, RuleCategory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_old_rules() -> Dict[str, Dict[str, Any]]:
    """
    Rule，Rule
    
    Returns:
        Rule {: {Rule}}
    """
    # Calculate
    try:
        rules_dir = Path(__file__).parent.parent / "rules"
    except NameError:
        # __file__，
        rules_dir = Path.cwd() / "rules"
    
    if not rules_dir.exists():
        # 
        rules_dir = Path.cwd() / "rules"
        if not rules_dir.exists():
            logger.error(f"Rule，: {rules_dir}")
            logger.error(f": {Path.cwd()}")
            return {}
    
    rule_info = {}
    
    for py_file in rules_dir.glob("*.py"):
        module_name = py_file.stem
        full_module_name = f"rules.{module_name}"
        
        try:
            # importlib
            import importlib
            module = importlib.import_module(full_module_name)
            
            # run_
            functions = inspect.getmembers(module, inspect.isfunction)
            run_functions = [(name, func) for name, func in functions if name.startswith('run_')]
            
            if not run_functions:
                continue
            
            # 
            content = py_file.read_text(encoding='utf-8')
            
            # Rule
            rule_info[module_name] = {
                "module": module,
                "module_path": str(py_file),
                "functions": run_functions,
                "content": content,
                "rules": extract_rules_from_code(content, module_name)
            }
            
            logger.info(f" {module_name}:  {len(run_functions)} Rule")
            
        except ImportError as e:
            logger.error(f" {full_module_name} : {e}")
        except Exception as e:
            logger.error(f" {module_name} : {e}")
    
    return rule_info


def extract_rules_from_code(content: str, module_name: str) -> List[Dict[str, Any]]:
    """
    Rule
    
    Args:
        content: code content
        module_name: 
        
    Returns:
        Rule
    """
    rules = []
    
    # findings.append
    pattern = r'findings\.append\(\s*{([^}]+)}\s*\)'
    
    for match in re.finditer(pattern, content, re.DOTALL):
        finding_text = match.group(1)
        
        # Rule
        rule_match = re.search(r'"rule"\s*:\s*"([^"]+)"', finding_text)
        severity_match = re.search(r'"severity"\s*:\s*"([^"]+)"', finding_text)
        message_match = re.search(r'"message"\s*:\s*"([^"]+)"', finding_text)
        
        if rule_match and severity_match and message_match:
            rule_id = rule_match.group(1)
            severity = severity_match.group(1)
            message = message_match.group(1)
            
            # RuleID
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
    Rule Metadata
    
    Args:
        rule_id: RuleID
        severity: 
        message: 
        module_name: 
        
    Returns:
        
    """
    # 
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
    
    # RuleID
    name_map = {
        "no_globalscope": "GlobalScope",
        "viewmodel_context": "ViewModelContext",
        "main_thread_io": "IO",
        "unspecified_scope": "",
        "launched_effect_unit": "LaunchedEffect(Unit)",
        "remember_context": "rememberContext",
        "flowon_main_dispatcher": "flowOn",
        # Add...
    }
    
    name = name_map.get(rule_id, rule_id.replace("_", " ").title())
    
    # 
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
    Generate
    
    Args:
        rule_id: RuleID
        
    Returns:
        
    """
    fixes = {
        "no_globalscope": "viewModelScope、lifecycleScopeCoroutineScopeGlobalScope",
        "viewmodel_context": "Application ContextAndroidViewModelGetContext",
        "main_thread_io": "IODispatchers.IO",
        "unspecified_scope": "，viewModelScopelifecycleScope",
        "launched_effect_unit": "keyUnit，",
        "remember_context": "rememberContext，ViewModel",
        "flowon_main_dispatcher": "Dispatchers.DefaultDispatchers.IOProcess",
    }
    
    return fixes.get(rule_id, "")


def create_legacy_adapters(rules_info: Dict[str, Dict[str, Any]]) -> List[Any]:
    """
    Rule（Disable，legacy_adapter Remove）

    Args:
        rules_info: Rule
        
    Returns:
        
    """
    logger.warning("legacy_adapter Remove，Disable")
    return []


def generate_migration_report(rules_info: Dict[str, Dict[str, Any]]) -> str:
    """
    Generate
    
    Args:
        rules_info: Rule
        
    Returns:
        
    """
    report_lines = []
    
    total_rules = 0
    for module_name, module_info in rules_info.items():
        rules = module_info["rules"]
        report_lines.append(f"## : {module_name}")
        report_lines.append(f": {module_info['module_path']}")
        report_lines.append(f"Rule: {len(rules)}")
        report_lines.append("")
        
        for rule in rules:
            total_rules += 1
            metadata = rule["metadata"]
            report_lines.append(f"### Rule: {rule['rule_id']}")
            report_lines.append(f"- : {rule['severity']}")
            report_lines.append(f"- : {rule['message']}")
            report_lines.append(f"- : {metadata['name']}")
            report_lines.append(f"- : {metadata['category'].value}")
            report_lines.append(f"- : {', '.join(metadata['tags'])}")
            report_lines.append(f"- : {metadata['suggested_fix']}")
            report_lines.append("")
    
    report_lines.insert(0, f"# Rule Migration")
    report_lines.insert(1, f"Rule: {total_rules}")
    report_lines.insert(2, "")
    
    return "\n".join(report_lines)


def migrate_rule_files(rules_info: Dict[str, Dict[str, Any]], output_dir: Path = None) -> Dict[str, str]:
    """
    Rule
    
    Args:
        rules_info: Rule
        output_dir: 
        
    Returns:
        Generate
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "rules" / "migrated"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generated_files = {}
    
    # 
    template_header = '''"""
Rule - Convert
"""
from typing import List
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule

'''
    
    for module_name, module_info in rules_info.items():
        output_file = output_dir / f"{module_name}_migrated.py"
        
        # GenerateRule
        code_lines = [template_header]
        
        for rule in module_info["rules"]:
            rule_id = rule["rule_id"]
            metadata = rule["metadata"]
            severity_str = rule["severity"]
            
            # GenerateRule
            if len(module_info["rules"]) == 1:
                # Rule，Generate
                class_code = generate_rule_class(rule_id, metadata, severity_str)
                code_lines.append(class_code)
            else:
                # Rule，Generate
                func_code = generate_rule_function(rule_id, metadata, severity_str)
                code_lines.append(func_code)
            
            code_lines.append("\n\n")
        
        # 
        output_file.write_text("".join(code_lines), encoding='utf-8')
        generated_files[module_name] = str(output_file)
        logger.info(f"GenerateRule: {output_file}")
    
    return generated_files


def generate_rule_class(rule_id: str, metadata: Dict[str, Any], severity_str: str) -> str:
    """
    GenerateRule
    
    Args:
        rule_id: RuleID
        metadata: 
        severity_str: 
        
    Returns:
        
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
        
        # TODO: Rule
        # Rule
        
        return findings'''
    
    return code


def generate_rule_function(rule_id: str, metadata: Dict[str, Any], severity_str: str) -> str:
    """
    GenerateRule
    
    Args:
        rule_id: RuleID
        metadata: 
        severity_str: 
        
    Returns:
        
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
    
    # TODO: Rule
    # Rule
    
    return findings'''
    
    return code


def main():
    """Main function"""
    print("=== Rule Migration ===")
    print()
    
    # Rule
    print("1. Rule...")
    rules_info = analyze_old_rules()
    
    if not rules_info:
        print("Rule")
        return
    
    print(f"， {len(rules_info)} ")
    print()
    
    # Generate
    print("2. Generate...")
    report = generate_migration_report(rules_info)
    
    report_file = Path(__file__).parent / "migration_report.md"
    report_file.write_text(report, encoding='utf-8')
    print(f"Save: {report_file}")
    print()
    
    # 
    print("3. ...")
    adapters = create_legacy_adapters(rules_info)
    print(f" {len(adapters)} ")
    print()
    
    # GenerateRule
    print("4. GenerateRule...")
    output_dir = Path(__file__).parent.parent / "rules" / "migrated"
    generated_files = migrate_rule_files(rules_info, output_dir)
    
    print(f"Generate {len(generated_files)} Rule: {output_dir}")
    print()
    
    # 
    print("===  ===")
    print()
    print(":")
    print("1. CheckGenerate")
    print("2. RuleTODO")
    print("3. Updatereview_runner.pyRuleRegister")
    print("4. Test")
    print()
    print(f": {report_file}")
    
    return adapters


if __name__ == "__main__":
    main()
