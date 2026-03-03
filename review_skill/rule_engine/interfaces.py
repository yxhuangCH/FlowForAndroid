"""
规则引擎核心接口定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable


class RuleSeverity(Enum):
    """规则严重级别"""
    INFO = "info"           # 信息性提示（不扣分）
    MINOR = "minor"         # 轻微问题（扣5分）
    MAJOR = "major"         # 主要问题（扣10分）
    CRITICAL = "critical"   # 严重问题（扣20分）
    BLOCKER = "blocker"     # 阻塞性问题（扣100分，直接阻塞PR）


class RuleCategory(Enum):
    """规则分类"""
    SECURITY = "security"            # 安全性
    PERFORMANCE = "performance"      # 性能
    BEST_PRACTICE = "best_practice"  # 最佳实践
    MAINTAINABILITY = "maintainability"  # 可维护性
    CORRECTNESS = "correctness"      # 正确性
    STYLE = "style"                  # 代码风格
    CONCURRENCY = "concurrency"      # 并发问题
    LIFECYCLE = "lifecycle"          # 生命周期管理


@dataclass
class RuleMetadata:
    """规则元数据"""
    id: str                         # 规则唯一标识符（如：no_globalscope）
    name: str                       # 规则名称（可读）
    description: str                # 规则详细描述
    severity: RuleSeverity          # 严重级别
    category: RuleCategory          # 分类
    enabled: bool = True            # 是否启用
    weight: float = 1.0             # 权重（影响评分）
    tags: List[str] = field(default_factory=list)  # 标签
    suggested_fix: Optional[str] = None  # 建议修复方式
    reference_url: Optional[str] = None  # 参考文档URL
    min_score_deduction: Optional[int] = None  # 最小扣分（覆盖默认扣分）
    max_score_deduction: Optional[int] = None  # 最大扣分（覆盖默认扣分）
    
    def __post_init__(self):
        """后初始化处理"""
        if not self.id:
            raise ValueError("规则ID不能为空")
        if not self.name:
            raise ValueError("规则名称不能为空")
        if not self.description:
            raise ValueError("规则描述不能为空")


@dataclass
class Finding:
    """审查发现的问题"""
    rule_id: str                     # 规则ID
    message: str                     # 问题描述
    severity: RuleSeverity           # 严重级别
    file_path: Optional[str] = None  # 文件路径
    line_number: Optional[int] = None  # 行号（从1开始）
    column: Optional[int] = None     # 列号（从1开始）
    code_snippet: Optional[str] = None  # 代码片段
    suggestion: Optional[str] = None  # 修复建议
    confidence: float = 1.0          # 检测置信度（0.0-1.0）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 附加元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（兼容现有系统）"""
        return {
            "rule": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            **self.metadata
        }


class Rule(ABC):
    """规则抽象基类"""
    
    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata:
        """获取规则元数据"""
        pass
    
    @abstractmethod
    def check(self, context: 'RuleContext') -> List[Finding]:
        """
        检查代码，返回发现的问题
        
        Args:
            context: 规则上下文，包含代码、文件信息等
            
        Returns:
            发现的问题列表
        """
        pass
    
    def on_register(self):
        """规则注册时的回调（可选）"""
        pass
    
    def on_unregister(self):
        """规则注销时的回调（可选）"""
        pass
    
    def get_score_deduction(self, severity: RuleSeverity) -> int:
        """
        根据严重级别计算扣分
        
        Args:
            severity: 严重级别
            
        Returns:
            扣分分数
        """
        if self.metadata.min_score_deduction is not None and self.metadata.max_score_deduction is not None:
            # 使用规则特定的扣分范围
            default_deductions = {
                RuleSeverity.INFO: 0,
                RuleSeverity.MINOR: 5,
                RuleSeverity.MAJOR: 10,
                RuleSeverity.CRITICAL: 20,
                RuleSeverity.BLOCKER: 100
            }
            deduction = default_deductions.get(severity, 0)
            return min(self.metadata.max_score_deduction, max(self.metadata.min_score_deduction, deduction))
        
        # 使用默认扣分
        default_deductions = {
            RuleSeverity.INFO: 0,
            RuleSeverity.MINOR: 5,
            RuleSeverity.MAJOR: 10,
            RuleSeverity.CRITICAL: 20,
            RuleSeverity.BLOCKER: 100
        }
        return default_deductions.get(severity, 0)


# 错误处理类
class ReviewError(Exception):
    """审查系统基础错误类"""
    pass


class RuleExecutionError(ReviewError):
    """规则执行错误"""
    pass


class ConfigurationError(ReviewError):
    """配置错误"""
    pass


class IntegrationError(ReviewError):
    """集成错误"""
    pass


class ValidationError(ReviewError):
    """验证错误"""
    pass
