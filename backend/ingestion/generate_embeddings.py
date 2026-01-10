"""
Generate embeddings for products and store in Qdrant.
"""

import json
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.services.embedding_service import get_embedding_service
from app.services.retriever import get_retriever_service
from app.config import get_settings


def generate_and_store_embeddings():
    """Generate text and image embeddings for all products."""
    
    # Load metadata
    metadata_path = Path("data/products_metadata.json")
    if not metadata_path.exists():
        print("Error: products_metadata.json not found!")
        print("Please run download_dataset.py first")
        return
    
    print("Loading products from metadata file...")
    with open(metadata_path, 'r') as f:
        products = json.load(f)
    
    print(f"Found {len(products)} products")
    
    # Initialize services
    print("\nInitializing embedding service (loading CLIP model)...")
    embedding_service = get_embedding_service()
    dimension = embedding_service.embedding_dimension
    print(f"Embedding dimension: {dimension}")
    
    print("\nInitializing Qdrant service...")
    retriever_service = get_retriever_service()
    
    # Create collection
    print("Creating Qdrant collection...")
    retriever_service.create_collection(dimension=dimension)
    
    # Process products in batches
    batch_size = 32
    print(f"\nGenerating embeddings (batch size: {batch_size})...")
    
    successful = 0
    failed = 0
    
    for i in tqdm(range(0, len(products), batch_size)):
        batch = products[i:i + batch_size]
        
        # Prepare batch data
        batch_descriptions = []
        batch_images = []
        batch_product_ids = []
        
        for product in batch:
            try:
                # Load image
                image_path = Path(product["image_path"])
                if not image_path.exists():
                    print(f"\nWarning: Image not found: {image_path}")
                    continue
                
                image = Image.open(image_path)
                
                batch_descriptions.append(product["description"])
                batch_images.append(image)
                batch_product_ids.append(product["product_id"])
                
            except Exception as e:
                print(f"\nError loading product {product['product_id']}: {e}")
                failed += 1
                continue
        
        if not batch_descriptions:
            continue
        
        try:
            # Generate embeddings in batch
            text_embeddings = embedding_service.encode_texts(batch_descriptions)
            image_embeddings = embedding_service.encode_images(batch_images)
            
            # Store in Qdrant
            # Store in Qdrant (Batch Insert)
            try:
                retriever_service.insert_batch_embeddings(
                    product_ids=batch_product_ids,
                    text_embeddings=text_embeddings,
                    image_embeddings=image_embeddings
                )
                successful += len(batch_product_ids)
            except Exception as e:
                print(f"\nError storing batch: {e}")
                failed += len(batch_product_ids)
                    
        except Exception as e:
            print(f"\nError processing batch: {e}")
            failed += len(batch_descriptions)
            continue
    
    print(f"\n✓ Successfully processed {successful} products")
    if failed > 0:
        print(f"✗ Failed to process {failed} products")
    
    # Verify
    try:
        collection_info = retriever_service.client.get_collection(
            retriever_service.collection_name
        )
        print(f"\n✓ Total vectors in Qdrant: {collection_info.points_count}")
        print(f"  Expected: {successful * 2} (2 vectors per product)")
    except Exception as e:
        print(f"Error getting collection info: {e}")


if __name__ == "__main__":
    generate_and_store_embeddings()
