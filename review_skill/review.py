import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from config import get_config
import traceback

# 尝试导入 LLM 层，如果可用的话
LLM_AVAILABLE = False
try:
    from llm_layer import semantic_review
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("⚠ llm_layer 导入失败，跳过LLM语义分析")
except Exception as e:
    LLM_AVAILABLE = False
    print(f"⚠ LLM层初始化失败: {e}")

# 导入统一规则引擎
RULE_ENGINE_AVAILABLE = False
try:
    from rule_engine.integration.review_runner import ReviewRunner
    from rule_engine.interfaces import ReviewError, ConfigurationError, IntegrationError
    RULE_ENGINE_AVAILABLE = True
    print("✓ 统一规则引擎可用")
except ImportError as e:
    RULE_ENGINE_AVAILABLE = False
    print(f"⚠ 规则引擎导入失败: {e}")
    # 回退到旧的错误处理
    class ReviewError(Exception):
        pass
    class ConfigurationError(ReviewError):
        pass
    class IntegrationError(ReviewError):
        pass
except Exception as e:
    RULE_ENGINE_AVAILABLE = False
    print(f"⚠ 规则引擎初始化失败: {e}")

# 尝试导入HTML报告生成器
REPORT_GENERATOR_AVAILABLE = False
try:
    from report_generator import GitDiffParser, HTMLReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError as e:
    REPORT_GENERATOR_AVAILABLE = False
    print(f"⚠ 报告生成器导入失败: {e}")
except Exception as e:
    REPORT_GENERATOR_AVAILABLE = False
    print(f"⚠ 报告生成器初始化失败: {e}")


# 获取 git diff
def get_git_diff():
    # 尝试多种方式获取代码变更
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
    
    # 如果都没有变更，返回空字符串
    return ""


def _review_with_new_engine(diff: str, config) -> Dict:
    """使用新引擎进行审查"""
    try:
        from rule_engine.integration.review_runner import ReviewRunner
        
        # 创建运行器
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
        
        # 审查diff
        results = runner.review_diff(diff)
        
        # 合并所有发现
        all_findings = []
        total_score = 0
        file_count = 0
        
        for file_result in results:
            all_findings.extend(file_result["findings"])
            total_score += file_result["score"]
            file_count += 1
        
        # 计算平均分
        score = total_score // file_count if file_count > 0 else 100
        
        min_score = config.get_min_score_threshold()
        block_pr = score < min_score or any(f.get("severity") == "critical" for f in all_findings)
        
        return {
            "findings": all_findings,
            "score": max(0, score),
            "block_pr": block_pr,
            "engine": "new",
            "file_count": file_count,
            "engine_info": runner.get_engine_info()
        }
    except Exception as e:
        print(f"⚠ 新规则引擎执行失败: {e}")
        import traceback
        traceback.print_exc()
        # 回退到旧引擎
        return _review_with_old_engine(diff, config)


def _review_with_old_engine(diff: str, config) -> Dict:
    """回退到旧引擎进行审查"""
    try:
        # 尝试导入旧规则模块
        from rules.base_rules import run_base_rules
        from rules.coroutine_rules import run_coroutine_rules
        from rules.compose_rules import run_compose_rules
        from rules.hilt_rules import run_hilt_rules
        from rules.flow_rules import run_flow_rules
        from rules.flow_lifecycle_rules import run_flow_lifecycle_rules
        from rules.flow_structure_rules import run_flow_structure_rules
        from scorer import calculate_score
        
        findings = []
        findings += run_base_rules(diff)
        findings += run_coroutine_rules(diff)
        findings += run_compose_rules(diff)
        findings += run_hilt_rules(diff)
        findings += run_flow_rules(diff)
        findings += run_flow_lifecycle_rules(diff)
        findings += run_flow_structure_rules(diff)
        
        score = calculate_score(findings)
        
        min_score = config.get_min_score_threshold()
        block_pr = score < min_score or any(f.get("severity") == "critical" for f in findings)
        
        return {
            "findings": findings,
            "score": score,
            "block_pr": block_pr,
            "engine": "old_fallback"
        }
    except ImportError as e:
        print(f"⚠ 旧规则引擎导入失败: {e}")
        print("❌ 没有可用的规则引擎，审查无法进行")
        raise ReviewError("没有可用的规则引擎") from e


