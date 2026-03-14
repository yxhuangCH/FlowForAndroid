# Android Review Skill - Technical Specification

## Overview

This technical specification describes the system architecture, design principles, core components, and implementation details of Android Review Skill. This tool is a professional Android/Kotlin code review platform supporting static rule scanning, LLM semantic analysis, and automated report generation.

## System Architecture

### Overall Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   CLI       │    │  CI/CD      │    │   Web UI    │        │
│  │  (CLI)      │    │  (GitHub)   │    │  (HTML)     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                 Business Logic Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Review Core Engine                     │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │    │
│  │  │  Git Integration │  File Filter │  Config     │    │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    Rule Engine Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Rule      │  │   Rule      │  │   Rule      │            │
│  │  Registry   │  │  Executor   │  │  Context    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Rule      │  │   Priority  │  │   Result    │            │
│  │   Cache     │  │  Scheduler  │  │  Aggregator │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                      Rule Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Base Rules │  │ Coroutine   │  │  Compose    │            │
│  │  (Base)     │  │  Rules      │  │   Rules     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Flow Rules │  │  Hilt Rules │  │ Custom Rules│            │
│  │  (Flow)     │  │  (Hilt)     │  │  (Custom)   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│              External Integration Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  LLM Service│  │   Report    │  │   Storage   │            │
│  │  (LLM API)  │  │  Generator  │  │  (Storage)  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Design Principles

1. **Modular Design**: Single responsibility for each component, easy to maintain and extend
2. **Backward Compatibility**: Support smooth transition between old and new systems
3. **High Performance**: Support parallel processing and cache optimization
4. **Configurability**: Support dynamic runtime configuration
5. **Extensibility**: Support plugin and custom rules

## Core Components

### 1. Rule Engine

#### 1.1 Design Goals
- Unified management of all rules, eliminating scattered rule files
- Support dynamic rule registration/unregistration
- Provide standardized rule interface
- Support parallel execution and cache optimization

#### 1.2 Main Components

##### 1.2.1 Rule Interface
```python
class Rule(ABC):
    """Rule Abstract Base Class"""
    
    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata:
        """Get rule metadata"""
        pass
    
    @abstractmethod
    def check(self, context: 'RuleContext') -> List[Finding]:
        """
        Check code and return found issues
        
        Args:
            context: Rule context containing code, file info, etc.
            
        Returns:
            List of found issues
        """
        pass
```

##### 1.2.2 Rule Metadata
```python
@dataclass
class RuleMetadata:
    """Rule Metadata"""
    id: str                      # Unique rule identifier
    name: str                    # Human-readable rule name
    description: str             # Rule description
    severity: RuleSeverity       # Severity level
    category: RuleCategory       # Category
    enabled: bool = True         # Whether enabled
    weight: float = 1.0          # Weight (affects scoring)
    tags: List[str] = None       # Tags
```

##### 1.2.3 Rule Context
```python
@dataclass
class RuleContext:
    """Rule Execution Context"""
    code: str                      # Code content
    file_path: str                 # File path
    language: str                  # Programming language
    file_hash: str = ""            # File hash (for caching)
    ast: Optional[Any] = None      # AST (if parsed)
    config: Dict[str, Any] = None  # Rule configuration
```

##### 1.2.4 Finding
```python
@dataclass
class Finding:
    """Review Finding"""
    rule_id: str                     # Rule ID
    message: str                     # Issue description
    severity: RuleSeverity           # Severity level
    file_path: Optional[str] = None  # File path
    line_number: Optional[int] = None # Line number
    suggestion: Optional[str] = None  # Fix suggestion
```

#### 1.3 Rule Registry

##### Features
- Singleton pattern for global unified rule management
- Support querying rules by category, tags, severity
- Support dynamic enable/disable rules
- Provide rule statistics

##### Core Methods
```python
class RuleRegistry:
    def register(self, rule: Rule) -> None:
        """Register rule"""
        
    def unregister(self, rule_id: str) -> None:
        """Unregister rule"""
        
    def get_rules_by_category(self, category: RuleCategory) -> List[Rule]:
        """Get rules by category"""
        
    def get_all_rules(self, enabled_only: bool = True) -> List[Rule]:
        """Get all rules"""
```

#### 1.4 Rule Engine

##### Execution Modes
- **Sequential Execution**: Simple rule-by-rule execution
- **Parallel Execution**: Utilize multi-core CPU for parallel rule execution
- **Intelligent Scheduling**: Optimize execution order based on rule type and complexity

##### Cache Mechanism
- **Memory Cache**: LRU strategy, limit maximum cache entries
- **File Hash**: Cache key based on file content hash
- **TTL Support**: Automatic expiration of long-unused cache

### 2. Adapter Layer

