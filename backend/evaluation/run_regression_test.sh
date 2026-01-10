#!/bin/bash

# Regression test script
# Runs evaluation and compares against baseline

set -e

echo "Running evaluation..."
cd "$(dirname "$0")/.."
python -m evaluation.evaluate

# Check if baseline exists
BASELINE_FILE="evaluation/results/baseline.json"
CURRENT_FILE="evaluation/results/current.json"

if [ ! -f "$BASELINE_FILE" ]; then
    echo ""
    echo "⚠️  No baseline found. Creating baseline from current results..."
    cp "$CURRENT_FILE" "$BASELINE_FILE"
    echo "✓ Baseline created: $BASELINE_FILE"
    exit 0
fi

# Compare metrics
echo ""
echo "Checking for regressions..."

CURRENT_RECALL=$(python -c "import json; print(json.load(open('$CURRENT_FILE'))['metrics']['recall_at_k_overall'])")
BASELINE_RECALL=$(python -c "import json; print(json.load(open('$BASELINE_FILE'))['metrics']['recall_at_k_overall'])")

CURRENT_MRR=$(python -c "import json; print(json.load(open('$CURRENT_FILE'))['metrics']['mrr'])")
BASELINE_MRR=$(python -c "import json; print(json.load(open('$BASELINE_FILE'))['metrics']['mrr'])")

# Calculate differences (using python for floating point)
RECALL_DIFF=$(python -c "print($CURRENT_RECALL - $BASELINE_RECALL)")
MRR_DIFF=$(python -c "print($CURRENT_MRR - $BASELINE_MRR)")

# Check for regressions (>5% drop)
THRESHOLD=-0.05

RECALL_REGRESSED=$(python -c "print('yes' if $RECALL_DIFF < $THRESHOLD else 'no')")
MRR_REGRESSED=$(python -c "print('yes' if $MRR_DIFF < $THRESHOLD else 'no')")

if [ "$RECALL_REGRESSED" == "yes" ] || [ "$MRR_REGRESSED" == "yes" ]; then
    echo ""
    echo "❌ REGRESSION DETECTED!"
    echo "   Recall@K: $CURRENT_RECALL (baseline: $BASELINE_RECALL, change: $RECALL_DIFF)"
    echo "   MRR: $CURRENT_MRR (baseline: $BASELINE_MRR, change: $MRR_DIFF)"
    echo ""
    echo "Performance dropped by more than 5%. Please investigate."
    exit 1
else
    echo ""
    echo "✓ No regressions detected"
    echo "  Recall@K: $CURRENT_RECALL (baseline: $BASELINE_RECALL, change: $RECALL_DIFF)"
    echo "  MRR: $CURRENT_MRR (baseline: $BASELINE_MRR, change: $MRR_DIFF)"
    exit 0
fi
