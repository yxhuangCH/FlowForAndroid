"""
Coroutine Rules - 协程相关规则

检测协程使用中的常见问题。
"""

from typing import List
from ..nodes import ASTNode, NodeType
from .base_ast_rule import (
    ASTBasedRule, Finding, RuleSeverity, RuleCategory, register_rule
)


@register_rule
class GlobalScopeRule(ASTBasedRule):
    """检测GlobalScope使用"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COROUTINE-001"
    
    @property
    def rule_name(self) -> str:
        return "Avoid GlobalScope"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COROUTINE
    
    @property
    def description(self) -> str:
        return "GlobalScope.launch is discouraged as it creates coroutines with global lifecycle"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 查找所有调用表达式
        calls = ast.find_all(NodeType.CALL_EXPRESSION)
        
        for call in calls:
            text = call.text
            # 检查是否是GlobalScope调用
            if "GlobalScope.launch" in text or "GlobalScope.async" in text:
                findings.append(self.create_finding(
                    node=call,
                    file_path=file_path,
                    message="GlobalScope 使用风险：协程生命周期不受控，可能导致内存泄漏",
                    suggestion="使用 lifecycleScope 或 viewModelScope 替代 GlobalScope"
                ))
        
        return findings


@register_rule
class UnspecifiedScopeRule(ASTBasedRule):
    """检测未指定作用域的协程启动"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COROUTINE-002"
    
    @property
    def rule_name(self) -> str:
        return "Coroutine Scope Required"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COROUTINE
    
    @property
    def description(self) -> str:
        return "Coroutine builders should be called on explicit scopes"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 查找所有调用表达式
        calls = ast.find_all(NodeType.CALL_EXPRESSION)
        
        for call in calls:
            text = call.text
            # 检查是否是直接的 launch/async 调用（没有点号前缀）
            if text.startswith("launch") or text.startswith("async"):
                # 检查是否有明确的作用域前缀
                if not any(scope in text for scope in ["Scope.launch", "Scope.async", 
                                                        ".launch", ".async"]):
                    findings.append(self.create_finding(
                        node=call,
                        file_path=file_path,
                        message="未指定作用域的协程启动：可能导致协程生命周期管理问题",
                        suggestion="显式指定协程作用域，如 lifecycleScope.launch { }"
                    ))
        
        return findings


@register_rule
class MainThreadIORule(ASTBasedRule):
    """检测主线程IO操作"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COROUTINE-003"
    
    @property
    def rule_name(self) -> str:
        return "IO on Main Thread"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COROUTINE
    
    @property
    def description(self) -> str:
        return "IO operations should not be performed on Dispatchers.Main"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 查找所有调用表达式
        calls = ast.find_all(NodeType.CALL_EXPRESSION)
        
        io_operations = [
            "readText", "writeText", "readBytes", "writeBytes",
            "readFile", "writeFile", "File(", "FileReader",
            "openConnection", "getInputStream", "getOutputStream"
        ]
        
        for call in calls:
            text = call.text
            # 检查是否包含主线程调度器和IO操作
            if "Dispatchers.Main" in text:
                for io_op in io_operations:
                    if io_op in text:
                        findings.append(self.create_finding(
                            node=call,
                            file_path=file_path,
                            message=f"主线程IO操作风险：在主线程执行 {io_op} 可能导致ANR",
                            suggestion="使用 withContext(Dispatchers.IO) 将IO操作切换到IO线程"
                        ))
                        break
        
        return findings


@register_rule
class ViewModelContextRule(ASTBasedRule):
    """检测ViewModel持有Context"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COROUTINE-004"
    
    @property
    def rule_name(self) -> str:
        return "ViewModel Context Leak"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.MEMORY_LEAK
    
    @property
    def description(self) -> str:
        return "ViewModel should not hold references to Context to avoid memory leaks"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 查找类声明
        classes = ast.find_all(NodeType.CLASS_DECLARATION)
        
        for class_node in classes:
            # 检查是否是ViewModel
            if "ViewModel" not in class_node.text:
                continue
            
            # 查找类内部的属性声明
            properties = class_node.find_all(NodeType.PROPERTY_DECLARATION)
            
            for prop in properties:
                text = prop.text
                metadata = prop.metadata
                
                # 检查是否是构造函数参数
                is_constructor_param = metadata.get('is_constructor_param', False)
                
                # 检查是否持有Context (通过text或metadata判断)
                has_context_type = (
                    ": Context" in text or 
                    ": Activity" in text or 
                    ": Fragment" in text or
                    "Context" in text or 
                    "Activity" in text or 
                    "Fragment" in text
                )
                
                # 如果是构造函数参数，检查完整类型（通过类名判断）
                prop_name = metadata.get('property_name', '')
                if is_constructor_param and prop_name:
                    # 构造函数参数没有完整类型信息，检查类名是否包含Context相关词
                    class_text = class_node.text
                    # 检查构造函数参数名是否暗示Context
                    context_param_names = ['context', 'activity', 'application', 'fragment']
                    if prop_name.lower() in context_param_names:
                        findings.append(self.create_finding(
                            node=prop,
                            file_path=file_path,
                            message=f"ViewModel持有Context参数：{prop_name}可能导致Activity/Fragment内存泄漏",
                            suggestion="使用Application Context代替，或通过SavedStateHandle存储数据"
                        ))
                elif has_context_type:
                    findings.append(self.create_finding(
                        node=prop,
                        file_path=file_path,
                        message="ViewModel持有Context：可能导致Activity/Fragment内存泄漏",
                        suggestion="使用Application Context代替，或通过SavedStateHandle存储数据"
                    ))
        
        return findings


