"""
Vector Store Implementation using FAISS for RAG Knowledge Base
Handles document embeddings, similarity search, and vector storage
"""
import os
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging

try:
    import faiss
except ImportError:
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for document embeddings and similarity search"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", 
                 index_path: str = "data/vector_index"):
        """
        Initialize the vector store
        
        Args:
            model_name: Hugging Face model name for embeddings
            index_path: Path to save/load the FAISS index
        """
        if faiss is None:
            raise ImportError("faiss-cpu is required. Install with: pip install faiss-cpu")
        
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")
        
        self.model_name = model_name
        self.index_path = index_path
        self.metadata_path = f"{index_path}_metadata.pkl"
        
        # Initialize the embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        # Initialize FAISS index
        self.index = None
        self.metadata = []
        
        # Load existing index if available
        self.load_index()
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Create embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            NumPy array of embeddings
        """
        logger.info(f"Creating embeddings for {len(texts)} texts")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        return embeddings.astype('float32')
    
    def build_index(self, documents: List[Dict[str, Any]]) -> None:
        """
        Build FAISS index from document chunks
        
        Args:
            documents: List of document chunks with content and metadata
        """
        if not documents:
            logger.warning("No documents provided for index building")
            return
        
        logger.info(f"Building FAISS index from {len(documents)} document chunks")
        
        # Extract text content
        texts = [doc['content'] for doc in documents]
        
        # Create embeddings
        embeddings = self.create_embeddings(texts)
        
        # Create FAISS index
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add embeddings to index
        self.index.add(embeddings)
        
        # Store metadata
        self.metadata = documents.copy()
        
        logger.info(f"Built FAISS index with {self.index.ntotal} vectors")
        
        # Save the index
        self.save_index()
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add new documents to existing index
        
        Args:
            documents: List of document chunks to add
        """
        if not documents:
            return
        
        logger.info(f"Adding {len(documents)} documents to existing index")
        
        # Extract text content
        texts = [doc['content'] for doc in documents]
        
        # Create embeddings
        embeddings = self.create_embeddings(texts)
        
        # Normalize embeddings
        faiss.normalize_L2(embeddings)
        
        # Initialize index if it doesn't exist
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.metadata = []
        
        # Add to index
        self.index.add(embeddings)
        
        # Add metadata
        self.metadata.extend(documents)
        
        logger.info(f"Index now contains {self.index.ntotal} vectors")
        
        # Save the updated index
        self.save_index()
    
    def search(self, query: str, k: int = 5, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Search query text
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of search results with content and metadata
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("No index available for search")
            return []
        
        # Create query embedding
        query_embedding = self.create_embeddings([query])
        faiss.normalize_L2(query_embedding)
        
        # Search the index
        scores, indices = self.index.search(query_embedding, k)
        
        # Prepare results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx == -1:  # FAISS returns -1 for empty results
                continue
                
            if score < score_threshold:
                continue
            
            result = {
                'content': self.metadata[idx]['content'],
                'score': float(score),
                'rank': i + 1,
                **{k: v for k, v in self.metadata[idx].items() if k != 'content'}
            }
            results.append(result)
        
        logger.info(f"Found {len(results)} results for query: {query[:50]}...")
        return results
    
    def save_index(self) -> None:
        """Save FAISS index and metadata to disk"""
        if self.index is None:
            logger.warning("No index to save")
            return
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, self.index_path)
        
        # Save metadata
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        
        logger.info(f"Saved index with {self.index.ntotal} vectors to {self.index_path}")
    
    def load_index(self) -> bool:
        """
        Load FAISS index and metadata from disk
        
        Returns:
            True if index was loaded successfully, False otherwise
        """
        if not os.path.exists(self.index_path) or not os.path.exists(self.metadata_path):
            logger.info("No existing index found")
            return False
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(self.index_path)
            
            # Load metadata
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            
            logger.info(f"Loaded index with {self.index.ntotal} vectors from {self.index_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            self.index = None
            self.metadata = []
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        if self.index is None:
            return {
                'total_vectors': 0,
                'embedding_dimension': self.embedding_dim,
                'model_name': self.model_name,
                'index_exists': False
            }
        
        return {
            'total_vectors': self.index.ntotal,
            'embedding_dimension': self.embedding_dim,
            'model_name': self.model_name,
            'index_exists': True,
            'total_documents': len(self.metadata)
        }
    
    def clear_index(self) -> None:
        """Clear the current index and metadata"""
        self.index = None
        self.metadata = []
        
        # Remove saved files
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)
        
        logger.info("Cleared vector store index")
    
    def rebuild_index(self, documents: List[Dict[str, Any]]) -> None:
        """
        Rebuild the entire index from scratch
        
        Args:
            documents: List of document chunks to build index from
        """
        logger.info("Rebuilding vector store index")
        self.clear_index()
        self.build_index(documents)
