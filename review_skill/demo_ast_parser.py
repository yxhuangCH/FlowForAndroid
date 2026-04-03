"""
演示：使用新的Kotlin AST解析器解析PermissionManager.kt

展示如何构建完整的语法树并分析代码结构
"""

import sys
import os
sys.path.insert(0, '/Users/yxhuang/code/AndroidDemo/flowforandroid/review_skill')

from ast_engine.parser_v2 import parse_kotlin_ast
from ast_engine.nodes import NodeType


def print_ast_tree(node, indent=0, max_depth=3):
    """以树形结构打印AST"""
    prefix = "  " * indent
    
    # 基本信息
    node_info = f"{node.node_type.name}"
    if hasattr(node, 'metadata') and node.metadata:
        if 'class_name' in node.metadata:
            node_info += f" (class: {node.metadata['class_name']})"
        elif 'function_name' in node.metadata:
            node_info += f" (fun: {node.metadata['function_name']})"
        elif 'property_name' in node.metadata:
            node_info += f" (val/var: {node.metadata['property_name']})"
    
    # 源码位置
    if hasattr(node, 'range') and node.range:
        start = node.range.start
        end = node.range.end
        node_info += f" [{start.line+1}:{start.column+1}-{end.line+1}:{end.column+1}]"
    
    print(f"{prefix}{node_info}")
    
    # 递归打印子节点（限制深度避免输出过长）
    if indent < max_depth:
        for child in node.children:
            print_ast_tree(child, indent + 1, max_depth)


def analyze_kotlin_file(file_path):
    """分析Kotlin文件并展示AST结构"""
    print("=" * 80)
    print("🔍 Kotlin AST 解析演示")
    print("=" * 80)
    
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        print(f"📁 文件: {os.path.basename(file_path)}")
        print(f"📊 代码行数: {len(source_code.splitlines())}")
        print(f"📏 字符数: {len(source_code)}")
        print()
        
        # 解析为AST
        print("🔄 正在解析语法树...")
        ast = parse_kotlin_ast(source_code)
        print("✅ 解析完成！")
        print()
        
        # 展示AST结构
        print("🌳 AST结构（前3层）：")
        print("-" * 50)
        print_ast_tree(ast, max_depth=3)
        print()
        
        # 统计信息
        print("📈 代码统计：")
        print("-" * 30)
        
        # 统计各类节点
        def count_nodes(node, node_type):
            count = 1 if node.node_type == node_type else 0
            for child in node.children:
                count += count_nodes(child, node_type)
            return count
        
        class_count = count_nodes(ast, NodeType.CLASS_DECLARATION)
        function_count = count_nodes(ast, NodeType.FUNCTION_DECLARATION)
        property_count = count_nodes(ast, NodeType.PROPERTY_DECLARATION)
        companion_count = count_nodes(ast, NodeType.COMPANION_OBJECT)
        
        print(f"📋 类声明: {class_count}")
        print(f"⚙️  函数声明: {function_count}")
        print(f"💾 属性声明: {property_count}")
        print(f"🏠 伴生对象: {companion_count}")
        
        # 查找特定模式
        print()
        print("🔍 代码模式分析：")
        print("-" * 30)
        
        # 查找suspend函数
        suspend_functions = []
        def find_suspend_functions(node):
            if (node.node_type == NodeType.FUNCTION_DECLARATION and 
                node.metadata and 
                node.metadata.get('is_suspend', False)):
                suspend_functions.append(node.metadata.get('function_name', ''))
            for child in node.children:
                find_suspend_functions(child)
        
        find_suspend_functions(ast)
        print(f"🔄 Suspend函数: {suspend_functions}")
        
        # 查找伴生对象中的函数
        companion_functions = []
        def find_companion_functions(node):
            if node.node_type == NodeType.COMPANION_OBJECT:
                for child in node.children:
                    if child.node_type == NodeType.FUNCTION_DECLARATION:
                        companion_functions.append(child.metadata.get('function_name', ''))
            for child in node.children:
                find_companion_functions(child)
        
        find_companion_functions(ast)
        print(f"🏠 伴生对象函数: {companion_functions}")
        
        return ast
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_rule_analysis(ast):
    """演示如何基于AST进行规则分析"""
    print()
    print("🎯 规则分析演示：")
    print("-" * 30)
    
    findings = []
    
    # 规则1: 检查GlobalScope使用
    def check_global_scope(node):
        if node.node_type == NodeType.STATEMENT and 'GlobalScope' in node.text:
            findings.append({
                'rule': 'GlobalScopeUsage',
                'message': '检测到GlobalScope使用，建议使用合适的CoroutineScope',
                'line': node.range.start.line + 1,
                'severity': 'WARNING'
            })
    
    # 规则2: 检查ViewModel持有Context
    def check_viewmodel_context(node):
        if (node.node_type == NodeType.PROPERTY_DECLARATION and 
            node.metadata and 
            'Context' in str(node.metadata) and
            'activity' in str(node.metadata).lower()):
            findings.append({
                'rule': 'ViewModelContext',
                'message': 'ViewModel不应直接持有Activity Context，可能导致内存泄漏',
                'line': node.range.start.line + 1,
                'severity': 'ERROR'
            })
    
    # 遍历AST应用规则
    def traverse_and_check(node):
        check_global_scope(node)
        check_viewmodel_context(node)
        for child in node.children:
            traverse_and_check(child)
    
    traverse_and_check(ast)
    
    if findings:
        print("⚠️  发现的问题：")
        for finding in findings:
            print(f"  [{finding['severity']}] 第{finding['line']}行: {finding['message']}")
    else:
        print("✅ 未发现明显问题")


if __name__ == "__main__":
    # 目标文件路径
    target_file = "/Users/yxhuang/code/AndroidDemo/flowforandroid/app/src/main/java/com/yxhuang/flowforandroid/permission/PermissionManager.kt"
    
    # 分析文件
    ast = analyze_kotlin_file(target_file)
    
    if ast:
        # 演示规则分析
        demo_rule_analysis(ast)
        
        print()
        print("=" * 80)
        print("🎉 演示完成！")
        print("这个解析器可以：")
        print("  • 构建完整的Kotlin语法树")
        print("  • 精确定位代码位置")
        print("  • 支持复杂的代码分析规则")
        print("  • 零依赖，纯Python实现")