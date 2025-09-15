import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # App Configuration
    APP_NAME: str = os.getenv("APP_NAME", "RAG Chatbot")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Rate Limiting
    DAILY_MESSAGE_LIMIT: int = int(os.getenv("DAILY_MESSAGE_LIMIT", 200))
    
    # Vector Database
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./vector_db")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "documents")
    
    # Models
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    
    # Enhanced Document Processing
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 600))  # Smaller for better precision
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", 50))   # Smaller overlap for less redundancy
    MAX_CONTEXT_LENGTH: int = int(os.getenv("MAX_CONTEXT_LENGTH", 5000))  # Larger context window
    
    # Enhanced Response Configuration
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", 800))  # More tokens for detailed responses
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", 0.7))
    
    # Advanced Search Configuration
    DEFAULT_SEARCH_RESULTS: int = 10  # More initial results
    MAX_QUERY_VARIATIONS: int = 12    # Maximum query variations to try
    SIMILARITY_THRESHOLD_STRICT: float = 0.8   # Strict threshold for high-quality matches
    SIMILARITY_THRESHOLD_LENIENT: float = 2.0  # Lenient threshold for fallback
    MIN_CONTEXT_LENGTH: int = 50      # Minimum meaningful context length
    
    # Multi-Strategy Search Settings
    ENABLE_MULTI_STRATEGY_SEARCH: bool = True
    ENABLE_DESPERATE_FALLBACK: bool = True
    MAX_SEARCH_ROUNDS: int = 3
    
    # Quality Control
    MIN_DOCUMENT_LENGTH: int = 20     # Skip very short documents
    MAX_DOCUMENTS_PER_CONTEXT: int = 8  # Maximum documents to include in context

settings = Settings()