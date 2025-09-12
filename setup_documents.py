#!/usr/bin/env python3
"""
Document Setup Script for RAG Chatbot

This script processes documents from the data/documents folder and adds them to the vector store.
Run this script to initialize your chatbot with documents before starting the server.

Usage:
    python setup_documents.py
"""

import os
import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.document_processor import document_processor
from app.core.vector_store import vector_store
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_documents():
    """Process and setup documents in the vector store"""
    try:
        print("🚀 Starting document setup for RAG Chatbot")
        print(f"📁 Looking for documents in: {os.path.abspath('data/documents')}")
        
        # Check if documents directory exists
        documents_dir = "data/documents"
        if not os.path.exists(documents_dir):
            print(f"📂 Creating documents directory: {documents_dir}")
            os.makedirs(documents_dir, exist_ok=True)
            print(f"✨ Created {documents_dir}")
            print("📋 Please add your documents (PDF, DOCX, TXT, MD) to this folder and run the script again.")
            return
        
        # Check if there are any documents
        supported_extensions = ['.pdf', '.docx', '.txt', '.md']
        all_files = []
        for root, dirs, files in os.walk(documents_dir):
            for file in files:
                if Path(file).suffix.lower() in supported_extensions:
                    all_files.append(os.path.join(root, file))
        
        if not all_files:
            print("📭 No supported documents found in the documents directory.")
            print("📋 Supported formats: PDF, DOCX, TXT, MD")
            print(f"📁 Please add documents to: {os.path.abspath(documents_dir)}")
            return
        
        print(f"📄 Found {len(all_files)} documents to process")
        
        # Process documents
        print("🔄 Processing documents...")
        chunks = document_processor.process_directory(documents_dir)
        
        if not chunks:
            print("⚠️  No content extracted from documents")
            return
        
        print(f"✂️  Created {len(chunks)} text chunks")
        
        # Add to vector store
        print("💾 Adding documents to vector store...")
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        added_count = vector_store.add_documents(texts, metadatas)
        
        # Get collection info
        collection_info = vector_store.get_collection_info()
        
        print("✅ Document setup completed successfully!")
        print(f"📊 Statistics:")
        print(f"   - Documents processed: {len(all_files)}")
        print(f"   - Chunks created: {len(chunks)}")
        print(f"   - Chunks added to vector store: {added_count}")
        print(f"   - Total documents in collection: {collection_info['count']}")
        print(f"🚀 Your RAG chatbot is ready to use!")
        
    except Exception as e:
        logger.error(f"Error during document setup: {e}")
        print(f"❌ Error during setup: {e}")
        sys.exit(1)

def reset_vector_store():
    """Reset the vector store (delete all documents)"""
    try:
        print("🗑️  Resetting vector store...")
        vector_store.reset_collection()
        print("✅ Vector store reset successfully!")
    except Exception as e:
        logger.error(f"Error resetting vector store: {e}")
        print(f"❌ Error resetting vector store: {e}")

def show_status():
    """Show current status of the vector store"""
    try:
        collection_info = vector_store.get_collection_info()
        print("📊 Current Status:")
        print(f"   - Collection name: {collection_info['name']}")
        print(f"   - Total documents: {collection_info['count']}")
        print(f"   - Status: {collection_info['status']}")
        
        # Check documents directory
        documents_dir = "data/documents"
        if os.path.exists(documents_dir):
            supported_extensions = ['.pdf', '.docx', '.txt', '.md']
            all_files = []
            for root, dirs, files in os.walk(documents_dir):
                for file in files:
                    if Path(file).suffix.lower() in supported_extensions:
                        all_files.append(file)
            print(f"   - Available documents: {len(all_files)}")
            if all_files:
                print("     Files:", ", ".join(all_files[:5]) + ("..." if len(all_files) > 5 else ""))
        else:
            print("   - Documents directory: Not found")
            
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        print(f"❌ Error getting status: {e}")

def main():
    """Main function with command line interface"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "reset":
            confirm = input("⚠️  Are you sure you want to reset the vector store? This will delete all documents. (y/N): ")
            if confirm.lower() == 'y':
                reset_vector_store()
            else:
                print("Reset cancelled.")
        elif command == "status":
            show_status()
        elif command == "help":
            print("📖 RAG Chatbot Document Setup")
            print("")
            print("Usage:")
            print("  python setup_documents.py          - Process and add documents")
            print("  python setup_documents.py status   - Show current status")
            print("  python setup_documents.py reset    - Reset vector store")
            print("  python setup_documents.py help     - Show this help")
            print("")
            print("📁 Place your documents in: data/documents/")