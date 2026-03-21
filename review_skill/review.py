import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import traceback

# Import i18n module first (needed for error messages)
import i18n

# Initialize i18n before any other operations
i18n.init_i18n()
# Get the translation function
_ = i18n._

# Import config after i18n
from config import get_config

# Try to import LLM layer if available
LLM_AVAILABLE = False
try:
    from llm_layer import semantic_review
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("⚠ llm_layer import failed, skipping LLM semantic analysis")
except Exception as e:
    LLM_AVAILABLE = False
    print(f"⚠ LLM layer initialization failed: {e}")

# Import unified rule engine
RULE_ENGINE_AVAILABLE = False
try:
    from rule_engine.integration.review_runner import ReviewRunner
    from rule_engine.interfaces import ReviewError, ConfigurationError, IntegrationError
    RULE_ENGINE_AVAILABLE = True
    print(_("✓ Unified rule engine available"))
except ImportError as e:
    RULE_ENGINE_AVAILABLE = False
    print(_("⚠ Rule engine import failed: {error}").format(error=e))
    # Fallback to old error handling
    class ReviewError(Exception):
        pass
    class ConfigurationError(ReviewError):
        pass
    class IntegrationError(ReviewError):
        pass
except Exception as e:
    RULE_ENGINE_AVAILABLE = False
    print(_("⚠ Rule engine initialization failed: {error}").format(error=e))

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


def _extract_file_from_location(location: str) -> str:
    """Extracts file path from location string like 'MainActivity.kt lines 50-68' or 'TestClass.kt lines 5-7'"""
    if not location:
        return ""
    
    import re
    # Try to extract filename from location
    # Patterns: "MainActivity.kt lines 50-68" or "TestClass.kt lines 5-7"
    pattern = r'^([a-zA-Z0-9_]+\.(?:kt|java))\s+lines\s+\d+(?:-\d+)?'
    match = re.search(pattern, location)
    if match:
        filename = match.group(1)
        # Try to infer full path (simple heuristic)
        if filename.endswith('.kt'):
            return f"app/src/main/java/com/yxhuang/flowforandroid/{filename}"
        elif filename.endswith('.java'):
            return f"app/src/main/java/com/yxhuang/flowforandroid/{filename}"
        return filename
    
    # If no match, return original location or empty
    return location if '.' in location else ""


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
        
        min_score = config.get_min_score_threshold()
        block_pr = score < min_score or any(f.get("severity") == "critical" for f in all_findings)
        
        return {
            "findings": all_findings,
            "score": max(0, score),
            "block_pr": block_pr,
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
            "engine": "empty_fallback"
        }


