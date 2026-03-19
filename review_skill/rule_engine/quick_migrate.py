#!/usr/bin/env python3
"""
Rule Migration - Rule
"""
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any

# Add
sys.path.insert(0, str(Path(__file__).parent.parent))

from rule_engine.interfaces import RuleSeverity, RuleCategory, Rule, RuleMetadata, Finding
from rule_engine.context import RuleContext
from rule_engine.adapters.decorators import rule


def migrate_coroutine_rules():
    """MigrationRule"""
    print("Rule...")
    
    # IORule
    @rule(
        rule_id="main_thread_io",
        name="IO",
        description="IOANR（）",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.PERFORMANCE,
        tags=["android", "kotlin", "coroutine", "io", "anr"],
        suggested_fix="IODispatchers.IO"
    )
    def main_thread_io_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        # Simplified detection：Dispatchers.MainIO
        has_main_dispatcher = any(
            "Dispatchers.Main" in line or "Dispatchers.Main" in line.upper()
            for line in context.get_lines()
        )
        
        has_io_operation = any(
            keyword in line.lower()
            for line in context.get_lines()
            for keyword in ["read", "write", "file", "network", "database", "sharedpreferences"]
        )
        
        if has_main_dispatcher and has_io_operation:
            findings.append(Finding(
                rule_id="main_thread_io",
                message="IO",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                suggestion="IODispatchers.IO"
            ))
        
        return findings
    
    # Rule
    @rule(
        rule_id="unspecified_scope",
        name="",
        description="",
        severity=RuleSeverity.MINOR,
        category=RuleCategory.LIFECYCLE,
        tags=["android", "kotlin", "coroutine", "lifecycle"],
        suggested_fix="，viewModelScopelifecycleScope"
    )
    def unspecified_scope_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "launch {" in line and "viewModelScope" not in line and "lifecycleScope" not in line:
                findings.append(Finding(
                    rule_id="unspecified_scope",
                    message="",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="，viewModelScopelifecycleScope"
                ))
        
        return findings
    
    return [main_thread_io_rule, unspecified_scope_rule]


def migrate_compose_rules():
    """MigrationComposeRule"""
    print("ComposeRule...")
    
    # LaunchedEffect(Unit)Rule
    @rule(
        rule_id="launched_effect_unit",
        name="LaunchedEffect(Unit)",
        description="LaunchedEffect(Unit)",
        severity=RuleSeverity.MINOR,
        category=RuleCategory.CORRECTNESS,
        tags=["android", "compose", "kotlin"],
        suggested_fix="keyUnit，"
    )
    def launched_effect_unit_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "LaunchedEffect(Unit)" in line:
                findings.append(Finding(
                    rule_id="launched_effect_unit",
                    message="LaunchedEffect(Unit)",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="keyUnit，"
                ))
        
        return findings
    
    # rememberContextRule
    @rule(
        rule_id="remember_context",
        name="rememberContext",
        description="rememberContext",
        severity=RuleSeverity.MAJOR,
        category=RuleCategory.LIFECYCLE,
        tags=["android", "compose", "kotlin", "context"],
        suggested_fix="rememberContext，ViewModel"
    )
    def remember_context_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "remember {" in line and "context" in line.lower():
                findings.append(Finding(
                    rule_id="remember_context",
                    message="rememberContext",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="rememberContext，ViewModel"
                ))
        
        return findings
    
    return [launched_effect_unit_rule, remember_context_rule]


