#!/usr/bin/env python3
"""
快速规则迁移脚本 - 直接迁移关键规则模块到新引擎格式
"""
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any

# 添加路径以便导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from rule_engine.interfaces import RuleSeverity, RuleCategory, Rule, RuleMetadata, Finding
from rule_engine.context import RuleContext
from rule_engine.adapters.decorators import rule


def migrate_coroutine_rules():
    """迁移协程相关规则"""
    print("迁移协程规则...")
    
    # 主线程IO规则
    @rule(
        rule_id="main_thread_io",
        name="主线程IO操作",
        description="在主线程执行IO操作可能导致ANR（应用无响应）",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.PERFORMANCE,
        tags=["android", "kotlin", "coroutine", "io", "anr"],
        suggested_fix="将IO操作移到Dispatchers.IO或后台线程"
    )
    def main_thread_io_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        # 简化检测：如果包含Dispatchers.Main并且有IO相关操作
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
                message="检测到在主线程执行IO操作的风险",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                suggestion="将IO操作移到Dispatchers.IO或后台线程"
            ))
        
        return findings
    
    # 未指定作用域规则
    @rule(
        rule_id="unspecified_scope",
        name="未指定协程作用域",
        description="协程启动未指定生命周期作用域",
        severity=RuleSeverity.MINOR,
        category=RuleCategory.LIFECYCLE,
        tags=["android", "kotlin", "coroutine", "lifecycle"],
        suggested_fix="明确指定协程作用域，如viewModelScope或lifecycleScope"
    )
    def unspecified_scope_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "launch {" in line and "viewModelScope" not in line and "lifecycleScope" not in line:
                findings.append(Finding(
                    rule_id="unspecified_scope",
                    message="协程启动未指定生命周期作用域",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="明确指定协程作用域，如viewModelScope或lifecycleScope"
                ))
        
        return findings
    
    return [main_thread_io_rule, unspecified_scope_rule]


def migrate_compose_rules():
    """迁移Compose相关规则"""
    print("迁移Compose规则...")
    
    # LaunchedEffect(Unit)规则
    @rule(
        rule_id="launched_effect_unit",
        name="LaunchedEffect(Unit)问题",
        description="LaunchedEffect(Unit)可能导致不必要的重新组合",
        severity=RuleSeverity.MINOR,
        category=RuleCategory.CORRECTNESS,
        tags=["android", "compose", "kotlin"],
        suggested_fix="使用合适的key参数替代Unit，避免不必要的重新组合"
    )
    def launched_effect_unit_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "LaunchedEffect(Unit)" in line:
                findings.append(Finding(
                    rule_id="launched_effect_unit",
                    message="LaunchedEffect(Unit)可能导致不必要的重新组合",
                    severity=RuleSeverity.MINOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="使用合适的key参数替代Unit，避免不必要的重新组合"
                ))
        
        return findings
    
    # remember持有Context规则
    @rule(
        rule_id="remember_context",
        name="remember持有Context",
        description="remember中持有Context可能导致内存泄漏",
        severity=RuleSeverity.MAJOR,
        category=RuleCategory.LIFECYCLE,
        tags=["android", "compose", "kotlin", "context"],
        suggested_fix="避免在remember中持有Context，考虑使用ViewModel或其他方式"
    )
    def remember_context_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        lines = context.get_lines()
        for i, line in enumerate(lines, 1):
            if "remember {" in line and "context" in line.lower():
                findings.append(Finding(
                    rule_id="remember_context",
                    message="remember中持有Context可能导致内存泄漏",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="避免在remember中持有Context，考虑使用ViewModel或其他方式"
                ))
        
        return findings
    
    return [launched_effect_unit_rule, remember_context_rule]


