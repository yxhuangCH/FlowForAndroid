"""
Enhanced AST Rules - 改进的 AST 规则

将原字符串匹配规则迁移到 AST 引擎，提供更精确的代码分析。
解决原规则的高误报率问题。
"""

import re
from typing import List, Optional, Set
from ..nodes import ASTNode, NodeType
from .base_ast_rule import (
    ASTBasedRule, Finding, RuleSeverity, RuleCategory, register_rule
)


# ==================== 1. no_globalscope - 精确检测 GlobalScope 调用 ====================

@register_rule
class NoGlobalScopeASTRule(ASTBasedRule):
    """精确检测 GlobalScope 使用，排除注释和字符串中的匹配"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-001"

    @property
    def rule_name(self) -> str:
        return "GlobalScope Usage Detection (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COROUTINE

    @property
    def description(self) -> str:
        return "GlobalScope.launch/async creates coroutines with global lifecycle, may cause memory leaks"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        # 获取所有调用表达式
        calls = ast.find_all(NodeType.CALL_EXPRESSION)

        # 获取注释节点以排除
        comments = self._get_all_comments(ast)
        comment_ranges = [(c.range.start.line, c.range.end.line) for c in comments]

        for call in calls:
            # 只检查实际的函数调用节点，而非注释中的内容
            if self._is_in_comment(call, comment_ranges):
                continue

            text = call.text.strip()

            # 精确匹配 GlobalScope.launch 或 GlobalScope.async
            # 使用正则确保是完整的调用表达式
            if re.search(r'\bGlobalScope\.(launch|async)\s*[({]', text):
                findings.append(self.create_finding(
                    node=call,
                    file_path=file_path,
                    message="GlobalScope 使用：协程生命周期不受控，可能导致内存泄漏",
                    suggestion="使用 lifecycleScope、viewModelScope 或自定义 CoroutineScope 替代 GlobalScope"
                ))

        return findings

    def _get_all_comments(self, ast: ASTNode) -> List[ASTNode]:
        """获取所有注释节点"""
        return ast.find_all(NodeType.COMMENT)

    def _is_in_comment(self, node: ASTNode, comment_ranges: List[tuple]) -> bool:
        """检查节点是否在注释范围内"""
        node_line = node.range.start.line
        for start, end in comment_ranges:
            if start <= node_line <= end:
                return True
        return False


# ==================== 2. viewmodel_context - 精确检测 ViewModel 中的 Context 持有 ====================

@register_rule
class ViewModelContextASTRule(ASTBasedRule):
    """精确检测 ViewModel 类中持有 Context/Activity/Fragment 引用"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-002"

    @property
    def rule_name(self) -> str:
        return "ViewModel Context Holding (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.MEMORY_LEAK

    @property
    def description(self) -> str:
        return "ViewModel should not hold Android Context references to avoid memory leaks"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        # 查找所有类声明
        classes = ast.find_all(NodeType.CLASS_DECLARATION)

        for class_node in classes:
            # 检查是否继承 ViewModel
            if not self._is_viewmodel_class(class_node):
                continue

            # 查找类内的属性声明
            properties = class_node.find_all(NodeType.PROPERTY_DECLARATION)

            for prop in properties:
                if self._has_context_reference(prop):
                    findings.append(self.create_finding(
                        node=prop,
                        file_path=file_path,
                        message=f"ViewModel 持有 Context 引用：可能导致 Activity/Fragment 内存泄漏",
                        suggestion="使用 Application Context 代替，或通过 SavedStateHandle 存储数据，或改用 AndroidViewModel 获取 Application"
                    ))

            # 检查构造函数参数
            constructor_params = self._get_constructor_params(class_node)
            for param in constructor_params:
                if self._is_context_param(param):
                    findings.append(self.create_finding(
                        node=param,
                        file_path=file_path,
                        message=f"ViewModel 构造函数持有 Context 参数：{param.text[:50]}",
                        suggestion="如果只需要 Application 级别 Context，使用 AndroidViewModel；如果需要 Activity 级别 Context，重新设计架构"
                    ))

        return findings

    def _is_viewmodel_class(self, class_node: ASTNode) -> bool:
        """检查类是否继承 ViewModel"""
        class_text = class_node.text
        # 匹配 : ViewModel 或 extends ViewModel
        return bool(re.search(r'(?:\:\s*|extends\s*)ViewModel\b', class_text))

    def _has_context_reference(self, prop_node: ASTNode) -> bool:
        """检查属性是否持有 Context 引用"""
        text = prop_node.text.strip()

        # 检查是否是 Context/Activity/Fragment 类型
        context_types = ['Context', 'Activity', 'Fragment', 'View']

        # 匹配 val/var xxx: Context/Activity/Fragment/View
        type_pattern = r'(?:val|var)\s+\w+\s*:\s*(?:' + '|'.join(context_types) + r')\b'
        if re.search(type_pattern, text):
            return True

        # 检查是否是 lateinit var xxx: Context/Activity/Fragment/View
        lateinit_pattern = r'lateinit\s+var\s+\w+\s*:\s*(?:' + '|'.join(context_types) + r')\b'
        if re.search(lateinit_pattern, text):
            return True

        return False

    def _get_constructor_params(self, class_node: ASTNode) -> List[ASTNode]:
        """获取构造函数参数"""
        # 简化处理：在类声明中查找看起来像构造函数参数的部分
        params = []
        for child in class_node.children:
            if 'constructor' in child.text.lower() or '(' in child.text:
                # 查找所有可能包含参数的节点
                params.extend(child.find_all(NodeType.PROPERTY_DECLARATION))
        return params

    def _is_context_param(self, param_node: ASTNode) -> bool:
        """检查参数是否是 Context 类型"""
        text = param_node.text
        context_types = ['Context', 'Activity', 'Fragment']
        return any(f': {t}' in text or f':{t}' in text for t in context_types)


