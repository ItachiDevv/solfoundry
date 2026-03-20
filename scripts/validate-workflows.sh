#!/usr/bin/env bash
# validate-workflows.sh -- Validate GitHub Actions workflow YAML files
#
# Checks:
#   1. Required workflow files exist
#   2. YAML syntax is valid (requires python3 with PyYAML)
#   3. Each workflow has required top-level keys (name, on, jobs)
#   4. No hardcoded secrets or tokens
#
# Usage: bash scripts/validate-workflows.sh

set -euo pipefail

WORKFLOW_DIR=".github/workflows"
REQUIRED_WORKFLOWS=("ci.yml" "deploy.yml" "anchor.yml")
ERRORS=0

echo "=== SolFoundry Workflow Validation ==="
echo ""

# -- Check 1: Required workflow files exist --
echo "1. Checking required workflow files..."
for wf in "${REQUIRED_WORKFLOWS[@]}"; do
  if [ -f "$WORKFLOW_DIR/$wf" ]; then
    echo "   PASS $wf exists"
  else
    echo "   FAIL $wf MISSING"
    ERRORS=$((ERRORS + 1))
  fi
done
echo ""

# -- Check 2: YAML syntax validation --
echo "2. Validating YAML syntax..."
for wf in "$WORKFLOW_DIR"/*.yml; do
  basename_wf=$(basename "$wf")
  if python3 -c "
import yaml, sys
with open(sys.argv[1], encoding='utf-8', errors='replace') as f:
    yaml.safe_load(f)
" "$wf" 2>/dev/null; then
    echo "   PASS $basename_wf -- valid YAML"
  else
    echo "   FAIL $basename_wf -- invalid YAML"
    ERRORS=$((ERRORS + 1))
  fi
done
echo ""

# -- Check 3: Required top-level keys --
echo "3. Checking workflow structure (name, on, jobs)..."
for wf in "${REQUIRED_WORKFLOWS[@]}"; do
  filepath="$WORKFLOW_DIR/$wf"
  [ -f "$filepath" ] || continue

  result=$(python3 -c "
import yaml, sys
with open(sys.argv[1], encoding='utf-8', errors='replace') as f:
    data = yaml.safe_load(f)
missing = []
if data is None:
    print('empty file')
    sys.exit(1)
if 'name' not in data:
    missing.append('name')
# PyYAML parses bare 'on' as boolean True
if True not in data and 'on' not in data:
    missing.append('on')
if 'jobs' not in data:
    missing.append('jobs')
if missing:
    print(','.join(missing))
    sys.exit(1)
" "$filepath" 2>&1)
  if [ $? -eq 0 ]; then
    echo "   PASS $wf -- has all required keys"
  else
    echo "   FAIL $wf -- missing: $result"
    ERRORS=$((ERRORS + 1))
  fi
done
echo ""

# -- Check 4: No hardcoded secrets --
echo "4. Checking for hardcoded secrets..."
for wf in "$WORKFLOW_DIR"/*.yml; do
  basename_wf=$(basename "$wf")
  if grep -qiE "(sk_live|pk_live|ghp_[A-Za-z0-9]+|gho_[A-Za-z0-9]+)" "$wf" 2>/dev/null; then
    echo "   FAIL $basename_wf -- possible hardcoded secret found"
    ERRORS=$((ERRORS + 1))
  else
    echo "   PASS $basename_wf -- no hardcoded secrets"
  fi
done
echo ""

# -- Summary --
if [ "$ERRORS" -eq 0 ]; then
  echo "All checks passed"
  exit 0
else
  echo "$ERRORS error(s) found"
  exit 1
fi
