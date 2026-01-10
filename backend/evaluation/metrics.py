"""
Evaluation metrics for search quality.
"""

from typing import List, Dict, Set
import numpy as np


def calculate_mrr(rankings: List[List[str]], ground_truth: Dict[str, Set[str]]) -> float:
    """
    Calculate Mean Reciprocal Rank.
    
    Args:
        rankings: List of ranked product IDs for each query
        ground_truth: Dict mapping query_id to set of relevant product IDs
        
    Returns:
        MRR score (0.0 to 1.0, higher is better)
    """
    reciprocal_ranks = []
    
    for query_id, ranked_ids in enumerate(rankings):
        relevant_ids = ground_truth.get(str(query_id), set())
        
        # Find rank of first relevant item
        for rank, product_id in enumerate(ranked_ids, start=1):
            if product_id in relevant_ids:
                reciprocal_ranks.append(1.0 / rank)
                break
        else:
            # No relevant item found
            reciprocal_ranks.append(0.0)
    
    return np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0


def calculate_precision_at_k(
    rankings: List[List[str]], 
    ground_truth: Dict[str, Set[str]], 
    k: int
) -> float:
    """
    Calculate Precision@K.
    
    Args:
        rankings: List of ranked product IDs for each query
        ground_truth: Dict mapping query_id to set of relevant product IDs
        k: Cut-off rank
        
    Returns:
        Precision@K score (0.0 to 1.0)
    """
    precisions = []
    
    for query_id, ranked_ids in enumerate(rankings):
        relevant_ids = ground_truth.get(str(query_id), set())
        top_k = ranked_ids[:k]
        
        num_relevant = sum(1 for pid in top_k if pid in relevant_ids)
        precisions.append(num_relevant / k)
    
    return np.mean(precisions) if precisions else 0.0


def calculate_recall_at_k(
    rankings: List[List[str]], 
    ground_truth: Dict[str, Set[str]], 
    k: int
) -> float:
    """
    Calculate Recall@K.
    
    Args:
        rankings: List of ranked product IDs for each query
        ground_truth: Dict mapping query_id to set of relevant product IDs
        k: Cut-off rank
        
    Returns:
        Recall@K score (0.0 to 1.0)
    """
    recalls = []
    
    for query_id, ranked_ids in enumerate(rankings):
        relevant_ids = ground_truth.get(str(query_id), set())
        if not relevant_ids:
            continue
            
        top_k = ranked_ids[:k]
        num_relevant = sum(1 for pid in top_k if pid in relevant_ids)
        recalls.append(num_relevant / len(relevant_ids))
    
    return np.mean(recalls) if recalls else 0.0


def calculate_average_rank(rankings: List[List[str]], ground_truth: Dict[str, Set[str]]) -> float:
    """
    Calculate average rank of first relevant item.
    
    Lower is better.
    """
    ranks = []
    
    for query_id, ranked_ids in enumerate(rankings):
        relevant_ids = ground_truth.get(str(query_id), set())
        
        for rank, product_id in enumerate(ranked_ids, start=1):
            if product_id in relevant_ids:
                ranks.append(rank)
                break
    
    return np.mean(ranks) if ranks else float('inf')


def calculate_category_accuracy(
    rankings: List[List[str]],
    query_categories: List[str],
    product_categories: Dict[str, str]
) -> float:
    """
    Calculate percentage where top result matches query category.
    
    Args:
        rankings: List of ranked product IDs
        query_categories: List of expected categories
        product_categories: Dict mapping product_id to category
        
    Returns:
        Accuracy (0.0 to 1.0)
    """
    matches = 0
    total = 0
    
    for ranked_ids, expected_category in zip(rankings, query_categories):
        if not expected_category or not ranked_ids:
            continue
            
        top_product = ranked_ids[0]
        top_category = product_categories.get(top_product)
        
        if top_category == expected_category:
            matches += 1
        total += 1
    
    return matches / total if total > 0 else 0.0


class MetricsCalculator:
    """Calculate all evaluation metrics."""
    
    def calculate_all(
        self,
        rankings: List[List[str]],
        ground_truth: Dict[str, Set[str]],
        query_categories: List[str] = None,
        product_categories: Dict[str, str] = None
    ) -> Dict:
        """
        Calculate all metrics.
        
        Returns:
            Dictionary of metric names to values
        """
        metrics = {
            "mrr": calculate_mrr(rankings, ground_truth),
            "precision_at_1": calculate_precision_at_k(rankings, ground_truth, k=1),
            "precision_at_5": calculate_precision_at_k(rankings, ground_truth, k=5),
            "precision_at_10": calculate_precision_at_k(rankings, ground_truth, k=10),
            "recall_at_5": calculate_recall_at_k(rankings, ground_truth, k=5),
            "recall_at_10": calculate_recall_at_k(rankings, ground_truth, k=10),
            "recall_at_20": calculate_recall_at_k(rankings, ground_truth, k=20),
            "average_rank": calculate_average_rank(rankings, ground_truth),
        }
        
        if query_categories and product_categories:
            metrics["category_accuracy"] = calculate_category_accuracy(
                rankings, query_categories, product_categories
            )
        
        return metrics
