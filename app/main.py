from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
import os
from typing import List, Optional

# Import models and services
from app.models.schemas import (
    ChatRequest, ChatResponse, UsageResponse, 
    DocumentUploadResponse, HealthResponse
)
from app.services.chat_service import chat_service
from app.services.usage_tracker import usage_tracker
from app.core.vector_store import vector_store
from app.core.rag_engine import rag_engine
from app.utils.document_processor import document_processor
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="A free RAG chatbot built with FastAPI and Groq",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting RAG Chatbot...")
    
    # Test Groq connection
    groq_status = rag_engine.test_connection()
    logger.info(f"Groq API status: {groq_status}")
    
    # Check vector store
    collection_info = vector_store.get_collection_info()
    logger.info(f"Vector store: {collection_info}")
    
    logger.info("RAG Chatbot started successfully!")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main chat interface"""
    try:
        with open("static/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>RAG Chatbot</h1><p>Frontend not found. Please ensure static/index.html exists.</p>",
            status_code=200
        )

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint"""
    try:
        # Process the message
        result = await chat_service.process_message(
            user_id=request.user_id,
            message=request.message,
            session_id=request.session_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=429 if "limit exceeded" in result.get("error", "").lower() else 500,
                detail=result.get("error", "Unknown error")
            )
        
        return ChatResponse(
            response=result["response"],
            sources_used=result["sources_used"],
            usage_remaining=result["usage_info"]["remaining"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/usage/{user_id}", response_model=UsageResponse)
async def get_usage(user_id: str):
    """Get usage information for a user"""
    try:
        usage_info = usage_tracker.get_user_usage(user_id)
        
        return UsageResponse(
            user_id=user_id,
            messages_used=usage_info["used"],
            messages_remaining=usage_info["remaining"],
            date=datetime.now().strftime("%Y-%m-%d"),
            limit_exceeded=usage_info["limit_exceeded"]
        )
        
    except Exception as e:
        logger.error(f"Usage endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage information")

@app.post("/api/upload-documents", response_model=DocumentUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    user_id: str = Form(...)
):
    """Upload and process documents"""
    try:
        # Check if user has permission (simple check)
        usage_info = usage_tracker.get_user_usage(user_id)
        if usage_info["limit_exceeded"]:
            raise HTTPException(status_code=429, detail="Daily limit exceeded")
        
        processed_docs = 0
        total_chunks = 0
        
        # Create temp directory for uploads
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            for file in files:
                # Save uploaded file temporarily
                file_path = os.path.join(temp_dir, file.filename)
                
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                # Process the document
                text = document_processor.extract_text_from_file(file_path)
                
                if text:
                    chunks = document_processor.process_text_directly(
                        text, 
                        source_name=file.filename
                    )
                    
                    # Add to vector store
                    texts = [chunk["text"] for chunk in chunks]
                    metadatas = [chunk["metadata"] for chunk in chunks]
                    
                    vector_store.add_documents(texts, metadatas)
                    
                    processed_docs += 1
                    total_chunks += len(chunks)
                
                # Clean up temp file
                os.remove(file_path)
        
        finally:
            # Clean up temp directory
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        
        return DocumentUploadResponse(
            message=f"Successfully processed {processed_docs} documents",
            documents_processed=processed_docs,
            chunks_created=total_chunks
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process documents")

@app.post("/api/add-text")
async def add_text_directly(
    text: str = Form(...),
    source_name: str = Form("direct_input"),
    user_id: str = Form(...)
):
    """Add text directly without file upload"""
    try:
        # Check user permissions
        usage_info = usage_tracker.get_user_usage(user_id)
        if usage_info["limit_exceeded"]:
            raise HTTPException(status_code=429, detail="Daily limit exceeded")
        
        # Process the text
        chunks = document_processor.process_text_directly(text, source_name)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No content to process")
        
        # Add to vector store
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        vector_store.add_documents(texts, metadatas)
        
        return {
            "message": f"Successfully processed text into {len(chunks)} chunks",
            "chunks_created": len(chunks),
            "source_name": source_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add text error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process text")

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check Groq API
        groq_status = rag_engine.test_connection()
        
        # Check vector store
        collection_info = vector_store.get_collection_info()
        
        return HealthResponse(
            status="healthy",
            vector_db_status=collection_info["status"],
            groq_api_status=groq_status["status"],
            documents_indexed=collection_info["count"]
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            status="unhealthy",
            vector_db_status="error",
            groq_api_status="error",
            documents_indexed=0
        )

@app.get("/api/stats")
async def get_stats(admin_key: Optional[str] = None):
    """Get system statistics (simple admin endpoint)"""
    try:
        # Simple admin check (you can make this more sophisticated)
        if admin_key != "admin123":
            raise HTTPException(status_code=403, detail="Access denied")
        
        usage_stats = usage_tracker.get_all_stats()
        chat_stats = chat_service.get_stats()
        vector_stats = vector_store.get_collection_info()
        
        return {
            "usage": usage_stats,
            "chat": chat_stats,
            "vector_store": vector_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@app.delete("/api/sessions/{user_id}")
async def clear_user_sessions(user_id: str, session_id: Optional[str] = None):
    """Clear user's chat sessions"""
    try:
        success = chat_service.clear_session(user_id, session_id)
        
        if success:
            return {"message": "Session cleared successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear session")

@app.get("/api/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """Get user's chat sessions"""
    try:
        sessions = chat_service.get_user_sessions(user_id)
        return {"sessions": sessions}
        
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sessions")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )