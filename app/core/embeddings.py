from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingManager:
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            if not self.model:
                self._load_model()
            
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            if not self.model:
                self._load_model()
            
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        except Exception as e:
            logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0

# Global embedding manager instance
embedding_manager = EmbeddingManager()