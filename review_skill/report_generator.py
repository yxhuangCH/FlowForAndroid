#!/usr/bin/env python3
"""
HTML报告生成器
为代码审查结果生成可视化HTML报告
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class GitDiffParser:
    """解析git diff输出"""
    
    @staticmethod
    def parse(diff_text: str) -> List[Dict[str, Any]]:
        """
        解析git diff输出，返回文件变更列表
        
        格式示例：
        diff --git a/file1 b/file1
        index xxx..xxx
        --- a/file1
        +++ b/file1
        @@ -l,s +l,s @@
        - 删除的行
        + 新增的行
         不变的行
        """
        if not diff_text.strip():
            return []
        
        files = []
        current_file = None
        lines = diff_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检测新文件开始
            if line.startswith('diff --git'):
                if current_file:
                    files.append(current_file)
                
                # 提取文件名
                match = re.search(r'^diff --git a/(.+) b/(.+)$', line)
                if match:
                    old_file = match.group(1)
                    new_file = match.group(2)
                    
                    current_file = {
                        'old_path': old_file,
                        'new_path': new_file,
                        'hunks': [],
                        'package': GitDiffParser._extract_package(new_file),
                        'language': GitDiffParser._detect_language(new_file)
                    }
                i += 1
                
            # 检测hunk开始
            elif line.startswith('@@') and current_file:
                # 格式: @@ -old_start,old_len +new_start,new_len @@
                hunk_match = re.search(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if hunk_match:
                    old_start = int(hunk_match.group(1))
                    old_len = int(hunk_match.group(2) or 1)
                    new_start = int(hunk_match.group(3))
                    new_len = int(hunk_match.group(4) or 1)
                    
                    hunk = {
                        'old_start': old_start,
                        'old_len': old_len,
                        'new_start': new_start,
                        'new_len': new_len,
                        'lines': [],
                        'context': line  # 保留原始上下文行
                    }
                    
                    i += 1
                    # 读取hunk内容直到下一个@@或文件结束
                    while i < len(lines) and not lines[i].startswith('@@') and not lines[i].startswith('diff --git'):
                        hunk_line = lines[i]
                        line_type = 'context'
                        if hunk_line.startswith('+'):
                            line_type = 'added'
                            content = hunk_line[1:]
                        elif hunk_line.startswith('-'):
                            line_type = 'removed'
                            content = hunk_line[1:]
                        else:
                            content = hunk_line[1:] if hunk_line.startswith(' ') else hunk_line
                        
                        hunk['lines'].append({
                            'type': line_type,
                            'content': content,
                            'original': hunk_line
                        })
                        i += 1
                    
                    current_file['hunks'].append(hunk)
                else:
                    i += 1
            
            else:
                i += 1
        
        # 添加最后一个文件
        if current_file:
            files.append(current_file)
        
        return files
    
    @staticmethod
    def _extract_package(file_path: str) -> str:
        """从文件路径提取包名（适用于Java/Kotlin）"""
        # 查找src/main/java/后面的路径
        patterns = [
            r'src/main/java/(.+)\.(kt|java)$',
            r'src/(.+)\.(kt|java)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, file_path)
            if match:
                # 将路径分隔符替换为点
                package_path = match.group(1)
                return package_path.replace('/', '.')
        
        # 如果无法提取，返回文件路径
        return file_path
    
    @staticmethod
    def _detect_language(file_path: str) -> str:
        """根据文件扩展名检测编程语言"""
        ext = Path(file_path).suffix.lower()
        if ext == '.kt':
            return 'kotlin'
        elif ext == '.java':
            return 'java'
        elif ext == '.py':
            return 'python'
        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
            return 'javascript'
        elif ext == '.md':
            return 'markdown'
        elif ext in ['.xml', '.html']:
            return 'xml'
        else:
            return 'unknown'


class HTMLReportGenerator:
    """生成HTML报告"""
    
    @staticmethod
    def generate_report(
        diff_data: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        score: int,
        output_path: str = 'code_review_report.html'
    ) -> str:
        """生成HTML报告"""
        
        # 按包名分组文件
        files_by_package = {}
        for file_data in diff_data:
            package = file_data['package']
            if package not in files_by_package:
                files_by_package[package] = []
            files_by_package[package].append(file_data)
        
        # 将findings映射到文件
        findings_by_file = {}
        for finding in findings:
            # 根据规则推断可能相关的文件
            # TODO: 更精确的映射需要规则引擎支持
            file_path = HTMLReportGenerator._infer_file_from_finding(finding, diff_data)
            if file_path:
                if file_path not in findings_by_file:
                    findings_by_file[file_path] = []
                findings_by_file[file_path].append(finding)
        
        # 生成HTML
        html = HTMLReportGenerator._generate_html(
            files_by_package, 
            findings_by_file, 
            score,
            len(findings)
        )
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    @staticmethod
    def _infer_file_from_finding(finding: Dict[str, Any], diff_data: List[Dict[str, Any]]) -> Optional[str]:
        """根据finding推断相关的文件"""
        rule = finding.get('rule', '')
        message = finding.get('message', '')
        
        # 简单规则：查找包含特定关键词的文件
        keywords = {
            'no_globalscope': ['GlobalScope'],
            'viewmodel_context': ['ViewModel', 'Context'],
            'main_thread_io': ['Dispatchers.Main', 'repository'],
            'collect_without_repeat': ['collect', 'repeatOnLifecycle'],
        }
        
        for file_data in diff_data:
            file_path = file_data['new_path']
            # 检查文件内容是否包含相关关键词
            for hunk in file_data.get('hunks', []):
                for line in hunk.get('lines', []):
                    content = line.get('content', '')
                    # 根据规则类型检查关键词
                    for rule_pattern, key_list in keywords.items():
                        if rule == rule_pattern:
                            for keyword in key_list:
                                if keyword.lower() in content.lower():
                                    return file_path
        
        return None
    
    @staticmethod
    def _generate_html(
        files_by_package: Dict[str, List[Dict[str, Any]]],
        findings_by_file: Dict[str, List[Dict[str, Any]]],
        score: int,
        total_findings: int
    ) -> str:
        """生成HTML内容"""
        
        # 严重性颜色映射
        severity_colors = {
            'critical': '#dc3545',  # 红色
            'major': '#fd7e14',     # 橙色
            'minor': '#ffc107',     # 黄色
            'warning': '#17a2b8',   # 青色
            'info': '#28a745',      # 绿色
        }
        
        # 分数颜色
        if score >= 90:
            score_color = '#28a745'
            score_label = '优秀'
        elif score >= 70:
            score_color = '#ffc107'
            score_label = '良好'
        elif score >= 50:
            score_color = '#fd7e14'
            score_label = '一般'
        else:
            score_color = '#dc3545'
            score_label = '需要改进'
        
        # 当前时间
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>代码审查报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .header .meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1rem;
            font-size: 0.9rem;
            opacity: 0.9;
        }}
        
        .score-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
        }}
        
        .score-number {{
            font-size: 4rem;
            font-weight: bold;
            color: {score_color};
            line-height: 1;
            margin-bottom: 0.5rem;
        }}
        
        .score-label {{
            font-size: 1.2rem;
            color: #666;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .summary-item {{
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        
        .summary-number {{
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }}
        
        .summary-label {{
            font-size: 0.9rem;
            color: #666;
            margin-top: 0.25rem;
        }}
        
        .package-section {{
            margin-bottom: 2rem;
        }}
        
        .package-header {{
            background: #343a40;
            color: white;
            padding: 1rem;
            border-radius: 6px 6px 0 0;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .file-section {{
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 0 0 6px 6px;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        
        .file-header {{
            background: #f8f9fa;
            padding: 1rem;
            border-bottom: 1px solid #dee2e6;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .file-path {{
            color: #495057;
        }}
        
        .code-container {{
            overflow-x: auto;
        }}
        
        .code-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }}
        
        .code-table tr:hover {{
            background-color: #f8f9fa;
        }}
        
        .line-number {{
            width: 50px;
            text-align: right;
            padding: 2px 10px;
            color: #6c757d;
            border-right: 1px solid #dee2e6;
            user-select: none;
            background-color: #f8f9fa;
        }}
        
        .code-line {{
            padding: 2px 10px;
            white-space: pre;
        }}
        
        .line-added {{
            background-color: #d4edda;
        }}
        
        .line-removed {{
            background-color: #f8d7da;
        }}
        
        .line-problem {{
            background-color: #fff3cd;
            border-left: 3px solid #ffc107;
            position: relative;
        }}
        
        .problem-marker {{
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.8rem;
            font-weight: bold;
            color: white;
        }}
        
        .findings-panel {{
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 1.5rem;
            margin-top: 2rem;
        }}
        
        .finding-item {{
            padding: 1rem;
            border-left: 4px solid;
            margin-bottom: 1rem;
            background-color: #f8f9fa;
        }}
        
        .finding-severity {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.8rem;
            font-weight: bold;
            color: white;
            margin-right: 0.5rem;
        }}
        
        .finding-rule {{
            font-weight: bold;
            color: #495057;
        }}
        
        .finding-message {{
            margin-top: 0.5rem;
            color: #6c757d;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .score-number {{
                font-size: 3rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📋 代码审查报告</h1>
            <p>基于DeepSeek模型的智能代码质量分析</p>
            <div class="meta">
                <div>生成时间: {now}</div>
                <div>审查工具: Android代码审查技能</div>
            </div>
        </header>
        
        <div class="score-card">
            <div class="score-number">{score}/100</div>
            <div class="score-label" style="color: {score_color};">{score_label}</div>
        </div>
        
        <div class="summary">
            <div class="summary-item">
                <div class="summary-number">{len(files_by_package)}</div>
                <div class="summary-label">包数量</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{sum(len(files) for files in files_by_package.values())}</div>
                <div class="summary-label">文件数量</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{total_findings}</div>
                <div class="summary-label">发现问题</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{len([f for f in findings_by_file.values() if any(finding.get('severity') == 'critical' for finding in f)])}</div>
                <div class="summary-label">严重问题</div>
            </div>
        </div>
        
        {HTMLReportGenerator._generate_package_sections(files_by_package, findings_by_file)}
        
        {HTMLReportGenerator._generate_findings_section(findings_by_file, severity_colors)}
        
        <footer class="footer">
            <p>© {datetime.now().year} Android代码审查工具 | 使用DeepSeek模型进行语义分析</p>
            <p>报告生成时间: {now}</p>
        </footer>
    </div>
    
    <script>
        // 简单的交互功能
        document.addEventListener('DOMContentLoaded', function() {{
            // 点击文件头部切换代码显示
            document.querySelectorAll('.file-header').forEach(header => {{
                header.addEventListener('click', function() {{
                    const codeContainer = this.nextElementSibling;
                    if (codeContainer.style.display === 'none') {{
                        codeContainer.style.display = 'block';
                        this.querySelector('.toggle-icon').textContent = '▼';
                    }} else {{
                        codeContainer.style.display = 'none';
                        this.querySelector('.toggle-icon').textContent = '▶';
                    }}
                }});
                
                // 添加切换图标
                const toggleIcon = document.createElement('span');
                toggleIcon.className = 'toggle-icon';
                toggleIcon.textContent = '▼';
                toggleIcon.style.marginLeft = '10px';
                toggleIcon.style.cursor = 'pointer';
                this.appendChild(toggleIcon);
            }});
            
            // 高亮有问题的行
            document.querySelectorAll('.line-problem').forEach(line => {{
                line.addEventListener('mouseenter', function() {{
                    this.style.backgroundColor = '#ffeaa7';
                }});
                line.addEventListener('mouseleave', function() {{
                    this.style.backgroundColor = '#fff3cd';
                }});
            }});
        }});
    </script>
</body>
</html>'''
        return html
    
    @staticmethod
    def _generate_package_sections(files_by_package, findings_by_file):
        """生成包和文件部分的HTML"""
        sections = []
        
        for package, files in sorted(files_by_package.items()):
            package_html = f'''
            <section class="package-section">
                <div class="package-header">
                    <span>📁 {package}</span>
                    <span>{len(files)} 个文件</span>
                </div>'''
            
            for file_data in files:
                file_path = file_data['new_path']
                file_findings = findings_by_file.get(file_path, [])
                
                # 生成代码行
                code_lines = []
                current_line = 1
                
                for hunk in file_data.get('hunks', []):
                    hunk_start = hunk.get('new_start', 1)
                    
                    # 添加hunk上下文
                    code_lines.append({
                        'line_number': '...',
                        'content': f'// {hunk.get("context", "变更块")}',
                        'type': 'context',
                        'findings': []
                    })
                    
                    for line_data in hunk.get('lines', []):
                        line_type = line_data['type']
                        content = line_data['content']
                        
                        # 检查这一行是否有问题
                        line_findings = []
                        for finding in file_findings:
                            # 简单匹配：如果行内容包含相关关键词
                            rule = finding.get('rule', '')
                            if rule == 'no_globalscope' and 'GlobalScope' in content:
                                line_findings.append(finding)
                            elif rule == 'collect_without_repeat' and 'collect' in content and 'repeatOnLifecycle' not in content:
                                line_findings.append(finding)
                        
                        code_lines.append({
                            'line_number': current_line if line_type != 'removed' else '-',
                            'content': content,
                            'type': line_type,
                            'findings': line_findings
                        })
                        
                        if line_type != 'removed':
                            current_line += 1
                
                # 生成文件HTML
                file_html = f'''
                <div class="file-section">
                    <div class="file-header">
                        <span class="file-path">{file_path}</span>
                        <span>{len(file_findings)} 个问题</span>
                    </div>
                    <div class="code-container">
                        <table class="code-table">
                            {HTMLReportGenerator._generate_code_rows(code_lines)}
                        </table>
                    </div>
                </div>'''
                
                package_html += file_html
            
            package_html += '</section>'
            sections.append(package_html)
        
        return '\n'.join(sections)
    
    @staticmethod
    def _generate_code_rows(code_lines):
        """生成代码行的HTML"""
        rows = []
        
        for line_data in code_lines:
            line_number = line_data['line_number']
            content = line_data['content']
            line_type = line_data['type']
            findings = line_data['findings']
            
            # 转义HTML特殊字符
            content = content.replace('&', '&').replace('<', '<').replace('>', '>')
            
            # 确定行类
            line_class = ''
            if line_type == 'added':
                line_class = 'line-added'
            elif line_type == 'removed':
                line_class = 'line-removed'
            
            # 如果有问题，添加问题标记
            problem_html = ''
            if findings:
                line_class += ' line-problem'
                # 显示第一个问题的严重性
                severity = findings[0].get('severity', 'minor')
                severity_colors = {
                    'critical': '#dc3545',
                    'major': '#fd7e14',
                    'minor': '#ffc107',
                    'warning': '#17a2b8',
                    'info': '#28a745',
                }
                color = severity_colors.get(severity, '#ffc107')
                problem_html = f'<span class="problem-marker" style="background-color: {color};">{severity.upper()}</span>'
            
            rows.append(f'''
            <tr class="{line_class.strip()}">
                <td class="line-number">{line_number}</td>
                <td class="code-line">{content}{problem_html}</td>
            </tr>''')
        
        return '\n'.join(rows)
    
    @staticmethod
    def _generate_findings_section(findings_by_file, severity_colors):
        """生成问题列表部分的HTML"""
        if not findings_by_file:
            return '<div class="findings-panel"><p>🎉 没有发现问题！代码质量优秀。</p></div>'
        
        all_findings = []
        for file_path, findings in findings_by_file.items():
            for finding in findings:
                finding['file_path'] = file_path
                all_findings.append(finding)
        
        # 按严重性排序：critical > major > minor > warning > info
        severity_order = {'critical': 0, 'major': 1, 'minor': 2, 'warning': 3, 'info': 4}
        all_findings.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 4))
        
        findings_html = '<div class="findings-panel"><h3 style="margin-bottom: 1rem;">📝 发现问题列表</h3>'
        
        for finding in all_findings:
            severity = finding.get('severity', 'info')
            rule = finding.get('rule', 'unknown')
            message = finding.get('message', '')
            file_path = finding.get('file_path', '未知文件')
            
            color = severity_colors.get(severity, '#6c757d')
            
            findings_html += f'''
            <div class="finding-item" style="border-left-color: {color};">
                <div>
                    <span class="finding-severity" style="background-color: {color};">{severity.upper()}</span>
                    <span class="finding-rule">{rule}</span>
                    <span style="color: #6c757d; font-size: 0.9rem;"> - {file_path}</span>
                </div>
                <div class="finding-message">{message}</div>
            </div>'''
        
        findings_html += '</div>'
        return findings_html


def main():
    """测试函数"""
    # 读取测试数据
    import sys
    sys.path.append('.')
    
    # 模拟测试数据
    test_diff = '''diff --git a/app/src/main/java/com/yxhuang/flowforandroid/HomeViewModel.kt b/app/src/main/java/com/yxhuang/flowforandroid/HomeViewModel.kt
index ebfe86a..c2ad7ad 100644
--- a/app/src/main/java/com/yxhuang/flowforandroid/HomeViewModel.kt
+++ b/app/src/main/java/com/yxhuang/flowforandroid/HomeViewModel.kt
@@ -8,6 +8,17 @@ import kotlinx.coroutines.launch

 class HomeViewModel : ViewModel() {

+    init {
+        GlobalScope.launch {
+            val flow = (1..10).asFlow()
+            flow.collect {
+                println("collect $it")
+                delay(1000)
+            }
+        }
+    }
 
+    override fun onCleared() {
+        super.onCleared()
+    }
 }'''
    
    test_findings = [
        {
            "severity": "critical",
            "rule": "no_globalscope",
            "message": "GlobalScope is lifecycle unsafe."
        },
        {
            "severity": "minor", 
            "rule": "unspecified_scope",
            "message": "Coroutine launched without lifecycle scope."
        }
    ]
    
    # 解析diff
    diff_data = GitDiffParser.parse(test_diff)
    
    # 生成报告
    report_path = HTMLReportGenerator.generate_report(
        diff_data, test_findings, 65, 'test_report.html'
    )
    
    print(f"报告已生成: {report_path}")
    print(f"打开报告: open {report_path}")


if __name__ == "__main__":
    main()