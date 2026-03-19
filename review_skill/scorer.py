import re

def run_base_rules(code):
    findings = []

    # GlobalScope detection
    if "GlobalScope.launch" in code:
        findings.append({
            "severity": "critical",
            "rule": "no_globalscope",
            "message": "GlobalScope is lifecycle unsafe."
        })

    # ViewModel holding Context
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
    Calculate code quality score based on findings
    Initial score: 100 points
    Deduction rules:
    - critical: -20 points each
    - major: -10 points each
    - minor: -5 points each
    Minimum score: 0 points
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
    
    # Ensure score is between 0-100
    return max(0, min(100, score))
