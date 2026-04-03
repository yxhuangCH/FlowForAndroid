"""
Compose Rules - Jetpack Compose 相关规则

检测Compose使用中的常见问题。
"""

from typing import List
from ..nodes import ASTNode, NodeType
from .base_ast_rule import (
    ASTBasedRule, Finding, RuleSeverity, RuleCategory, register_rule
)


@register_rule
class ComposeRememberRule(ASTBasedRule):
    """检测Compose remember使用问题"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COMPOSE-001"
    
    @property
    def rule_name(self) -> str:
        return "Compose Remember Usage"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COMPOSE
    
    @property
    def description(self) -> str:
        return "remember should be used correctly with mutableState"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 获取源码用于字符串匹配
        source_code = ast.text
        
        # 查找所有函数声明
        functions = ast.find_all(NodeType.FUNCTION_DECLARATION)
        
        for func in functions:
            # 检查是否是Composable函数
            start_line = func.range.start.line
            end_line = func.range.end.line + 1
            
            lines = source_code.split('\n') if source_code else []
            check_lines = lines[max(0, start_line-2):end_line]
            check_source = '\n'.join(check_lines)
            
            is_composable = "@Composable" in check_source
            
            if is_composable:
                # 获取函数源码
                func_source = '\n'.join(lines[start_line:end_line])
                
                # 使用正则表达式检查：mutableStateOf是否在remember外部
                # 模式: { mutableStateOf(...) } 表示在remember内部
                import re
                
                # 检查是否有remember包裹mutableStateOf
                has_remember_wrap = bool(re.search(r'remember\s*\{[^}]*mutableStateOf', func_source))
                
                # 检查是否有独立的mutableStateOf（不在remember中）
                # 移除remember块后再检查
                func_without_remember = re.sub(r'remember\s*\{[^}]*\}', '', func_source)
                has_standalone_mutableState = 'mutableStateOf' in func_without_remember
                
                if has_standalone_mutableState and not has_remember_wrap:
                    findings.append(self.create_finding(
                        node=func,
                        file_path=file_path,
                        message="mutableStateOf缺少remember：直接使用会导致状态丢失",
                        suggestion="使用 'var state by remember { mutableStateOf(...) }' 包装"
                    ))
        
        return findings


@register_rule
class ComposeLaunchedEffectRule(ASTBasedRule):
    """检测LaunchedEffect使用问题"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COMPOSE-002"
    
    @property
    def rule_name(self) -> str:
        return "LaunchedEffect Key Usage"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COMPOSE
    
    @property
    def description(self) -> str:
        return "LaunchedEffect should have appropriate keys to control recomposition"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 查找所有调用表达式
        calls = ast.find_all(NodeType.CALL_EXPRESSION)
        
        for call in calls:
            text = call.text
            # 检查是否是LaunchedEffect
            if "LaunchedEffect" in text:
                # 检查是否使用了Unit作为key（可能不需要重新触发）
                if "LaunchedEffect(Unit)" in text:
                    # 查找父级Composable函数确认
                    parent_function = call.find_parent(NodeType.FUNCTION_DECLARATION)
                    if parent_function and "@Composable" in parent_function.text:
                        findings.append(self.create_finding(
                            node=call,
                            file_path=file_path,
                            message="LaunchedEffect(Unit)：确保这是预期的行为，只在首次组合时执行",
                            suggestion="如果需要响应状态变化，请使用具体的状态作为key，如 LaunchedEffect(state)"
                        ))
        
        return findings


