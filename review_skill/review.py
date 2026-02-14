import subprocess
import json
import os
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

    if result["block_pr"]:
        exit(1)


if __name__ == "__main__":
    review()
