#!/bin/bash
# Unified Engine Test Runner
# Run all tests for the unified engine

set -e

echo "========================================="
echo "  Unified Engine Test Suite"
echo "========================================="
echo ""

cd "$(dirname "$0")/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

run_test() {
    local name="$1"
    local cmd="$2"

    echo -e "${YELLOW}Running: ${name}${NC}"
    echo "-----------------------------------------"

    if eval "$cmd"; then
        echo -e "${GREEN}✓ ${name} passed${NC}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}✗ ${name} failed${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo ""
}

# Unit Tests
echo "=== UNIT TESTS ==="
echo ""

run_test "Interface Tests" \
    "python3 -m pytest test_unified/test_interfaces.py -v --tb=short"

run_test "Scheduler Tests" \
    "python3 -m pytest test_unified/test_scheduler.py -v --tb=short"

run_test "Integration Tests" \
    "python3 -m pytest test_unified/test_integration.py -v --tb=short"

run_test "Memory Cache Tests" \
    "python3 -m pytest test_unified/test_cache/test_memory_cache.py -v --tb=short"

run_test "Disk Cache Tests" \
    "python3 -m pytest test_unified/test_cache/test_disk_cache.py -v --tb=short"

run_test "Incremental Cache Tests" \
    "python3 -m pytest test_unified/test_cache/test_incremental_cache.py -v --tb=short"

run_test "Unified Cache Tests" \
    "python3 -m pytest test_unified/test_cache/test_unified_cache.py -v --tb=short"

run_test "Base Rules Tests" \
    "python3 -m pytest test_unified/test_rules/test_base_rules.py -v --tb=short"

run_test "Coroutine Rules Tests" \
    "python3 -m pytest test_unified/test_rules/test_coroutine_rules.py -v --tb=short"

run_test "Compose Rules Tests" \
    "python3 -m pytest test_unified/test_rules/test_compose_rules.py -v --tb=short"

run_test "Flow Rules Tests" \
    "python3 -m pytest test_unified/test_rules/test_flow_rules.py -v --tb=short"

# Specialized Tests
echo "=== SPECIALIZED TESTS ==="
echo ""

run_test "False Positive Tests" \
    "python3 -m pytest test_unified/test_false_positives.py -v --tb=short"

# E2E and Regression
echo "=== E2E & REGRESSION TESTS ==="
echo ""

run_test "E2E Workflow Tests" \
    "python3 -m pytest test_unified/e2e/test_review_workflow.py -v --tb=short"

run_test "Regression Tests" \
    "python3 -m pytest test_unified/regression/test_regression.py -v --tb=short"

# Performance Benchmarks (optional, can be slow)
if [ "${RUN_BENCHMARKS:-false}" = "true" ]; then
    echo "=== PERFORMANCE BENCHMARKS ==="
    echo ""

    run_test "Performance Benchmarks" \
        "python3 -m pytest test_unified/benchmark/test_performance.py -v --tb=short"
fi

# Summary
echo "========================================="
echo "  TEST SUMMARY"
echo "========================================="
echo -e "Passed: ${GREEN}${PASS_COUNT}${NC}"
echo -e "Failed: ${RED}${FAIL_COUNT}${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
