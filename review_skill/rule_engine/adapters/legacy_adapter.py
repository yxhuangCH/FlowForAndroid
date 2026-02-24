"""
旧规则适配器，用于向后兼容现有规则
"""
from typing import List, Callable, Dict, Any
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext


class LegacyRuleAdapter(Rule):
    """旧规则适配器"""
    
    def __init__(self, rule_id: str, legacy_function: Callable, metadata: RuleMetadata):
        """
        初始化适配器
        
        Args:
            rule_id: 规则ID
            legacy_function: 旧规则函数（接受code字符串，返回list of dicts）
            metadata: 规则元数据
        """
        self._metadata = metadata
        self._metadata.id = rule_id  # 确保ID一致
        self.legacy_function = legacy_function
    
    @property
    def metadata(self) -> RuleMetadata:
        return self._metadata
    
    def check(self, context: RuleContext) -> List[Finding]:
        # 调用旧函数
        try:
            legacy_findings = self.legacy_function(context.code)
        except Exception as e:
            # 如果旧函数失败，返回错误
            return [Finding(
                rule_id=self._metadata.id,
                message=f"旧规则执行失败: {str(e)[:100]}",
                severity=RuleSeverity.MINOR,
                file_path=context.file_path
            )]
        
        # 转换为新的Finding格式
        findings = []
        
        if not isinstance(legacy_findings, list):
            # 如果返回值不是列表，包装成列表
            legacy_findings = [legacy_findings] if legacy_findings else []
        
        for legacy_finding in legacy_findings:
            if not isinstance(legacy_finding, dict):
                continue
            
            # 转换严重级别字符串为枚举
            severity_str = legacy_finding.get("severity", "minor")
            try:
                severity = RuleSeverity(severity_str)
            except ValueError:
                # 如果无法识别严重级别，默认为minor
                severity = RuleSeverity.MINOR
            
            # 创建Finding
            finding = Finding(
                rule_id=self._metadata.id,
                message=legacy_finding.get("message", "未指定问题描述"),
                severity=severity,
                file_path=context.file_path,
                suggestion=legacy_finding.get("suggestion")
            )
            
            # 复制其他可能的字段
            for key in ["line_number", "code_snippet", "confidence"]:
                if key in legacy_finding:
                    setattr(finding, key, legacy_finding[key])
            
            findings.append(finding)
        
        return findings


def create_legacy_adapter(rule_id: str, legacy_function: Callable, **metadata_kwargs) -> LegacyRuleAdapter:
    """
    创建旧规则适配器的快捷函数
    
    Args:
        rule_id: 规则ID
        legacy_function: 旧规则函数
        **metadata_kwargs: 元数据参数
        
    Returns:
        配置好的适配器
    """
    # 默认元数据
    default_metadata = {
        "id": rule_id,
        "name": rule_id.replace("_", " ").title(),
        "description": f"旧规则适配器: {rule_id}",
        "severity": RuleSeverity.MINOR,
        "category": RuleCategory.CORRECTNESS,
        "tags": ["legacy", "adapter"]
    }
    
    # 更新默认值
    default_metadata.update(metadata_kwargs)
    
    # 创建元数据对象
    metadata = RuleMetadata(**default_metadata)
    
    return LegacyRuleAdapter(rule_id, legacy_function, metadata)