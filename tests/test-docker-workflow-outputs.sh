#!/usr/bin/env bash
# Unit test for docker-build-push workflow output format
# Tests that the workflow outputs meet expected format for downstream consumers
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_FILE="${SCRIPT_DIR}/../.github/workflows/docker-build-push.yml"

echo "=== git-flow: Docker Build Workflow Output Tests ==="
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
  echo "PASS: $1"
  TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
  echo "FAIL: $1"
  TESTS_FAILED=$((TESTS_FAILED + 1))
}

# Test 1: Workflow file exists
echo "Test 1: Workflow file exists"
if [[ -f "$WORKFLOW_FILE" ]]; then
  pass "Workflow file found at $WORKFLOW_FILE"
else
  fail "Workflow file not found at $WORKFLOW_FILE"
  exit 1
fi

# Test 2: Workflow defines 'digest' output
echo ""
echo "Test 2: Workflow defines 'digest' output"
if grep -q "^[[:space:]]*digest:" "$WORKFLOW_FILE"; then
  pass "Workflow defines 'digest' output"
else
  fail "Workflow missing 'digest' output definition"
fi

# Test 3: Workflow defines 'tags' output
echo ""
echo "Test 3: Workflow defines 'tags' output"
if grep -q "^[[:space:]]*tags:" "$WORKFLOW_FILE"; then
  pass "Workflow defines 'tags' output"
else
  fail "Workflow missing 'tags' output definition"
fi

# Test 4: Workflow defines 'sbom-path' output
echo ""
echo "Test 4: Workflow defines 'sbom-path' output"
if grep -q "^[[:space:]]*sbom-path:" "$WORKFLOW_FILE"; then
  pass "Workflow defines 'sbom-path' output"
else
  fail "Workflow missing 'sbom-path' output definition"
fi

# Test 5: Digest output comes from build step
echo ""
echo "Test 5: Digest output sources from build step"
if grep -q 'digest:.*\${{ steps.build.outputs.digest }}' "$WORKFLOW_FILE"; then
  pass "Digest output correctly sourced from build step"
else
  fail "Digest output not correctly sourced from build step"
fi

# Test 6: Tags output comes from meta step
echo ""
echo "Test 6: Tags output sources from meta step"
if grep -q 'tags:.*\${{ steps.meta.outputs.tags }}' "$WORKFLOW_FILE"; then
  pass "Tags output correctly sourced from meta step"
else
  fail "Tags output not correctly sourced from meta step"
fi

# Test 7: Workflow uses docker/metadata-action for consistent tagging
echo ""
echo "Test 7: Uses docker/metadata-action for tag generation"
if grep -q "docker/metadata-action" "$WORKFLOW_FILE"; then
  pass "Uses docker/metadata-action for consistent tagging"
else
  fail "Missing docker/metadata-action for tag generation"
fi

# Test 8: Workflow uses docker/build-push-action
echo ""
echo "Test 8: Uses docker/build-push-action"
if grep -q "docker/build-push-action" "$WORKFLOW_FILE"; then
  pass "Uses docker/build-push-action"
else
  fail "Missing docker/build-push-action"
fi

# Test 9: Workflow supports cosign signing
echo ""
echo "Test 9: Supports cosign image signing"
if grep -q "sigstore/cosign-installer" "$WORKFLOW_FILE"; then
  pass "Supports cosign image signing"
else
  fail "Missing cosign signing support"
fi

# Test 10: Workflow generates SBOM
echo ""
echo "Test 10: Generates SBOM with anchore/sbom-action"
if grep -q "anchore/sbom-action" "$WORKFLOW_FILE"; then
  pass "Generates SBOM with anchore/sbom-action"
else
  fail "Missing SBOM generation"
fi

echo ""
echo "=== Test Results ==="
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo ""

if [[ $TESTS_FAILED -gt 0 ]]; then
  echo "FAILED: Some tests did not pass"
  exit 1
else
  echo "SUCCESS: All tests passed"
  exit 0
fi