def migrate_flow_rules():
    """迁移Flow相关规则"""
    print("迁移Flow规则...")
    
    # flowOn主线程规则
    @rule(
        rule_id="flowon_main_dispatcher",
        name="flowOn主线程问题",
        description="flowOn(Dispatchers.Main)可能在上游执行主线程操作",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.CONCURRENCY,
        tags=["kotlin", "coroutine", "flow"],
        suggested_fix="使用Dispatchers.Default或Dispatchers.IO处理上游操作"
    )
    def flowon_main_dispatcher_rule(context: RuleContext) -> List[Finding]:
        findings = []
        
        code = context.code
        pattern = r"flow\s*\{[\s\S]*?\}\.flowOn\s*\(\s*Dispatchers\.Main"
        if re.search(pattern, code):
            findings.append(Finding(
                rule_id="flowon_main_dispatcher",
                message="flowOn(Dispatchers.Main)可能在上游执行主线程操作",
                severity=RuleSeverity.CRITICAL,
                file_path=context.file_path,
                suggestion="使用Dispatchers.Default或Dispatchers.IO处理上游操作"
            ))
        
        return findings
    
    # MutableStateFlow暴露规则
    @rule(
        rule_id="mutable_stateflow_exposed",
        name="MutableStateFlow暴露",
        description="MutableStateFlow不应公开暴露",
        severity=RuleSeverity.MAJOR,
        category=RuleCategory.CORRECTNESS,
        tags=["kotlin", "flow", "stateflow"],
        suggested_fix="将MutableStateFlow设为私有，通过StateFlow公开只读版本"
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
                    message="MutableStateFlow不应公开暴露",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    suggestion="将MutableStateFlow设为私有，通过StateFlow公开只读版本"
                ))
        
        return findings
    
    return [flowon_main_dispatcher_rule, mutable_stateflow_exposed_rule]


def migrate_hilt_rules():
    """迁移Hilt相关规则"""
    print("迁移Hilt规则...")
    
    @rule(
        rule_id="singleton_activity",
        name="Singleton Activity注入",
        description="@Singleton不应注入Activity",
        severity=RuleSeverity.MAJOR,
        category=RuleCategory.CORRECTNESS,
        tags=["android", "hilt", "dagger", "dependency-injection"],
        suggested_fix="使用@ActivityScoped替代@Singleton注入Activity"
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
                    message="@Singleton不应注入Activity",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line,
                    suggestion="使用@ActivityScoped替代@Singleton注入Activity"
                ))
                in_singleton_block = False
        
        return findings
    
    return [singleton_activity_rule]


def generate_rule_module(module_name: str, rules: List[Any], output_dir: Path = None) -> str:
    """
    生成规则模块文件
    
    Args:
        module_name: 模块名
        rules: 规则列表
        output_dir: 输出目录
        
    Returns:
        生成的文件路径
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "rules" / "migrated"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{module_name}.py"
    
    # 生成模块头部
    template = '''"""
{module_name} - 迁移规则模块
从旧规则系统迁移到新规则引擎
"""
from typing import List
from rule_engine.interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from rule_engine.context import RuleContext
from rule_engine.adapters.decorators import rule

'''
    
    content = template.format(module_name=module_name.replace("_", " ").title())
    
    # 收集规则代码
    for rule_func in rules:
        # 获取源代码
        import inspect
        source = inspect.getsource(rule_func)
        content += source + "\n\n"
    
    # 添加__all__导出
    rule_names = [rule_func.__name__ for rule_func in rules]
    content += f"__all__ = {rule_names!r}\n"
    
    # 写入文件
    output_file.write_text(content, encoding='utf-8')
    print(f"生成规则模块: {output_file}")
    
    return str(output_file)


def main():
    """主函数"""
    print("=== 快速规则迁移 ===")
    print()
    
    # 迁移各模块规则
    all_rules = []
    
    # 协程规则
    coroutine_rules = migrate_coroutine_rules()
    all_rules.extend(coroutine_rules)
    
    # Compose规则
    compose_rules = migrate_compose_rules()
    all_rules.extend(compose_rules)
    
    # Flow规则
    flow_rules = migrate_flow_rules()
    all_rules.extend(flow_rules)
    
    # Hilt规则
    hilt_rules = migrate_hilt_rules()
    all_rules.extend(hilt_rules)
    
    print(f"总计迁移 {len(all_rules)} 个规则")
    print()
    
    # 生成模块文件
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
    print("=== 迁移完成 ===")
    print()
    print("生成的文件:")
    for file_path in generated_files:
        print(f"  - {file_path}")
    print()
    print("下一步操作:")
    print("1. 导入新规则到review_runner.py")
    print("2. 更新规则注册逻辑")
    print("3. 测试迁移后的系统")


if __name__ == "__main__":
    main()