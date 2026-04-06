import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from config import get_config
import traceback

# Import i18n module
from i18n import init_i18n, _

# Try to import LLM layer if available
LLM_AVAILABLE = False
try:
    from llm_layer import semantic_review
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print(_("⚠ llm_layer import failed, skipping LLM semantic analysis"))
except Exception as e:
    LLM_AVAILABLE = False
    print(_("⚠ LLM layer initialization failed: {error}").format(error=e))

# Import unified engine (preferred)
UNIFIED_ENGINE_AVAILABLE = False
try:
    from unified_engine.engine import UnifiedExecutionEngine
    UNIFIED_ENGINE_AVAILABLE = True
    print(_("✓ Using unified engine (recommended)"))
except ImportError as e:
    UNIFIED_ENGINE_AVAILABLE = False
    print(_("⚠ Unified engine not available: {error}"))

# Import legacy rule engine (deprecated - fallback only)
RULE_ENGINE_AVAILABLE = False
try:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from rule_engine.integration.review_runner import ReviewRunner
        from rule_engine.interfaces import ReviewError, ConfigurationError, IntegrationError
    RULE_ENGINE_AVAILABLE = True
    print(_("⚠ Using legacy rule engine (deprecated)"))
except ImportError as e:
    RULE_ENGINE_AVAILABLE = False
    print(_("⚠ Legacy rule engine import failed: {error}"))
except Exception as e:
    RULE_ENGINE_AVAILABLE = False
    print(_("⚠ Legacy rule engine initialization failed: {error}"))

# Import legacy AST Engine (deprecated)
AST_ENGINE_AVAILABLE = False
try:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from ast_engine.integration import ASTEngine, is_ast_engine_enabled
    AST_ENGINE_AVAILABLE = True
    if UNIFIED_ENGINE_AVAILABLE:
        print(_("⚠ AST engine available but not needed (using unified engine)"))
except ImportError as e:
    AST_ENGINE_AVAILABLE = False
except Exception as e:
    AST_ENGINE_AVAILABLE = False

# Try to import HTML report generator
REPORT_GENERATOR_AVAILABLE = False
try:
    from report_generator import GitDiffParser, HTMLReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError as e:
    REPORT_GENERATOR_AVAILABLE = False
    print(_("⚠ Report generator import failed: {error}").format(error=e))
except Exception as e:
    REPORT_GENERATOR_AVAILABLE = False
    print(_("⚠ Report generator initialization failed: {error}").format(error=e))


# Get git diff
def get_git_diff():
    # Try multiple ways to get code changes
    diff_commands = [
        ["git", "diff", "original/develop...HEAD"],
        ["git", "diff", "HEAD~1", "HEAD"],
        ["git", "diff", "--staged"]
    ]
    
    for cmd in diff_commands:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            return result.stdout
    
    # If no changes found, return empty string
    return ""


def _review_with_new_engine(diff: str, config) -> Dict:
    """Review using new engine"""
    try:
        from rule_engine.integration.review_runner import ReviewRunner
        
        # Create runner
        new_engine_config = config.get("rule_engine.new_engine_config", {})
        runner_config = {
            "rules": {
                "enabled_categories": new_engine_config.get("enabled_categories", ["security", "performance", "correctness"]),
                "disabled_rules": new_engine_config.get("disabled_rules", []),
                "parallel_execution": new_engine_config.get("parallel_execution", True)
            }
        }
        
        runner = ReviewRunner(runner_config)
        runner.initialize()
        
        # Review diff
        results = runner.review_diff(diff)
        
        # Merge all findings
        all_findings = []
        total_score = 0
        file_count = 0
        
        for file_result in results:
            all_findings.extend(file_result["findings"])
            total_score += file_result["score"]
            file_count += 1
        
        # Calculate average score
        score = total_score // file_count if file_count > 0 else 100
        
        # Check for block issues (blocker severity)
        block_issues = [f for f in all_findings if f.get("severity") == "blocker"]
        
        min_score = config.get_min_score_threshold()
        block_pr = score < min_score or any(f.get("severity") == "critical" for f in all_findings) or len(block_issues) > 0
        
        return {
            "findings": all_findings,
            "score": max(0, score),
            "block_pr": block_pr,
            "block_issues": block_issues,
            "engine": "new",
            "file_count": file_count,
            "engine_info": runner.get_engine_info()
        }
    except Exception as e:
        print(_("⚠ New rule engine execution failed: {error}").format(error=e))
        import traceback
        traceback.print_exc()
        # Fallback to old engine
        return _review_with_old_engine(diff, config)


