import re

def run_dagger2_rules(code):
    findings = []

    # 检测 @Singleton Component 注入 Activity
    if "@Singleton" in code and "@Component" in code and "Activity" in code:
        findings.append({
            "severity": "major",
            "rule": "singleton_component_inject_activity",
            "message": "Singleton Component injecting Activity may cause lifecycle mismatch."
        })

    # Field Injection 检测
    if re.search(r"@Inject\s+lateinit\s+var", code):
        findings.append({
            "severity": "minor",
            "rule": "field_injection_detected",
            "message": "Field injection detected. Prefer constructor injection."
        })

    # @Provides 无 scope
    if "@Provides" in code and "@Singleton" not in code:
        findings.append({
            "severity": "minor",
            "rule": "provides_without_scope",
            "message": "@Provides method without scope may create multiple instances."
        })

    return findings