@register_rule
class ComposeSideEffectRule(ASTBasedRule):
    """检测SideEffect使用问题"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COMPOSE-003"
    
    @property
    def rule_name(self) -> str:
        return "SideEffect Usage"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COMPOSE
    
    @property
    def description(self) -> str:
        return "SideEffect should be used carefully to avoid unnecessary side effects"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        calls = ast.find_all(NodeType.CALL_EXPRESSION)
        
        for call in calls:
            text = call.text
            if "SideEffect" in text and "DisposableEffect" not in text:
                # 检查是否包含资源清理逻辑
                if "onDispose" not in text and "cleanup" not in text.lower():
                    findings.append(self.create_finding(
                        node=call,
                        file_path=file_path,
                        message="SideEffect使用：如果涉及需要清理的资源，建议使用DisposableEffect",
                        suggestion="DisposableEffect(key) { /* setup */ onDispose { /* cleanup */ } }"
                    ))
        
        return findings


@register_rule
class ComposeModifierOrderRule(ASTBasedRule):
    """检测Modifier链式调用顺序"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COMPOSE-004"
    
    @property
    def rule_name(self) -> str:
        return "Modifier Chain Order"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COMPOSE
    
    @property
    def description(self) -> str:
        return "Modifier chain order should follow Compose best practices"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 查找包含Modifier的调用
        calls = ast.find_all(NodeType.CALL_EXPRESSION)
        
        for call in calls:
            text = call.text
            if "Modifier." in text:
                # 检查常见的顺序问题
                # size/height/width 应该在 padding 之后
                if "padding(" in text and ("height(" in text or "width(" in text or "size(" in text):
                    # 简单检查顺序
                    padding_idx = text.find("padding(")
                    size_idx = min(
                        text.find("height(") if "height(" in text else float('inf'),
                        text.find("width(") if "width(" in text else float('inf'),
                        text.find("size(") if "size(" in text else float('inf')
                    )
                    if size_idx < padding_idx:
                        findings.append(self.create_finding(
                            node=call,
                            file_path=file_path,
                            message="Modifier顺序建议：size/height/width 通常应在 padding 之前",
                            suggestion="Modifier.size(100.dp).padding(16.dp) 比 Modifier.padding(16.dp).size(100.dp) 更高效"
                        ))
        
        return findings


@register_rule
class ComposeRememberMissingRule(ASTBasedRule):
    """检测Compose remember缺失问题"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COMPOSE-006"
    
    @property
    def rule_name(self) -> str:
        return "State Hoisting"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COMPOSE
    
    @property
    def description(self) -> str:
        return "Composable functions should hoist state appropriately"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 获取源码用于字符串匹配
        source_code = ast.text
        
        # 查找所有函数声明
        functions = ast.find_all(NodeType.FUNCTION_DECLARATION)
        
        for func in functions:
            # 检查是否是Composable函数
            # 需要检查函数定义前的注解
            # 使用源码范围来检查
            start_line = func.range.start.line
            end_line = func.range.end.line + 1
            
            # 获取函数及其前面的源码行（检查是否有@Composable注解）
            lines = source_code.split('\n') if source_code else []
            check_lines = lines[max(0, start_line-2):end_line]
            check_source = '\n'.join(check_lines)
            
            is_composable = "@Composable" in check_source
            
            if is_composable:
                # 查找函数内所有的调用表达式
                calls = func.find_all(NodeType.CALL_EXPRESSION)
                
                has_remember = any("remember" in c.text for c in calls)
                has_mutableState = any("mutableStateOf" in c.text for c in calls)
                
                if has_mutableState and not has_remember:
                    for call in calls:
                        if "mutableStateOf" in call.text:
                            findings.append(self.create_finding(
                                node=call,
                                file_path=file_path,
                                message="mutableStateOf缺少remember：直接使用会导致状态丢失",
                                suggestion="使用 'var state by remember { mutableStateOf(...) }' 包装"
                            ))
                            break
                
                # 如果调用表达式为空，使用函数源码范围检查
                if not calls:
                    func_source = '\n'.join(lines[start_line:end_line])
                    
                    if "mutableStateOf" in func_source and "remember" not in func_source:
                        findings.append(self.create_finding(
                            node=func,
                            file_path=file_path,
                            message="mutableStateOf缺少remember：直接使用会导致状态丢失",
                            suggestion="使用 'var state by remember { mutableStateOf(...) }' 包装"
                        ))
        
        return findings


@register_rule
class ComposeRecompositionRule(ASTBasedRule):
    """检测可能导致过度重组的问题"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COMPOSE-006"
    
    @property
    def rule_name(self) -> str:
        return "Recomposition Optimization"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PERFORMANCE
    
    @property
    def description(self) -> str:
        return "Avoid unnecessary recompositions by using appropriate memoization"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        functions = ast.find_all(NodeType.FUNCTION_DECLARATION)
        
        for func in functions:
            text = func.text
            if "@Composable" in text:
                # 检查是否在Composable中进行复杂计算
                complex_ops = ["filter", "map", "sortedBy", "groupBy", "reduce"]
                for op in complex_ops:
                    if f".{op}" in text:
                        # 检查是否使用了remember缓存
                        if "remember" not in text and "derivedStateOf" not in text:
                            findings.append(self.create_finding(
                                node=func,
                                file_path=file_path,
                                message=f"性能优化建议：{op} 操作可能导致过度重组",
                                suggestion="使用 remember { list.{op} { } } 或 derivedStateOf { } 缓存计算结果"
                            ))
                            break  # 只报告一次
        
        return findings
