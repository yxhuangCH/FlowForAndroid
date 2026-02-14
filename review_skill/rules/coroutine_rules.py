def run_coroutine_rules(code):
    findings = []

    # Main thread IO
    if "Dispatchers.Main" in code and "repository" in code:
        findings.append({
            "severity": "major",
            "rule": "main_thread_io",
            "message": "Possible IO on Main thread."
        })

    # 未指定 scope launch
    if "launch {" in code and "viewModelScope" not in code:
        findings.append({
            "severity": "minor",
            "rule": "unspecified_scope",
            "message": "Coroutine launched without lifecycle scope."
        })

    return findings
