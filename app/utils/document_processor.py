import os
from typing import List, Dict, Any
import logging
from pathlib import Path
import PyPDF2
import docx
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.config import settings

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def read_pdf(self, file_path: str) -> str:
        """Read text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            logger.error(f"Failed to read PDF {file_path}: {e}")
            return ""
    
    def read_docx(self, file_path: str) -> str:
        """Read text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Failed to read DOCX {file_path}: {e}")
            return ""
    
    def read_txt(self, file_path: str) -> str:
        """Read text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            logger.error(f"Failed to read TXT {file_path}: {e}")
            return ""
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file types"""
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            return self.read_pdf(file_path)
        elif file_extension == '.docx':
            return self.read_docx(file_path)
        elif file_extension in ['.txt', '.md']:
            return self.read_txt(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_extension}")
            return ""
    
    def split_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata"""
        if not text.strip():
            return []
        
        chunks = self.text_splitter.split_text(text)
        
        result = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                "chunk_id": i,
                "chunk_size": len(chunk),
                "total_chunks": len(chunks)
            })
            
            result.append({
                "text": chunk,
                "metadata": chunk_metadata
            })
        
        return result
    
    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Process all supported files in a directory"""
        if not os.path.exists(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return []
        
        all_chunks = []
        supported_extensions = ['.pdf', '.docx', '.txt', '.md']
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_extension = Path(file).suffix.lower()
                
                if file_extension in supported_extensions:
                    logger.info(f"Processing file: {file}")
                    
                    # Extract text
                    text = self.extract_text_from_file(file_path)
                    
                    if text:
                        # Prepare metadata
                        metadata = {
                            "source": file,
                            "file_path": file_path,
                            "file_type": file_extension,
                            "file_size": os.path.getsize(file_path)
                        }
                        
                        # Split into chunks
                        chunks = self.split_text(text, metadata)
                        all_chunks.extend(chunks)
                        
                        logger.info(f"Created {len(chunks)} chunks from {file}")
                    else:
                        logger.warning(f"No text extracted from {file}")
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks
    
    def process_text_directly(self, text: str, source_name: str = "direct_input") -> List[Dict[str, Any]]:
        """Process text directly without file I/O"""
        metadata = {
            "source": source_name,
            "file_type": "text",
            "input_method": "direct"
        }
        
        return self.split_text(text, metadata)

# Global document processor instance
document_processor = DocumentProcessor()