# ==================== 3. main_thread_io - 检测同一代码块中的主线程IO ====================

@register_rule
class MainThreadIOASTRule(ASTBasedRule):
    """检测在同一协程作用域中使用 Dispatchers.Main 执行 IO 操作"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-003"

    @property
    def rule_name(self) -> str:
        return "Main Thread IO Operations (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PERFORMANCE

    @property
    def description(self) -> str:
        return "IO operations on main thread may cause ANR"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        io_keywords = [
            'read', 'write', 'File(', 'FileReader', 'FileWriter',
            'openConnection', 'getInputStream', 'getOutputStream',
            'database', 'query', 'insert', 'update', 'delete',
            'SharedPreferences', 'getSharedPreferences'
        ]

        # 查找所有函数声明和 lambda 表达式（作为作用域边界）
        scopes = ast.find_all(NodeType.FUNCTION_DECLARATION)
        scopes.extend(ast.find_all(NodeType.LAMBDA_EXPRESSION))

        for scope in scopes:
            # 检查作用域内是否使用了 Dispatchers.Main
            if not self._uses_main_dispatcher(scope):
                continue

            # 在相同作用域内查找 IO 操作
            io_calls = self._find_io_operations(scope, io_keywords)

            for call in io_calls:
                findings.append(self.create_finding(
                    node=call,
                    file_path=file_path,
                    message=f"主线程 IO 操作风险：在 Dispatchers.Main 中执行 IO 可能导致 ANR",
                    suggestion="使用 withContext(Dispatchers.IO) { } 将 IO 操作切换到 IO 线程，或使用 flowOn(Dispatchers.IO)"
                ))

        return findings

    def _uses_main_dispatcher(self, scope: ASTNode) -> bool:
        """检查作用域是否使用 Dispatchers.Main"""
        text = scope.text
        # 检查 withContext(Dispatchers.Main) 或 launch(Dispatchers.Main)
        return bool(re.search(r'(?:withContext|launch|async)\s*\(\s*Dispatchers\.Main\b', text))

    def _find_io_operations(self, scope: ASTNode, io_keywords: List[str]) -> List[ASTNode]:
        """在作用域内查找 IO 操作调用"""
        findings = []
        calls = scope.find_all(NodeType.CALL_EXPRESSION)

        for call in calls:
            text = call.text
            for keyword in io_keywords:
                if keyword in text:
                    findings.append(call)
                    break

        return findings


# ==================== 4. unspecified_scope - 精确检测未指定作用域的协程启动 ====================

@register_rule
class UnspecifiedScopeASTRule(ASTBasedRule):
    """精确检测未指定作用域的协程启动，排除对象方法调用"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-004"

    @property
    def rule_name(self) -> str:
        return "Unspecified Coroutine Scope (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COROUTINE

    @property
    def description(self) -> str:
        return "Coroutine builders should be called with explicit scope"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        # 查找所有调用表达式
        calls = ast.find_all(NodeType.CALL_EXPRESSION)

        for call in calls:
            text = call.text.strip()

            # 检查是否是直接的 launch/async 调用（没有作用域前缀）
            # 匹配模式：launch { 或 launch( 但不是 xxx.launch {
            if not self._is_direct_coroutine_builder(text):
                continue

            # 排除有明确作用域前缀的情况
            if self._has_explicit_scope(text):
                continue

            # 排除在 withContext 内部的调用
            if self._is_inside_withcontext(call):
                continue

            findings.append(self.create_finding(
                node=call,
                file_path=file_path,
                message="未指定作用域的协程启动：可能导致协程生命周期管理问题",
                suggestion="显式指定协程作用域，如 viewModelScope.launch { } 或 lifecycleScope.launch { }"
            ))

        return findings

    def _is_direct_coroutine_builder(self, text: str) -> bool:
        """检查是否是直接的协程构建器调用"""
        # 匹配 launch { 或 launch( 开头
        patterns = [
            r'^launch\s*\{',
            r'^launch\s*\(',
            r'^async\s*\{',
            r'^async\s*\(',
        ]
        return any(re.search(p, text) for p in patterns)

    def _has_explicit_scope(self, text: str) -> bool:
        """检查是否有明确的作用域前缀"""
        scope_patterns = [
            r'\w+Scope\.(launch|async)',
            r'coroutineScope\.(launch|async)',
            r'\w+\.(launch|async)\s*\{',
        ]
        return any(re.search(p, text) for p in scope_patterns)

    def _is_inside_withcontext(self, call: ASTNode) -> bool:
        """检查是否在 withContext 块内部"""
        parent = call.parent
        while parent:
            if 'withContext' in parent.text:
                return True
            parent = parent.parent
        return False


