"""
Ingest products to MongoDB.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.models import Product
from app.services.database import get_mongodb_service


async def ingest_products():
    """Load products from metadata file and insert into MongoDB."""
    
    # Load metadata
    metadata_path = Path("data/products_metadata.json")
    if not metadata_path.exists():
        print("Error: products_metadata.json not found!")
        print("Please run download_dataset.py first")
        return
    
    print("Loading products from metadata file...")
    with open(metadata_path, 'r') as f:
        products_data = json.load(f)
    
    print(f"Found {len(products_data)} products to ingest")
    
    # Initialize database service
    db_service = get_mongodb_service()
    
    # Create indexes
    print("Creating database indexes...")
    await db_service.create_indexes()
    
    # Check if products already exist
    existing_count = await db_service.count_products()
    if existing_count > 0:
        print(f"\nWarning: {existing_count} products already exist in database")
        print("To ensure data consistency with the new 5000-item sample, we should CLEAR the old data.")
        response = input("Do you want to CLEAR existing data and insert new products? (y/n): ")
        if response.lower() == 'y':
            print("Clearing database...")
            await db_service.products.delete_many({})
            print("✓ Database cleared.")
        else:
            print("Ingestion cancelled to prevent data corruption.")
            return
    
    # Convert to Product models
    products = [Product(**p) for p in products_data]
    
    # Insert products
    print(f"\nInserting {len(products)} products into MongoDB...")
    try:
        inserted_count = await db_service.insert_products(products)
        print(f"✓ Successfully inserted {inserted_count} products")
        
        # Verify
        total_count = await db_service.count_products()
        print(f"✓ Total products in database: {total_count}")
        
        # Show sample
        sample_product = await db_service.get_product_by_id(products[0].product_id)
        if sample_product:
            print(f"\nSample product from database:")
            print(f"  ID: {sample_product.product_id}")
            print(f"  Description: {sample_product.description[:80]}...")
            print(f"  Categories: {sample_product.categories}")
        
    except Exception as e:
        print(f"Error inserting products: {e}")
    finally:
        await db_service.close()


if __name__ == "__main__":
    asyncio.run(ingest_products())
