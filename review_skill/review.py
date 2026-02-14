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
try:
    from llm_layer import semantic_review
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
except Exception:
    LLM_AVAILABLE = False


# 获取 git diff
def get_git_diff():
    result = subprocess.run(
        ["git", "diff", "original/develop...HEAD"],
        capture_output=True,
        text=True
    )
    return result.stdout


def review():
    diff = get_git_diff()

    findings = []
    findings += run_base_rules(diff)
    findings += run_coroutine_rules(diff)
    findings += run_compose_rules(diff)
    findings += run_hilt_rules(diff)
    findings += run_flow_rules(diff)
    findings += run_flow_lifecycle_rules(diff)
    findings += run_flow_structure_rules(diff)


    score = calculate_score(findings)

    result = {
        "findings": findings,
        "score": score,
        "block_pr": score < 70 or any(f["severity"] == "critical" for f in findings)
    }

    print(json.dumps(result, indent=2))

    if result["block_pr"]:
        exit(1)


if __name__ == "__main__":
    review()
