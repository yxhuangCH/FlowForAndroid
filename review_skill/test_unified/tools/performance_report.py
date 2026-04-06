"""Performance report generator for unified engine tests"""

import json
from datetime import datetime
from pathlib import Path


class PerformanceReport:
    """Generate performance comparison reports"""

    def generate(self, results: dict, output_path: str) -> dict:
        """
        Generate a performance comparison report.

        Args:
            results: Dictionary with benchmark results
            output_path: Path to save report

        Returns:
            Report dictionary
        """
        targets = {
            "first_scan_ms": 50,
            "cached_scan_ms": 5,
            "large_file_ms": 500,
            "parallel_speedup": 2.0,
            "memory_mb": 200,
        }

        # Build report
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {},
            "details": results
        }

        # Calculate summary metrics
        for metric, target in targets.items():
            actual = results.get(metric, 0)
            status = "PASS" if actual <= target else "FAIL"

            report["summary"][metric] = {
                "target": target,
                "actual": round(actual, 2),
                "status": status
            }

        # Generate markdown report
        markdown = self._generate_markdown(report, targets)

        # Save reports
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # JSON report
        json_path = output_path.with_suffix('.json')
        json_path.write_text(json.dumps(report, indent=2))

        # Markdown report
        md_path = output_path.with_suffix('.md')
        md_path.write_text(markdown)

        print(f"\nPerformance report saved to:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")

        return report

    def _generate_markdown(self, report: dict, targets: dict) -> str:
        """Generate markdown format report"""
        lines = [
            "# Unified Engine Performance Report",
            "",
            f"**Generated:** {report['generated_at']}",
            "",
            "## Performance Metrics",
            "",
            "| Metric | Target | Actual | Status |",
            "|--------|--------|--------|--------|",
        ]

        for metric, info in report["summary"].items():
            target = info["target"]
            actual = info["actual"]
            status = info["status"]
            icon = "✅" if status == "PASS" else "⚠️"

            lines.append(
                f"| {metric} | {target} | {actual} | {icon} |"
            )

        lines.extend([
            "",
            "## Detailed Results",
            "",
            "```json",
            json.dumps(report.get("details", {}), indent=2),
            "```",
            ""
        ])

        return "\n".join(lines)


class FalsePositiveReport:
    """Generate false positive test reports"""

    def generate(self, test_results: list, output_path: str) -> dict:
        """
        Generate false positive test report.

        Args:
            test_results: List of test result dicts
            output_path: Path to save report

        Returns:
            Report dictionary
        """
        total_tests = len(test_results)
        passed = sum(1 for r in test_results if r.get("passed", False))
        failed = total_tests - passed

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_scenarios": total_tests,
                "passed": passed,
                "failed": failed,
                "pass_rate": round(passed / total_tests * 100, 1) if total_tests > 0 else 0
            },
            "details": test_results
        }

        # Save report
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        json_path = output_path.with_suffix('.json')
        json_path.write_text(json.dumps(report, indent=2))

        # Print summary
        print(f"\nFalse Positive Test Results:")
        print(f"  Total scenarios: {total_tests}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Pass rate: {report['summary']['pass_rate']}%")

        if failed > 0:
            print("\nFailed tests:")
            for r in test_results:
                if not r.get("passed", False):
                    print(f"  - {r.get('description', 'Unknown')}")

        return report


class TestCoverageReport:
    """Generate test coverage summary"""

    def __init__(self):
        self.rule_coverage = {}
        self.component_coverage = {}

    def add_rule_test(self, rule_id: str, tested: bool, findings_count: int = 0):
        """Record rule test coverage"""
        self.rule_coverage[rule_id] = {
            "tested": tested,
            "findings_count": findings_count
        }

    def add_component_test(self, component: str, tested: bool, test_count: int = 0):
        """Record component test coverage"""
        self.component_coverage[component] = {
            "tested": tested,
            "test_count": test_count
        }

    def generate(self, output_path: str) -> dict:
        """Generate coverage report"""
        total_rules = len(self.rule_coverage)
        rules_tested = sum(1 for v in self.rule_coverage.values() if v["tested"])

        total_components = len(self.component_coverage)
        components_tested = sum(1 for v in self.component_coverage.values() if v["tested"])

        report = {
            "generated_at": datetime.now().isoformat(),
            "rules": {
                "total": total_rules,
                "tested": rules_tested,
                "coverage_pct": round(rules_tested / total_rules * 100, 1) if total_rules > 0 else 0,
                "details": self.rule_coverage
            },
            "components": {
                "total": total_components,
                "tested": components_tested,
                "coverage_pct": round(components_tested / total_components * 100, 1) if total_components > 0 else 0,
                "details": self.component_coverage
            }
        }

        # Save report
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2))

        return report
