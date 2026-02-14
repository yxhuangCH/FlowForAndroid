import re

def run_base_rules(code):
    findings = []

    # GlobalScope 检测
    if "GlobalScope.launch" in code:
        findings.append({
            "severity": "critical",
            "rule": "no_globalscope",
            "message": "GlobalScope is lifecycle unsafe."
        })

    # ViewModel 持有 Context
    pattern = r"class\s+\w+ViewModel.*Context"
    if re.search(pattern, code):
        findings.append({
            "severity": "major",
            "rule": "viewmodel_context",
            "message": "ViewModel should not hold Android Context."
        })

    return findings


def calculate_score(findings):
    """
    基于 findings 计算代码质量分数
    初始分数：100分
    扣分规则：
    - critical: 每个扣20分
    - major: 每个扣10分
    - minor: 每个扣5分
    最低分数：0分
    """
    if not findings:
        return 100
    
    score = 100
    
    for finding in findings:
        severity = finding.get("severity", "minor")
        if severity == "critical":
            score -= 20
        elif severity == "major":
            score -= 10
        elif severity == "minor":
            score -= 5
    
    # 确保分数在0-100之间
    return max(0, min(100, score))