def _review_with_old_engine(diff: str, config) -> Dict:
    """Fallback to base engine for review (all rules migrated to new engine)"""
    try:
        # Try to use base new engine configuration
        from rule_engine.integration.review_runner import ReviewRunner
        
        # Create base runner with minimal configuration
        runner_config = {
            "rules": {
                "enabled_categories": ["lifecycle", "concurrency", "correctness"],
                "parallel_execution": False  # Disable parallel execution for compatibility
            }
        }
        
        runner = ReviewRunner(runner_config)
        runner.initialize()
        
        # Review diff
        results = runner.review_diff(diff)
        
        # Merge all findings
        all_findings = []
        total_score = 0
        file_count = 0
        
        for file_result in results:
            all_findings.extend(file_result["findings"])
            total_score += file_result["score"]
            file_count += 1
        
        # Calculate average score
        score = total_score // file_count if file_count > 0 else 100
        
        # Check for block issues (blocker severity)
        block_issues = [f for f in all_findings if f.get("severity") == "blocker"]
        
        min_score = config.get_min_score_threshold()
        block_pr = score < min_score or any(f.get("severity") == "critical" for f in all_findings) or len(block_issues) > 0
        
        return {
            "findings": all_findings,
            "score": max(0, score),
            "block_pr": block_pr,
            "block_issues": block_issues,
            "engine": "fallback_new_engine",
            "file_count": file_count,
            "engine_info": runner.get_engine_info()
        }
    except Exception as e:
        print(_("⚠ Fallback engine execution failed: {error}").format(error=e))
        import traceback
        traceback.print_exc()
        # Final fallback: return empty result
        return {
            "findings": [],
            "score": 100,
            "block_pr": False,
            "block_issues": [],
            "engine": "empty_fallback"
        }


def _review_with_ast_engine(diff: str, config) -> Dict:
    """Review using AST engine"""
    try:
        from ast_engine.integration import ASTEngine
        
        # Create AST engine
        ast_config = {
            "disabled_rules": config.get("ast_engine.disabled_rules", [])
        }
        engine = ASTEngine(ast_config)
        
        # Review diff
        result = engine.review_diff(diff)
        
        # Convert findings to dict format
        all_findings = [f.to_dict() for f in result.findings]
        
        # Calculate score based on findings
        # Start with 100, subtract based on severity
        score = 100
        for finding in result.findings:
            if finding.severity.value == "error":
                score -= 10
            elif finding.severity.value == "warning":
                score -= 5
            elif finding.severity.value == "info":
                score -= 1
        
        score = max(0, score)
        
        # Check for block issues (error severity)
        block_issues = [f for f in all_findings if f.get("severity") == "error"]
        
        min_score = config.get_min_score_threshold()
        block_pr = score < min_score or len(block_issues) > 0
        
        return {
            "findings": all_findings,
            "score": score,
            "block_pr": block_pr,
            "block_issues": block_issues,
            "engine": "ast_engine",
            "file_count": result.files_scanned,
            "engine_info": result.engine_info,
            "scan_time": result.total_time
        }
    except Exception as e:
        print(_("⚠ AST engine execution failed: {error}").format(error=e))
        import traceback
        traceback.print_exc()
        # Fallback to new engine
        return _review_with_new_engine(diff, config)


