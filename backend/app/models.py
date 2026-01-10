from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ChatMessage(BaseModel):
    """Individual chat message."""
    role: str  # "user" or "assistant"
    content: str
    image_url: Optional[str] = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=1000)
    chat_history: Optional[List[ChatMessage]] = Field(default_factory=list)
    # Note: image file will be sent as multipart form data, not JSON


class ProductResult(BaseModel):
    """Individual product search result."""
    product_id: str
    description: str
    image_path: str
    score: float = Field(..., ge=0.0, le=1.01)  # Allow small FP errors
    categories: Optional[Dict[str, str]] = None


class QueryPlan(BaseModel):
    """LLM-generated query plan for retrieval."""
    refined_queries: List[str] = Field(..., min_items=1)
    use_image: bool = False
    text_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    top_k: int = Field(default=20, ge=1, le=100)
    filters: Optional[Dict[str, str]] = None  # Extracted filters like {"color": "red"}
    reasoning: Optional[str] = None  # Why the LLM chose this plan


class DebugInfo(BaseModel):
    """Debug information about the search process."""
    query_plan: Optional[QueryPlan] = None
    text_results_count: int = 0
    image_results_count: int = 0
    total_unique_results: int = 0
    processing_time_ms: float = 0.0


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    assistant_message: str
    results: List[ProductResult]
    debug: Optional[DebugInfo] = None


class Product(BaseModel):
    """Product document stored in MongoDB."""
    product_id: str
    description: str
    image_path: str
    categories: Optional[Dict[str, str]] = None
    source_index: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
