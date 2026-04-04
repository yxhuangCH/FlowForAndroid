"""
测试 parser_v2 - 更多真实Kotlin文件测试
"""

import sys
import os
sys.path.insert(0, '/Users/yxhuang/code/AndroidDemo/flowforandroid/review_skill')

from ast_engine.parser_v2 import analyze_kotlin_file, parse_kotlin_ast
from ast_engine.nodes import NodeType


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


def test_file(filepath):
    """测试单个文件"""
    try:
        ast = analyze_kotlin_file(filepath)
        if ast is None:
            return None
        
        stats = count_nodes(ast)
        return stats
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


def main():
    print("🚀 测试 parser_v2 解析更多真实Kotlin文件")
    print()
    
    # 要测试的文件列表
    files = [
        "app/src/main/java/com/yxhuang/flowforandroid/MainActivity.kt",
        "app/src/main/java/com/yxhuang/flowforandroid/HomeViewModel.kt",
        "app/src/main/java/com/yxhuang/flowforandroid/FlowApplication.kt",
        "app/src/main/java/com/yxhuang/flowforandroid/permission/PermissionResult.kt",
        "app/src/main/java/com/yxhuang/flowforandroid/permission/PermissionExample.kt",
    ]
    
    results = []
    
    for filepath in files:
        full_path = f"/Users/yxhuang/code/AndroidDemo/flowforandroid/{filepath}"
        print(f"📄 测试: {filepath}")
        
        if not os.path.exists(full_path):
            print(f"   ⚠️ 文件不存在")
            continue
        
        stats = test_file(full_path)
        if stats:
            print(f"   ✅ 成功")
            print(f"      类: {stats['classes']}, 接口: {stats['interfaces']}", end="")
            print(f", 函数: {stats['functions']} (suspend: {stats['suspend_functions']})", end="")
            print(f", 属性: {stats['properties']}, companion: {stats['companion_objects']}")
            results.append((filepath, True, stats))
        else:
            print(f"   ❌ 失败")
            results.append((filepath, False, None))
        print()
    
    # 总结
    print("=" * 80)
    print("📋 测试结果总结")
    print("=" * 80)
    
    total_files = len(results)
    success_files = sum(1 for _, success, _ in results if success)
    
    print(f"总计: {total_files} 个文件")
    print(f"成功: {success_files} 个")
    print(f"失败: {total_files - success_files} 个")
    
    if success_files == total_files:
        print("\n🎉 所有文件解析成功！")
    
    return success_files == total_files


if __name__ == "__main__":
    main()
