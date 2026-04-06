"""
Execution Monitor - 执行监控器

实时监控规则执行性能，收集指标并生成报告。

特性:
- 规则执行时间记录
- 性能指标收集
- 慢规则识别
- 生成性能报告
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .interfaces import Finding, RuleSeverity, UnifiedRule, ExecutionMode


@dataclass
class RuleExecutionRecord:
    """规则执行记录"""

    rule_id: str
    execution_mode: "ExecutionMode"
    start_time: float
    end_time: float
    findings_count: int
    file_path: str
    file_size: int
    line_count: int

    @property
    def elapsed_ms(self) -> float:
        """执行耗时（毫秒）"""
        return (self.end_time - self.start_time) * 1000


@dataclass
class FileExecutionRecord:
    """文件执行记录"""

    file_path: str
    file_size: int
    line_count: int
    start_time: float
    end_time: float
    rules_executed: int
    findings_count: int

    @property
    def elapsed_ms(self) -> float:
        """执行耗时（毫秒）"""
        return (self.end_time - self.start_time) * 1000


class ExecutionMonitor:
    """
    执行监控器

    收集规则执行时间、命中率等性能指标，
    帮助识别性能瓶颈和慢规则。

    Example:
        ```python
        monitor = ExecutionMonitor()

        # 开始记录
        record = monitor.start_rule_execution(rule, file_path, content)

        # 执行规则
        findings = rule.check(context)

        # 结束记录
        monitor.end_rule_execution(record, findings)

        # 生成报告
        report = monitor.generate_report()
        monitor.print_report()
        ```
    """

    def __init__(self):
        """初始化监控器"""
        # 规则执行记录
        self._rule_records: List[RuleExecutionRecord] = []

        # 文件执行记录
        self._file_records: List[FileExecutionRecord] = []

        # 统计缓存
        self._rule_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_ms": 0.0, "findings": 0}
        )

        # 锁
        self._lock = threading.Lock()

        # 当前执行中的记录（用于匹配开始和结束）
        self._active_records: Dict[int, RuleExecutionRecord] = {}

    def start_rule_execution(
        self,
        rule: "UnifiedRule",
        file_path: str,
        content: str,
    ) -> RuleExecutionRecord:
        """
        开始记录规则执行

        Args:
            rule: 规则实例
            file_path: 文件路径
            content: 文件内容

        Returns:
            执行记录（需要在执行完成后传入 end_rule_execution）
        """
        record = RuleExecutionRecord(
            rule_id=rule.metadata.id,
            execution_mode=rule.execution_mode,
            start_time=time.perf_counter(),
            end_time=0.0,  # 临时值
            findings_count=0,
            file_path=file_path,
            file_size=len(content),
            line_count=len(content.split("\n")),
        )

        # 存储到活跃记录
        record_id = id(record)
        with self._lock:
            self._active_records[record_id] = record

        return record

    def end_rule_execution(
        self,
        record: RuleExecutionRecord,
        findings: List["Finding"],
    ) -> None:
        """
        结束记录规则执行

        Args:
            record: start_rule_execution 返回的记录
            findings: 规则发现的问题列表
        """
        record_id = id(record)

        with self._lock:
            # 检查记录是否有效
            if record_id not in self._active_records:
                return

            # 更新记录
            record.end_time = time.perf_counter()
            record.findings_count = len(findings)

            # 移动到已完成记录
            del self._active_records[record_id]
            self._rule_records.append(record)

            # 更新统计
            stats = self._rule_stats[record.rule_id]
            stats["count"] += 1
            stats["total_ms"] += record.elapsed_ms
            stats["findings"] += record.findings_count

    def start_file_execution(
        self,
        file_path: str,
        content: str,
    ) -> FileExecutionRecord:
        """
        开始记录文件执行

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            文件执行记录
        """
        return FileExecutionRecord(
            file_path=file_path,
            file_size=len(content),
            line_count=len(content.split("\n")),
            start_time=time.perf_counter(),
            end_time=0.0,
            rules_executed=0,
            findings_count=0,
        )

    def end_file_execution(
        self,
        record: FileExecutionRecord,
        rules_executed: int,
        findings_count: int,
    ) -> None:
        """
        结束记录文件执行

        Args:
            record: 文件执行记录
            rules_executed: 执行的规则数量
            findings_count: 发现的问题数量
        """
        record.end_time = time.perf_counter()
        record.rules_executed = rules_executed
        record.findings_count = findings_count

        with self._lock:
            self._file_records.append(record)

    def get_slow_rules(self, n: int = 5) -> List[Tuple[str, float]]:
        """
        获取最慢的规则

        Args:
            n: 返回规则数量

        Returns:
            (rule_id, avg_time_ms) 列表，按耗时排序
        """
        with self._lock:
            rule_times = []
            for rule_id, stats in self._rule_stats.items():
                if stats["count"] > 0:
                    avg_time = stats["total_ms"] / stats["count"]
                    rule_times.append((rule_id, avg_time))

            # 按耗时排序
            rule_times.sort(key=lambda x: x[1], reverse=True)
            return rule_times[:n]

    def get_slow_files(self, n: int = 5) -> List[Tuple[str, float]]:
        """
        获取最慢的文件

        Args:
            n: 返回文件数量

        Returns:
            (file_path, elapsed_ms) 列表
        """
        with self._lock:
            file_times = [
                (r.file_path, r.elapsed_ms)
                for r in self._file_records
                if r.end_time > 0
            ]
            file_times.sort(key=lambda x: x[1], reverse=True)
            return file_times[:n]

    def get_stats_by_mode(self) -> Dict[str, Dict[str, Any]]:
        """
        按执行模式获取统计

        Returns:
            执行模式 -> 统计信息的字典
        """
        with self._lock:
            mode_stats = defaultdict(
                lambda: {"count": 0, "total_ms": 0.0, "findings": 0}
            )

            for record in self._rule_records:
                mode = record.execution_mode.value
                mode_stats[mode]["count"] += 1
                mode_stats[mode]["total_ms"] += record.elapsed_ms
                mode_stats[mode]["findings"] += record.findings_count

            # 计算平均时间
            result = {}
            for mode, stats in mode_stats.items():
                result[mode] = {
                    "count": stats["count"],
                    "avg_time_ms": round(stats["total_ms"] / stats["count"], 2)
                    if stats["count"] > 0
                    else 0,
                    "total_findings": stats["findings"],
                }

            return result

    def generate_report(self) -> Dict[str, Any]:
        """
        生成性能报告

        Returns:
            性能报告字典
        """
        with self._lock:
            # 总规则执行次数
            total_rule_executions = len(self._rule_records)

            # 总文件执行次数
            total_file_executions = len(self._file_records)

            # 总执行时间
            total_rule_time_ms = sum(r.elapsed_ms for r in self._rule_records)
            total_file_time_ms = sum(r.elapsed_ms for r in self._file_records)

            # 平均时间
            avg_rule_time_ms = (
                total_rule_time_ms / total_rule_executions
                if total_rule_executions > 0
                else 0
            )
            avg_file_time_ms = (
                total_file_time_ms / total_file_executions
                if total_file_executions > 0
                else 0
            )

            # 总发现问题数
            total_findings = sum(r.findings_count for r in self._rule_records)

            return {
                "summary": {
                    "total_rule_executions": total_rule_executions,
                    "total_file_executions": total_file_executions,
                    "total_findings": total_findings,
                    "avg_rule_time_ms": round(avg_rule_time_ms, 2),
                    "avg_file_time_ms": round(avg_file_time_ms, 2),
                    "total_rule_time_ms": round(total_rule_time_ms, 2),
                    "total_file_time_ms": round(total_file_time_ms, 2),
                },
                "slow_rules": [
                    {"rule_id": r[0], "avg_time_ms": round(r[1], 2)}
                    for r in self.get_slow_rules(10)
                ],
                "slow_files": [
                    {"file_path": r[0], "time_ms": round(r[1], 2)}
                    for r in self.get_slow_files(10)
                ],
                "by_mode": self.get_stats_by_mode(),
            }

    def print_report(self) -> None:
        """打印性能报告"""
        report = self.generate_report()
        summary = report["summary"]

        print("\n" + "=" * 60)
        print("Execution Performance Report")
        print("=" * 60)

        print(f"\n📊 Summary:")
        print(f"  Files Scanned: {summary['total_file_executions']}")
        print(f"  Rules Executed: {summary['total_rule_executions']}")
        print(f"  Issues Found: {summary['total_findings']}")
        print(f"  Avg File Time: {summary['avg_file_time_ms']:.2f}ms")
        print(f"  Avg Rule Time: {summary['avg_rule_time_ms']:.2f}ms")
        print(f"  Total Time: {summary['total_file_time_ms']:.2f}ms")

        # 按模式统计
        by_mode = report.get("by_mode", {})
        if by_mode:
            print(f"\n📈 By Execution Mode:")
            for mode, stats in by_mode.items():
                print(
                    f"  {mode.upper():8s}: {stats['count']:4d} rules, "
                    f"avg {stats['avg_time_ms']:.2f}ms"
                )

        # 最慢规则
        slow_rules = report.get("slow_rules", [])
        if slow_rules:
            print(f"\n🐌 Slowest Rules:")
            for i, rule in enumerate(slow_rules[:5], 1):
                print(f"  {i}. {rule['rule_id']}: {rule['avg_time_ms']:.2f}ms")

        # 最慢文件
        slow_files = report.get("slow_files", [])
        if slow_files:
            print(f"\n📁 Slowest Files:")
            for i, f in enumerate(slow_files[:5], 1):
                print(f"  {i}. {f['file_path']}: {f['time_ms']:.2f}ms")

        print("=" * 60 + "\n")

    def reset(self) -> None:
        """重置所有记录"""
        with self._lock:
            self._rule_records.clear()
            self._file_records.clear()
            self._rule_stats.clear()
            self._active_records.clear()