def review():
    global _
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

    # Always use unified rule engine (if available)
    if RULE_ENGINE_AVAILABLE:
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
    llm_analysis_data = None  # Store structured LLM analysis data for report
    if LLM_AVAILABLE and diff.strip() and config.is_enabled_semantic_review():
        try:
            # Limit code length to avoid exceeding token limit
            code_sample = diff[:2000]  # Take first 2000 characters for semantic analysis
            llm_result = semantic_review(code_sample)
            if llm_result:
                print(_("🔍 LLM result received, length: {length}").format(length=len(llm_result)))
                # Try to parse LLM result as JSON
                try:
                    # First, extract JSON if it's wrapped in markdown code blocks
                    import re
                    import json
                    
                    # Remove markdown code block markers if present
                    cleaned_result = llm_result.strip()
                    print(_("🔍 LLM result after strip, length: {length}").format(length=len(cleaned_result)))
                    print(_("🔍 First 200 chars: {preview}").format(preview=cleaned_result[:200]))
                    
                    # Try multiple JSON extraction patterns
                    # Find content between ```json and ``` markers
                    json_match = None
                    extraction_log = []  # 记录提取过程用于调试
                    
                    # Debug: print actual characters
                    extraction_log.append(f"🔍 [JSON提取] LLM响应总长度: {len(cleaned_result)}")
                    extraction_log.append(f"🔍 [JSON提取] 前100字符: {repr(cleaned_result[:100])}")
                    extraction_log.append(f"🔍 [JSON提取] 后100字符: {repr(cleaned_result[-100:])}")
                    
                    # Method 1: Find ```json ... ``` pattern
                    start_marker = '```json'
                    end_marker = '```'
                    extraction_log.append(f"🔍 [JSON提取-方法1] 查找起始标记: {repr(start_marker)}")
                    start_idx = cleaned_result.find(start_marker)
                    extraction_log.append(f"🔍 [JSON提取-方法1] 起始标记位置: {start_idx}")
                    
                    if start_idx != -1:
                        # Find the content after ```json
                        content_start = start_idx + len(start_marker)
                        # Skip any leading newlines or whitespace
                        while content_start < len(cleaned_result) and cleaned_result[content_start] in '\n\r\t ':
                            content_start += 1
                        extraction_log.append(f"🔍 [JSON提取-方法1] 内容起始位置: {content_start}")
                        
                        # Find the closing ``` - search from content_start onwards
                        end_idx = cleaned_result.find(end_marker, content_start)
                        extraction_log.append(f"🔍 [JSON提取-方法1] 结束标记位置: {end_idx}")
                        
                        # If no closing marker found, try to extract from content_start to end of string
                        if end_idx == -1:
                            extraction_log.append(f"🔍 [JSON提取-方法1] 未找到结束标记，尝试提取到字符串末尾")
                            json_content = cleaned_result[content_start:].strip()
                        else:
                            json_content = cleaned_result[content_start:end_idx].strip()
                        
                        if json_content:
                            extraction_log.append(f"🔍 [JSON提取-方法1] 提取内容长度: {len(json_content)}")
                            extraction_log.append(f"🔍 [JSON提取-方法1] 提取内容前50字符: {repr(json_content[:50])}")
                            extraction_log.append(f"🔍 [JSON提取-方法1] 提取内容后50字符: {repr(json_content[-50:])}")
                            
                            # Try to find valid JSON object in the extracted content
                            # Look for balanced braces
                            depth = 0
                            json_end = -1
                            for i, char in enumerate(json_content):
                                if char == '{':
                                    if depth == 0:
                                        json_start = i
                                    depth += 1
                                elif char == '}':
                                    depth -= 1
                                    if depth == 0:
                                        json_end = i + 1
                                        break
                            
                            if json_end > 0:
                                extracted_json = json_content[:json_end]
                                extraction_log.append(f"🔍 [JSON提取-方法1] 找到平衡的大括号，JSON长度: {len(extracted_json)}")
                                try:
                                    # Validate it's valid JSON
                                    test_data = json.loads(extracted_json)
                                    cleaned_result = extracted_json
                                    json_match = True
                                    extraction_log.append("✓ [JSON提取-方法1] 成功提取并验证JSON")
                                except json.JSONDecodeError as e:
                                    extraction_log.append(f"⚠ [JSON提取-方法1] JSON验证失败: {e}")
                                    # Still use the extracted content for further processing
                                    cleaned_result = extracted_json
                                    extraction_log.append("🔍 [JSON提取-方法1] 使用提取的内容继续尝试")
                            else:
                                extraction_log.append(f"⚠ [JSON提取-方法1] 未找到平衡的大括号结构")
                                # Try to use the content as-is if it starts with {
                                if json_content.startswith('{'):
                                    cleaned_result = json_content
                                    extraction_log.append("🔍 [JSON提取-方法1] 内容以'{'开头，将尝试解析")
                                else:
                                    extraction_log.append(f"⚠ [JSON提取-方法1] 内容不以'{{'开头，实际开头: {repr(json_content[:20])}")
                        else:
                            extraction_log.append(f"⚠ [JSON提取-方法1] 提取的内容为空")
                    else:
                        extraction_log.append("⚠ [JSON提取-方法1] 未找到起始标记```json")
                    
                    # Method 2: If Method 1 failed, try ``` without json label
                    if not json_match:
                        extraction_log.append("🔍 [JSON提取-方法2] 尝试查找普通代码块```...```")
                        start_marker = '```'
                        start_idx = cleaned_result.find(start_marker)
                        extraction_log.append(f"🔍 [JSON提取-方法2] 起始标记位置: {start_idx}")
                        if start_idx != -1:
                            content_start = start_idx + len(start_marker)
                            end_idx = cleaned_result.find(end_marker, content_start)
                            extraction_log.append(f"🔍 [JSON提取-方法2] 结束标记位置: {end_idx}")
                            if end_idx != -1:
                                json_content = cleaned_result[content_start:end_idx].strip()
                                extraction_log.append(f"🔍 [JSON提取-方法2] 提取内容长度: {len(json_content)}")
                                extraction_log.append(f"🔍 [JSON提取-方法2] 提取内容前30字符: {repr(json_content[:30])}")
                                if json_content.startswith('{') and json_content.endswith('}'):
                                    cleaned_result = json_content
                                    json_match = True
                                    extraction_log.append("✓ [JSON提取-方法2] 成功提取JSON")
                                else:
                                    extraction_log.append(f"⚠ [JSON提取-方法2] 内容格式不符，开头: {repr(json_content[:10])}, 结尾: {repr(json_content[-10:])}")
                            else:
                                extraction_log.append("⚠ [JSON提取-方法2] 未找到结束标记")
                        else:
                            extraction_log.append("⚠ [JSON提取-方法2] 未找到起始标记```")
                    
                    # Method 3: Try direct JSON extraction using brace matching
                    if not json_match:
                        extraction_log.append("🔍 [JSON提取-方法3] 尝试使用大括号匹配")
                        try:
                            depth = 0
                            start = -1
                            json_blocks = []
                            
                            for i, char in enumerate(cleaned_result):
                                if char == '{':
                                    if depth == 0:
                                        start = i
                                    depth += 1
                                elif char == '}':
                                    depth -= 1
                                    if depth == 0 and start != -1:
                                        json_blocks.append(cleaned_result[start:i+1])
                            
                            extraction_log.append(f"🔍 [JSON提取-方法3] 找到 {len(json_blocks)} 个JSON块")
                            
                            if json_blocks:
                                # Use the longest block (likely the main JSON object)
                                longest_block = max(json_blocks, key=len)
                                extraction_log.append(f"🔍 [JSON提取-方法3] 最长块长度: {len(longest_block)}")
                                extraction_log.append(f"🔍 [JSON提取-方法3] 最长块前50字符: {repr(longest_block[:50])}")
                                
                                # Try to parse it
                                try:
                                    test_data = json.loads(longest_block)
                                    cleaned_result = longest_block
                                    json_match = True
                                    extraction_log.append("✓ [JSON提取-方法3] 成功解析JSON")
                                except json.JSONDecodeError as e:
                                    extraction_log.append(f"⚠ [JSON提取-方法3] JSON解析失败: {e}")
                            else:
                                extraction_log.append("⚠ [JSON提取-方法3] 未找到任何JSON块")
                        except Exception as e:
                            extraction_log.append(f"⚠ [JSON提取-方法3] 处理异常: {e}")
                    
                    # Method 4: Check if entire response is JSON
                    if not json_match:
                        extraction_log.append("🔍 [JSON提取-方法4] 检查整个响应是否为JSON")
                        try:
                            test_data = json.loads(cleaned_result)
                            extraction_log.append("✓ [JSON提取-方法4] 整个响应是有效JSON")
                            json_match = True
                        except json.JSONDecodeError as e:
                            extraction_log.append(f"⚠ [JSON提取-方法4] 不是有效JSON: {e}")
                    
                    # Method 5: Try to fix incomplete JSON by finding the last complete element
                    if not json_match:
                        extraction_log.append("🔍 [JSON提取-方法5] 尝试修复不完整的JSON")
                        try:
                            result_copy = cleaned_result
                            fixed = False
                            
                            # Strategy: The JSON is incomplete, so we need to find where to truncate
                            # and then add closing brackets. Look for positions where we can
                            # close all open structures.
                            
                            # First, let's understand the structure by tracking depths
                            def get_depths(text):
                                """Track brace and bracket depths at each position"""
                                depths = []
                                depth_brace = 0
                                depth_bracket = 0
                                in_string = False
                                escape = False
                                
                                for i, char in enumerate(text):
                                    depths.append((depth_brace, depth_bracket, in_string))
                                    
                                    if escape:
                                        escape = False
                                        continue
                                    if char == '\\':
                                        escape = True
                                        continue
                                    if char == '"':
                                        in_string = not in_string
                                        continue
                                    if in_string:
                                        continue
                                    
                                    if char == '{':
                                        depth_brace += 1
                                    elif char == '}':
                                        depth_brace -= 1
                                    elif char == '[':
                                        depth_bracket += 1
                                    elif char == ']':
                                        depth_bracket -= 1
                                
                                return depths
                            
                            depths = get_depths(result_copy)
                            extraction_log.append(f"🔍 [JSON提取-方法5] 文本长度: {len(result_copy)}, 深度跟踪长度: {len(depths)}")
                            
                            # Find potential truncation points
                            # We want positions where:
                            # 1. We're not inside a string
                            # 2. We're at a logical boundary (after }, ], or ,)
                            # 3. We can close all remaining open structures
                            
                            potential_stops = []
                            for i in range(len(result_copy) - 1, 50, -1):  # Search backwards from end
                                if i >= len(depths):
                                    continue
                                brace_depth, bracket_depth, in_str = depths[i]
                                
                                if in_str:
                                    continue
                                
                                char = result_copy[i]
                                # Look for logical stopping points
                                if char in '}],':
                                    potential_stops.append((i, brace_depth, bracket_depth, char))
                            
                            extraction_log.append(f"🔍 [JSON提取-方法5] 找到 {len(potential_stops)} 个潜在截断点")
                            
                            # Try each potential stop point
                            for stop_pos, open_braces, open_brackets, stop_char in potential_stops[:20]:  # Try first 20
                                # Truncate at this position (include the closing char)
                                truncated = result_copy[:stop_pos + 1]
                                
                                # If we stopped at a comma, we might need to remove it
                                if stop_char == ',':
                                    # Check if removing comma helps
                                    test_truncated = truncated.rstrip().rstrip(',')
                                else:
                                    test_truncated = truncated
                                
                                # Calculate how many brackets we need to close
                                # We need to close all structures that are still open at this point
                                braces_to_close = open_braces
                                brackets_to_close = open_brackets
                                
                                # Build the completion string
                                completion = ''
                                for __ in range(brackets_to_close):
                                    completion += ']'
                                for __ in range(braces_to_close):
                                    completion += '}'
                                
                                test_result = test_truncated + completion
                                
                                try:
                                    json.loads(test_result)
                                    cleaned_result = test_result
                                    json_match = True
                                    fixed = True
                                    extraction_log.append(f"✓ [JSON提取-方法5] 成功修复！截断位置: {stop_pos}, 停止字符: '{stop_char}', 闭合: {repr(completion)}, 最终长度: {len(cleaned_result)}")
                                    break
                                except json.JSONDecodeError:
                                    continue
                            
                            if not fixed:
                                extraction_log.append("⚠ [JSON提取-方法5] 所有潜在截断点尝试均失败")
                        except Exception as e:
                            extraction_log.append(f"⚠ [JSON提取-方法5] 修复过程出错: {e}")
                            import traceback
                            extraction_log.append(traceback.format_exc())
                        
                        # Fallback: try the original character-by-character approach
                        if not fixed:
                            extraction_log.append("🔍 [JSON提取-方法5] 尝试逐字符截断...")
                            result_copy = cleaned_result
                            while len(result_copy) > 100:
                                try:
                                    json.loads(result_copy)
                                    cleaned_result = result_copy
                                    json_match = True
                                    extraction_log.append(f"✓ [JSON提取-方法5] 成功修复，保留 {len(cleaned_result)} 字符")
                                    break
                                except json.JSONDecodeError:
                                    result_copy = result_copy[:-1]
                            
                            if not json_match:
                                extraction_log.append("⚠ [JSON提取-方法5] 所有修复尝试均失败")
                    
                    # Print extraction log
                    for log_entry in extraction_log:
                        print(log_entry)
                    
                    if json_match:
                        print(_("🔍 Extracted JSON length: {length}").format(length=len(cleaned_result)))
                        print(_("🔍 Extracted first 200 chars: {preview}").format(preview=cleaned_result[:200]))
                    else:
                        print(_("⚠ 所有JSON提取方法均失败"))
                    
                    # Parse JSON
                    try:
                        analysis_data = json.loads(cleaned_result)
                        print(_("✓ JSON parsed successfully"))
                        print(_("🔍 Parsed data type: {type}").format(type=type(analysis_data)))
                        
                    except json.JSONDecodeError as json_err:
                        print(_("⚠ Direct JSON parse failed: {error}").format(error=json_err))
                        print(_("🔍 Original text first 500 chars: {preview}").format(preview=llm_result[:500]))
                        print(_("🔍 Trying to find JSON object in text with aggressive pattern..."))
                        
                        # Try to extract JSON object more aggressively - use simple balanced brace matching
                        # Since Python re doesn't support (?R) for recursion, we'll use a simpler approach
                        import re
                        
                        # Try to find the outermost { ... } block
                        # This is a simplified approach that works for most JSON responses
                        depth = 0
                        start = -1
                        json_blocks = []
                        
                        for i, char in enumerate(cleaned_result):
                            if char == '{':
                                if depth == 0:
                                    start = i
                                depth += 1
                            elif char == '}':
                                depth -= 1
                                if depth == 0 and start != -1:
                                    json_blocks.append(cleaned_result[start:i+1])
                        
                        if json_blocks:
                            print(_("✓ Found {count} JSON-like blocks using balanced matching").format(count=len(json_blocks)))
                            # Use the longest block (likely the main JSON object)
                            cleaned_result = max(json_blocks, key=len)
                            print(_("🔍 Longest block length: {length}").format(length=len(cleaned_result)))
                            print(_("🔍 Longest block first 200 chars: {preview}").format(preview=cleaned_result[:200]))
                            
                            try:
                                analysis_data = json.loads(cleaned_result)
                                print(_("✓ JSON parsed from balanced extraction"))
                            except json.JSONDecodeError as nested_err:
                                print(_("⚠ Balanced extraction failed: {error}").format(error=nested_err))
                                # Try one more approach: find JSON with regex looking for { ... } with content
                                json_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
                                matches = re.findall(json_pattern, cleaned_result, re.DOTALL)
                                if matches:
                                    cleaned_result = max(matches, key=len)
                                    try:
                                        analysis_data = json.loads(cleaned_result)
                                        print(_("✓ JSON parsed from regex fallback"))
                                    except json.JSONDecodeError:
                                        raise json_err
                                else:
                                    raise json_err
                        else:
                            print(_("⚠ No JSON-like blocks found with balanced matching"))
                            raise json_err
                    
                    # Store structured analysis data for report rendering
                    llm_analysis_data = analysis_data
                    
                    print(_("🔍 Parsed data keys: {keys}").format(keys=list(analysis_data.keys())))
                    
                    # Extract issues from analysis - support two formats:
                    # 1. New format: direct keys like "single_responsibility_violations"
                    # 2. Old format: nested under "analysis" key
                    
                    analysis = None
                    if isinstance(analysis_data, dict):
                        if 'analysis' in analysis_data:
                            analysis = analysis_data['analysis']
                            print(_("🔍 Using 'analysis' key structure"))
                        else:
                            # Direct format - treat the entire dict as analysis
                            analysis = analysis_data
                            print(_("🔍 Using direct key structure"))
                    
                    if analysis:
                        print(_("🔍 Analysis keys: {keys}").format(keys=list(analysis.keys())))
                        
                        # Process single responsibility violations
                        if 'single_responsibility_violations' in analysis:
                            violations = analysis['single_responsibility_violations']
                            print(_("🔍 Found {count} single responsibility violations").format(count=len(violations)))
                            for issue in violations:
                                llm_findings.append({
                                    'severity': issue.get('severity', 'info').lower(),
                                    'rule': 'single_responsibility',
                                    'message': f"{issue.get('issue', 'Unknown issue')}: {issue.get('description', '')}",
                                    'location': issue.get('location', ''),
                                    'file_path': _extract_file_from_location(issue.get('location', '')),
                                    'suggestion': issue.get('suggestion', ''),
                                    'category': 'single_responsibility'
                                })
                        
                        # Process excessive coupling
                        if 'excessive_coupling' in analysis:
                            violations = analysis['excessive_coupling']
                            print(_("🔍 Found {count} excessive coupling violations").format(count=len(violations)))
                            for issue in violations:
                                llm_findings.append({
                                    'severity': issue.get('severity', 'info').lower(),
                                    'rule': 'excessive_coupling',
                                    'message': f"{issue.get('issue', 'Unknown issue')}: {issue.get('description', '')}",
                                    'location': issue.get('location', ''),
                                    'file_path': _extract_file_from_location(issue.get('location', '')),
                                    'suggestion': issue.get('suggestion', ''),
                                    'category': 'excessive_coupling'
                                })
                        
                        # Process difficulty in unit testing
                        if 'difficulty_in_unit_testing' in analysis:
                            violations = analysis['difficulty_in_unit_testing']
                            print(_("🔍 Found {count} difficulty in unit testing violations").format(count=len(violations)))
                            for issue in violations:
                                llm_findings.append({
                                    'severity': issue.get('severity', 'info').lower(),
                                    'rule': 'unit_test_difficulty',
                                    'message': f"{issue.get('issue', 'Unknown issue')}: {issue.get('description', '')}",
                                    'location': issue.get('location', ''),
                                    'file_path': _extract_file_from_location(issue.get('location', '')),
                                    'suggestion': issue.get('suggestion', ''),
                                    'category': 'difficulty_in_unit_testing'
                                })
                        
                        print(_("🔍 Total LLM findings after processing: {count}").format(count=len(llm_findings)))
                        
                        # Add a special finding to trigger structured display in report
                        if llm_findings:
                            llm_findings.append({
                                "severity": "info",
                                "rule": "llm_semantic_review",
                                "message": "Structured LLM analysis available",
                                "structured_data": llm_analysis_data,
                                "is_structured": True
                            })
                            print(_("✓ Added structured LLM analysis finding"))
                        
                        # If no issues found in structured format, fall back to raw result
                        if not llm_findings:
                            print(_("⚠ No structured violations found, falling back to raw result"))
                            llm_findings.append({
                                "severity": "info",
                                "rule": "llm_semantic_review",
                                "message": f"LLM Semantic Analysis: {llm_result[:500]}..."
                            })
                    else:
                        print(_("⚠ No analysis data found in parsed JSON"))
                        llm_findings.append({
                            "severity": "info",
                            "rule": "llm_semantic_review",
                            "message": f"LLM Semantic Analysis: {llm_result[:500]}..."
                        })
                    
                except (json.JSONDecodeError, KeyError, AttributeError) as json_error:
                    # If JSON parsing fails, use raw result
                    print(f"⚠ Failed to parse LLM JSON result: {json_error}")
                    llm_findings.append({
                        "severity": "info",
                        "rule": "llm_semantic_review",
                        "message": f"LLM Semantic Analysis: {llm_result[:500]}..."
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
            
            # Prepare LLM semantic results for structured display
            llm_semantic_results = None
            if llm_analysis_data and isinstance(llm_analysis_data, dict) and 'analysis' in llm_analysis_data:
                analysis = llm_analysis_data['analysis']
                llm_semantic_results = []
                
                # Map analysis categories to report format
                category_mapping = {
                    'single_responsibility_violations': 'single_responsibility',
                    'excessive_coupling': 'excessive_coupling',
                    'difficulty_in_unit_testing': 'difficulty_in_unit_testing'
                }
                
                for json_key, category_key in category_mapping.items():
                    if json_key in analysis and analysis[json_key]:
                        violations = []
                        for item in analysis[json_key]:
                            violations.append({
                                'severity': item.get('severity', 'low').lower(),
                                'issue': item.get('issue', ''),
                                'location': item.get('location', ''),
                                'description': item.get('description', ''),
                                'suggestion': item.get('suggestion', '')
                            })
                        if violations:
                            llm_semantic_results.append({
                                'category': category_key,
                                'violations': violations
                            })
            
            report_path = HTMLReportGenerator.generate_report(
                diff_data=diff_data,
                findings=result["findings"],  # Use all findings (including LLM)
                score=result["score"],
                output_path=str(html_report_path),
                llm_semantic_results=llm_semantic_results
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
