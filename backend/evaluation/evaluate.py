"""
Main evaluation script for search quality assessment.

Usage:
    python3 -m evaluation.evaluate                # Run evaluation
    python3 -m evaluation.evaluate --save-baseline  # Save as new baseline
    python3 -m evaluation.evaluate --compare        # Compare to baseline
"""

import asyncio
import json
import argparse
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
from app.services.retriever import get_retriever_service
from app.services.database import get_mongodb_service
from evaluation.metrics import MetricsCalculator


class SearchEvaluator:
    """Evaluate search quality using benchmark queries."""
    
    def __init__(self, benchmark_path: Path, ground_truth_path: Path):
        """Initialize evaluator with benchmark data."""
        with open(benchmark_path) as f:
            self.benchmark_data = json.load(f)
            self.queries = self.benchmark_data["queries"]
        
        with open(ground_truth_path) as f:
            self.ground_truth = json.load(f)
        
        self.retriever = None
        self.db_service = None
    
    async def run_evaluation(self) -> Dict:
        """
        Run evaluation on all benchmark queries.
        
        Returns:
            Results dictionary with metrics and per-query results
        """
        print(f"Running evaluation on {len(self.queries)} queries...")
        
        # Initialize services
        self.retriever = get_retriever_service()
        self.db_service = get_mongodb_service()
        
        # Run all queries
        all_rankings = []
        per_query_results = []
        
        by_type = {"text": [], "image": [], "combined": []}
        
        for i, query in enumerate(self.queries):
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{len(self.queries)}")
            
            try:
                # Execute query
                results = await self._execute_query(query)
                ranked_ids = [r.product_id for r in results]
                all_rankings.append(ranked_ids)
                
                # Track by type
                query_type = query["type"]
                by_type[query_type].append(ranked_ids)
                
                # Check if first result is correct
                expected_ids = set(query.get("expected_product_ids", []))
                is_correct = ranked_ids[0] in expected_ids if ranked_ids else False
                
                per_query_results.append({
                    "query_id": query["query_id"],
                    "type": query_type,
                    "expected": list(expected_ids),
                    "top_result": ranked_ids[0] if ranked_ids else None,
                    "correct": is_correct,
                    "num_results": len(ranked_ids)
                })
                
            except Exception as e:
                print(f"  Error on query {query['query_id']}: {e}")
                all_rankings.append([])
                per_query_results.append({
                    "query_id": query["query_id"],
                    "type": query["type"],
                    "error": str(e)
                })
        
        # Calculate metrics
        print("\nCalculating metrics...")
        calculator = MetricsCalculator()
        
        # Prepare ground truth for metrics
        gt_for_metrics = {
            str(i): set(self.ground_truth[q["query_id"]]["primary_positives"])
            for i, q in enumerate(self.queries)
        }
        
        overall_metrics = calculator.calculate_all(all_rankings, gt_for_metrics)
        
        # Calculate per-type metrics
        type_metrics = {}
        for qtype, rankings in by_type.items():
            if not rankings:
                continue
            
            # Filter queries of this type
            type_queries = [q for q in self.queries if q["type"] == qtype]
            
            # Create GT with fresh indices 0..N matching the rankings list
            type_gt = {
                str(idx): set(self.ground_truth[q["query_id"]]["primary_positives"])
                for idx, q in enumerate(type_queries)
            }
            type_metrics[qtype] = calculator.calculate_all(rankings, type_gt)
        
        await self.db_service.close()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "num_queries": len(self.queries),
            "overall_metrics": overall_metrics,
            "by_type_metrics": type_metrics,
            "per_query_results": per_query_results,
            "summary": {
                "total_correct": sum(1 for r in per_query_results if r.get("correct", False)),
                "total_errors": sum(1 for r in per_query_results if "error" in r)
            }
        }
    
    async def _execute_query(self, query: Dict) -> List:
        """Execute a single benchmark query."""
        query_type = query["type"]
        
        if query_type == "text":
            # Text-only search
            return await self.retriever.search_by_text(
                queries=[query["query_text"]],
                top_k=20
            )
        
        elif query_type == "image":
            # Image-only search
            image_path = Path(query["query_image_path"])
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            image = Image.open(image_path)
            return await self.retriever.search_by_image(
                image=image,
                top_k=20
            )
        
        elif query_type == "combined":
            # Text + image search
            image_path = Path(query["query_image_path"])
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            image = Image.open(image_path)
            
            text_results = await self.retriever.search_by_text(
                queries=[query["query_text"]],
                top_k=20
            )
            
            image_results = await self.retriever.search_by_image(
                image=image,
                top_k=20
            )
            
            return await self.retriever.merge_results(
                text_results=text_results,
                image_results=image_results,
                text_weight=0.5
            )
        
        else:
            raise ValueError(f"Unknown query type: {query_type}")


