import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from rules.base_rules import run_base_rules
from rules.coroutine_rules import run_coroutine_rules
from rules.compose_rules import run_compose_rules
from rules.hilt_rules import run_hilt_rules
from rules.flow_rules import run_flow_rules
from rules.flow_lifecycle_rules import run_flow_lifecycle_rules
from rules.flow_structure_rules import run_flow_structure_rules
from scorer import calculate_score

# 尝试导入 LLM 层，如果可用的话
LLM_AVAILABLE = False
try:
    from llm_layer import semantic_review
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("⚠ llm_layer 导入失败，跳过LLM语义分析")
except Exception as e:
    LLM_AVAILABLE = False
    print(f"⚠ LLM层初始化失败: {e}")

# 尝试导入HTML报告生成器
REPORT_GENERATOR_AVAILABLE = False
try:
    from report_generator import GitDiffParser, HTMLReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError as e:
    REPORT_GENERATOR_AVAILABLE = False
    print(f"⚠ 报告生成器导入失败: {e}")
except Exception as e:
    REPORT_GENERATOR_AVAILABLE = False
    print(f"⚠ 报告生成器初始化失败: {e}")


# 获取 git diff
def get_git_diff():
    # 尝试多种方式获取代码变更
    diff_commands = [
        ["git", "diff", "original/develop...HEAD"],
        ["git", "diff", "HEAD~1", "HEAD"],
        ["git", "diff", "--staged"]
    ]
    
    for cmd in diff_commands:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            return result.stdout
    
    # 如果都没有变更，返回空字符串
    return ""


def review():
    diff = get_git_diff()
    
    if not diff.strip():
        print("No changes to review. Git diff is empty.")
        return

    findings = []
    findings += run_base_rules(diff)
    findings += run_coroutine_rules(diff)
    findings += run_compose_rules(diff)
    findings += run_hilt_rules(diff)
    findings += run_flow_rules(diff)
    findings += run_flow_lifecycle_rules(diff)
    findings += run_flow_structure_rules(diff)
    
    # 如果 LLM 可用且有代码变更，进行语义审查
    llm_findings = []
    if LLM_AVAILABLE and diff.strip():
        try:
            # 限制代码长度，避免超过 token 限制
            code_sample = diff[:2000]  # 取前2000个字符进行语义分析
            llm_result = semantic_review(code_sample)
            if llm_result:
                llm_findings.append({
                    "severity": "info",
                    "rule": "llm_semantic_review",
                    "message": f"LLM语义分析: {llm_result}"
                })
        except Exception as e:
            llm_findings.append({
                "severity": "warning",
                "rule": "llm_error",
                "message": f"LLM语义分析失败: {str(e)}"
            })
    
    # 合并所有发现
    all_findings = findings + llm_findings

    score = calculate_score(findings)  # 仅基于规则扫描计算分数

    result = {
        "findings": all_findings,
        "score": score,
        "block_pr": score < 70 or any(f["severity"] == "critical" for f in findings),
        "llm_available": LLM_AVAILABLE
    }

    print(json.dumps(result, indent=2))

    # 生成HTML报告
    if REPORT_GENERATOR_AVAILABLE and diff.strip():
        try:
            # 解析git diff
            diff_data = GitDiffParser.parse(diff)
            
            # 生成HTML报告 - 保存到report目录
            report_dir = Path(__file__).parent / 'report'
            report_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_report_path = report_dir / f'code_review_report_{timestamp}.html'
            json_report_path = report_dir / f'code_review_details_{timestamp}.json'
            
            report_path = HTMLReportGenerator.generate_report(
                diff_data=diff_data,
                findings=findings,  # 只使用规则扫描的结果
                score=score,
                output_path=str(html_report_path)
            )
            
            print(f"\n📊 HTML报告已生成: {report_path}")
            print(f"📂 打开报告: open {report_path}")
            print(f"📁 报告目录: {report_dir}")
            
            # 同时生成一个更详细的JSON报告
            detailed_result = {
                "timestamp": datetime.now().isoformat(),
                "diff_files_count": len(diff_data),
                "files_by_package": {},
                "detailed_findings": all_findings,
                "score": score,
                "block_pr": result["block_pr"],
                "llm_available": LLM_AVAILABLE,
                "report_generator_available": REPORT_GENERATOR_AVAILABLE
            }
            
            # 按包名分组
            for file_data in diff_data:
                package = file_data['package']
                if package not in detailed_result["files_by_package"]:
                    detailed_result["files_by_package"][package] = []
                detailed_result["files_by_package"][package].append({
                    "file": file_data['new_path'],
                    "language": file_data['language']
                })
            
            # 保存详细JSON报告到report目录
            with open(json_report_path, 'w', encoding='utf-8') as f:
                json.dump(detailed_result, f, indent=2, ensure_ascii=False)
            
            print(f"📝 详细JSON报告: {json_report_path}")
            
        except Exception as e:
            print(f"⚠ HTML报告生成失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        if not REPORT_GENERATOR_AVAILABLE:
            print("⚠ HTML报告生成器不可用，跳过HTML报告生成")
        else:
            print("⚠ 没有代码变更，跳过HTML报告生成")

    if result["block_pr"]:
        exit(1)


if __name__ == "__main__":
    review()
