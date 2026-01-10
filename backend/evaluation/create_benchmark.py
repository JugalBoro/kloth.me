"""
Create benchmark dataset for evaluation.
Uses self-supervised approach with identity and paraphrased queries.
"""

import json
import random
from pathlib import Path
import sys
import asyncio
import google.generativeai as genai

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings


async def generate_paraphrases(description: str, model: genai.GenerativeModel) -> list[str]:
    """Generate paraphrased queries using Gemini."""
    prompt = f"""Generate 2 different paraphrased versions of this fashion product description.
Make them natural queries a user might search for.
Keep them concise (under 20 words each).

Original: "{description}"

Output as a JSON array of strings, e.g.: ["paraphrase 1", "paraphrase 2"]"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=200,
            )
        )
        
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        # Handle different response formats
        if isinstance(result, list):
            return result[:2]
        elif isinstance(result, dict):
            for value in result.values():
                if isinstance(value, list):
                    return value[:2]
        return []
        
    except Exception as e:
        print(f"Error generating paraphrases: {e}")
        return []


async def create_benchmark():
    """Create evaluation benchmark dataset."""
    
    # Load products metadata
    metadata_path = Path("data/products_metadata.json")
    if not metadata_path.exists():
        print("Error: products_metadata.json not found!")
        return
    
    with open(metadata_path, 'r') as f:
        all_products = json.load(f)
    
    print(f"Found {len(all_products)} total products")
    
    # Sample 100 products for benchmark
    random.seed(42)
    benchmark_size = min(100, len(all_products))
    sampled_products = random.sample(all_products, benchmark_size)
    
    print(f"Sampled {benchmark_size} products for benchmark")
    
    # Initialize Gemini
    settings = get_settings()
    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    
    benchmark_queries = []
    query_id = 0
    
    print("\nGenerating benchmark queries...")
    
    for i, product in enumerate(sampled_products):
        print(f"Processing product {i+1}/{len(sampled_products)}: {product['product_id']}")
        
        # 1. Identity query (text)
        benchmark_queries.append({
            "id": f"query_{query_id:03d}",
            "type": "text",
            "text": product["description"],
            "image_path": None,
            "expected_product_ids": [product["product_id"]],
            "expected_in_top_k": 5
        })
        query_id += 1
        
        # 2. Paraphrased queries
        paraphrases = await generate_paraphrases(product["description"], model)
        for j, paraphrase in enumerate(paraphrases):
            benchmark_queries.append({
                "id": f"query_{query_id:03d}",
                "type": "text",
                "text": paraphrase,
                "image_path": None,
                "expected_product_ids": [product["product_id"]],
                "expected_in_top_k": 10  # More lenient for paraphrases
            })
            query_id += 1
        
        # 3. Image query
        benchmark_queries.append({
            "id": f"query_{query_id:03d}",
            "type": "image",
            "text": None,
            "image_path": product["image_path"],
            "expected_product_ids": [product["product_id"]],
            "expected_in_top_k": 5
        })
        query_id += 1
        
        # Only do a few to save API costs for now
        if i >= 19:  # 20 products = ~80 queries
            print(f"\nStopping at 20 products to save API costs")
            break
    
    # Save benchmark
    benchmark_data = {
        "version": "1.0",
        "created_at": "2026-01-07",
        "num_queries": len(benchmark_queries),
        "queries": benchmark_queries
    }
    
    output_dir = Path("evaluation")
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "benchmark.json"
    with open(output_path, 'w') as f:
        json.dump(benchmark_data, f, indent=2)
    
    print(f"\n✓ Created benchmark with {len(benchmark_queries)} queries")
    print(f"✓ Saved to: {output_path}")
    
    # Statistics
    type_counts = {}
    for q in benchmark_queries:
        type_counts[q["type"]] = type_counts.get(q["type"], 0) + 1
    
    print(f"\nQuery type distribution:")
    for qtype, count in type_counts.items():
        print(f"  {qtype}: {count}")


if __name__ == "__main__":
    asyncio.run(create_benchmark())
