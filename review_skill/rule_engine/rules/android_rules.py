"""
Android-specific rules
"""
from typing import List, Tuple
import re
from ..interfaces import Rule, RuleMetadata, RuleSeverity, RuleCategory, Finding
from ..context import RuleContext
from ..adapters.decorators import rule


@rule(
    rule_id="startactivity_without_trycatch",
    name="startActivity should be wrapped in try-catch",
    description="startActivity may throw ActivityNotFoundException when the target activity is not found. It should be wrapped in try-catch block.",
    severity=RuleSeverity.MAJOR,
    category=RuleCategory.CORRECTNESS,
    tags=["android", "kotlin", "startActivity", "exception-handling"],
    suggested_fix="Wrap startActivity call in try-catch block to handle ActivityNotFoundException",
    weight=1.2
)
def startactivity_without_trycatch_rule(context: RuleContext) -> List[Finding]:
    """
    Detect startActivity calls that are not wrapped in try-catch blocks.
    
    This rule checks if startActivity() calls are properly protected with try-catch
    to handle ActivityNotFoundException when the target activity doesn't exist.
    """
    findings = []
    lines = context.get_lines()
    
    # Pattern to match startActivity calls
    startactivity_pattern = re.compile(r'\.startActivity\s*\(', re.IGNORECASE)
    
    # Find all try-catch blocks first
    try_catch_ranges = _find_try_catch_ranges(lines)
    
    # Find all function ranges with @Throws annotation
    throws_function_ranges = _find_throws_function_ranges(lines)
    
    for i, line in enumerate(lines, 1):
        if startactivity_pattern.search(line):
            # Check if this line is inside a try-catch block
            is_in_try_catch = _is_line_in_ranges(i, try_catch_ranges)
            
            # Check if this line is inside a function with @Throws
            is_in_throws_function = _is_line_in_ranges(i, throws_function_ranges)
            
            if not is_in_try_catch and not is_in_throws_function:
                findings.append(Finding(
                    rule_id="startactivity_without_trycatch",
                    message="startActivity should be wrapped in try-catch to handle ActivityNotFoundException",
                    severity=RuleSeverity.MAJOR,
                    file_path=context.file_path,
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion="Wrap startActivity call in try-catch block: try { startActivity(intent) } catch (e: ActivityNotFoundException) { /* handle error */ }"
                ))
    
    return findings


def _find_try_catch_ranges(lines: List[str]) -> List[Tuple[int, int]]:
    """
    Find all line ranges that are inside try-catch blocks.
    
    Returns:
        List of (start_line, end_line) tuples representing try block ranges (1-based, inclusive)
    """
    ranges = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Look for try keyword
        if re.search(r'\btry\s*\{', stripped):
            # Found try block, now find its range
            start_line = i + 1  # 1-based line number
            brace_depth = 1
            j = i + 1
            has_catch = False
            
            while j < len(lines) and brace_depth > 0:
                current_line = lines[j]
                
                # Check for catch on this line (before we process the brace)
                # This handles: } catch (e: Exception) { 
                if brace_depth == 1 and re.search(r'\}\s*catch\s*\(', current_line):
                    has_catch = True
                
                # Also check for standalone catch
                if re.search(r'\bcatch\s*\(', current_line.strip()) and not re.search(r'\}\s*catch', current_line):
                    has_catch = True
                
                brace_depth += current_line.count('{') - current_line.count('}')
                j += 1
            
            # If has catch, add the range (the entire try block)
            if has_catch:
                # j is now at the line after try block ends
                # Range is from start_line+1 (inside try) to j-1 (end of try block)
                end_line = j  # Line where try block ends (1-based)
                ranges.append((start_line, end_line))
            
            i = j
        else:
            i += 1
    
    return ranges


def _find_throws_function_ranges(lines: List[str]) -> List[Tuple[int, int]]:
    """
    Find all line ranges of functions that have @Throws annotation.
    
    Returns:
        List of (start_line, end_line) tuples representing function ranges (1-based, inclusive)
    """
    ranges = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check for @Throws annotation
        if '@Throws' in stripped:
            # Look for function definition in next few lines
            for j in range(i + 1, min(i + 5, len(lines))):
                func_line = lines[j].strip()
                if re.search(r'\bfun\s+\w+', func_line) or func_line.startswith('fun '):
                    # Found function, now find its range
                    start_line = j + 1  # 1-based line number
                    
                    # Find the opening brace
                    brace_line = j
                    brace_depth = 0
                    
                    # If function definition has opening brace on same line
                    if '{' in func_line:
                        brace_depth = func_line.count('{') - func_line.count('}')
                    else:
                        # Look for opening brace in subsequent lines
                        for k in range(j + 1, min(j + 3, len(lines))):
                            if '{' in lines[k]:
                                brace_line = k
                                brace_depth = lines[k].count('{') - lines[k].count('}')
                                break
                    
                    if brace_depth > 0:
                        # Track braces to find end of function
                        k = brace_line + 1
                        while k < len(lines) and brace_depth > 0:
                            brace_depth += lines[k].count('{') - lines[k].count('}')
                            k += 1
                        
                        end_line = k  # 1-based line number where function ends
                        ranges.append((start_line, end_line))
                    break
        
        i += 1
    
    return ranges


def _is_line_in_ranges(line_number: int, ranges: List[Tuple[int, int]]) -> bool:
    """
    Check if a line number falls within any of the given ranges.
    
    Args:
        line_number: 1-based line number to check
        ranges: List of (start, end) tuples (1-based, inclusive)
        
    Returns:
        True if line_number is within any range
    """
    for start, end in ranges:
        if start <= line_number <= end:
            return True
    return False
