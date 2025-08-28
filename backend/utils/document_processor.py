"""
Document Processor for RAG Knowledge Base
Handles loading and processing of various document formats (PDF, DOCX, MD)
"""
import os
import re
from typing import List, Dict, Any
import logging
from pathlib import Path

try:
    import pypdf
    from pypdf import PdfReader
except ImportError:
    pypdf = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import markdown
    from bs4 import BeautifulSoup
except ImportError:
    markdown = None
    BeautifulSoup = None

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Processes various document formats for knowledge base ingestion"""
    
    def __init__(self, knowledge_base_dir: str = "knowledge_base"):
        self.knowledge_base_dir = knowledge_base_dir
        self.supported_extensions = {'.pdf', '.docx', '.md', '.txt'}
    
    def load_documents(self) -> List[Dict[str, Any]]:
        """
        Load all supported documents from the knowledge base directory
        
        Returns:
            List of document dictionaries with content and metadata
        """
        documents = []
        
        if not os.path.exists(self.knowledge_base_dir):
            logger.warning(f"Knowledge base directory {self.knowledge_base_dir} does not exist")
            return documents
        
        for root, dirs, files in os.walk(self.knowledge_base_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = Path(file_path).suffix.lower()
                
                if file_ext in self.supported_extensions:
                    try:
                        content = self._extract_text(file_path, file_ext)
                        if content.strip():
                            documents.append({
                                'content': content,
                                'source': file_path,
                                'filename': file,
                                'extension': file_ext,
                                'size': os.path.getsize(file_path)
                            })
                            logger.info(f"Loaded document: {file}")
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {str(e)}")
        
        logger.info(f"Loaded {len(documents)} documents from knowledge base")
        return documents
    
    def _extract_text(self, file_path: str, file_ext: str) -> str:
        """Extract text content from a file based on its extension"""
        
        if file_ext == '.pdf':
            return self._extract_pdf_text(file_path)
        elif file_ext == '.docx':
            return self._extract_docx_text(file_path)
        elif file_ext == '.md':
            return self._extract_markdown_text(file_path)
        elif file_ext == '.txt':
            return self._extract_txt_text(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file"""
        if pypdf is None:
            raise ImportError("pypdf is required for PDF processing. Install with: pip install pypdf")
        
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error extracting PDF text from {file_path}: {str(e)}")
            raise
        
        return self._clean_text(text)
    
    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        if Document is None:
            raise ImportError("python-docx is required for DOCX processing. Install with: pip install python-docx")
        
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"Error extracting DOCX text from {file_path}: {str(e)}")
            raise
        
        return self._clean_text(text)
    
    def _extract_markdown_text(self, file_path: str) -> str:
        """Extract text from Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                md_content = file.read()
            
            if markdown is not None and BeautifulSoup is not None:
                # Convert markdown to HTML then extract text
                html = markdown.markdown(md_content)
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text()
            else:
                # Fallback: basic markdown processing
                text = self._basic_markdown_to_text(md_content)
            
        except Exception as e:
            logger.error(f"Error extracting Markdown text from {file_path}: {str(e)}")
            raise
        
        return self._clean_text(text)
    
    def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as file:
                text = file.read()
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            raise
        
        return self._clean_text(text)
    
    def _basic_markdown_to_text(self, md_content: str) -> str:
        """Basic markdown to text conversion without external libraries"""
        # Remove markdown formatting
        text = re.sub(r'#{1,6}\s+', '', md_content)  # Headers
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)  # Italic
        text = re.sub(r'`(.*?)`', r'\1', text)  # Inline code
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # Code blocks
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # Lists
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere with processing
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', ' ', text)
        # Remove extra spaces
        text = ' '.join(text.split())
        
        return text.strip()
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for better retrieval
        
        Args:
            text: Input text to chunk
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size - 100:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def process_documents_for_rag(self, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Process all documents and return chunks ready for RAG pipeline
        
        Args:
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of document chunks with metadata
        """
        documents = self.load_documents()
        processed_chunks = []
        
        for doc in documents:
            chunks = self.chunk_text(doc['content'], chunk_size, overlap)
            
            for i, chunk in enumerate(chunks):
                processed_chunks.append({
                    'content': chunk,
                    'source': doc['source'],
                    'filename': doc['filename'],
                    'chunk_id': f"{doc['filename']}_chunk_{i}",
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                })
        
        logger.info(f"Created {len(processed_chunks)} chunks from {len(documents)} documents")
        return processed_chunks
