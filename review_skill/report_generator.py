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
                hunk_match = re.search(r'@@ -(\d+)(?:(\d+))? \+(\d+)(?:(\d+))? @@', line)
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
        'missing_flowon': 'flowon_main_dispatcher_refer.kt',
        'channel_flow_usage': 'flowon_main_dispatcher_refer.kt',
        'eager_sharing_detected': 'flowon_main_dispatcher_refer.kt',
        'mutable_stateflow_exposed': 'flowon_main_dispatcher_refer.kt',
        
        # Flow lifecycle rules
        'statein_globalscope': 'no_globalscope_refer.kt',
        'sharein_globalscope': 'no_globalscope_refer.kt',
        'collect_without_repeat': 'flowon_main_dispatcher_refer.kt',
        'statein_without_viewmodelscope': 'unspecified_scope_refer.kt',
        
        # Flow structure rules
        'nested_launch_in_collect': 'flowon_main_dispatcher_refer.kt',
        'launch_inside_flow': 'flowon_main_dispatcher_refer.kt',
        'multiple_collects': 'flowon_main_dispatcher_refer.kt',
        'channel_flow_no_awaitclose': 'flowon_main_dispatcher_refer.kt',
        
        # Dagger2/Hilt rules
        'singleton_activity': 'viewmodel_context_refer.kt',
        'singleton_component_inject_activity': 'viewmodel_context_refer.kt',
        'field_injection_detected': 'viewmodel_context_refer.kt',
        'provides_without_scope': 'viewmodel_context_refer.kt',
    }
    
    # LLM Category display configuration
    LLM_CATEGORY_CONFIG = {
        'single_responsibility': {
            'icon': '🔹',
            'title': 'Single Responsibility Violations',
            'description': 'Classes or functions with too many responsibilities'
        },
        'excessive_coupling': {
            'icon': '🔗',
            'title': 'Excessive Coupling Issues',
            'description': 'High dependencies between components'
        },
        'difficulty_in_unit_testing': {
            'icon': '🧪',
            'title': 'Unit Testing Difficulties',
            'description': 'Code that is hard to test in isolation'
        }
    }
    
    @staticmethod
    def generate_report(
        diff_data: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        score: int,
        output_path: str = 'code_review_report.html',
        llm_semantic_results: Optional[List[Dict[str, Any]]] = None
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
            file_path = finding.get('file_path')
            if not file_path:
                file_path = HTMLReportGenerator._infer_file_from_finding(finding, diff_data)
            
            if not file_path and diff_data:
                file_path = diff_data[0]['new_path']
            
            if not file_path:
                file_path = 'unknown_file.kt'
            
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
            report_dir,
            llm_semantic_results
        )
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    @staticmethod
    def _copy_refer_examples_to_report(report_dir: str):
        """Copies refer_examples directory to report directory"""
        import shutil
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        source_dir = os.path.join(script_dir, 'refer_examples')
        target_dir = os.path.join(report_dir, 'refer_examples')
        
        if not os.path.exists(source_dir):
            cwd = os.getcwd()
            alt_source_dir = os.path.join(cwd, 'refer_examples')
            if os.path.exists(alt_source_dir):
                source_dir = alt_source_dir
            else:
                return
        
        os.makedirs(target_dir, exist_ok=True)
        
        for filename in os.listdir(source_dir):
            if filename.endswith('.kt'):
                source_file = os.path.join(source_dir, filename)
                target_file = os.path.join(target_dir, filename)
                try:
                    shutil.copy2(source_file, target_file)
                except Exception:
                    pass
    
    @staticmethod
    def _infer_file_from_finding(finding: Dict[str, Any], diff_data: List[Dict[str, Any]]) -> Optional[str]:
        """Infers related files from finding"""
        rule = finding.get('rule', '')
        
        keywords = {
            'no_globalscope': ['GlobalScope'],
            'viewmodel_context': ['ViewModel', 'Context'],
            'main_thread_io': ['Dispatchers.Main', 'repository'],
            'collect_without_repeat': ['collect', 'repeatOnLifecycle'],
        }
        
        for file_data in diff_data:
            file_path = file_data['new_path']
            for hunk in file_data.get('hunks', []):
                for line in hunk.get('lines', []):
                    content = line.get('content', '')
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
        report_dir: str = '',
        llm_semantic_results: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generates HTML content"""
        
        severity_colors = {
            'critical': '#dc3545',
            'major': '#fd7e14',
            'minor': '#ffc107',
            'warning': '#17a2b8',
            'info': '#28a745',
        }
        
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
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Review Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background-color: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        .header .meta {{ display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; font-size: 0.9rem; opacity: 0.9; }}
        .score-card {{ background: white; padding: 1.5rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); margin-bottom: 2rem; }}
        .score-number {{ font-size: 4rem; font-weight: bold; color: {score_color}; line-height: 1; margin-bottom: 0.5rem; }}
        .score-label {{ font-size: 1.2rem; color: #666; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .summary-item {{ background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); text-align: center; }}
        .summary-number {{ font-size: 2rem; font-weight: bold; color: #667eea; }}
        .summary-label {{ font-size: 0.9rem; color: #666; margin-top: 0.25rem; }}
        .package-section {{ margin-bottom: 2rem; }}
        .package-header {{ background: #343a40; color: white; padding: 1rem; border-radius: 6px 6px 0 0; font-weight: bold; display: flex; justify-content: space-between; align-items: center; }}
        .file-section {{ background: white; border: 1px solid #dee2e6; border-radius: 0 0 6px 6px; margin-bottom: 1.5rem; overflow: hidden; }}
        .file-header {{ background: #f8f9fa; padding: 1rem; border-bottom: 1px solid #dee2e6; font-family: 'Courier New', monospace; font-weight: bold; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }}
        .file-path {{ color: #495057; }}
        .code-container {{ overflow-x: auto; }}
        .code-table {{ width: 100%; border-collapse: collapse; font-family: 'Courier New', monospace; font-size: 0.9rem; }}
        .code-table tr:hover {{ background-color: #f8f9fa; }}
        .line-number {{ width: 50px; text-align: right; padding: 2px 10px; color: #6c757d; border-right: 1px solid #dee2e6; user-select: none; background-color: #f8f9fa; }}
        .code-line {{ padding: 2px 10px; white-space: pre; }}
        .line-added {{ background-color: #d4edda; }}
        .line-removed {{ background-color: #f8d7da; }}
        .line-problem {{ background-color: #fff3cd; border-left: 3px solid #ffc107; position: relative; }}
        .problem-marker {{ position: absolute; right: 10px; top: 50%; transform: translateY(-50%); padding: 2px 8px; border-radius: 3px; font-size: 0.8rem; font-weight: bold; color: white; }}
        .findings-panel {{ background: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 1.5rem; margin-top: 2rem; }}
        .finding-item {{ padding: 1rem; border-left: 4px solid; margin-bottom: 1rem; background-color: #f8f9fa; }}
        .finding-severity {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.8rem; font-weight: bold; color: white; margin-right: 0.5rem; }}
        .finding-rule {{ font-weight: bold; color: #495057; }}
        .finding-message {{ margin-top: 0.5rem; color: #6c757d; }}
        
        /* LLM Analysis Section Styles */
        .llm-analysis-section {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; padding: 1.5rem; margin-top: 2rem; color: white; }}
        .llm-analysis-header {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.2); }}
        .llm-analysis-header h3 {{ font-size: 1.5rem; margin: 0; }}
        .llm-category {{ background: rgba(255, 255, 255, 0.95); border-radius: 8px; margin-bottom: 1rem; overflow: hidden; color: #333; }}
        .llm-category-header {{ display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; font-weight: 600; font-size: 1rem; border-bottom: 2px solid #f0f0f0; }}
        .llm-category-single-responsibility .llm-category-header {{ background: linear-gradient(90deg, #e3f2fd 0%, #bbdefb 100%); color: #1565c0; border-left: 4px solid #3498db; }}
        .llm-category-excessive-coupling .llm-category-header {{ background: linear-gradient(90deg, #fff3e0 0%, #ffe0b2 100%); color: #e65100; border-left: 4px solid #e67e22; }}
        .llm-category-difficulty_in_unit_testing .llm-category-header {{ background: linear-gradient(90deg, #f3e5f5 0%, #e1bee7 100%); color: #6a1b9a; border-left: 4px solid #9b59b6; }}
        .llm-violation-card {{ background: #fafafa; border-radius: 6px; margin: 0.75rem 1rem; border: 1px solid #e0e0e0; overflow: hidden; }}
        .llm-violation-header {{ display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; background: #f5f5f5; border-bottom: 1px solid #e0e0e0; }}
        .llm-severity-badge {{ display: inline-flex; align-items: center; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
        .llm-severity-high {{ background: #ffebee; color: #c62828; }}
        .llm-severity-medium {{ background: #fff3e0; color: #e65100; }}
        .llm-severity-low {{ background: #e8f5e9; color: #2e7d32; }}
        .llm-issue-title {{ flex: 1; font-weight: 600; color: #333; }}
        .llm-location-tag {{ display: inline-flex; align-items: center; gap: 0.25rem; background: #e0e0e0; color: #555; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-family: 'Courier New', monospace; }}
        .llm-violation-body {{ padding: 1rem; }}
        .llm-description {{ color: #555; line-height: 1.6; margin-bottom: 1rem; }}
        .llm-suggestion-box {{ background: linear-gradient(90deg, #e8f5e9 0%, #f1f8e9 100%); border-left: 4px solid #4caf50; padding: 0.75rem 1rem; border-radius: 0 6px 6px 0; margin-top: 0.75rem; }}
        .llm-suggestion-box .label {{ font-weight: 600; color: #2e7d32; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.5rem; }}
        .llm-suggestion-box .content {{ color: #555; font-size: 0.95rem; }}
        .llm-empty-state {{ padding: 1.5rem; text-align: center; color: #28a745; }}
        
        .footer {{ text-align: center; margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 0.9rem; }}
        @media (max-width: 768px) {{ .container {{ padding: 10px; }} .header h1 {{ font-size: 2rem; }} .score-number {{ font-size: 3rem; }} }}
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
        
        {HTMLReportGenerator._generate_llm_analysis_section(llm_semantic_results)}
        
        <footer class="footer">
            <p>© {datetime.now().year} Android Code Review Tool | Semantic analysis using DeepSeek model</p>
            <p>Report generated: {now}</p>
        </footer>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
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
                const toggleIcon = document.createElement('span');
                toggleIcon.className = 'toggle-icon';
                toggleIcon.textContent = '▼';
                toggleIcon.style.marginLeft = '10px';
                toggleIcon.style.cursor = 'pointer';
                this.appendChild(toggleIcon);
            }});
        }});
    </script>
</body>
</html>'''
        return html
    
    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalizes file path for consistent comparison"""
        if not path:
            return path
        # Remove leading slash and normalize
        path = path.lstrip('/')
        # Convert backslash to forward slash
        path = path.replace('\\', '/')
        return path
    
    @staticmethod
    def _generate_package_sections(files_by_package, findings_by_file):
        """Generates HTML for package and file sections"""
        sections = []
        
        # Normalize findings_by_file keys for matching
        normalized_findings = {}
        for key, value in findings_by_file.items():
            normalized_key = HTMLReportGenerator._normalize_path(key)
            normalized_findings[normalized_key] = value
        
        for package, files in sorted(files_by_package.items()):
            package_html = f'''
            <section class="package-section">
                <div class="package-header">
                    <span>📁 {package}</span>
                    <span>{len(files)} files</span>
                </div>'''
            
            for file_data in files:
                file_path = file_data['new_path']
                normalized_file_path = HTMLReportGenerator._normalize_path(file_path)
                file_findings = normalized_findings.get(normalized_file_path, [])
                
                code_lines = []
                current_line = 1
                
                for hunk in file_data.get('hunks', []):
                    code_lines.append({
                        'line_number': '...',
                        'content': f'// {hunk.get("context", "Change block")}',
                        'type': 'context',
                        'findings': []
                    })
                    
                    for line_data in hunk.get('lines', []):
                        line_type = line_data['type']
                        content = line_data['content']
                        
                        line_findings = []
                        for finding in file_findings:
                            # Skip LLM-related findings - they are displayed separately
                            rule = finding.get('rule', '')
                            if rule in HTMLReportGenerator.LLM_RULE_NAMES:
                                continue
                            
                            # Method 1: Match by line number (most accurate)
                            finding_line = finding.get('line_number')
                            if finding_line and str(current_line) == str(finding_line):
                                line_findings.append(finding)
                            # Method 2: Match by code snippet content
                            elif finding.get('code_snippet') and finding.get('code_snippet') in content:
                                line_findings.append(finding)
                            # Method 3: Match by keywords (fallback for specific rules)
                            elif rule == 'no_globalscope' and 'GlobalScope' in content:
                                line_findings.append(finding)
                            elif rule == 'collect_without_repeat' and 'collect' in content and 'repeatOnLifecycle' not in content:
                                line_findings.append(finding)
                            elif rule == 'startactivity_without_trycatch' and 'startActivity' in content:
                                line_findings.append(finding)
                            elif 'startActivity' in finding.get('message', '') and 'startActivity' in content:
                                line_findings.append(finding)
                        
                        code_lines.append({
                            'line_number': current_line if line_type != 'removed' else '-',
                            'content': content,
                            'type': line_type,
                            'findings': line_findings
                        })
                        
                        if line_type != 'removed':
                            current_line += 1
                
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
            
            content = HTMLReportGenerator._escape_html(content)
            
            line_class = ''
            if line_type == 'added':
                line_class = 'line-added'
            elif line_type == 'removed':
                line_class = 'line-removed'
            
            problem_html = ''
            if findings:
                line_class += ' line-problem'
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
    
    # LLM rule names that should be excluded from regular findings section
    LLM_RULE_NAMES = {'llm_semantic_review', 'single_responsibility', 'excessive_coupling', 'unit_test_difficulty', 'llm_error'}
    
    @staticmethod
    def _generate_findings_section(findings_by_file, severity_colors, report_dir=''):
        """Generates HTML for findings list section"""
        if not findings_by_file:
            return '<div class="findings-panel"><p>🎉 No issues found! Excellent code quality.</p></div>'
        
        all_findings = []
        for file_path, findings in findings_by_file.items():
            for finding in findings:
                # Skip LLM-related findings - they are displayed in the dedicated LLM section
                rule = finding.get('rule', '')
                if rule in HTMLReportGenerator.LLM_RULE_NAMES:
                    continue
                finding['file_path'] = file_path
                all_findings.append(finding)
        
        severity_order = {'critical': 0, 'major': 1, 'minor': 2, 'warning': 3, 'info': 4}
        all_findings.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 4))
        
        findings_html = '<div class="findings-panel"><h3 style="margin-bottom: 1rem;">📝 Issues Found</h3>'
        
        for finding_index, finding in enumerate(all_findings):
            severity = finding.get('severity', 'info')
            rule = finding.get('rule', 'unknown')
            message = finding.get('message', '')
            file_path = finding.get('file_path', 'Unknown file')
            
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
    
    @staticmethod
    def _generate_llm_analysis_section(llm_results: Optional[List[Dict[str, Any]]]) -> str:
        """Generates HTML for LLM semantic analysis section"""
        if not llm_results:
            return ''
        
        # Ensure llm_results is a list
        if isinstance(llm_results, dict):
            # If it's a dict, try to convert it to the expected format
            # This handles the case where llm_analysis_data is passed directly
            converted_results = []
            if 'analysis' in llm_results:
                analysis = llm_results['analysis']
                category_mapping = {
                    'single_responsibility_violations': 'single_responsibility',
                    'excessive_coupling': 'excessive_coupling', 
                    'difficulty_in_unit_testing': 'difficulty_in_unit_testing'
                }
                for json_key, category_key in category_mapping.items():
                    if json_key in analysis and isinstance(analysis[json_key], list):
                        violations = []
                        for item in analysis[json_key]:
                            if isinstance(item, dict):
                                violations.append({
                                    'severity': item.get('severity', 'low').lower(),
                                    'issue': item.get('issue', ''),
                                    'location': item.get('location', ''),
                                    'description': item.get('description', ''),
                                    'suggestion': item.get('suggestion', '')
                                })
                        if violations:
                            converted_results.append({
                                'category': category_key,
                                'violations': violations
                            })
            llm_results = converted_results
        
        if not isinstance(llm_results, list):
            return ''
        
        html = '''
        <div class="llm-analysis-section">
            <div class="llm-analysis-header">
                <span style="font-size: 2rem;">🤖</span>
                <h3>LLM Semantic Analysis</h3>
                <span style="margin-left: auto; opacity: 0.8; font-size: 0.9rem;">Powered by DeepSeek AI</span>
            </div>
        '''
        
        for result in llm_results:
            # Skip non-dict items
            if not isinstance(result, dict):
                continue
            
            category = result.get('category', '')
            violations = result.get('violations', [])
            
            # Get category config
            config = HTMLReportGenerator.LLM_CATEGORY_CONFIG.get(category, {
                'icon': '📋',
                'title': category.replace('_', ' ').title(),
                'description': ''
            })
            
            category_class = f'llm-category-{category.lower().replace(" ", "_")}'
            
            html += f'''
            <div class="llm-category {category_class}">
                <div class="llm-category-header">
                    <span style="font-size: 1.25rem;">{config['icon']}</span>
                    <span>{config['title']}</span>
                    <span style="margin-left: auto; font-size: 0.85rem; color: #666;">{len(violations)} issues</span>
                </div>
            '''
            
            if not violations:
                html += '''
                <div class="llm-empty-state">
                    <span style="font-size: 1.5rem;">✅</span>
                    <p>No violations found in this category</p>
                </div>
                '''
            else:
                for violation in violations:
                    severity = violation.get('severity', 'low')
                    issue = violation.get('issue', '')
                    location = violation.get('location', '')
                    description = violation.get('description', '')
                    suggestion = violation.get('suggestion', '')
                    
                    severity_class = f'llm-severity-{severity}'
                    
                    html += f'''
                    <div class="llm-violation-card">
                        <div class="llm-violation-header">
                            <span class="llm-severity-badge {severity_class}">{severity.upper()}</span>
                            <span class="llm-issue-title">{issue}</span>
                            <span class="llm-location-tag">📍 {location}</span>
                        </div>
                        <div class="llm-violation-body">
                            <div class="llm-description">{description}</div>
                            {f'<div class="llm-suggestion-box"><div class="label">💡 Suggestion</div><div class="content">{suggestion}</div></div>' if suggestion else ''}
                        </div>
                    </div>
                    '''
            
            html += '</div>'
        
        html += '</div>'
        return html


