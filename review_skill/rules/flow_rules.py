import re

# -----------------------------------
# flowOn 错误线程
# -----------------------------------

def detect_flowon_main(code: str):
    findings = []

    pattern = r"flow\s*\{[\s\S]*?\}\.flowOn\s*\(\s*Dispatchers\.Main"
    if re.search(pattern, code):
        findings.append({
            "severity": "critical",
            "rule": "flowon_main_dispatcher",
            "message": "flowOn(Dispatchers.Main) may execute upstream on Main thread."
        })

    return findings


# -----------------------------------
# 未指定 dispatcher 的 IO
# -----------------------------------

def detect_missing_flowon_for_io(code: str):
    findings = []

    if "flow {" in code and "repository" in code and "flowOn" not in code:
        findings.append({
            "severity": "major",
            "rule": "missing_flowon",
            "message": "Flow performing IO without explicit flowOn dispatcher."
        })

    return findings


# -----------------------------------
# channelFlow 使用检测
# -----------------------------------

def detect_channel_flow_usage(code: str):
    findings = []

    if "channelFlow {" in code:
        findings.append({
            "severity": "major",
            "rule": "channel_flow_usage",
            "message": "channelFlow used. Verify structured concurrency and cancellation."
        })

    return findings


# -----------------------------------
# Eager sharing
# -----------------------------------

def detect_eager_sharing(code: str):
    findings = []

    if "SharingStarted.Eagerly" in code:
        findings.append({
            "severity": "major",
            "rule": "eager_sharing_detected",
            "message": "Eager sharing keeps upstream active regardless of collectors."
        })

    return findings


# -----------------------------------
# MutableStateFlow 暴露
# -----------------------------------

def detect_mutable_stateflow_exposed(code: str):
    findings = []

    pattern = r"val\s+\w+\s*=\s*MutableStateFlow"
    matches = re.findall(pattern, code)

    for match in matches:
        if "private" not in match:
            findings.append({
                "severity": "major",
                "rule": "mutable_stateflow_exposed",
                "message": "MutableStateFlow should not be publicly exposed."
            })

    return findings


def run_flow_rules(code: str):
    findings = []
    findings += detect_flowon_main(code)
    findings += detect_missing_flowon_for_io(code)
    findings += detect_channel_flow_usage(code)
    findings += detect_eager_sharing(code)
    findings += detect_mutable_stateflow_exposed(code)
    return findings
