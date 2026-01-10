from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from typing import List, Union
import numpy as np
from functools import lru_cache
import torch

from app.config import get_settings


class EmbeddingService:
    """Service for generating text and image embeddings using CLIP."""
    
    _instance = None
    _model = None
    _processor = None
    _use_transformers = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one model instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the CLIP model (only once due to singleton)."""
        if self._model is None:
            settings = get_settings()
            print(f"Loading CLIP model: {settings.clip_model_name}")
            
            # Check if CUDA is available
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {self.device}")
            
            try:
                # Try SentenceTransformer first (standard path)
                if "fashion-clip" not in settings.clip_model_name:
                     self._model = SentenceTransformer(settings.clip_model_name, device=self.device)
                     self._use_transformers = False
                     print("CLIP model loaded successfully (SentenceTransformer)")
                else:
                    raise ValueError("Force Transformers for Fashion-CLIP")
            except Exception as e:
                print(f"SentenceTransformer load failed or skipped: {e}")
                print("Attempting direct Transformers load...")
                try:
                    self._model = CLIPModel.from_pretrained(settings.clip_model_name).to(self.device)
                    self._processor = CLIPProcessor.from_pretrained(settings.clip_model_name)
                    self._use_transformers = True
                    print(f"CLIP model loaded successfully (Transformers: {settings.clip_model_name})")
                except Exception as hf_e:
                    raise RuntimeError(f"Failed to load model with both methods. ST error: {e}, HF error: {hf_e}")
    
    def encode_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        if self._use_transformers:
            inputs = self._processor(text=[text], return_tensors="pt", padding=True, truncation=True).to(self.device)
            with torch.no_grad():
                outputs = self._model.get_text_features(**inputs)
            
            # Check for NaNs in raw output
            if torch.isnan(outputs).any():
                print(f"WARNING: NaN detected in text embedding for '{text[:20]}...'")
                outputs = torch.nan_to_num(outputs, nan=0.0)

            # Normalize embeddings if using raw CLIPModel
            outputs = outputs / (outputs.norm(p=2, dim=-1, keepdim=True) + 1e-6)
            
            # Check for NaNs after normalization (just in case)
            if torch.isnan(outputs).any():
                outputs = torch.nan_to_num(outputs, nan=0.0)
                
            return outputs.cpu().numpy()[0].tolist()
        else:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
    
    def encode_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch processing)."""
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        if self._use_transformers:
            # Simple batch implementation, could be optimized with DataLoader
            inputs = self._processor(text=texts, return_tensors="pt", padding=True, truncation=True, max_length=77).to(self.device)
            with torch.no_grad():
                outputs = self._model.get_text_features(**inputs)
            
            if torch.isnan(outputs).any():
                print(f"WARNING: NaN detected in batch text embeddings")
                outputs = torch.nan_to_num(outputs, nan=0.0)

            outputs = outputs / (outputs.norm(p=2, dim=-1, keepdim=True) + 1e-6)
            
            if torch.isnan(outputs).any():
                outputs = torch.nan_to_num(outputs, nan=0.0)
                
            return outputs.cpu().numpy().tolist()
        else:
            embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            return embeddings.tolist()
    
    def encode_image(self, image: Image.Image) -> List[float]:
        """Generate embedding for an image."""
        if image is None:
            raise ValueError("Image cannot be None")
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        if self._use_transformers:
            inputs = self._processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self._model.get_image_features(**inputs)
            
            if torch.isnan(outputs).any():
                print("WARNING: NaN detected in image embedding")
                outputs = torch.nan_to_num(outputs, nan=0.0)

            outputs = outputs / (outputs.norm(p=2, dim=-1, keepdim=True) + 1e-6)
            
            if torch.isnan(outputs).any():
                outputs = torch.nan_to_num(outputs, nan=0.0)
                
            return outputs.cpu().numpy()[0].tolist()
        else:
            embedding = self._model.encode(image, convert_to_numpy=True)
            return embedding.tolist()
    
    def encode_images(self, images: List[Image.Image]) -> List[List[float]]:
        """Generate embeddings for multiple images (batch processing)."""
        if not images:
            raise ValueError("Images list cannot be empty")
        
        # Convert all to RGB
        rgb_images = [img.convert('RGB') if img.mode != 'RGB' else img for img in images]
        
        if self._use_transformers:
            inputs = self._processor(images=rgb_images, return_tensors="pt", padding=True).to(self.device)
            with torch.no_grad():
                outputs = self._model.get_image_features(**inputs)
            
            if torch.isnan(outputs).any():
                print("WARNING: NaN detected in batch image embeddings")
                outputs = torch.nan_to_num(outputs, nan=0.0)

            outputs = outputs / (outputs.norm(p=2, dim=-1, keepdim=True) + 1e-6)
            
            if torch.isnan(outputs).any():
                outputs = torch.nan_to_num(outputs, nan=0.0)
                
            return outputs.cpu().numpy().tolist()
        else:
            embeddings = self._model.encode(rgb_images, convert_to_numpy=True, show_progress_bar=True)
            return embeddings.tolist()
    
    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        if self._use_transformers:
            return self._model.config.projection_dim
        
        # Handle both old and new sentence-transformers APIs
        if hasattr(self._model, 'get_sentence_embedding_dimension'):
            dim = self._model.get_sentence_embedding_dimension()
            if dim is not None:
                return dim
        
        # Fallback: generate a test embedding
        test_embedding = self._model.encode("test", convert_to_numpy=True)
        return test_embedding.shape[0]


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get cached embedding service instance."""
    return EmbeddingService()