#### 2.1 Design Purpose
- Provide concise rule definition methods
- Support functional programming style
- Maintain readability and maintainability of rule definitions

#### 2.2 Decorator Support
The adapter layer provides `rule` and `pattern_rule` decorators to simplify rule definition:

```python
@rule(
    rule_id="no_globalscope",
    name="Prohibit GlobalScope",
    severity=RuleSeverity.CRITICAL,
    category=RuleCategory.LIFECYCLE
)
def no_globalscope_rule(context: RuleContext) -> List[Finding]:
    """Functional rule definition"""
    findings = []
    if "GlobalScope.launch" in context.code:
        findings.append(Finding(
            rule_id="no_globalscope",
            message="GlobalScope is lifecycle unsafe.",
            severity=RuleSeverity.CRITICAL
        ))
    return findings
```

#### 2.3 Pattern Matching Decorator
For simple pattern matching rules, use the `pattern_rule` decorator:

```python
from rule_engine.adapters import pattern_rule

@pattern_rule(
    pattern="GlobalScope\\.launch",
    rule_id="no_globalscope_pattern",
    message="GlobalScope is lifecycle unsafe.",
    severity=RuleSeverity.CRITICAL,
    case_sensitive=False
)
def no_globalscope_pattern_rule(context: RuleContext) -> List[Finding]:
    # Decorator automatically implements pattern matching logic
    return []
```

### 3. Review Runner

#### 3.1 Core Flow
```
1. Initialize configuration
2. Get Git diff
3. Filter files (by configuration)
4. Initialize rule engine
5. Execute rules for each file
6. Aggregate results, calculate score
7. Generate report
8. Output results
```

#### 3.2 Mixed Mode Support
```python
class ReviewRunner:
    """Review runner supporting both old and new engines"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.registry = RuleRegistry()
        self.engine = RuleEngine(self.registry)
        
    def review_diff(self, diff: str) -> List[Dict[str, Any]]:
        """Review Git diff"""
        # Parse diff, execute review for each file
        files = parse_git_diff(diff)
        results = []
        
        for file_info in files:
            context = RuleContext(
                code=file_info['content'],
                file_path=file_info['path'],
                language="kotlin"
            )
            
            findings, stats = self.engine.execute_all(context)
            score = self._calculate_score(findings)
            
            results.append({
                "file": file_info['path'],
                "findings": findings,
                "score": score,
                "stats": stats
            })
        
        return results
```

### 4. Configuration Management System

#### 4.1 Configuration Levels
1. **Default Configuration**: Built-in reasonable defaults
2. **Configuration File**: JSON/YAML format user configuration
3. **Environment Variables**: Runtime configuration override
4. **Command Line Arguments**: Temporary configuration override

#### 4.2 Configuration Content
```json
{
  "file_extensions": [".kt", ".kts"],
  "scan_directories": ["app/src/main/java"],
  "exclude_patterns": ["*/build/*"],
  "rule_engine": {
    "use_new_engine": true,
    "new_engine_config": {
      "enabled_categories": ["security", "performance", "correctness"],
      "parallel_execution": true,
      "cache_enabled": true
    }
  }
}
```

## Rule System

### 1. Rule Classification System

#### 1.1 Severity Levels (RuleSeverity)
```python
class RuleSeverity(Enum):
    INFO = "info"           # Informational hints (no deduction)
    MINOR = "minor"         # Minor issues (-5 pts)
    MAJOR = "major"         # Major issues (-10 pts)
    CRITICAL = "critical"   # Critical issues (-20 pts)
    BLOCKER = "blocker"     # Blocking issues (-100 pts)
```

#### 1.2 Rule Categories (RuleCategory)
```python
class RuleCategory(Enum):
    SECURITY = "security"            # Security
    PERFORMANCE = "performance"      # Performance
    BEST_PRACTICE = "best_practice"  # Best practices
    MAINTAINABILITY = "maintainability"  # Maintainability
    CORRECTNESS = "correctness"      # Correctness
    STYLE = "style"                  # Code style
    CONCURRENCY = "concurrency"      # Concurrency issues
    LIFECYCLE = "lifecycle"          # Lifecycle management
```

### 2. Rule Implementation Methods

#### 2.1 Class-based Rules
```python
class NoGlobalScopeRule(Rule):
    """Prohibit GlobalScope rule"""
    
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            id="no_globalscope",
            name="Prohibit GlobalScope",
            description="GlobalScope.launch may cause memory leaks",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.LIFECYCLE,
            tags=["android", "kotlin", "coroutine"]
        )
    
    def check(self, context: RuleContext) -> List[Finding]:
        findings = []
        if "GlobalScope.launch" in context.code:
            findings.append(Finding(
                rule_id=self.metadata.id,
                message=self.metadata.description,
                severity=self.metadata.severity
            ))
        return findings
```