# ==================== 5. remember_context - 精确检测 remember 块中的 Context 引用 ====================

@register_rule
class RememberContextASTRule(ASTBasedRule):
    """精确检测 remember { } 块中持有 Context 引用"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-005"

    @property
    def rule_name(self) -> str:
        return "Remember Context Holding (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.MEMORY_LEAK

    @property
    def description(self) -> str:
        return "Holding Context in remember block may cause memory leaks"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        # 查找所有 Composable 函数
        functions = ast.find_all(NodeType.FUNCTION_DECLARATION)

        for func in functions:
            # 检查是否是 @Composable 函数
            if not self._is_composable_function(func):
                continue

            # 在函数内查找 remember 调用
            calls = func.find_all(NodeType.CALL_EXPRESSION)

            for call in calls:
                if not self._is_remember_call(call):
                    continue

                # 检查 remember 块内是否使用了 Context
                if self._contains_context_reference(call):
                    findings.append(self.create_finding(
                        node=call,
                        file_path=file_path,
                        message="remember 块中持有 Context：可能导致内存泄漏",
                        suggestion="避免在 remember 中持有 Context，考虑使用 ViewModel 或其他生命周期感知的方式"
                    ))

        return findings

    def _is_composable_function(self, func: ASTNode) -> bool:
        """检查函数是否是 @Composable"""
        # 检查函数文本或父节点是否包含 @Composable
        func_text = func.text
        return '@Composable' in func_text

    def _is_remember_call(self, call: ASTNode) -> bool:
        """检查是否是 remember 调用"""
        text = call.text.strip()
        # 匹配 remember { 或 remember(key) {
        return bool(re.search(r'^remember\s*[({]', text))

    def _contains_context_reference(self, remember_call: ASTNode) -> bool:
        """检查 remember 调用中是否包含 Context 引用"""
        text = remember_call.text

        # 检查是否包含 Context 类型或 context 变量
        context_patterns = [
            r'\bContext\b',
            r'\bActivity\b',
            r'\bFragment\b',
            r':\s*Context',
            r'context\s*\.',
        ]

        return any(re.search(p, text) for p in context_patterns)


# ==================== 6. missing_flowon_for_io - 检测 Flow 构建器中的 IO 操作 ====================

@register_rule
class MissingFlowOnASTRule(ASTBasedRule):
    """精确检测 Flow 构建器中的 IO 操作是否缺少 flowOn"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-006"

    @property
    def rule_name(self) -> str:
        return "Flow Missing flowOn (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COROUTINE

    @property
    def description(self) -> str:
        return "Flow performing IO operations should explicitly specify dispatcher"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        # 查找所有函数声明（作为 Flow 构建器可能所在的范围）
        functions = ast.find_all(NodeType.FUNCTION_DECLARATION)

        for func in functions:
            # 检查函数是否返回 Flow
            if not self._returns_flow(func):
                continue

            # 检查函数内是否有 flow { } 构建器
            flow_builders = self._find_flow_builders(func)

            for builder in flow_builders:
                # 检查 flow 构建器内是否有 IO 操作
                if not self._has_io_operations(builder):
                    continue

                # 检查整个函数链是否有 flowOn
                if not self._has_flowon_in_chain(func):
                    findings.append(self.create_finding(
                        node=builder,
                        file_path=file_path,
                        message="Flow 执行 IO 操作但未指定 flowOn 调度器：可能在主线程执行 IO",
                        suggestion="添加 .flowOn(Dispatchers.IO) 指定 IO 调度器"
                    ))

        return findings

    def _returns_flow(self, func: ASTNode) -> bool:
        """检查函数是否返回 Flow 类型"""
        func_text = func.text
        # 匹配返回类型为 Flow<xxx> 或 : Flow
        return bool(re.search(r'(?:\:\s*|->\s*)Flow\s*<', func_text))

    def _find_flow_builders(self, func: ASTNode) -> List[ASTNode]:
        """查找 flow { } 构建器"""
        builders = []
        calls = func.find_all(NodeType.CALL_EXPRESSION)

        for call in calls:
            text = call.text.strip()
            # 匹配 flow { 或 flowOf( 或 callbackFlow {
            if re.search(r'^(flow|callbackFlow|channelFlow)\s*[({]', text):
                builders.append(call)

        return builders

    def _has_io_operations(self, node: ASTNode) -> bool:
        """检查节点内是否有 IO 操作"""
        io_keywords = [
            'repository', 'database', 'dao', 'file', 'network',
            'read', 'write', 'query', 'insert', 'update', 'delete'
        ]

        text = node.text.lower()
        return any(kw in text for kw in io_keywords)

    def _has_flowon_in_chain(self, func: ASTNode) -> bool:
        """检查函数内是否有 flowOn 调用"""
        text = func.text
        return '.flowOn(' in text or 'flowOn(' in text


