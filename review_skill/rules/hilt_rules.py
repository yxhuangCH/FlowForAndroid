def run_hilt_rules(code):
    findings = []

    if "@Singleton" in code and "Activity" in code:
        findings.append({
            "severity": "major",
            "rule": "singleton_activity",
            "message": "Singleton injected into Activity scope."
        })

    return findings