def review():
    # Get configuration
    config = get_config()
    
    # Get raw git diff
    raw_diff = get_git_diff()
    
    if not raw_diff.strip():
        print(_("No changes to review. Git diff is empty."))
        return
    
    # Filter diff to only scan files matching configuration
    diff = config.filter_git_diff(raw_diff)
    
    if not diff.strip():
        print(_("No files to scan."))
        print(_("Configured file extensions: {extensions}").format(extensions=config.get_file_extensions()))
        print(_("Configured scan directories: {directories}").format(directories=config.get_scan_directories()))
        return

    # Choose engine based on configuration
    # Priority: AST Engine (if enabled) > Unified Rule Engine > Fallback
    
    if AST_ENGINE_AVAILABLE and is_ast_engine_enabled():
        print(_("Using AST engine for review..."))
        try:
            result = _review_with_ast_engine(diff, config)
        except Exception as e:
            print(_("⚠ AST engine execution failed: {error}").format(error=e))
            print(_("Fallback to unified rule engine..."))
            if RULE_ENGINE_AVAILABLE:
                result = _review_with_new_engine(diff, config)
            else:
                result = _review_with_old_engine(diff, config)
    elif RULE_ENGINE_AVAILABLE:
        print(_("Using unified rule engine for review..."))
        try:
            result = _review_with_new_engine(diff, config)
        except Exception as e:
            print(_("⚠ Unified rule engine execution failed: {error}").format(error=e))
            print(_("Fallback to old rule engine..."))
            result = _review_with_old_engine(diff, config)
    else:
        print(_("Unified rule engine not available, using old rule engine..."))
        result = _review_with_old_engine(diff, config)
    
    # If LLM is available and there are code changes, perform semantic review
    llm_findings = []
    if LLM_AVAILABLE and diff.strip() and config.is_enabled_semantic_review():
        try:
            # Limit code length to avoid exceeding token limit
            code_sample = diff[:2000]  # Take first 2000 characters for semantic analysis
            llm_result = semantic_review(code_sample)
            if llm_result:
                llm_findings.append({
                    "severity": "info",
                    "rule": "llm_semantic_review",
                    "message": f"LLM Semantic Analysis: {llm_result}"
                })
        except Exception as e:
            llm_findings.append({
                "severity": "warning",
                "rule": "llm_error",
                "message": f"LLM semantic analysis failed: {str(e)}"
            })
    
    # Merge all findings
    all_findings = result["findings"] + llm_findings

    # Update result
    result["findings"] = all_findings
    result["llm_available"] = LLM_AVAILABLE
    result["config"] = {
        "file_extensions": config.get_file_extensions(),
        "scan_directories": config.get_scan_directories(),
        "min_score_threshold": config.get_min_score_threshold(),
        "filtered_diff": diff != raw_diff,
        "rule_engine_available": RULE_ENGINE_AVAILABLE,
        "engine_used": result.get("engine", "unknown")
    }

    print(json.dumps(result, indent=2))

    # Generate HTML report
    if REPORT_GENERATOR_AVAILABLE and diff.strip():
        try:
            # Parse git diff
            diff_data = GitDiffParser.parse(diff)
            
            # Generate HTML report - save to report directory
            report_dir = Path(__file__).parent / 'report'
            report_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_report_path = report_dir / f'code_review_report_{timestamp}.html'
            json_report_path = report_dir / f'code_review_details_{timestamp}.json'
            
            report_path = HTMLReportGenerator.generate_report(
                diff_data=diff_data,
                findings=result["findings"],  # Use all findings (including LLM)
                score=result["score"],
                output_path=str(html_report_path),
                block_issues=result.get("block_issues", [])
            )
            
            print(_("\n📊 HTML report generated: {path}").format(path=report_path))
            print(_("📂 Open report: open {path}").format(path=report_path))
            print(_("📁 Report directory: {directory}").format(directory=report_dir))
            
            # Also generate a more detailed JSON report
            detailed_result = {
                "timestamp": datetime.now().isoformat(),
                "diff_files_count": len(diff_data),
                "files_by_package": {},
                "detailed_findings": result["findings"],
                "score": result["score"],
                "block_pr": result["block_pr"],
                "llm_available": LLM_AVAILABLE,
                "report_generator_available": REPORT_GENERATOR_AVAILABLE,
                "engine": result.get("engine", "unknown"),
                "file_count": result.get("file_count", 0)
            }
            
            # Group by package name
            for file_data in diff_data:
                package = file_data['package']
                if package not in detailed_result["files_by_package"]:
                    detailed_result["files_by_package"][package] = []
                detailed_result["files_by_package"][package].append({
                    "file": file_data['new_path'],
                    "language": file_data['language']
                })
            
            # Save detailed JSON report to report directory
            with open(json_report_path, 'w', encoding='utf-8') as f:
                json.dump(detailed_result, f, indent=2, ensure_ascii=False)
            
            print(_("📝 Detailed JSON report: {path}").format(path=json_report_path))
            
        except Exception as e:
            print(_("⚠ HTML report generation failed: {error}").format(error=e))
            import traceback
            traceback.print_exc()
    else:
        if not REPORT_GENERATOR_AVAILABLE:
            print(_("⚠ Report generator not available, skip HTML report generation"))
        else:
            print(_("⚠ No code changes, skip HTML report generation"))

    if result["block_pr"]:
        exit(1)


if __name__ == "__main__":
    review()
