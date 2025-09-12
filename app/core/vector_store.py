import chromadb
from chromadb.config import Settings as ChromaSettings
import os
from typing import List, Dict, Any, Optional
import uuid
import logging
from app.core.config import settings
from app.core.embeddings import embedding_manager

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.client = None
        self.collection = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create vector_db directory if it doesn't exist
            os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
            
            # Initialize ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(
                path=settings.VECTOR_DB_PATH,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=settings.COLLECTION_NAME)
                logger.info(f"Loaded existing collection: {settings.COLLECTION_NAME}")
            except ValueError:
                # Collection doesn't exist, create it
                self.collection = self.client.create_collection(
                    name=settings.COLLECTION_NAME,
                    metadata={"description": "RAG chatbot document collection"}
                )
                logger.info(f"Created new collection: {settings.COLLECTION_NAME}")
                
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]] = None) -> int:
        """Add documents to the vector store"""
        try:
            if not texts:
                return 0
            
            # Generate embeddings
            embeddings = embedding_manager.embed_texts(texts)
            
            # Generate IDs
            ids = [str(uuid.uuid4()) for _ in texts]
            
            # Prepare metadatas
            if metadatas is None:
                metadatas = [{"source": f"document_{i}"} for i in range(len(texts))]
            
            # Add to collection
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(texts)} documents to vector store")
            return len(texts)
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = embedding_manager.embed_text(query)
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            return {
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else []
            }
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return {"documents": [], "metadatas": [], "distances": []}
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            count = self.collection.count()
            return {
                "name": settings.COLLECTION_NAME,
                "count": count,
                "status": "active"
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {
                "name": settings.COLLECTION_NAME,
                "count": 0,
                "status": "error"
            }
    
    def reset_collection(self):
        """Reset the collection (delete all documents)"""
        try:
            self.client.delete_collection(settings.COLLECTION_NAME)
            self.collection = self.client.create_collection(
                name=settings.COLLECTION_NAME,
                metadata={"description": "RAG chatbot document collection"}
            )
            logger.info("Collection reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise

# Global vector store instance
vector_store = VectorStore()