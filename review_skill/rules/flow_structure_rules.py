import re

# -----------------------------------
# launch + collectLatest 内部再 launch
# -----------------------------------

def detect_nested_launch_in_collect(code: str):
    findings = []

    pattern = r"collectLatest\s*\{[\s\S]*?launch\s*\{"
    if re.search(pattern, code):
        findings.append({
            "severity": "major",
            "rule": "nested_launch_in_collect",
            "message": "Nested launch inside collectLatest may break structured concurrency."
        })

    return findings


# -----------------------------------
# flow builder 内部 launch
# -----------------------------------

def detect_launch_inside_flow_builder(code: str):
    findings = []

    pattern = r"flow\s*\{[\s\S]*?launch\s*\{"
    if re.search(pattern, code):
        findings.append({
            "severity": "critical",
            "rule": "launch_inside_flow",
            "message": "launch inside flow builder breaks structured concurrency."
        })

    return findings


# -----------------------------------
# 多次 collect 同一 Flow
# -----------------------------------

def detect_multiple_collects(code: str):
    findings = []

    collects = len(re.findall(r"\.collect\s*\{", code))
    if collects > 1:
        findings.append({
            "severity": "minor",
            "rule": "multiple_collects",
            "message": "Multiple collect calls detected. Verify cold/hot flow behavior."
        })

    return findings


# -----------------------------------
# channelFlow 未 awaitClose
# -----------------------------------

def detect_channel_flow_without_awaitclose(code: str):
    findings = []

    if "channelFlow {" in code and "awaitClose" not in code:
        findings.append({
            "severity": "major",
            "rule": "channel_flow_no_awaitclose",
            "message": "channelFlow without awaitClose may leak."
        })

    return findings


def run_flow_structure_rules(code: str):
    findings = []
    findings += detect_nested_launch_in_collect(code)
    findings += detect_launch_inside_flow_builder(code)
    findings += detect_multiple_collects(code)
    findings += detect_channel_flow_without_awaitclose(code)
    return findings
