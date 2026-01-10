# Evaluation System

Automatic evaluation and regression testing for fashion search quality.

## Overview

This evaluation system provides:
- **Benchmark dataset** of 100 test queries (text, image, and combined)
- **Automatic metrics** calculation (MRR, Precision@K, Recall@K)
- **Regression detection** by comparing to baseline performance
- **Reproducible testing** (no LLM costs, deterministic queries)

---

## Quick Start

### 1. Generate Benchmark (One-time)

```bash
cd backend
python3 -m evaluation.generate_benchmark
```

This creates:
- `evaluation/benchmark_queries.json` - 100 test queries
- `evaluation/ground_truth.json` - Expected results

### 2. Run Evaluation

```bash
python3 -m evaluation.evaluate
```

This will:
- Run all 100 benchmark queries
- Calculate metrics
- Display results

### 3. Save Baseline

```bash
python3 -m evaluation.evaluate --save-baseline
```

Saves current performance as baseline for comparison.

### 4. Detect Regressions

```bash
python3 -m evaluation.evaluate --compare
```

Compares current results to baseline and flags regressions.

---

## Metrics Explained

### MRR (Mean Reciprocal Rank)
**Range**: 0.0 - 1.0 (higher is better)

Measures how quickly the first relevant result appears:
- MRR = 1.0: First result is always correct
- MRR = 0.5: Correct result is typically at rank 2
- MRR = 0.33: Correct result is typically at rank 3

**Target**: > 0.80

### Precision@K
**Range**: 0.0 - 1.0 (higher is better)

Percentage of relevant items in top K results:
- Precision@1 ≈ Top-1 accuracy
- Precision@5: Quality of top 5 results
- Precision@10: Quality of top 10 results

**Targets**: 
- P@1 > 0.70
- P@5 > 0.40
- P@10 > 0.25

### Recall@K
**Range**: 0.0 - 1.0 (higher is better)

Percentage of all relevant items found in top K:
- Recall@20: Did we find the relevant items?

**Target**: R@20 > 0.90

### Average Rank
Lower is better. Average position of first relevant result.

**Target**: < 2.0

---

## Benchmark Query Types

### Text-Only (33 queries)
Uses exact product descriptions as queries.
Tests whether search can find the product from its own text.

**Example**:
```json
{
  "query_text": "black top with polka dot pattern",
  "expected": ["fashion_000000"]
}
```

### Image-Only (33 queries)
Uses product images as queries.
Tests image similarity search.

**Example**:
```json
{
  "query_image_path": "data/images/fashion_001234.jpg",
  "expected": ["fashion_001234"]
}
```

### Combined (34 queries)
Uses simplified text + image together.
Tests multimodal search.

**Example**:
```json
{
  "query_text": "black top with polka",  
  "query_image_path": "data/images/fashion_000000.jpg",
  "expected": ["fashion_000000"]
}
```

---

## Example Output

```
============================================================
EVALUATION RESULTS
============================================================

Timestamp: 2026-01-09T15:45:00
Queries evaluated: 100
Correct (top-1): 85 (85.0%)
Errors: 0

------------------------------------------------------------
OVERALL METRICS
------------------------------------------------------------
  mrr                 : 0.8734
  precision_at_1      : 0.8500
  precision_at_5      : 0.4200
  precision_at_10     : 0.2300
  recall_at_20        : 0.9200
  average_rank        : 1.45

------------------------------------------------------------
METRICS BY QUERY TYPE
------------------------------------------------------------

TEXT:
  mrr                 : 0.9100
  precision_at_1      : 0.9091
  ...

IMAGE:
  mrr                 : 0.8500
  precision_at_1      : 0.8182
  ...

COMBINED:
  mrr                 : 0.8600
  precision_at_1      : 0.8235
  ...
============================================================
```

---

## Regression Detection Example

```
============================================================
REGRESSION DETECTION
============================================================

Baseline: 2026-01-09T10:00:00
Current:  2026-01-09T15:45:00

------------------------------------------------------------
METRIC COMPARISON
------------------------------------------------------------
  mrr                 : 0.8734 → 0.8500 (-2.7%) ✅
  precision_at_1      : 0.8500 → 0.8200 (-3.5%) ✅
  precision_at_5      : 0.4200 → 0.3800 (-9.5%) ⚠️ REGRESSION

============================================================

⚠️  1 REGRESSIONS DETECTED:
  - precision_at_5
```

---

## Files

```
evaluation/
├── __init__.py                 # Package init
├── generate_benchmark.py       # Generate test queries
├── evaluate.py                 # Main evaluation script
├── metrics.py                  # Metric calculation functions
├── benchmark_queries.json      # 100 test queries (committed to git)
├── ground_truth.json           # Expected results (committed to git)
├── baseline_results.json       # Current baseline (committed to git)
└── README.md                   # This file
```

---

## Use Cases

### 1. Before Deploying Changes
```bash
# Run evaluation before deployment
python3 -m evaluation.evaluate --compare

# If no regressions, deploy
# If regressions detected, investigate
```

### 2. After Changing Embeddings
```bash
# Re-generate embeddings
python3 -m ingestion.generate_embeddings

# Check if search quality maintained
python3 -m evaluation.evaluate --compare
```

### 3. After Updating CLIP Model
```bash
# Change model in .env
# Re-run embedding generation
# Evaluate and save new baseline if better
python3 -m evaluation.evaluate --save-baseline
```

---

## Design Decisions

### Self-supervised Ground Truth
- Uses products' own descriptions/images as queries
- No manual labeling required
- Reproducible and scalable
- Tests actual retrieval quality

### 100 Queries
- Fast execution (~2-3 minutes)
- Statistically significant
- Covers all modalities

### No LLM Costs
- All queries pre-generated
- Evaluation is deterministic
- Can run unlimited times for free

---

## Interpretation Guide

**Excellent Performance** (Production-ready):
- MRR > 0.85
- P@1 > 0.80
- R@20 > 0.90

**Good Performance** (Acceptable):
- MRR > 0.75
- P@1 > 0.70
- R@20 > 0.80

**Needs Improvement**:
- MRR < 0.70
- P@1 < 0.60
- R@20 < 0.70

---

## Troubleshooting

### "Benchmark not found"
```bash
python3 -m evaluation.generate_benchmark
```

### "No baseline found"
```bash
python3 -m evaluation.evaluate --save-baseline
```

### Low scores on image queries
Check:
- Image embeddings generated correctly
- Image preprocessing consistent
- Qdrant image vectors indexed

### Low scores on text queries
Check:
- Text embeddings quality
- Query preprocessing
- CLIP model loaded correctly

---

## Next Steps

1. **Run initial evaluation** to establish baseline
2. **Monitor metrics** after each change
3. **Investigate failures** in per_query_results
4. **Expand benchmark** if needed (add more queries)
5. **Track metrics over time** to detect trends
