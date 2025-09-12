from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    user_id: str = Field(..., min_length=1, max_length=100, description="Unique user identifier")
    session_id: Optional[str] = Field(None, max_length=100, description="Optional session identifier")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Bot response")
    sources_used: Optional[List[str]] = Field(None, description="Document sources used")
    timestamp: datetime = Field(default_factory=datetime.now)
    usage_remaining: int = Field(..., description="Remaining messages for today")

class UsageResponse(BaseModel):
    user_id: str
    messages_used: int
    messages_remaining: int
    date: str
    limit_exceeded: bool

class DocumentUploadResponse(BaseModel):
    message: str
    documents_processed: int
    chunks_created: int

class HealthResponse(BaseModel):
    status: str
    vector_db_status: str
    groq_api_status: str
    documents_indexed: int