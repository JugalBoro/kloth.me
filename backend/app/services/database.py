from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
from functools import lru_cache
import certifi

from app.config import get_settings
from app.models import Product


class MongoDBService:
    """Service for interacting with MongoDB."""
    
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    
    def __init__(self):
        """Initialize MongoDB connection."""
        settings = get_settings()
        self._client = AsyncIOMotorClient(
            settings.mongodb_uri,
            tlsCAFile=certifi.where(),
            tlsAllowInvalidCertificates=True
        )
        self._db = self._client[settings.mongodb_db]
    
    @property
    def products(self):
        """Get products collection."""
        return self._db.products
    
    async def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """
        Retrieve a product by its ID.
        
        Args:
            product_id: Unique product identifier
            
        Returns:
            Product model or None if not found
        """
        doc = await self.products.find_one({"product_id": product_id})
        if doc:
            # Remove MongoDB's _id field
            doc.pop("_id", None)
            return Product(**doc)
        return None
    
    async def get_products_by_ids(self, product_ids: List[str]) -> List[Product]:
        """
        Retrieve multiple products by their IDs.
        
        Args:
            product_ids: List of product identifiers
            
        Returns:
            List of Product models
        """
        cursor = self.products.find({"product_id": {"$in": product_ids}})
        products = []
        async for doc in cursor:
            doc.pop("_id", None)
            products.append(Product(**doc))
        return products
    
    async def insert_product(self, product: Product) -> str:
        """
        Insert a new product.
        
        Args:
            product: Product model to insert
            
        Returns:
            Inserted product ID
        """
        result = await self.products.insert_one(product.model_dump())
        return str(result.inserted_id)
    
    async def insert_products(self, products: List[Product]) -> int:
        """
        Insert multiple products.
        
        Args:
            products: List of Product models to insert
            
        Returns:
            Number of products inserted
        """
        if not products:
            return 0
        
        docs = [p.model_dump() for p in products]
        result = await self.products.insert_many(docs)
        return len(result.inserted_ids)
    
    async def count_products(self) -> int:
        """Get total number of products."""
        return await self.products.count_documents({})
    
    async def create_indexes(self):
        """Create database indexes for better performance."""
        await self.products.create_index("product_id", unique=True)
        await self.products.create_index("category")
    
    async def close(self):
        """Close database connection."""
        if self._client:
            self._client.close()


@lru_cache()
def get_mongodb_service() -> MongoDBService:
    """Get cached MongoDB service instance."""
    return MongoDBService()