@register_rule
class FlowOnMainDispatcherRule(ASTBasedRule):
    """检测Flow在主调度器上的操作"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COROUTINE-005"
    
    @property
    def rule_name(self) -> str:
        return "Flow Main Dispatcher"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COROUTINE
    
    @property
    def description(self) -> str:
        return "Flow operators should specify appropriate dispatchers"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 查找所有调用表达式
        calls = ast.find_all(NodeType.CALL_EXPRESSION)
        
        flow_ops = ["map", "filter", "flatMapLatest", "transform"]
        
        for call in calls:
            text = call.text
            # 检查是否是Flow操作且没有指定调度器
            if any(op in text for op in flow_ops):
                if ".flowOn(" not in text and "Dispatchers" not in text:
                    # 简单启发式：如果在ViewModel或Repository中
                    parent_function = call.find_parent(NodeType.FUNCTION_DECLARATION)
                    if parent_function and any(keyword in parent_function.text 
                                                for keyword in ["ViewModel", "Repository", "UseCase"]):
                        findings.append(self.create_finding(
                            node=call,
                            file_path=file_path,
                            message=f"Flow操作可能阻塞主线程：{text[:50]}",
                            suggestion="添加 .flowOn(Dispatchers.IO) 或 .flowOn(Dispatchers.Default)"
                        ))
        
        return findings


@register_rule
class SuspendFunctionNamingRule(ASTBasedRule):
    """检测挂起函数命名规范"""
    
    @property
    def rule_id(self) -> str:
        return "AST-COROUTINE-006"
    
    @property
    def rule_name(self) -> str:
        return "Suspend Function Naming"
    
    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO
    
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.BEST_PRACTICE
    
    @property
    def description(self) -> str:
        return "Suspend functions should follow naming conventions"
    
    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []
        
        # 查找所有函数声明
        functions = ast.find_all(NodeType.FUNCTION_DECLARATION)
        
        for func in functions:
            metadata = func.metadata
            # 检查是否是挂起函数
            if metadata.get("is_suspend", False):
                func_name = metadata.get("function_name", "")
                
                # 检查命名规范（挂起函数建议以Async或Suspend结尾，或以get/set开头）
                good_patterns = ["Async", "Suspend", "get", "set", "load", "fetch", "save"]
                if not any(pattern in func_name for pattern in good_patterns):
                    findings.append(self.create_finding(
                        node=func,
                        file_path=file_path,
                        message=f"挂起函数命名建议：{func_name} 建议使用 Async/Suspend 后缀或 get/set 前缀",
                        suggestion="例如：fetchDataAsync() 或 getDataSuspend()"
                    ))
        
        return findings
