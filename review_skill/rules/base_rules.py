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