def review():
    # 获取配置
    config = get_config()
    
    # 获取原始的git diff
    raw_diff = get_git_diff()
    
    if not raw_diff.strip():
        print("No changes to review. Git diff is empty.")
        return
    
    # 过滤diff，只扫描符合配置的文件
    diff = config.filter_git_diff(raw_diff)
    
    if not diff.strip():
        print("没有需要扫描的文件变更。")
        print(f"配置的文件扩展名: {config.get_file_extensions()}")
        print(f"配置的扫描目录: {config.get_scan_directories()}")
        return

    # 总是使用统一规则引擎（如果可用）
    if RULE_ENGINE_AVAILABLE:
        print("使用统一规则引擎进行审查...")
        try:
            result = _review_with_new_engine(diff, config)
        except Exception as e:
            print(f"⚠ 统一规则引擎执行失败: {e}")
            print("回退到旧规则引擎...")
            result = _review_with_old_engine(diff, config)
    else:
        print("统一规则引擎不可用，使用旧规则引擎...")
        result = _review_with_old_engine(diff, config)
    
    # 如果 LLM 可用且有代码变更，进行语义审查
    llm_findings = []
    if LLM_AVAILABLE and diff.strip() and config.is_enabled_semantic_review():
        try:
            # 限制代码长度，避免超过 token 限制
            code_sample = diff[:2000]  # 取前2000个字符进行语义分析
            llm_result = semantic_review(code_sample)
            if llm_result:
                llm_findings.append({
                    "severity": "info",
                    "rule": "llm_semantic_review",
                    "message": f"LLM语义分析: {llm_result}"
                })
        except Exception as e:
            llm_findings.append({
                "severity": "warning",
                "rule": "llm_error",
                "message": f"LLM语义分析失败: {str(e)}"
            })
    
    # 合并所有发现
    all_findings = result["findings"] + llm_findings

    # 更新结果
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

    # 生成HTML报告
    if REPORT_GENERATOR_AVAILABLE and diff.strip():
        try:
            # 解析git diff
            diff_data = GitDiffParser.parse(diff)
            
            # 生成HTML报告 - 保存到report目录
            report_dir = Path(__file__).parent / 'report'
            report_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_report_path = report_dir / f'code_review_report_{timestamp}.html'
            json_report_path = report_dir / f'code_review_details_{timestamp}.json'
            
            report_path = HTMLReportGenerator.generate_report(
                diff_data=diff_data,
                findings=result["findings"],  # 使用所有发现（包括LLM）
                score=result["score"],
                output_path=str(html_report_path)
            )
            
            print(f"\n📊 HTML报告已生成: {report_path}")
            print(f"📂 打开报告: open {report_path}")
            print(f"📁 报告目录: {report_dir}")
            
            # 同时生成一个更详细的JSON报告
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
            
            # 按包名分组
            for file_data in diff_data:
                package = file_data['package']
                if package not in detailed_result["files_by_package"]:
                    detailed_result["files_by_package"][package] = []
                detailed_result["files_by_package"][package].append({
                    "file": file_data['new_path'],
                    "language": file_data['language']
                })
            
            # 保存详细JSON报告到report目录
            with open(json_report_path, 'w', encoding='utf-8') as f:
                json.dump(detailed_result, f, indent=2, ensure_ascii=False)
            
            print(f"📝 详细JSON报告: {json_report_path}")
            
        except Exception as e:
            print(f"⚠ HTML报告生成失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        if not REPORT_GENERATOR_AVAILABLE:
            print("⚠ HTML报告生成器不可用，跳过HTML报告生成")
        else:
            print("⚠ 没有代码变更，跳过HTML报告生成")

    if result["block_pr"]:
        exit(1)


if __name__ == "__main__":
    review()