def print_results(results: Dict):
    """Print evaluation results in a readable format."""
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    
    print(f"\nTimestamp: {results['timestamp']}")
    print(f"Queries evaluated: {results['num_queries']}")
    print(f"Correct (top-1): {results['summary']['total_correct']} ({100*results['summary']['total_correct']/results['num_queries']:.1f}%)")
    print(f"Errors: {results['summary']['total_errors']}")
    
    print("\n" + "-"*60)
    print("OVERALL METRICS")
    print("-"*60)
    for metric, value in results["overall_metrics"].items():
        print(f"  {metric:20s}: {value:.4f}")
    
    print("\n" + "-"*60)
    print("METRICS BY QUERY TYPE")
    print("-"*60)
    for qtype, metrics in results["by_type_metrics"].items():
        print(f"\n{qtype.upper()}:")
        for metric, value in metrics.items():
            print(f"  {metric:20s}: {value:.4f}")
    
    print("\n" + "="*60)


def compare_to_baseline(current_results: Dict, baseline_path: Path):
    """Compare current results to baseline."""
    if not baseline_path.exists():
        print(f"\n⚠️  No baseline found at {baseline_path}")
        print("Run with --save-baseline to create one.")
        return
    
    with open(baseline_path) as f:
        baseline = json.load(f)
    
    print("\n" + "="*60)
    print("REGRESSION DETECTION")
    print("="*60)
    
    print(f"\nBaseline: {baseline['timestamp']}")
    print(f"Current:  {current_results['timestamp']}")
    
    print("\n" + "-"*60)
    print("METRIC COMPARISON")
    print("-"*60)
    
    threshold = 0.05  # 5% drop is considered a regression
    regressions = []
    
    for metric in current_results["overall_metrics"]:
        baseline_value = baseline["overall_metrics"][metric]
        current_value = current_results["overall_metrics"][metric]
        delta = current_value - baseline_value
        pct_change = (delta / baseline_value * 100) if baseline_value != 0 else 0
        
        status = "✅"
        if delta < -threshold * baseline_value:  # Significant drop
            status = "⚠️ REGRESSION"
            regressions.append(metric)
        elif delta > threshold * baseline_value:  # Significant improvement
            status = "🎉 IMPROVED"
        
        print(f"  {metric:20s}: {baseline_value:.4f} → {current_value:.4f} ({pct_change:+.1f}%) {status}")
    
    print("\n" + "="*60)
    
    if regressions:
        print(f"\n⚠️  {len(regressions)} REGRESSIONS DETECTED:")
        for metric in regressions:
            print(f"  - {metric}")
        return False
    else:
        print("\n✅ No regressions detected!")
        return True


async def main():
    parser = argparse.ArgumentParser(description="Evaluate search quality")
    parser.add_argument("--save-baseline", action="store_true", help="Save results as new baseline")
    parser.add_argument("--compare", action="store_true", help="Compare to baseline")
    args = parser.parse_args()
    
    eval_dir = Path(__file__).parent
    benchmark_path = eval_dir / "benchmark_queries.json"
    ground_truth_path = eval_dir / "ground_truth.json"
    baseline_path = eval_dir / "baseline_results.json"
    
    if not benchmark_path.exists():
        print("❌ Benchmark not found. Run: python3 -m evaluation.generate_benchmark")
        return
    
    # Run evaluation
    evaluator = SearchEvaluator(benchmark_path, ground_truth_path)
    results = await evaluator.run_evaluation()
    
    # Print results
    print_results(results)
    
    # Save baseline if requested
    if args.save_baseline:
        with open(baseline_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Saved baseline to {baseline_path}")
    
    # Compare to baseline if requested
    if args.compare:
        compare_to_baseline(results, baseline_path)


if __name__ == "__main__":
    asyncio.run(main())
