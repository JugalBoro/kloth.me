from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Optional, Dict, Tuple
from PIL import Image
import uuid
import re

from app.config import get_settings
from app.models import ProductResult
from app.services.embedding_service import get_embedding_service
from app.services.database import get_mongodb_service


class RetrieverService:
    """Service for vector search and result retrieval."""
    
    def __init__(self):
        """Initialize Qdrant client."""
        settings = get_settings()
        
        # Support both local and cloud Qdrant
        if settings.qdrant_api_key:
            # Cloud Qdrant with API key
            self.client = QdrantClient(
                url=f"https://{settings.qdrant_host}:{settings.qdrant_port}" if settings.qdrant_use_https else f"http://{settings.qdrant_host}:{settings.qdrant_port}",
                api_key=settings.qdrant_api_key,
                timeout=60,
            )
        else:
            # Local Qdrant
            self.client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                timeout=60,
            )
            
        self.collection_name = settings.qdrant_collection
        self.embedding_service = get_embedding_service()
        self.db_service = get_mongodb_service()
    
    def _filter_results(
        self,
        results: List[ProductResult],
        filters: Optional[Dict[str, str]]
    ) -> List[ProductResult]:
        """Apply strict filters to results."""
        if not filters:
            return results
            
        filtered = []
        for res in results:
            keep = True
            
            # Check color
            if "color" in filters and filters["color"]:
                color = filters["color"].lower()
                # Check description and categories for color
                text_content = (res.description or "").lower()
                cats = res.categories or {}
                cat_content = " ".join([str(v).lower() for v in cats.values()])
                
                # Regex for whole word match to avoid "zippered" matching "red"
                pattern = r'\b' + re.escape(color) + r'\b'
                if not re.search(pattern, text_content) and not re.search(pattern, cat_content):
                    keep = False
            
            # Check category
            if keep and "category" in filters and filters["category"]:
                cat = filters["category"].lower()
                text_content = (res.description or "").lower()
                cats = res.categories or {}
                cat_content = " ".join([str(v).lower() for v in cats.values()])
                
                # Regex for category as well
                pattern = r'\b' + re.escape(cat) + r'\b'
                if not re.search(pattern, text_content) and not re.search(pattern, cat_content):
                    keep = False
            
            if keep:
                filtered.append(res)
                
        return filtered

    async def search_by_text(
        self,
        queries: List[str],
        top_k: int = 20,
        filters: Optional[Dict[str, str]] = None,
        score_threshold: float = 0.70
    ) -> List[ProductResult]:
        """
        Search for products using text queries.
        
        Args:
            queries: List of text queries to search
            top_k: Number of results to retrieve per query
            filters: Optional dictionary of strict filters (color, category)
            score_threshold: Minimum similarity score to include result
            
        Returns:
            List of ProductResult objects, deduplicated and sorted by score
        """
        all_results = {}  # product_id -> (score, product_data)
        # Filter out empty queries (for image-only searches)
        valid_queries = [q for q in queries if q and q.strip()]
        
        if not valid_queries:
            return []
            
        # If filtering, fetch more candidates to ensure we have enough after filtering
        search_limit = top_k * 5 if filters else top_k
        
        for query in valid_queries:
            # Generate embedding for query
            query_embedding = self.embedding_service.encode_text(query)
            
            # Search in Qdrant (filter for text embeddings)
            search_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=search_limit,
                # Using score_threshold here at query level is efficient
                score_threshold=score_threshold,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="modality",
                            match=MatchValue(value="text")
                        )
                    ]
                )
            ).points
            
            # Merge results
            for result in search_results:
                product_id = result.payload["product_id"]
                score = result.score
                
                # Keep highest score for each product
                if product_id not in all_results or score > all_results[product_id][0]:
                    all_results[product_id] = (score, result.payload)
        
        # Convert to ProductResult and fetch full product data
        initial_results = await self._convert_to_product_results(all_results)
        
        # Apply filters if present
        if filters:
            final_results = self._filter_results(initial_results, filters)
            return final_results[:top_k]
            
        return initial_results
    
    async def search_by_image(
        self,
        image: Image.Image,
        top_k: int = 20,
        filters: Optional[Dict[str, str]] = None,
        score_threshold: float = 0.70
    ) -> List[ProductResult]:
        """
        Search for products using an image.
        
        Args:
            image: PIL Image object
            top_k: Number of results to retrieve
            filters: Optional dictionary of strict filters
            score_threshold: Minimum similarity score to include result
            
        Returns:
            List of ProductResult objects
        """
        # Generate embedding for image
        image_embedding = self.embedding_service.encode_image(image)
        
        # If filtering, fetch more candidates
        search_limit = top_k * 5 if filters else top_k
        
        # Search in Qdrant (filter for image embeddings)
        search_results = self.client.query_points(
            collection_name=self.collection_name,
            query=image_embedding,
            limit=search_limit,
            score_threshold=score_threshold,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="modality",
                        match=MatchValue(value="image")
                    )
                ]
            )
        ).points
        
        # Convert results
        all_results = {
            result.payload["product_id"]: (result.score, result.payload)
            for result in search_results
        }
        
        initial_results = await self._convert_to_product_results(all_results)
        
        # Apply filters if present
        if filters:
            final_results = self._filter_results(initial_results, filters)
            return final_results[:top_k]
            
        return initial_results
    
    async def merge_results(
        self,
        text_results: List[ProductResult],
        image_results: List[ProductResult],
        text_weight: float = 0.5
    ) -> List[ProductResult]:
        """
        Merge and rerank text and image search results.
        
        Args:
            text_results: Results from text search
            image_results: Results from image search
            text_weight: Weight for text results (0-1), image weight = 1 - text_weight
            
        Returns:
            Merged and reranked list of ProductResult objects
        """
        # Handle empty cases early
        if not text_results and not image_results:
            return []
            
        image_weight = 1.0 - text_weight
        
        # Create dictionaries for easy lookup
        text_dict = {r.product_id: r.score for r in text_results}
        image_dict = {r.product_id: r.score for r in image_results}
        
        # Get all unique product IDs
        all_product_ids = set(text_dict.keys()) | set(image_dict.keys())
        
        # Compute weighted scores
        merged_scores = []
        for product_id in all_product_ids:
            text_score = text_dict.get(product_id, 0.0)
            image_score = image_dict.get(product_id, 0.0)
            
            # Use non-zero score if present, else 0 (or could use penalty)
            # If a result is in one list but not the other, it means it was retrieved
            # by one modality but missed (or below threshold) in the other.
            
            final_score = (text_weight * text_score) + (image_weight * image_score)
            
            # Correction: if item only appeared in one source, re-normalize?
            # For now, simple weighted sum is robust enough. 
            # If text_score is 0, it contributes nothing.
            
            merged_scores.append((product_id, final_score))
        
        # Sort by final score
        merged_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Fetch product data from MongoDB
        product_ids = [pid for pid, _ in merged_scores]
        products = await self.db_service.get_products_by_ids(product_ids)
        
        # Create ProductResult objects with merged scores
        product_map = {p.product_id: p for p in products}
        results = []
        
        for product_id, score in merged_scores:
            if product_id in product_map:
                product = product_map[product_id]
                results.append(ProductResult(
                    product_id=product.product_id,
                    description=product.description,
                    image_path=product.image_path,
                    score=score,
                    categories=product.categories
                ))
        
        return results
    
    async def _convert_to_product_results(
        self,
        results_dict: Dict[str, Tuple[float, dict]]
    ) -> List[ProductResult]:
        """
        Convert Qdrant results to ProductResult objects.
        
        Args:
            results_dict: Dictionary mapping product_id to (score, payload)
            
        Returns:
            List of ProductResult objects
        """
        # Sort by score
        sorted_results = sorted(results_dict.items(), key=lambda x: x[1][0], reverse=True)
        
        # Fetch product data
        product_ids = [pid for pid, _ in sorted_results]
        products = await self.db_service.get_products_by_ids(product_ids)
        product_map = {p.product_id: p for p in products}
        
        # Create ProductResult objects
        results = []
        for product_id, (score, _) in sorted_results:
            if product_id in product_map:
                product = product_map[product_id]
                results.append(ProductResult(
                    product_id=product.product_id,
                    description=product.description,
                    image_path=product.image_path,
                    score=score,
                    categories=product.categories
                ))
        
        return results
    
    def create_collection(self, dimension: int = 512):
        """
        Create Qdrant collection if it doesn't exist.
        
        Args:
            dimension: Embedding vector dimension
        """
        from qdrant_client.models import PayloadSchemaType
        
        try:
            self.client.get_collection(self.collection_name)
            print(f"Collection '{self.collection_name}' already exists")
            
            # Create index on modality field if it doesn't exist
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="modality",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                print("Created index on 'modality' field")
            except Exception as e:
                print(f"Index on 'modality' may already exist: {e}")
        except:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
            )
            print(f"Created collection '{self.collection_name}'")
            
            # Create index on modality field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="modality",
                field_schema=PayloadSchemaType.KEYWORD
            )
            print("Created index on 'modality' field")

    
    def insert_batch_embeddings(
        self,
        product_ids: List[str],
        text_embeddings: List[List[float]],
        image_embeddings: List[List[float]]
    ):
        """
        Insert batch of text and image embeddings.
        
        Args:
            product_ids: List of unique product identifiers
            text_embeddings: List of text embedding vectors
            image_embeddings: List of image embedding vectors
        """
        points = []
        
        for pid, text_emb, img_emb in zip(product_ids, text_embeddings, image_embeddings):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=text_emb,
                    payload={"product_id": pid, "modality": "text"}
                )
            )
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=img_emb,
                    payload={"product_id": pid, "modality": "image"}
                )
            )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def insert_embeddings(
            self,
            product_id: str,
            text_embedding: List[float],
            image_embedding: List[float]
        ):
        """
        Insert text and image embeddings for a product.
        
        Args:
            product_id: Unique product identifier
            text_embedding: Text embedding vector
            image_embedding: Image embedding vector
        """
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=text_embedding,
                payload={"product_id": product_id, "modality": "text"}
            ),
            PointStruct(
                id=str(uuid.uuid4()),
                vector=image_embedding,
                payload={"product_id": product_id, "modality": "image"}
            )
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )


def get_retriever_service() -> RetrieverService:
    """Get retriever service instance."""
    return RetrieverService()
