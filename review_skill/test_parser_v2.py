"""
测试 parser_v2 - 验证真正的Kotlin AST解析器
"""

import sys
sys.path.insert(0, '/Users/yxhuang/code/AndroidDemo/flowforandroid/review_skill')

from ast_engine.parser_v2 import parse_kotlin_ast, analyze_kotlin_file


def print_ast_tree(node, indent=0):
    """打印AST树"""
    prefix = "  " * indent
    info = node.node_type.name
    
    if node.metadata:
        if 'class_name' in node.metadata:
            info += f" [class: {node.metadata['class_name']}]"
        elif 'function_name' in node.metadata:
            info += f" [fun: {node.metadata['function_name']}]"
            if node.metadata.get('is_suspend'):
                info += " (suspend)"
        elif 'property_name' in node.metadata:
            info += f" [prop: {node.metadata['property_name']}]"
            if node.metadata.get('is_mutable'):
                info += " (var)"
            else:
                info += " (val)"
        elif 'package_name' in node.metadata:
            info += f" [package: {node.metadata['package_name']}]"
        elif 'import_path' in node.metadata:
            info += f" [import: {node.metadata['import_path']}]"
    
    print(f"{prefix}{info}")
    
    for child in node.children:
        print_ast_tree(child, indent + 1)


def count_nodes(node, stats=None):
    """统计AST节点"""
    if stats is None:
        stats = {
            'classes': 0,
            'interfaces': 0,
            'functions': 0,
            'suspend_functions': 0,
            'properties': 0,
            'companion_objects': 0,
            'objects': 0,
        }
    
    from ast_engine.nodes import NodeType
    
    if node.node_type == NodeType.CLASS_DECLARATION:
        stats['classes'] += 1
    elif node.node_type == NodeType.INTERFACE_DECLARATION:
        stats['interfaces'] += 1
    elif node.node_type == NodeType.FUNCTION_DECLARATION:
        stats['functions'] += 1
        if node.metadata and node.metadata.get('is_suspend'):
            stats['suspend_functions'] += 1
    elif node.node_type == NodeType.PROPERTY_DECLARATION:
        stats['properties'] += 1
    elif node.node_type == NodeType.COMPANION_OBJECT:
        stats['companion_objects'] += 1
    elif node.node_type == NodeType.OBJECT_DECLARATION:
        stats['objects'] += 1
    
    for child in node.children:
        count_nodes(child, stats)
    
    return stats


def test_simple_kotlin():
    """测试简单Kotlin代码"""
    print("=" * 80)
    print("🧪 测试1: 简单Kotlin代码")
    print("=" * 80)
    
    code = """
package com.example

import kotlinx.coroutines.*

class MyClass {
    private var count: Int = 0
    
    suspend fun doSomething(): String {
        delay(100)
        return "Hello"
    }
    
    companion object {
        fun create(): MyClass = MyClass()
    }
}
"""
    
    try:
        ast = parse_kotlin_ast(code)
        print("✅ 解析成功！")
        print("\n🌳 AST结构：")
        print_ast_tree(ast)
        
        stats = count_nodes(ast)
        print("\n📊 统计信息：")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        return True
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_permission_manager():
    """测试PermissionManager.kt"""
    print("\n" + "=" * 80)
    print("🧪 测试2: PermissionManager.kt (真实代码)")
    print("=" * 80)
    
    filepath = "/Users/yxhuang/code/AndroidDemo/flowforandroid/app/src/main/java/com/yxhuang/flowforandroid/permission/PermissionManager.kt"
    
    try:
        ast = analyze_kotlin_file(filepath)
        if ast is None:
            print("❌ 文件解析失败")
            return False
        
        print("✅ 文件解析成功！")
        
        # 打印AST结构（简化）
        print("\n🌳 AST结构（前3层）：")
        
        def print_limited(node, indent=0, max_depth=3):
            if indent > max_depth:
                return
            prefix = "  " * indent
            info = node.node_type.name
            
            if node.metadata:
                if 'class_name' in node.metadata:
                    info += f" [{node.metadata['class_name']}]"
                elif 'function_name' in node.metadata:
                    info += f" [{node.metadata['function_name']}]"
                    if node.metadata.get('is_suspend'):
                        info += " (suspend)"
                elif 'property_name' in node.metadata:
                    info += f" [{node.metadata['property_name']}]"
            
            print(f"{prefix}{info}")
            
            for child in node.children:
                print_limited(child, indent + 1, max_depth)
        
        print_limited(ast)
        
        # 统计
        stats = count_nodes(ast)
        print("\n📊 代码统计：")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_extension_functions():
    """测试扩展函数解析"""
    print("\n" + "=" * 80)
    print("🧪 测试3: 扩展函数")
    print("=" * 80)
    
    code = """
fun String.addPrefix(prefix: String): String {
    return prefix + this
}

suspend fun PermissionManager.requestNotificationPermission(): PermissionResult {
    return requestPermission(Manifest.permission.POST_NOTIFICATIONS)
}
"""
    
    try:
        ast = parse_kotlin_ast(code)
        print("✅ 解析成功！")
        
        # 查找函数声明
        from ast_engine.nodes import NodeType
        functions = []
        
        def find_functions(node):
            if node.node_type == NodeType.FUNCTION_DECLARATION:
                functions.append(node)
            for child in node.children:
                find_functions(child)
        
        find_functions(ast)
        
        print("\n🔍 发现的函数：")
        for func in functions:
            name = func.metadata.get('function_name', 'unknown')
            is_suspend = func.metadata.get('is_suspend', False)
            print(f"  - {name} {'(suspend)' if is_suspend else ''}")
        
        return True
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 开始测试 parser_v2")
    print()
    
    results = []
    
    # 运行测试
    results.append(("简单Kotlin代码", test_simple_kotlin()))
    results.append(("PermissionManager.kt", test_permission_manager()))
    results.append(("扩展函数", test_extension_functions()))
    
    # 总结
    print("\n" + "=" * 80)
    print("📋 测试结果总结")
    print("=" * 80)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    print()
    if all_passed:
        print("🎉 所有测试通过！parser_v2 工作正常！")
    else:
        print("⚠️ 部分测试失败，需要进一步调试。")