# ==================== 7. mutable_stateflow_exposed - 精确检测可见性 ====================

@register_rule
class MutableStateFlowExposedASTRule(ASTBasedRule):
    """精确检测 MutableStateFlow 是否被公开暴露"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-007"

    @property
    def rule_name(self) -> str:
        return "MutableStateFlow Exposed (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.BEST_PRACTICE

    @property
    def description(self) -> str:
        return "MutableStateFlow should be private and exposed as read-only StateFlow"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        # 查找类声明
        classes = ast.find_all(NodeType.CLASS_DECLARATION)

        for class_node in classes:
            # 查找类内的属性声明
            properties = class_node.find_all(NodeType.PROPERTY_DECLARATION)

            for prop in properties:
                if not self._is_mutable_stateflow(prop):
                    continue

                # 检查可见性修饰符
                if not self._is_private(prop):
                    findings.append(self.create_finding(
                        node=prop,
                        file_path=file_path,
                        message="MutableStateFlow 被公开暴露：应该使用 private 修饰并通过 asStateFlow() 暴露只读版本",
                        suggestion="改为 'private val _state = MutableStateFlow(...)' 并添加 'val state: StateFlow<...> = _state.asStateFlow()'"
                    ))

        return findings

    def _is_mutable_stateflow(self, prop: ASTNode) -> bool:
        """检查是否是 MutableStateFlow 属性"""
        text = prop.text.strip()
        # 匹配 val/var xxx = MutableStateFlow(...) 或 val/var xxx: MutableStateFlow<...>
        patterns = [
            r'(?:val|var)\s+\w+\s*=\s*MutableStateFlow',
            r'(?:val|var)\s+\w+\s*:\s*MutableStateFlow',
        ]
        return any(re.search(p, text) for p in patterns)

    def _is_private(self, prop: ASTNode) -> bool:
        """检查属性是否是 private"""
        text = prop.text.strip()
        return text.startswith('private')


# ==================== 8. singleton_activity - 验证注入关系 ====================

@register_rule
class SingletonActivityASTRule(ASTBasedRule):
    """检测 @Singleton 组件注入到 Activity/Fragment 中"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-008"

    @property
    def rule_name(self) -> str:
        return "Singleton in Activity Scope (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.BEST_PRACTICE

    @property
    def description(self) -> str:
        return "@Singleton component injected into Activity/Fragment may cause lifecycle mismatch"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        # 查找类声明
        classes = ast.find_all(NodeType.CLASS_DECLARATION)

        for class_node in classes:
            # 检查是否是 Activity/Fragment
            if not self._is_activity_or_fragment(class_node):
                continue

            # 查找注入的依赖（构造函数参数或 @Inject 字段）
            injected_deps = self._find_injected_dependencies(class_node)

            for dep in injected_deps:
                # 检查依赖是否是 @Singleton
                if self._is_singleton_dependency(dep):
                    findings.append(self.create_finding(
                        node=dep,
                        file_path=file_path,
                        message="@Singleton 组件注入到 Activity/Fragment 作用域：可能导致生命周期不匹配",
                        suggestion="考虑使用 @ActivityScoped 或 @FragmentScoped 替代 @Singleton，或重新设计依赖关系"
                    ))

        return findings

    def _is_activity_or_fragment(self, class_node: ASTNode) -> bool:
        """检查类是否是 Activity 或 Fragment"""
        class_text = class_node.text
        patterns = [
            r':\s*AppCompatActivity',
            r':\s*Activity\b',
            r':\s*Fragment\b',
            r'extends\s+Activity',
            r'extends\s+Fragment',
        ]
        return any(re.search(p, class_text) for p in patterns)

    def _find_injected_dependencies(self, class_node: ASTNode) -> List[ASTNode]:
        """查找注入的依赖"""
        deps = []

        # 查找构造函数参数
        properties = class_node.find_all(NodeType.PROPERTY_DECLARATION)
        for prop in properties:
            # 检查是否有 @Inject 注解或在构造函数中
            if '@Inject' in prop.text or 'constructor' in prop.text:
                deps.append(prop)

        return deps

    def _is_singleton_dependency(self, dep: ASTNode) -> bool:
        """检查依赖是否是 @Singleton"""
        # 简化处理：检查依赖类型是否是 @Singleton 标记的类
        # 实际实现可能需要跨文件分析
        dep_text = dep.text

        # 如果依赖声明附近有 @Singleton 注解
        # 或依赖类名暗示是单例
        singleton_indicators = [
            '@Singleton',
            'Singleton',
        ]

        # 检查属性类型
        return any(ind in dep_text for ind in singleton_indicators)


