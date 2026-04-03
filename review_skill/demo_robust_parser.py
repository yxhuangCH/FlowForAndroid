"""
演示：使用健壮的Kotlin解析器解析PermissionManager.kt

展示如何分析真实Kotlin代码的结构和模式
"""

import sys
import os
import re
sys.path.insert(0, '/Users/yxhuang/code/AndroidDemo/flowforandroid/review_skill')

from ast_engine.parser_robust import analyze_kotlin_patterns, RobustKotlinParser


def print_ast_simple(ast, indent=0):
    """简化版AST打印"""
    prefix = "  " * indent
    node_info = f"{ast.node_type}"
    
    if ast.metadata:
        if 'class_name' in ast.metadata:
            node_info += f" ({ast.metadata['class_name']})"
        elif 'function_name' in ast.metadata:
            node_info += f" ({ast.metadata['function_name']}"
            if ast.metadata.get('is_suspend'):
                node_info += " - suspend"
            node_info += ")"
        elif 'property_name' in ast.metadata:
            node_info += f" ({ast.metadata['property_name']}"
            if ast.metadata.get('is_mutable'):
                node_info += " - var"
            else:
                node_info += " - val"
            node_info += ")"
    
    print(f"{prefix}{node_info}")
    
    for child in ast.children:
        print_ast_simple(child, indent + 1)


def demo_permission_manager():
    """演示PermissionManager.kt的解析"""
    print("=" * 80)
    print("🔍 健壮Kotlin解析器演示")
    print("=" * 80)
    
    # 目标文件路径
    target_file = "/Users/yxhuang/code/AndroidDemo/flowforandroid/app/src/main/java/com/yxhuang/flowforandroid/permission/PermissionManager.kt"
    
    try:
        # 读取文件内容
        with open(target_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        print(f"📁 文件: {os.path.basename(target_file)}")
        print(f"📊 代码行数: {len(source_code.splitlines())}")
        print(f"📏 字符数: {len(source_code)}")
        print()
        
        # 使用健壮解析器分析
        print("🔄 正在分析代码结构...")
        result = analyze_kotlin_patterns(source_code)
        print("✅ 分析完成！")
        print()
        
        # 展示AST结构
        print("🌳 代码结构：")
        print("-" * 50)
        print_ast_simple(result['ast'])
        print()
        
        # 展示统计信息
        stats = result['stats']
        print("📈 代码统计：")
        print("-" * 30)
        print(f"📋 类/接口/对象: {stats['classes']}")
        print(f"⚙️  函数: {stats['functions']}")
        print(f"🔄 Suspend函数: {stats['suspend_functions']}")
        print(f"💾 属性: {stats['properties']}")
        print(f"📄 总行数: {stats['total_lines']}")
        print()
        
        # 展示代码模式分析
        findings = result['findings']
        print("🔍 代码模式分析：")
        print("-" * 30)
        
        if findings:
            for rule_name, matches in findings.items():
                print(f"⚠️  {rule_name}:")
                for match in matches:
                    print(f"   第{match['line']}行: {match['text'][:60]}...")
        else:
            print("✅ 未发现明显问题")
        
        print()
        
        # 展示具体代码片段
        print("📋 关键代码片段：")
        print("-" * 30)
        
        lines = source_code.splitlines()
        
        # 查找类定义
        for i, line in enumerate(lines):
            if 'class PermissionManager' in line:
                print(f"📋 类定义 (第{i+1}行):")
                print(f"   {line.strip()}")
                break
        
        # 查找suspend函数
        suspend_lines = [(i+1, line) for i, line in enumerate(lines) 
                        if 'suspend fun' in line]
        if suspend_lines:
            print(f"🔄 Suspend函数:")
            for line_num, line in suspend_lines[:3]:  # 显示前3个
                print(f"   第{line_num}行: {line.strip()}")
        
        # 查找伴生对象
        companion_lines = [(i+1, line) for i, line in enumerate(lines) 
                          if 'companion object' in line]
        if companion_lines:
            print(f"🏠 伴生对象:")
            for line_num, line in companion_lines:
                print(f"   第{line_num}行: {line.strip()}")
        
        # 查找属性声明
        property_lines = [(i+1, line) for i, line in enumerate(lines) 
                         if re.search(r'\b(val|var)\s+\w+', line) and 
                         not line.strip().startswith('//')]
        if property_lines:
            print(f"💾 属性声明:")
            for line_num, line in property_lines[:5]:  # 显示前5个
                print(f"   第{line_num}行: {line.strip()}")
        
        return result
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_rule_integration():
    """演示规则集成"""
    print("=" * 80)
    print("🎯 规则集成演示")
    print("=" * 80)
    
    target_file = "/Users/yxhuang/code/AndroidDemo/flowforandroid/app/src/main/java/com/yxhuang/flowforandroid/permission/PermissionManager.kt"
    
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # 定义检查规则
        rules = {
            'coroutine_scope': [
                r'GlobalScope\.launch',
                r'launch\s*\{',
                r'withContext\s*\(',
            ],
            'context_leak': [
                r'val.*Activity.*Context',
                r'var.*Activity.*Context',
                r'lateinit\s+var.*Context',
            ],
            'naming_convention': [
                r'fun\s+[A-Z]\w*',
                r'suspend\s+fun\s+[A-Z]\w*',
            ],
            'error_handling': [
                r'try\s*\{',
                r'catch\s*\(',
                r'finally\s*\{',
            ]
        }
        
        parser = RobustKotlinParser(source_code)
        
        print("🔍 应用规则检查...")
        for rule_name, patterns in rules.items():
            findings = parser.find_patterns(patterns)
            if findings:
                print(f"\n⚠️  {rule_name.upper()}:")
                for finding in findings[:3]:  # 显示前3个
                    print(f"   第{finding['line']}行: {finding['text']}")
            else:
                print(f"✅ {rule_name.upper()}: 无问题")
        
    except Exception as e:
        print(f"❌ 规则检查失败: {e}")


if __name__ == "__main__":
    # 演示PermissionManager.kt解析
    result = demo_permission_manager()
    
    if result:
        print()
        print("=" * 80)
        print("🎉 健壮解析器演示完成！")
        print()
        print("✨ 特点：")
        print("  • 零依赖，纯Python实现")
        print("  • 处理复杂真实代码")
        print("  • 支持代码审查规则")
        print("  • 精确定位问题行")
        print("  • 易于扩展和定制")
        print()
        print("🚀 可以集成到review_skill系统中！")
    
    # 演示规则集成
    demo_rule_integration()