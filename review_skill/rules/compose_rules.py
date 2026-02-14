def run_compose_rules(code):
    findings = []

    if "LaunchedEffect(Unit)" in code:
        findings.append({
            "severity": "minor",
            "rule": "launched_effect_unit",
            "message": "LaunchedEffect(Unit) may cause unintended recomposition."
        })

    if "remember {" in code and "context" in code:
        findings.append({
            "severity": "major",
            "rule": "remember_context",
            "message": "remember holding context may leak."
        })

    return findings
