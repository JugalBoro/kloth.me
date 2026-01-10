"""
Download and sample Fashion200k dataset from Hugging Face.
"""

from datasets import load_dataset
import random
from pathlib import Path
import json
from PIL import Image
from tqdm import tqdm
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.config import get_settings


def download_and_sample_dataset():
    """Download Fashion200k from Hugging Face and sample a subset."""
    settings = get_settings()
    
    print(f"Loading Fashion200k dataset from Hugging Face: {settings.dataset_name}")
    print("This may take a few minutes on first run...")
    
    # Load dataset
    try:
        dataset = load_dataset(settings.dataset_name, split="data")
        print(f"Dataset loaded: {len(dataset)} total items")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        print("\nTrying alternative loading method...")
        # Alternative: Load from Kaggle or manual download
        print("Please download the dataset manually from:")
        print("https://www.kaggle.com/datasets/mayukh18/fashion200k-dataset")
        return None
    
    # Sample subset
    random.seed(settings.random_seed)
    total_items = len(dataset)
    sample_size = min(settings.sample_size, total_items)
    
    print(f"\nSampling {sample_size} items from {total_items} total items...")
    
    # Random sampling with reproducibility
    indices = random.sample(range(total_items), sample_size)
    sampled_data = dataset.select(indices)
    
    # Create data directory
    data_dir = Path("data")
    images_dir = data_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Process and save sampled data
    processed_products = []
    
    print("\nProcessing sampled products...")
    for idx, item in enumerate(tqdm(sampled_data)):
        try:
            # Generate product ID
            product_id = f"fashion_{idx:06d}"
            
            # Extract description (field names vary by dataset version)
            description = None
            for desc_field in ["description", "productDisplayName", "caption", "text"]:
                if desc_field in item and item[desc_field]:
                    description = str(item[desc_field])
                    break
            
            if not description:
                print(f"Warning: No description found for item {idx}, skipping")
                continue
            
            # Extract and save image
            image = None
            for img_field in ["image", "img", "photo"]:
                if img_field in item and item[img_field]:
                    image = item[img_field]
                    break
            
            if not image:
                print(f"Warning: No image found for item {idx}, skipping")
                continue
            
            # Save image
            image_filename = f"{product_id}.jpg"
            image_path = images_dir / image_filename
            
            # Convert to PIL Image if necessary
            if not isinstance(image, Image.Image):
                continue
            
            # Convert to RGB and save
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(image_path, 'JPEG', quality=85)
            
            # Extract categories (HuggingFace has category1, category2, category3)
            categories = {}
            for cat_num in [1, 2, 3]:
                cat_field = f"category{cat_num}"
                if cat_field in item and item[cat_field]:
                    categories[cat_field] = str(item[cat_field])
            
            # Fallback to generic category field if available
            if not categories:
                for cat_field in ["category", "masterCategory", "subCategory", "articleType"]:
                    if cat_field in item and item[cat_field]:
                        categories["category"] = str(item[cat_field])
                        break
            
            # Create product record
            product = {
                "product_id": product_id,
                "description": description,
                "image_path": str(image_path),
                "categories": categories if categories else None,
                "source_index": indices[idx]
            }
            
            processed_products.append(product)
            
        except Exception as e:
            print(f"Error processing item {idx}: {e}")
            continue
    
    # Save processed products metadata
    metadata_path = data_dir / "products_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(processed_products, f, indent=2)
    
    print(f"\n✓ Successfully processed {len(processed_products)} products")
    print(f"✓ Images saved to: {images_dir}")
    print(f"✓ Metadata saved to: {metadata_path}")
    
    return processed_products


if __name__ == "__main__":
    products = download_and_sample_dataset()
    if products:
        print(f"\nSample product:")
        print(json.dumps(products[0], indent=2))