def migrate_flow_rules():
    """MigrationFlowRule"""
    print("FlowRule...")
    
    # flowOnRule
    @rule(
        rule_id="flowon_main_dispatcher",
        name="flowOn",
        description="flowOn(Dispatchers.Main)",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.CONCURRENCY,
        tags=["kotlin", "coroutine", "flow"],
        suggested_fix="Dispatchers.DefaultDispatchers.IOProcess"
    )
    def flowon_main_dispatcher_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        code = context.code
        pattern = r"flow\s*\{[\s\S]*?\}\.flowOn\s*\(\s*Dispatchers\.Main"
        if re.search(pattern, code):
            findings.append(Finding(
                rule_id="flowon_main_dispatcher",
                message="flowOn(Dispatchers.Main)",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                suggestion="Dispatchers.DefaultDispatchers.IOProcess"
            ))
        
        return findings
    
    # MutableStateFlowRule
    @rule(
        rule_id="mutable_stateflow_exposed",
        name="MutableStateFlow",
        description="MutableStateFlow",
        severity=RuleSeverity.MAJOR,
        category=RuleCategory.CORRECTNESS,
        tags=["kotlin", "flow", "stateflow"],
        suggested_fix="MutableStateFlow，StateFlow"
    )
    def mutable_stateflow_exposed_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        code = context.code
        pattern = r"val\s+\w+\s*=\s*MutableStateFlow"
        matches = re.findall(pattern, code)
        
        for match in matches:
            if "private" not in match:
                findings.append(Finding(
                    rule_id="mutable_stateflow_exposed",
                    message="MutableStateFlow",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    suggestion="MutableStateFlow，StateFlow"
                ))
        
        return findings
    
    return [flowon_main_dispatcher_rule, mutable_stateflow_exposed_rule]


def migrate_hilt_rules():
    """MigrationHiltRule"""
    print("HiltRule...")
    
    @rule(
        rule_id="singleton_activity",
        name="Singleton Activity",
        description="@SingletonActivity",
        severity=RuleSeverity.MAJOR,
        category=RuleCategory.CORRECTNESS,
        tags=["android", "hilt", "dagger", "dependency-injection"],
        suggested_fix="@ActivityScoped@SingletonActivity"
    )
    def singleton_activity_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        lines = context.get_lines()
        in_singleton_block = False
        
        for i, line in enumerate(lines, 1):
            if "@Singleton" in line:
                in_singleton_block = True
            
            if in_singleton_block and "Activity" in line:
                findings.append(Finding(
                    rule_id="singleton_activity",
                    message="@SingletonActivity",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="@ActivityScoped@SingletonActivity"
                ))
                in_singleton_block = False
        
        return findings
    
    return [singleton_activity_rule]


def generate_rule_module(module_name: str, rules: List[Any], output_dir: Path = None) -> str:
    """
    GenerateRule
    
    Args:
        module_name: 
        rules: Rule
        output_dir: 
        
    Returns:
        Generate
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "rules" / "migrated"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{module_name}.py"
    
    # Generate
    template = '''"""
{module_name} - Rule
RuleRule Engine
"""
from typing import List
from rule_engine.interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from rule_engine.context import RuleContext
from rule_engine.adapters.decorators import rule

'''
    
    content = template.format(module_name=module_name.replace("_", " ").title())
    
    # Rule
    for rule_func in rules:
        # Get
        import inspect
        source = inspect.getsource(rule_func)
        content += source + "\n\n"
    
    # Add__all__
    rule_names = [rule_func.__name__ for rule_func in rules]
    content += f"__all__ = {rule_names!r}\n"
    
    # 
    output_file.write_text(content, encoding='utf-8')
    print(f"GenerateRule: {output_file}")
    
    return str(output_file)


def main():
    """Main function"""
    print("=== Rule Migration ===")
    print()
    
    # Rule
    all_rules = []
    
    # Rule
    coroutine_rules = migrate_coroutine_rules()
    all_rules.extend(coroutine_rules)
    
    # ComposeRule
    compose_rules = migrate_compose_rules()
    all_rules.extend(compose_rules)
    
    # FlowRule
    flow_rules = migrate_flow_rules()
    all_rules.extend(flow_rules)
    
    # HiltRule
    hilt_rules = migrate_hilt_rules()
    all_rules.extend(hilt_rules)
    
    print(f" {len(all_rules)} Rule")
    print()
    
    # Generate
    modules = {
        "coroutine_rules": coroutine_rules,
        "compose_rules": compose_rules,
        "flow_rules": flow_rules,
        "hilt_rules": hilt_rules,
    }
    
    generated_files = []
    for module_name, rules in modules.items():
        if rules:
            file_path = generate_rule_module(module_name, rules)
            generated_files.append(file_path)
    
    print()
    print("===  ===")
    print()
    print("Generate:")
    for file_path in generated_files:
        print(f"  - {file_path}")
    print()
    print(":")
    print("1. Rulereview_runner.py")
    print("2. UpdateRuleRegister")
    print("3. Test")


if __name__ == "__main__":
    main()