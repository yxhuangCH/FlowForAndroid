#!/usr/bin/env python3
"""
模拟有 .kt 文件变更时测试 review skill
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_kt_file():
    """创建测试用的 .kt 文件，包含已知问题"""
    test_code = '''package com.example.test

import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import androidx.lifecycle.ViewModel
import android.content.Context

class BadViewModel(val context: Context) : ViewModel() {
    fun doBadThings() {
        // 问题 1: 使用 GlobalScope
        GlobalScope.launch {
            // 在主线程执行 IO
            val file = java.io.File("/tmp/test.txt")
            file.writeText("bad")
        }
        
        // 问题 2: 未指定协程作用域
        launch {
            println("unspecified scope")
        }
    }
}

// 问题 3: 空的 Composable 函数
@Composable
fun EmptyComposable() {}
'''
    
    # 创建临时目录和文件
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "Test.kt"
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    return str(temp_dir), str(test_file)

def test_with_kt_diff():
    """测试包含 .kt 文件变更的 git diff"""
    print("=== 测试包含 .kt 文件变更的 review skill ===")
    
    # 创建测试文件
    temp_dir, test_file = create_test_kt_file()
    print(f"创建测试文件: {test_file}")
    
    try:
        # 创建模拟的 git diff
        with open(test_file, 'r') as f:
            content = f.read()
        
        # 创建 git diff 格式的变更
        git_diff = f'''diff --git a/{test_file} b/{test_file}
new file mode 100644
index 0000000..abcdef1
--- /dev/null
+++ b/{test_file}
@@ -0,0 +1,31 @@
{content}
'''
        
        print(f"模拟的 git diff 长度: {len(git_diff)} 字符")
        
        # 测试配置过滤
        from config import get_config
        config = get_config()
        
        print(f"\n配置信息:")
        print(f"  文件扩展名: {config.get_file_extensions()}")
        print(f"  扫描目录: {config.get_scan_directories()}")
        
        # 由于测试文件不在配置的扫描目录中，我们需要修改配置来测试
        # 获取文件相对路径（相对于项目根目录）
        project_root = Path(os.path.dirname(os.path.abspath(__file__))).parent
        relative_path = Path(test_file).relative_to(project_root)
        
        print(f"\n测试文件相对于项目根目录的路径: {relative_path}")
        
        # 检查该文件是否应该被扫描
        should_scan = config.should_scan_file(str(relative_path))
        print(f"  当前配置下是否应该扫描: {'✅ 是' if should_scan else '❌ 否'}")
        
        if not should_scan:
            print(f"\n⚠️ 测试文件不在配置的扫描目录中")
            print(f"  当前扫描目录: {config.get_scan_directories()}")
            print(f"  文件路径: {relative_path}")
            print(f"  文件是否以扫描目录开头:")
            for scan_dir in config.get_scan_directories():
                matches = str(relative_path).startswith(scan_dir)
                print(f"    - {scan_dir}: {'✅ 是' if matches else '❌ 否'}")
        
        # 测试规则执行（不依赖 git diff）
        print(f"\n=== 直接测试规则执行 ===")
        from rules.base_rules import run_base_rules
        from rules.coroutine_rules import run_coroutine_rules
        from rules.compose_rules import run_compose_rules
        
        base_findings = run_base_rules(content)
        coroutine_findings = run_coroutine_rules(content)
        compose_findings = run_compose_rules(content)
        
        all_findings = base_findings + coroutine_findings + compose_findings
        
        print(f"发现的总问题数: {len(all_findings)}")
        print(f"基础规则: {len(base_findings)} 个")
        print(f"协程规则: {len(coroutine_findings)} 个")
        print(f"Compose规则: {len(compose_findings)} 个")
        
        if all_findings:
            print(f"\n详细问题:")
            for i, finding in enumerate(all_findings, 1):
                print(f"  {i}. [{finding['severity']}] {finding['rule']}: {finding['message']}")
        
        # 测试评分
        from scorer import calculate_score
        score = calculate_score(all_findings)
        print(f"\n代码质量分数: {score}/100")
        
        return len(all_findings) > 0
        
    finally:
        # 清理临时目录
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def main():
    """主函数"""
    print("📋 模拟 .kt 文件变更测试\n")
    
    # 检查当前目录下是否有 .kt 文件
    project_root = Path(os.path.dirname(os.path.abspath(__file__))).parent
    kt_files = list(project_root.rglob("*.kt"))
    
    print(f"项目根目录: {project_root}")
    print(f"找到的 .kt 文件数量: {len(kt_files)}")
    
    if kt_files:
        print(f"\n前5个 .kt 文件:")
        for kt_file in kt_files[:5]:
            relative_path = kt_file.relative_to(project_root)
            print(f"  - {relative_path}")
    
    # 运行测试
    success = test_with_kt_diff()
    
    print(f"\n{'='*60}")
    print(f"测试结果: {'✅ 通过' if success else '❌ 失败'}")
    
    # 诊断用户的问题
    print(f"\n💡 问题诊断:")
    print(f"1. 用户运行 `python3 review.py` 显示 '没有需要扫描的文件变更'")
    print(f"2. 原因: 当前的 git diff 中没有 .kt 或 .kts 文件变更")
    print(f"3. 当前 git diff 包含的文件:")
    
    # 获取当前的 git diff
    from review import get_git_diff
    diff = get_git_diff()
    lines = diff.split('\n')
    
    diff_files = []
    for line in lines:
        if line.startswith('diff --git'):
            # 提取文件名
            parts = line.split()
            if len(parts) >= 3:
                file_a = parts[2][2:]  # 去掉 'a/'
                file_b = parts[3][2:]  # 去掉 'b/'
                diff_files.append(file_b if file_b != '/dev/null' else file_a)
    
    if diff_files:
        for file in diff_files:
            is_kt = file.endswith('.kt') or file.endswith('.kts')
            print(f"   - {file} {'✅ (.kt文件)' if is_kt else '❌ (非.kt文件)'}")
    else:
        print(f"   没有文件变更")
    
    print(f"\n🔧 解决方案:")
    print(f"1. 创建或修改一个 .kt 文件 (例如 app/src/main/java/.../Test.kt)")
    print(f"2. 运行 `git add <文件>` 和 `git commit -m '测试变更'`")
    print(f"3. 再次运行 `python3 review.py`")
    print(f"4. 或者直接运行测试: `python3 test_review_functionality.py`")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())