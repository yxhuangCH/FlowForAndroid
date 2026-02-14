import re

# -----------------------------------
# stateIn(GlobalScope)
# -----------------------------------

def detect_statein_globalscope(code: str):
    findings = []

    if "stateIn(GlobalScope" in code:
        findings.append({
            "severity": "critical",
            "rule": "statein_globalscope",
            "message": "StateFlow scoped to GlobalScope may leak forever."
        })

    return findings


# -----------------------------------
# shareIn(GlobalScope)
# -----------------------------------

def detect_sharein_globalscope(code: str):
    findings = []

    if "shareIn(GlobalScope" in code:
        findings.append({
            "severity": "critical",
            "rule": "sharein_globalscope",
            "message": "SharedFlow scoped to GlobalScope may leak."
        })

    return findings


# -----------------------------------
# collect 未使用 repeatOnLifecycle
# -----------------------------------

def detect_collect_without_repeat(code: str):
    findings = []

    if "collect {" in code and "repeatOnLifecycle" not in code:
        findings.append({
            "severity": "major",
            "rule": "collect_without_repeat",
            "message": "Flow collected without repeatOnLifecycle in UI layer."
        })

    return findings


# -----------------------------------
# ViewModel 未使用 viewModelScope
# -----------------------------------

def detect_statein_wrong_scope(code: str):
    findings = []

    if "stateIn(" in code and "viewModelScope" not in code:
        findings.append({
            "severity": "major",
            "rule": "statein_without_viewmodelscope",
            "message": "stateIn should typically use viewModelScope in ViewModel."
        })

    return findings


def run_flow_lifecycle_rules(code: str):
    findings = []
    findings += detect_statein_globalscope(code)
    findings += detect_sharein_globalscope(code)
    findings += detect_collect_without_repeat(code)
    findings += detect_statein_wrong_scope(code)
    return findings
