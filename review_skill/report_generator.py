#!/usr/bin/env python3
"""
HTML Report Generator
Generates visual HTML reports for code review results
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class GitDiffParser:
    """Parses git diff output"""
    
    @staticmethod
    def parse(diff_text: str) -> List[Dict[str, Any]]:
        """
        Parses git diff output, returns list of file changes
        
        Format Example:
        diff --git a/file1 b/file1
        index xxx..xxx
        --- a/file1
        +++ b/file1
        @@ -l,s +l,s @@
        - Deleted lines
        + Added lines
         Unchanged lines
        """
        if not diff_text.strip():
            return []
        
        files = []
        current_file = None
        lines = diff_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Detect new file start
            if line.startswith('diff --git'):
                if current_file:
                    files.append(current_file)
                
                # Extract filename
                match = re.search(r'^diff --git a/(.+) b(.+)$', line)
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
                
            # Detect hunk start
            elif line.startswith('@@') and current_file:
                # Format: @@ -old_start,old_len +new_start,new_len @@
                hunk_match = re.search(r'@@ -(\d+)(?,(\d+))? \+(\d+)(?,(\d+))? @@', line)
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
                        'context': line  # Keep original context line
                    }
                    
                    i += 1
                    # Read hunk content until next @@ or end of file
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
        
        # Add last file
        if current_file:
            files.append(current_file)
        
        return files
    
    @staticmethod
    def _extract_package(file_path: str) -> str:
        """Extracts package name from file path (for Java/Kotlin)"""
        # Find path after src/main/java/
        patterns = [
            r'src/main/java/(.+)\.(kt|java)$',
            r'src/(.+)\.(kt|java)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, file_path)
            if match:
                # Replace path separators with dots
                package_path = match.group(1)
                return package_path.replace('/', '.')
        
        # If cannot extract, return file path
        return file_path
    
    @staticmethod
    def _detect_language(file_path: str) -> str:
        """Detects programming language based on file extension"""
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
    """Generates HTML reports"""
    
    # Rule to refer file mapping
    RULE_REFER_MAPPING = {
        # Base rules
        'no_globalscope': 'no_globalscope_refer.kt',
        'viewmodel_context': 'viewmodel_context_refer.kt',
        
        # Coroutine rules
        'main_thread_io': 'main_thread_io_refer.kt',
        'unspecified_scope': 'unspecified_scope_refer.kt',
        
        # Compose rules
        'launched_effect_unit': 'launched_effect_unit_refer.kt',
        'remember_context': 'remember_context_refer.kt',
        
        # Flow rules
        'flowon_main_dispatcher': 'flowon_main_dispatcher_refer.kt',
        'missing_flowon': 'flowon_main_dispatcher_refer.kt',  # Uses same refer
        'channel_flow_usage': 'flowon_main_dispatcher_refer.kt',  # Uses same refer
        'eager_sharing_detected': 'flowon_main_dispatcher_refer.kt',  # Uses same refer
        'mutable_stateflow_exposed': 'flowon_main_dispatcher_refer.kt',  # Uses same refer
        
        # Flow lifecycle rules
        'statein_globalscope': 'no_globalscope_refer.kt',  # Similar global scope issue
        'sharein_globalscope': 'no_globalscope_refer.kt',  # Similar global scope issue
        'collect_without_repeat': 'flowon_main_dispatcher_refer.kt',  # Flow lifecycle management
        'statein_without_viewmodelscope': 'unspecified_scope_refer.kt',  # Scope issue
        
        # Flow structure rules
        'nested_launch_in_collect': 'flowon_main_dispatcher_refer.kt',  # Flow structured concurrency
        'launch_inside_flow': 'flowon_main_dispatcher_refer.kt',  # Flow structured concurrency
        'multiple_collects': 'flowon_main_dispatcher_refer.kt',  # Flow usage pattern
        'channel_flow_no_awaitclose': 'flowon_main_dispatcher_refer.kt',  # channelFlow correct usage
        
        # Dagger2/Hilt rules
        'singleton_activity': 'viewmodel_context_refer.kt',  # Similar dependency injection issue
        'singleton_component_inject_activity': 'viewmodel_context_refer.kt',  # DI lifecycle
        'field_injection_detected': 'viewmodel_context_refer.kt',  # DI best practice
        'provides_without_scope': 'viewmodel_context_refer.kt',  # DI scope
    }
    
    @staticmethod
    def generate_report(
        diff_data: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        score: int,
        output_path: str = 'code_review_report.html'
    ) -> str:
        """Generates HTML report"""
        
        # Group files by package
        files_by_package = {}
        for file_data in diff_data:
            package = file_data['package']
            if package not in files_by_package:
                files_by_package[package] = []
            files_by_package[package].append(file_data)
        
        # Map findings to files
        findings_by_file = {}
        for finding in findings:
            # Infer potentially related files based on rules
            # TODO: More precise mapping requires rule engine support
            file_path = HTMLReportGenerator._infer_file_from_finding(finding, diff_data)
            if file_path:
                if file_path not in findings_by_file:
                    findings_by_file[file_path] = []
                findings_by_file[file_path].append(finding)
        
        # Copy refer_examples to report directory
        report_dir = os.path.dirname(output_path)
        if report_dir:
            HTMLReportGenerator._copy_refer_examples_to_report(report_dir)
        
        # Generate HTML
        html = HTMLReportGenerator._generate_html(
            files_by_package, 
            findings_by_file, 
            score,
            len(findings),
            report_dir
        )
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    @staticmethod
    def _copy_refer_examples_to_report(report_dir: str):
        """Copies refer_examples directory to report directory"""
        import shutil
        
        # Get absolute path of current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        source_dir = os.path.join(script_dir, 'refer_examples')
        target_dir = os.path.join(report_dir, 'refer_examples')
        
        print(f"🔍 Copying refer files - Source: {source_dir}")
        print(f"🔍 Copying refer files - Target: {target_dir}")
        
        if not os.path.exists(source_dir):
            print(f"⚠ refer_examples directory not found: {source_dir}")
            # Try to find in current working directory
            cwd = os.getcwd()
            alt_source_dir = os.path.join(cwd, 'refer_examples')
            if os.path.exists(alt_source_dir):
                print(f"🔍 Using alternative source directory: {alt_source_dir}")
                source_dir = alt_source_dir
            else:
                return
        
        # Create target directory
        os.makedirs(target_dir, exist_ok=True)
        
        # Copy all .kt files
        files_copied = 0
        for filename in os.listdir(source_dir):
            if filename.endswith('.kt'):
                source_file = os.path.join(source_dir, filename)
                target_file = os.path.join(target_dir, filename)
                try:
                    shutil.copy2(source_file, target_file)
                    print(f"✓ Copied refer file: {filename}")
                    files_copied += 1
                except Exception as e:
                    print(f"✗ Failed to copy file {filename}: {e}")
        
        print(f"📦 Total {files_copied} refer files copied to report directory")
    
    @staticmethod
    def _infer_file_from_finding(finding: Dict[str, Any], diff_data: List[Dict[str, Any]]) -> Optional[str]:
        """Infers related files from finding"""
        rule = finding.get('rule', '')
        message = finding.get('message', '')
        
        # Simple rule: find files containing specific keywords
        keywords = {
            'no_globalscope': ['GlobalScope'],
            'viewmodel_context': ['ViewModel', 'Context'],
            'main_thread_io': ['Dispatchers.Main', 'repository'],
            'collect_without_repeat': ['collect', 'repeatOnLifecycle'],
        }
        
        for file_data in diff_data:
            file_path = file_data['new_path']
            # Check if file content contains related keywords
            for hunk in file_data.get('hunks', []):
                for line in hunk.get('lines', []):
                    content = line.get('content', '')
                    # Check keywords based on rule type
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
        total_findings: int,
        report_dir: str = ''
    ) -> str:
        """Generates HTML content"""
        
        # Calculate base path for refer files
        if report_dir:
            refer_base_path = 'refer_examples/'
        else:
            refer_base_path = '../refer_examples/'
        
        # Severity color mapping
        severity_colors = {
            'critical': '#dc3545',  # Red
            'major': '#fd7e14',     # Orange
            'minor': '#ffc107',     # Yellow
            'warning': '#17a2b8',   # Cyan
            'info': '#28a745',      # Green
        }
        
        # Score color
        if score >= 90:
            score_color = '#28a745'
            score_label = 'Excellent'
        elif score >= 70:
            score_color = '#ffc107'
            score_label = 'Good'
        elif score >= 50:
            score_color = '#fd7e14'
            score_label = 'Average'
        else:
            score_color = '#dc3545'
            score_label = 'Needs Improvement'
        
        # Current time
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Review Report</title>
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
            <h1>📋 Code Review Report</h1>
            <p>Intelligent code quality analysis based on DeepSeek model</p>
            <div class="meta">
                <div>Generated: {now}</div>
                <div>Review Tool: Android Code Review Skill</div>
            </div>
        </header>
        
        <div class="score-card">
            <div class="score-number">{score}/100</div>
            <div class="score-label" style="color: {score_color};">{score_label}</div>
        </div>
        
        <div class="summary">
            <div class="summary-item">
                <div class="summary-number">{len(files_by_package)}</div>
                <div class="summary-label">Packages</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{sum(len(files) for files in files_by_package.values())}</div>
                <div class="summary-label">Files</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{total_findings}</div>
                <div class="summary-label">Issues Found</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{len([f for f in findings_by_file.values() if any(finding.get('severity') == 'critical' for finding in f)])}</div>
                <div class="summary-label">Critical Issues</div>
            </div>
        </div>
        
        {HTMLReportGenerator._generate_package_sections(files_by_package, findings_by_file)}
        
        {HTMLReportGenerator._generate_findings_section(findings_by_file, severity_colors, report_dir)}
        
        <footer class="footer">
            <p>© {datetime.now().year} Android Code Review Tool | Semantic analysis using DeepSeek model</p>
            <p>Report generated: {now}</p>
        </footer>
    </div>
    
    <script>
        // Simple interaction features
        document.addEventListener('DOMContentLoaded', function() {{
            // Toggle code display when clicking file header
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
                
                // Add toggle icon
                const toggleIcon = document.createElement('span');
                toggleIcon.className = 'toggle-icon';
                toggleIcon.textContent = '▼';
                toggleIcon.style.marginLeft = '10px';
                toggleIcon.style.cursor = 'pointer';
                this.appendChild(toggleIcon);
            }});
            
            // Highlight problematic lines
            document.querySelectorAll('.line-problem').forEach(line => {{
                line.addEventListener('mouseenter', function() {{
                    this.style.backgroundColor = '#ffeaa7';
                }});
                line.addEventListener('mouseleave', function() {{
                    this.style.backgroundColor = '#fff3cd';
                }});
            }});
            
            // Toggle refer code example display
            document.querySelectorAll('.toggle-refer-btn').forEach(button => {{
                button.addEventListener('click', function() {{
                    const targetId = this.getAttribute('data-target');
                    const codeContainer = document.getElementById(targetId);
                    const toggleIcon = this.querySelector('.toggle-icon');
                    
                    if (codeContainer.style.display === 'none' || codeContainer.style.display === '') {{
                        codeContainer.style.display = 'block';
                        toggleIcon.textContent = '▼';
                        this.style.backgroundColor = '#007bff';
                        this.style.color = 'white';
                    }} else {{
                        codeContainer.style.display = 'none';
                        toggleIcon.textContent = '▶';
                        this.style.backgroundColor = '';
                        this.style.color = '#007bff';
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>'''
        return html
    
    @staticmethod
    def _generate_package_sections(files_by_package, findings_by_file):
        """Generates HTML for package and file sections"""
        sections = []
        
        for package, files in sorted(files_by_package.items()):
            package_html = f'''
            <section class="package-section">
                <div class="package-header">
                    <span>📁 {package}</span>
                    <span>{len(files)} files</span>
                </div>'''
            
            for file_data in files:
                file_path = file_data['new_path']
                file_findings = findings_by_file.get(file_path, [])
                
                # Generate code lines
                code_lines = []
                current_line = 1
                
                for hunk in file_data.get('hunks', []):
                    hunk_start = hunk.get('new_start', 1)
                    
                    # Add hunk context
                    code_lines.append({
                        'line_number': '...',
                        'content': f'// {hunk.get("context", "Change block")}',
                        'type': 'context',
                        'findings': []
                    })
                    
                    for line_data in hunk.get('lines', []):
                        line_type = line_data['type']
                        content = line_data['content']
                        
                        # Check if this line has issues
                        line_findings = []
                        for finding in file_findings:
                            # Simple match: if line content contains related keywords
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
                
                # Generate file HTML
                file_html = f'''
                <div class="file-section">
                    <div class="file-header">
                        <span class="file-path">{file_path}</span>
                        <span>{len(file_findings)} issues</span>
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
        """Generates HTML for code lines"""
        rows = []
        
        for line_data in code_lines:
            line_number = line_data['line_number']
            content = line_data['content']
            line_type = line_data['type']
            findings = line_data['findings']
            
            # Escape HTML special characters
            content = HTMLReportGenerator._escape_html(content)
            
            # Determine line class
            line_class = ''
            if line_type == 'added':
                line_class = 'line-added'
            elif line_type == 'removed':
                line_class = 'line-removed'
            
            # If there are issues, add problem marker
            problem_html = ''
            if findings:
                line_class += ' line-problem'
                # Display severity of first issue
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
    def _escape_html(text: str) -> str:
        """Escapes HTML special characters"""
        return (text.replace('&', '&')
                    .replace('<', '<')
                    .replace('>', '>')
                    .replace('"', '"')
                    .replace("'", '&#039;'))
    
    @staticmethod
    def _read_refer_file_content(refer_file_path: str) -> Optional[str]:
        """Reads refer file content, returns None if file does not exist"""
        try:
            if os.path.exists(refer_file_path):
                with open(refer_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Try to find in current directory's refer_examples
            cwd = os.getcwd()
            alt_path = os.path.join(cwd, 'refer_examples', os.path.basename(refer_file_path))
            if os.path.exists(alt_path):
                with open(alt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Try to find in script directory's refer_examples
            script_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(script_dir, 'refer_examples', os.path.basename(refer_file_path))
            if os.path.exists(script_path):
                with open(script_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            return None
        except Exception as e:
            print(f"⚠ Failed to read refer file {refer_file_path}: {e}")
            return None
    
    @staticmethod
    def _generate_findings_section(findings_by_file, severity_colors, report_dir=''):
        """Generates HTML for findings list section"""
        if not findings_by_file:
            return '<div class="findings-panel"><p>🎉 No issues found! Excellent code quality.</p></div>'
        
        all_findings = []
        for file_path, findings in findings_by_file.items():
            for finding in findings:
                finding['file_path'] = file_path
                all_findings.append(finding)
        
        # Sort by severity: critical > major > minor > warning > info
        severity_order = {'critical': 0, 'major': 1, 'minor': 2, 'warning': 3, 'info': 4}
        all_findings.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 4))
        
        findings_html = '<div class="findings-panel"><h3 style="margin-bottom: 1rem;">📝 Issues Found</h3>'
        
        for finding_index, finding in enumerate(all_findings):
            severity = finding.get('severity', 'info')
            rule = finding.get('rule', 'unknown')
            message = finding.get('message', '')
            file_path = finding.get('file_path', 'Unknown file')
            
            color = severity_colors.get(severity, '#6c757d')
            
            # Get refer file content
            refer_content_html = ''
            refer_file = HTMLReportGenerator.RULE_REFER_MAPPING.get(rule)
            if refer_file:
                # Try multiple ways to find refer file
                refer_paths_to_try = []
                
                # 1. refer_examples in report directory
                if report_dir:
                    refer_paths_to_try.append(os.path.join(report_dir, 'refer_examples', refer_file))
                
                # 2. refer_examples in current working directory
                cwd = os.getcwd()
                refer_paths_to_try.append(os.path.join(cwd, 'refer_examples', refer_file))
                
                # 3. refer_examples in script directory
                script_dir = os.path.dirname(os.path.abspath(__file__))
                refer_paths_to_try.append(os.path.join(script_dir, 'refer_examples', refer_file))
                
                refer_content = None
                for refer_path in refer_paths_to_try:
                    if os.path.exists(refer_path):
                        try:
                            with open(refer_path, 'r', encoding='utf-8') as f:
                                refer_content = f.read()
                            break
                        except Exception:
                            continue
                
                if refer_content:
                    # All examples expanded by default
                    default_expanded = True
                    display_style = 'block' if default_expanded else 'none'
                    toggle_icon = '▼' if default_expanded else '▶'
                    
                    # Escape HTML and add syntax highlighting classes
                    escaped_content = HTMLReportGenerator._escape_html(refer_content)
                    refer_content_html = f'''
                    <div class="refer-code-container" id="refer-code-{finding_index}" style="display: {display_style}; margin-top: 1rem;">
                        <div class="refer-header" style="background: #f1f3f5; padding: 0.5rem 1rem; border-radius: 4px 4px 0 0; font-weight: bold; font-size: 0.9rem; color: #495057;">
                            📄 Correct Code Example: {refer_file}
                        </div>
                        <pre class="refer-code" style="margin: 0; padding: 1rem; background: #f8f9fa; border-radius: 0 0 4px 4px; overflow-x: auto; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 0.85rem; line-height: 1.4; color: #212529; border: 1px solid #dee2e6; border-top: none; max-height: 400px; overflow-y: auto;">
{escaped_content}
                        </pre>
                    </div>'''
            
            # Generate refer link and toggle button
            refer_link_html = ''
            if refer_file:
                # All examples expanded by default
                default_expanded = True
                toggle_icon = '▼' if default_expanded else '▶'
                button_style = 'background: #007bff; color: white;' if default_expanded else 'background: none; color: #007bff;'
                
                refer_link_html = f'''
                <div style="margin-top: 0.5rem; font-size: 0.9rem;">
                    <button class="toggle-refer-btn" data-target="refer-code-{finding_index}" style="{button_style} border: 1px solid #007bff; padding: 0.25rem 0.75rem; border-radius: 4px; cursor: pointer; font-size: 0.85rem; transition: all 0.2s;">
                        📖 View Correct Code Example <span class="toggle-icon">{toggle_icon}</span>
                    </button>
                </div>'''
            
            findings_html += f'''
            <div class="finding-item" style="border-left-color: {color};">
                <div>
                    <span class="finding-severity" style="background-color: {color};">{severity.upper()}</span>
                    <span class="finding-rule">{rule}</span>
                    <span style="color: #6c757d; font-size: 0.9rem;"> - {file_path}</span>
                </div>
                <div class="finding-message">{message}</div>
                {refer_link_html}
                {refer_content_html}
            </div>'''
        
        findings_html += '</div>'
        return findings_html


def main():
    """Main function"""
    # Read test data
    import sys
    sys.path.append('.')
    
    # Mock test data
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
    
    # Parse diff
    diff_data = GitDiffParser.parse(test_diff)
    
    # Generate report
    report_path = HTMLReportGenerator.generate_report(
        diff_data, test_findings, 65, 'test_report.html'
    )
    
    print(f"Report generated: {report_path}")
    print(f"Open report: open {report_path}")


if __name__ == "__main__":
    main()
