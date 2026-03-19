"""Rule Engine Core Interface Definitions
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable


class RuleSeverity(Enum):
    """Rule severity levels"""
    INFO = "info"           # Informational (no deduction)
    MINOR = "minor"         # Minor issue (deduct 5 points)
    MAJOR = "major"         # Major issue (deduct 10 points)
    CRITICAL = "critical"   # Critical issue (deduct 20 points)
    BLOCKER = "blocker"     # Blocker issue (deduct 100 points, block PR)


class RuleCategory(Enum):
    """Rule categories"""
    SECURITY = "security"            # Security
    PERFORMANCE = "performance"      # Performance
    BEST_PRACTICE = "best_practice"  # Best Practice
    MAINTAINABILITY = "maintainability"  # Maintainability
    CORRECTNESS = "correctness"      # Correctness
    STYLE = "style"                  # Code Style
    CONCURRENCY = "concurrency"      # Concurrency
    LIFECYCLE = "lifecycle"          # Lifecycle Management


@dataclass
class RuleMetadata:
    """Rule metadata"""
    id: str                         # Unique rule identifier (e.g.: no_globalscope)
    name: str                       # Rule name (human-readable)
    description: str                # Detailed rule description
    severity: RuleSeverity          # Severity level
    category: RuleCategory          # Category
    enabled: bool = True            # Whether enabled
    weight: float = 1.0             # Weight (affects scoring)
    tags: List[str] = field(default_factory=list)  # Tags
    suggested_fix: Optional[str] = None  # Suggested fix
    reference_url: Optional[str] = None  # Reference URL
    min_score_deduction: Optional[int] = None  # Min deduction (overrides default)
    max_score_deduction: Optional[int] = None  # Max deduction (overrides default)
    
    def __post_init__(self):
        """Post-init processing"""
        if not self.id:
            raise ValueError("Rule ID cannot be empty")
        if not self.name:
            raise ValueError("Rule name cannot be empty")
        if not self.description:
            raise ValueError("Rule description cannot be empty")


@dataclass
class Finding:
    """Review finding/issue"""
    rule_id: str                     # Rule ID
    message: str                     # Issue description
    severity: RuleSeverity           # Severity level
    file_path: Optional[str] = None  # File path
    line_number: Optional[int] = None  # Line number (1-based)
    column: Optional[int] = None     # Column number (1-based)
    code_snippet: Optional[str] = None  # Code snippet
    suggestion: Optional[str] = None  # Fix suggestion
    confidence: float = 1.0          # Detection confidence (0.0-1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format (compatible with existing system)"""
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
    """Rule abstract base class"""
    
    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata:
        """Get rule metadata"""
        pass
    
    @abstractmethod
    def check(self, context: 'RuleContext') -> List[Finding]:
        """
        Check code, return findings
        
        Args:
            context: rule context, containing code, file info, etc.
            
        Returns:
            list of findings
        """
        pass
    
    def on_register(self):
        """Callback when rule is registered (optional)"""
        pass
    
    def on_unregister(self):
        """Callback when rule is unregistered (optional)"""
        pass
    
    def get_score_deduction(self, severity: RuleSeverity) -> int:
        """
        Calculate deduction based on severity
        
        Args:
            severity: severity level
            
        Returns:
            deduction score
        """
        if self.metadata.min_score_deduction is not None and self.metadata.max_score_deduction is not None:
            # Use rule-specific deduction range
            default_deductions = {
                RuleSeverity.INFO: 0,
                RuleSeverity.MINOR: 5,
                RuleSeverity.MAJOR: 10,
                RuleSeverity.CRITICAL: 20,
                RuleSeverity.BLOCKER: 100
            }
            deduction = default_deductions.get(severity, 0)
            return min(self.metadata.max_score_deduction, max(self.metadata.min_score_deduction, deduction))
        
        # Use default deduction
        default_deductions = {
            RuleSeverity.INFO: 0,
            RuleSeverity.MINOR: 5,
            RuleSeverity.MAJOR: 10,
            RuleSeverity.CRITICAL: 20,
            RuleSeverity.BLOCKER: 100
        }
        return default_deductions.get(severity, 0)


# Error handling classes
class ReviewError(Exception):
    """Review system base error class"""
    pass


class RuleExecutionError(ReviewError):
    """Rule execution error"""
    pass


class ConfigurationError(ReviewError):
    """Configuration error"""
    pass


class IntegrationError(ReviewError):
    """Integration error"""
    pass


class ValidationError(ReviewError):
    """Validation error"""
    pass