def main():
    """Main function"""
    test_diff = '''diff --git a/app/src/main/java/com/yxhuang/flowforandroid/HomeViewModel.kt b/app/src/main/java/com/yxhuang/flowforandroid/HomeViewModel.kt
index ebfe86a..c2ad7ad 100644
--- a/app/src/main/java/com/yxhuang/flowforandroid/HomeViewModel.kt
+++ b/app/src/main/java/com/yxhuang/flowforandroid/HomeViewModel.kt
@@ -8,6 +8,17 @@ import kotlinx.coroutines.launch

 class HomeViewModel : ViewModel() {{

+    init {{
+        GlobalScope.launch {{
+            val flow = (1..10).asFlow()
+            flow.collect {{
+                println("collect $it")
+                delay(1000)
+            }}
+        }}
+    }}

+    override fun onCleared() {{
+        super.onCleared()
+    }}
 }}'''
    
    test_findings = [
        {"severity": "critical", "rule": "no_globalscope", "message": "GlobalScope is lifecycle unsafe."},
        {"severity": "minor", "rule": "unspecified_scope", "message": "Coroutine launched without lifecycle scope."}
    ]
    
    # Test LLM semantic results
    test_llm_results = [
        {
            "category": "single_responsibility",
            "violations": [
                {
                    "severity": "high",
                    "issue": "Class has too many responsibilities",
                    "location": "HomeViewModel.kt:15",
                    "description": "The HomeViewModel class is handling data loading, UI state management, and business logic. This violates the Single Responsibility Principle.",
                    "suggestion": "Consider splitting into separate classes: HomeViewModel for UI state, HomeRepository for data operations, and HomeUseCase for business logic."
                }
            ]
        },
        {
            "category": "excessive_coupling",
            "violations": [
                {
                    "severity": "medium",
                    "issue": "Direct dependency on concrete implementation",
                    "location": "HomeViewModel.kt:20",
                    "description": "The ViewModel directly instantiates Repository instead of using dependency injection.",
                    "suggestion": "Use constructor injection with Hilt to provide Repository dependencies."
                }
            ]
        }
    ]
    
    diff_data = GitDiffParser.parse(test_diff)
    report_path = HTMLReportGenerator.generate_report(
        diff_data, test_findings, 65, 'test_report.html', test_llm_results
    )
    
    print(f"Report generated: {report_path}")


if __name__ == "__main__":
    main()