# ==================== 9. collect_without_repeat - 检测缺少 repeatOnLifecycle 的 collect ====================

@register_rule
class CollectWithoutRepeatASTRule(ASTBasedRule):
    """检测 UI 层中缺少 repeatOnLifecycle 的 Flow collect"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-009"

    @property
    def rule_name(self) -> str:
        return "Collect Without repeatOnLifecycle (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.LIFECYCLE

    @property
    def description(self) -> str:
        return "UI layer Flow collect should use repeatOnLifecycle"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        # 查找类声明
        classes = ast.find_all(NodeType.CLASS_DECLARATION)

        for class_node in classes:
            # 检查是否是 UI 层（Activity/Fragment）
            if not self._is_ui_layer(class_node):
                continue

            # 查找 collect/collectLatest 调用
            calls = class_node.find_all(NodeType.CALL_EXPRESSION)

            for call in calls:
                if not self._is_collect_call(call):
                    continue

                # 检查是否在 repeatOnLifecycle 块内
                if self._is_inside_repeat_on_lifecycle(call):
                    continue

                findings.append(self.create_finding(
                    node=call,
                    file_path=file_path,
                    message="UI 层 Flow collect 缺少 repeatOnLifecycle：应用进入后台时仍会接收事件，可能导致崩溃或资源浪费",
                    suggestion="使用 'lifecycleScope.launch { repeatOnLifecycle(Lifecycle.State.STARTED) { flow.collect { } } }' 包装 collect"
                ))

        return findings

    def _is_ui_layer(self, class_node: ASTNode) -> bool:
        """检查是否是 UI 层类"""
        class_text = class_node.text
        patterns = [
            r':\s*AppCompatActivity',
            r':\s*Activity\b',
            r':\s*Fragment\b',
            r'extends\s+Activity',
            r'extends\s+Fragment',
        ]
        return any(re.search(p, class_text) for p in patterns)

    def _is_collect_call(self, call: ASTNode) -> bool:
        """检查是否是 collect/collectLatest 调用"""
        text = call.text.strip()
        return bool(re.search(r'\.(collect|collectLatest)\s*[({]', text))

    def _is_inside_repeat_on_lifecycle(self, call: ASTNode) -> bool:
        """检查是否在 repeatOnLifecycle 块内"""
        parent = call.parent
        while parent:
            if 'repeatOnLifecycle' in parent.text:
                return True
            parent = parent.parent
        return False


# ==================== 10. multiple_collects - 检测同一 Flow 的多次收集 ====================

@register_rule
class MultipleCollectsASTRule(ASTBasedRule):
    """检测对同一 Cold Flow 的多次收集"""

    @property
    def rule_id(self) -> str:
        return "AST-ENHANCED-010"

    @property
    def rule_name(self) -> str:
        return "Multiple Collects on Cold Flow (AST)"

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.BEST_PRACTICE

    @property
    def description(self) -> str:
        return "Multiple collects on same Cold Flow causes duplicate upstream execution"

    def check(self, ast: ASTNode, file_path: str) -> List[Finding]:
        findings = []

        # 查找类或函数声明
        scopes = ast.find_all(NodeType.CLASS_DECLARATION)
        scopes.extend(ast.find_all(NodeType.FUNCTION_DECLARATION))

        for scope in scopes:
            # 查找所有 collect 调用
            calls = scope.find_all(NodeType.CALL_EXPRESSION)

            # 收集 collect 调用及其目标 Flow
            collect_calls = []
            for call in calls:
                flow_name = self._get_flow_name_from_collect(call)
                if flow_name:
                    collect_calls.append((call, flow_name))

            # 检查同一 Flow 是否被多次收集
            flow_counts = {}
            for call, flow_name in collect_calls:
                if flow_name not in flow_counts:
                    flow_counts[flow_name] = []
                flow_counts[flow_name].append(call)

            # 报告多次收集的 Flow
            for flow_name, calls_list in flow_counts.items():
                if len(calls_list) > 1:
                    findings.append(self.create_finding(
                        node=calls_list[0],
                        file_path=file_path,
                        message=f"Cold Flow '{flow_name}' 被多次收集：会导致上游操作重复执行，浪费资源",
                        suggestion="使用 shareIn() 或 stateIn() 将 Cold Flow 转换为 Hot Flow，避免重复执行"
                    ))

        return findings

    def _get_flow_name_from_collect(self, call: ASTNode) -> Optional[str]:
        """从 collect 调用中提取 Flow 名称"""
        text = call.text.strip()

        # 匹配 xxx.collect { 或 xxx.collectLatest {
        match = re.search(r'(\w+)\.(?:collect|collectLatest)\s*[({]', text)
        if match:
            return match.group(1)

        return None


# ==================== 模块导出 ====================

__all__ = [
    'NoGlobalScopeASTRule',
    'ViewModelContextASTRule',
    'MainThreadIOASTRule',
    'UnspecifiedScopeASTRule',
    'RememberContextASTRule',
    'MissingFlowOnASTRule',
    'MutableStateFlowExposedASTRule',
    'SingletonActivityASTRule',
    'CollectWithoutRepeatASTRule',
    'MultipleCollectsASTRule',
]
