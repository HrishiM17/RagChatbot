#!/usr/bin/env python3
"""
RAG Chatbot Server Runner

This script starts the FastAPI server for the RAG chatbot.
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
current_dir = Path(__file__).parent
app_dir = current_dir / "app"
sys.path.insert(0, str(current_dir))

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment...")
    
    # Check if .env file exists
    env_file = current_dir / ".env"
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Please create a .env file with your Groq API key:")
        print("GROQ_API_KEY=your_groq_api_key_here")
        return False
    
    # Check if Groq API key is set
    from dotenv import load_dotenv
    load_dotenv()
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key or groq_api_key == "your_groq_api_key_here":
        print("❌ Groq API key not configured!")
        print("Please set your Groq API key in the .env file:")
        print("GROQ_API_KEY=your_actual_api_key")
        print("Get your API key from: https://console.groq.com/")
        return False
    
    print("✅ Environment configuration OK")
    return True

def check_directories():
    """Create necessary directories"""
    print("📁 Checking directories...")
    
    directories = [
        "data/documents",
        "vector_db",
        "static"
    ]
    
    for directory in directories:
        dir_path = current_dir / directory
        if not dir_path.exists():
            print(f"📂 Creating {directory}/")
            dir_path.mkdir(parents=True, exist_ok=True)
    
    print("✅ Directory structure OK")

def check_documents():
    """Check if documents are available"""
    print("📄 Checking for documents...")
    
    documents_dir = current_dir / "data" / "documents"
    supported_extensions = ['.pdf', '.docx', '.txt', '.md']
    
    document_files = []
    if documents_dir.exists():
        for file_path in documents_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                document_files.append(file_path.name)
    
    if document_files:
        print(f"✅ Found {len(document_files)} documents")
        print("📋 Documents:", ", ".join(document_files[:3]) + ("..." if len(document_files) > 3 else ""))
    else:
        print("⚠️  No documents found in data/documents/")
        print("💡 You can:")
        print("   1. Add documents to data/documents/ and run 'python setup_documents.py'")
        print("   2. Upload documents through the web interface after starting the server")

def main():
    """Main function to start the server"""
    print("🚀 Starting RAG Chatbot Server")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check directories
    check_directories()
    
    # Check documents
    check_documents()
    
    print("=" * 50)
    print("🌟 Starting server...")
    print("📝 Access the chatbot at: http://localhost:8000")
    print("📊 API docs at: http://localhost:8000/docs")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Import here to ensure environment is loaded
        from app.core.config import settings
        
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()