#### 2.2 Functional Rules (Decorators)
```python
@rule(
    rule_id="viewmodel_context",
    name="ViewModel should not hold Context",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.LIFECYCLE
)
def viewmodel_context_rule(context: RuleContext) -> List[Finding]:
    """Functional rule definition"""
    findings = []
    # Rule logic
    return findings
```

### 3. Rule Scoring System

#### 3.1 Score Calculation Algorithm
```
Initial score = 100
For each found issue:
    if severity == INFO: deduction = 0
    elif severity == MINOR: deduction = 5
    elif severity == MAJOR: deduction = 10
    elif severity == CRITICAL: deduction = 20
    elif severity == BLOCKER: deduction = 100
    
    Final deduction = deduction * rule weight
    Current score -= Final deduction

Final score = max(0, min(100, Current score))
```

## File Processing System

### 1. Git Diff Processing

#### 1.1 Diff Acquisition Strategy
```python
def get_git_diff():
    """Get Git diff"""
    diff_commands = [
        ["git", "diff", "original/develop...HEAD"],  # PR review
        ["git", "diff", "HEAD~1", "HEAD"],           # Latest commit
        ["git", "diff", "--staged"]                  # Staged
    ]
    
    for cmd in diff_commands:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            return result.stdout
    
    return ""  # No changes
```

### 2. File Filtering System

#### 2.1 Filtering Strategy
1. **Extension Filtering**: Only scan configured extensions (.kt, .kts)
2. **Directory Filtering**: Only scan configured directories
3. **Pattern Exclusion**: Use glob patterns to exclude specific files/directories

## Report Generation System

### 1. Report Formats

#### 1.1 JSON Format
```json
{
  "findings": [
    {
      "severity": "critical",
      "rule": "no_globalscope",
      "message": "GlobalScope is lifecycle unsafe.",
      "file": "app/src/main/java/com/example/MyActivity.kt",
      "line": 42,
      "suggestion": "Use lifecycleScope or viewModelScope"
    }
  ],
  "score": 85,
  "block_pr": false,
  "engine": "new",
  "statistics": {
    "total_files": 3,
    "total_findings": 2,
    "execution_time": 1.234
  }
}
```

#### 1.2 HTML Visualization Report
- **Dashboard**: Overall score and statistics
- **Issue Categories**: Classified by severity and rule type
- **File View**: Detailed issues and suggestions for each file
- **Code Comparison**: Display problematic code snippets
- **Fix Suggestions**: Specific fix steps and suggested code

## Performance Optimization Strategies

### 1. Parallel Processing Optimization

#### 1.1 Thread Pool Management
```python
class ParallelRuleExecutor:
    """Parallel rule executor"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or os.cpu_count()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
    
    def execute_rules(self, rules: List[Rule], context: RuleContext):
        """Execute rules in parallel"""
        futures = {}
        for rule in rules:
            future = self.executor.submit(rule.check, context)
            futures[future] = rule
        
        # Collect results
        all_findings = []
        for future in as_completed(futures):
            findings = future.result()
            all_findings.extend(findings)
        
        return all_findings
```

### 2. Cache Optimization

#### 2.1 Multi-level Cache
```python
class MultiLevelCache:
    """Multi-level cache system"""
    
    def __init__(self):
        self.memory_cache = LRUCache(maxsize=1000)  # Memory cache
        self.disk_cache = DiskCache()               # Disk cache
        self.redis_cache = RedisCache()             # Redis cache (distributed)
    
    def get(self, key):
        """Get cached value"""
        # 1. Check memory cache
        # 2. Check disk cache
        # 3. Check Redis cache
        # 4. If none, compute and cache
```

## Extensibility Design

### 1. Plugin System

#### 1.1 Plugin Interface
```python
class RuleEnginePlugin:
    """Rule engine plugin interface"""
    
    def before_engine_start(self, engine):
        """Called before engine starts"""
        pass
    
    def after_engine_finish(self, engine, results):
        """Called after engine finishes"""
        pass
    
    def before_rule_execute(self, rule, context):
        """Called before rule execution"""
        pass
    
    def after_rule_execute(self, rule, context, findings):
        """Called after rule execution"""
        pass
```

### 2. Custom Rule Loader

#### 2.1 Loader Interface
```python
class RuleLoader:
    """Rule loader interface"""
    
    def load_rules(self, source) -> List[Rule]:
        """Load rules from source"""
        pass


class YamlRuleLoader(RuleLoader):
    """YAML rule loader"""
    
    def load_rules(self, yaml_file: str) -> List[Rule]:
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
            return self._parse_rules(config['rules'])


class PythonModuleRuleLoader(RuleLoader):
    """Python module rule loader"""
    
    def load_rules(self, module_path: str) -> List[Rule]:
        module = importlib.import_module(module_path)
        rules = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, Rule):
                rules.append(attr)
        return rules
```

## Testing Strategy

### 1. Unit Testing

#### 1.1 Rule Engine Testing
```python
class TestRuleEngine(unittest.TestCase):
    """Rule engine tests"""
    
    def test_rule_registration(self):
        """Test rule registration"""
        registry = RuleRegistry()
        rule = NoGlobalScopeRule()
        registry.register(rule)
        self.assertIn("no_globalscope", registry.get_all_rule_ids())
    
    def test_rule_execution(self):
        """Test rule execution"""
        engine = RuleEngine()
        context = RuleContext(code="GlobalScope.launch {}", file_path="test.kt")
        findings = engine.execute_all(context)
        self.assertTrue(any(f.rule_id == "no_globalscope" for f in findings))
```

### 2. Integration Testing

#### 2.1 End-to-End Testing
```python
class TestFullReviewPipeline(unittest.TestCase):
    """Full review pipeline tests"""
    
    def test_end_to_end_review(self):
        """Test end-to-end review flow"""
        # 1. Create test code
        test_code = create_test_kotlin_code()
        
        # 2. Execute review
        result = review()
        
        # 3. Verify results
        self.assertIn("findings", result)
        self.assertIn("score", result)
        self.assertIn("block_pr", result)
        
        # 4. Verify report generation
        self.assertTrue(os.path.exists("report/code_review_report.html"))
```

## Deployment and Operations

### 1. Deployment Architecture

#### 1.1 Local Deployment
```
review_skill/
├── review.py              # Main entry
├── config.py             # Configuration management
├── rule_engine/          # Rule engine
├── rules/               # Rule implementations
├── tests/               # Test code
└── report/              # Generated reports
```

#### 1.2 CI/CD Integration
```yaml
# .github/workflows/review.yml
name: Code Review
on: [pull_request]
jobs:
  code-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -r review_skill/requirements.txt
      - name: Run code review
        run: |
          cd review_skill
          python3 review.py
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
```

### 2. Monitoring and Logging

#### 2.1 Log Configuration
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('review.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

## Troubleshooting and Debugging

### 1. Common Issues

#### 1.1 Rule Engine Initialization Failed
**Symptoms**: Rules cannot be loaded or executed
**Possible Causes**:
- Missing dependency packages
- Configuration file errors
- Rule definition syntax errors

**Solutions**:
```bash
# Check dependencies
pip install -r requirements.txt

# Check configuration
python3 -c "import json; json.load(open('review_config.json'))"

# Enable debug logging
export LOG_LEVEL=DEBUG
python3 review.py
```

#### 1.2 Performance Issues
**Symptoms**: Review process is very slow
**Possible Causes**:
- Too many or too complex rules
- Codebase too large
- Cache not effective

**Solutions**:
```bash
# Enable parallel execution
export RULE_ENGINE_PARALLEL=true

# Adjust thread count
export MAX_WORKERS=4

# Clear cache
python3 -c "from rule_engine.engine import RuleEngine; RuleEngine().clear_cache()"
```

### 2. Debugging Tools

#### 2.1 Debug Mode
```python
# Enable verbose debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Add debug points in review.py
def debug_review():
    config = get_config()
    print(f"Configuration: {config.__dict__}")
    
    raw_diff = get_git_diff()
    print(f"Raw diff length: {len(raw_diff)}")
    
    # ... other debug output
```

## Future Evolution Roadmap

### 1. Short-term (1-3 months)
1. **Rule Engine Optimization**: Improve caching strategy and parallel processing
2. **Rule Library Expansion**: Add more Android best practice rules
3. **Integration Improvements**: Enhance CI/CD integration and IDE plugins

### 2. Medium-term (3-6 months)
1. **Smart Analysis**: Introduce machine learning to optimize rule execution order
2. **Incremental Scanning**: Only analyze changed files and code
3. **Team Collaboration**: Support team rule sharing and configuration management

### 3. Long-term (6-12 months)
1. **Cloud Service**: Provide cloud-based code review service
2. **Advanced Analysis**: Support architecture-level and design pattern analysis
3. **Ecosystem Integration**: Integrate with more development tools and platforms

## Summary

Android Review Skill is a modular, extensible, high-performance code review tool. Its core architecture is based on a unified rule engine, supporting multiple rule definition methods, providing a complete review pipeline. Through carefully designed component separation, cache optimization, and parallel processing, the tool can provide excellent performance while ensuring accuracy. Whether for local development, team collaboration, or CI/CD integration, it can provide a consistently excellent experience.

---

**Version**: 1.0.2  
**Last Updated**: February 28, 2025
