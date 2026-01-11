from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import io
import time
from typing import Optional, List
import json
from pathlib import Path

from app.config import get_settings
from app.models import ChatResponse, ProductResult, DebugInfo, ChatMessage
from app.services.llm_planner import get_llm_planner
from app.services.retriever import get_retriever_service
from app.services.embedding_service import get_embedding_service

# Initialize FastAPI app
app = FastAPI(
    title="Fashion Search API",
    description="Agentic multimodal fashion search system",
    version="1.0.0"
)

# Get settings
settings = get_settings()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount images directory for serving product images
images_dir = Path("data/images")
images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")

# Initialize services (warm up models)
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("Initializing services...")
    # Initialize embedding service (loads CLIP model)
    get_embedding_service()
    print("Services initialized successfully")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Fashion Search API is running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "embedding_model": "loaded",
        }
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    message: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    chat_history: Optional[str] = Form(None)  # JSON string
):
    """
    Main chat endpoint for fashion search.
    
    Args:
        message: User's text query
        image: Optional uploaded image file
        chat_history: Optional JSON string of chat history
        
    Returns:
        ChatResponse with assistant message and product results
    """
    start_time = time.time()
    
    # Parse chat history
    history = []
    if chat_history:
        try:
            history_data = json.loads(chat_history)
            history = [ChatMessage(**msg) for msg in history_data]
        except Exception as e:
            print(f"Error parsing chat history: {e}")
    
    # Validate that at least message or image is provided
    if not message and not image:
        raise HTTPException(status_code=400, detail="Either message or image must be provided")
    
    # Use empty string if no message provided (image-only search)
    if not message:
        message = ""
    
    # Load image if provided
    uploaded_image = None
    if image:
        try:
            image_data = await image.read()
            uploaded_image = Image.open(io.BytesIO(image_data))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
    
    try:
        # Step 1: Create query plan using LLM
        llm_planner = get_llm_planner()
        query_plan = await llm_planner.create_query_plan(
            user_message=message,
            image=uploaded_image,
            chat_history=[{"role": m.role, "content": m.content} for m in history]
        )
        
        print(f"Query plan: {query_plan}")
        
        # Step 2: Execute retrieval
        retriever = get_retriever_service()
        
        text_results = []
        image_results = []
        
        # Text search
        if query_plan.refined_queries:
            text_results = await retriever.search_by_text(
                queries=query_plan.refined_queries,
                top_k=query_plan.top_k,
                filters=query_plan.filters
            )
        
        # Image search
        if query_plan.use_image and uploaded_image:
            image_results = await retriever.search_by_image(
                image=uploaded_image,
                top_k=query_plan.top_k,
                filters=query_plan.filters
            )
        
        # Step 3: Merge results
        if text_results and image_results:
            final_results = await retriever.merge_results(
                text_results=text_results,
                image_results=image_results,
                text_weight=query_plan.text_weight
            )
        elif text_results:
            final_results = text_results
        elif image_results:
            final_results = image_results
        else:
            final_results = []
        
        # Limit to top 20 results for response
        final_results = final_results[:20]
        
        # Step 4: Generate natural language response
        products_for_llm = [
            {"description": r.description, "score": r.score}
            for r in final_results
        ]
        
        assistant_message = await llm_planner.generate_response(
            user_query=message,
            products=products_for_llm,
            query_plan=query_plan
        )
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Create debug info
        debug_info = DebugInfo(
            query_plan=query_plan,
            text_results_count=len(text_results),
            image_results_count=len(image_results),
            total_unique_results=len(final_results),
            processing_time_ms=processing_time
        )
        
        return ChatResponse(
            assistant_message=assistant_message,
            results=final_results,
            debug=debug_info
        )
        
    except Exception as e:
        print(f"Error processing chat request: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
