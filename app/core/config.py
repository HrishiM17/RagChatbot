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
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    
    # Document Processing
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_CONTEXT_LENGTH: int = 3000
    
    # Response Configuration
    MAX_TOKENS: int = 500
    TEMPERATURE: float = 0.7

settings = Settings()