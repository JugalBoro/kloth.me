"""
Generate benchmark queries for evaluation.

This script creates a deterministic set of test queries by:
1. Sampling products from the MongoDB database
2. Creating text, image, and combined queries
3. Saving queries and ground truth to JSON files
"""

import asyncio
import json
import random
from pathlib import Path
from typing import List, Dict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.database import get_mongodb_service
from app.models import Product


class BenchmarkGenerator:
    """Generate evaluation benchmark from existing products."""
    
    def __init__(self, num_queries: int = 100, seed: int = 42):
        """
        Initialize benchmark generator.
        
        Args:
            num_queries: Total number of queries to generate
            seed: Random seed for reproducibility
        """
        self.num_queries = num_queries
        self.seed = seed
        random.seed(seed)
        
    async def generate(self) -> tuple[List[Dict], Dict]:
        """
        Generate benchmark queries and ground truth.
        
        Returns:
            (queries, ground_truth) tuple
        """
        print(f"Generating {self.num_queries} benchmark queries...")
        
        # Connect to MongoDB
        db_service = get_mongodb_service()
        
        # Get random sample of products
        total_products = await db_service.count_products()
        print(f"Total products in database: {total_products}")
        
        # Sample product IDs
        sample_size = min(self.num_queries, total_products)
        all_product_ids = []
        
        async for doc in db_service.products.find({}, {"product_id": 1}):
            all_product_ids.append(doc["product_id"])
        
        sampled_ids = random.sample(all_product_ids, sample_size)
        
        # Fetch sampled products
        products = await db_service.get_products_by_ids(sampled_ids)
        print(f"Sampled {len(products)} products")
        
        # Generate queries
        queries = []
        ground_truth = {}
        
        # Distribute evenly across query types
        queries_per_type = self.num_queries // 3
        
        for i, product in enumerate(products[:queries_per_type]):
            # Text-only query (exact description)
            text_query = self._create_text_query(product, i, exact=True)
            queries.append(text_query)
            ground_truth[text_query["query_id"]] = {
                "primary_positives": [product.product_id],
                "type": "text"
            }
        
        for i, product in enumerate(products[queries_per_type:2*queries_per_type]):
            # Image-only query
            image_query = self._create_image_query(product, i)
            queries.append(image_query)
            ground_truth[image_query["query_id"]] = {
                "primary_positives": [product.product_id],
                "type": "image"
            }
        
        for i, product in enumerate(products[2*queries_per_type:]):
            # Combined text+image query (simplified text + image)
            combined_query = self._create_combined_query(product, i)
            queries.append(combined_query)
            ground_truth[combined_query["query_id"]] = {
                "primary_positives": [product.product_id],
                "type": "combined"
            }
        
        await db_service.close()
        
        print(f"✓ Generated {len(queries)} queries")
        print(f"  - Text-only: {queries_per_type}")
        print(f"  - Image-only: {queries_per_type}")
        print(f"  - Combined: {len(queries) - 2*queries_per_type}")
        
        return queries, ground_truth
    
    def _create_text_query(self, product: Product, index: int, exact: bool = True) -> Dict:
        """Create a text-only query."""
        # Use exact description for exact match test
        query_text = product.description
        
        # Optionally simplify (take first sentence)
        if not exact and ". " in query_text:
            query_text = query_text.split(". ")[0] + "."
        
        return {
            "query_id": f"text_{index:03d}",
            "type": "text",
            "query_text": query_text,
            "expected_product_ids": [product.product_id],
            "category": product.categories.get("category1") if product.categories else None
        }
    
    def _create_image_query(self, product: Product, index: int) -> Dict:
        """Create an image-only query."""
        return {
            "query_id": f"image_{index:03d}",
            "type": "image",
            "query_image_path": product.image_path,
            "expected_product_ids": [product.product_id],
            "category": product.categories.get("category1") if product.categories else None
        }
    
    def _create_combined_query(self, product: Product, index: int) -> Dict:
        """Create a text+image query."""
        # Simplified text (first few words)
        words = product.description.split()[:5]
        query_text = " ".join(words)
        
        return {
            "query_id": f"combined_{index:03d}",
            "type": "combined",
            "query_text": query_text,
            "query_image_path": product.image_path,
            "expected_product_ids": [product.product_id],
            "category": product.categories.get("category1") if product.categories else None
        }
    
    def save(self, queries: List[Dict], ground_truth: Dict, output_dir: Path):
        """Save queries and ground truth to JSON files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save queries
        queries_file = output_dir / "benchmark_queries.json"
        with open(queries_file, 'w') as f:
            json.dump({
                "metadata": {
                    "num_queries": len(queries),
                    "seed": self.seed,
                    "generated_at": "2026-01-09T15:40:00"
                },
                "queries": queries
            }, f, indent=2)
        print(f"✓ Saved queries to {queries_file}")
        
        # Save ground truth
        gt_file = output_dir / "ground_truth.json"
        with open(gt_file, 'w') as f:
            json.dump(ground_truth, f, indent=2)
        print(f"✓ Saved ground truth to {gt_file}")


async def main():
    """Generate benchmark queries."""
    generator = BenchmarkGenerator(num_queries=100, seed=42)
    queries, ground_truth = await generator.generate()
    
    output_dir = Path(__file__).parent
    generator.save(queries, ground_truth, output_dir)
    
    print("\n✅ Benchmark generation complete!")
    print("Next step: python3 -m evaluation.evaluate")


if __name__ == "__main__":
    asyncio.run(main())
