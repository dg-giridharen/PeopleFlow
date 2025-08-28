#!/usr/bin/env python3
"""
Build Vector Store Script
Processes policy documents and creates FAISS index for RAG system
"""
import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.document_processor import DocumentProcessor
from backend.utils.vector_store import VectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to build the vector store"""
    try:
        logger.info("Starting vector store build process")
        
        # Initialize document processor
        doc_processor = DocumentProcessor(knowledge_base_dir="knowledge_base")
        
        # Process documents
        logger.info("Processing documents from knowledge base")
        document_chunks = doc_processor.process_documents_for_rag(
            chunk_size=1000,
            overlap=200
        )
        
        if not document_chunks:
            logger.error("No documents found in knowledge base directory")
            return False
        
        logger.info(f"Processed {len(document_chunks)} document chunks")
        
        # Initialize vector store
        vector_store = VectorStore(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            index_path="data/vector_index"
        )
        
        # Build the index
        logger.info("Building FAISS index")
        vector_store.build_index(document_chunks)
        
        # Verify the index
        stats = vector_store.get_stats()
        logger.info(f"Vector store statistics: {stats}")
        
        # Test search functionality
        logger.info("Testing search functionality")
        test_queries = [
            "What is the work from home policy?",
            "How do I submit expense reports?",
            "What are the company values?",
            "Remote work requirements"
        ]
        
        for query in test_queries:
            results = vector_store.search(query, k=3)
            logger.info(f"Query: '{query}' - Found {len(results)} results")
            if results:
                logger.info(f"Top result score: {results[0]['score']:.3f}")
        
        logger.info("Vector store build completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error building vector store: {str(e)}")
        return False


def rebuild_index():
    """Rebuild the entire index from scratch"""
    try:
        logger.info("Rebuilding vector store index")
        
        # Initialize components
        doc_processor = DocumentProcessor(knowledge_base_dir="knowledge_base")
        vector_store = VectorStore(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            index_path="data/vector_index"
        )
        
        # Clear existing index
        vector_store.clear_index()
        
        # Process documents
        document_chunks = doc_processor.process_documents_for_rag(
            chunk_size=1000,
            overlap=200
        )
        
        if not document_chunks:
            logger.error("No documents found to rebuild index")
            return False
        
        # Rebuild index
        vector_store.rebuild_index(document_chunks)
        
        logger.info("Index rebuild completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error rebuilding index: {str(e)}")
        return False


def add_new_documents(knowledge_base_dir: str = "knowledge_base"):
    """Add new documents to existing index"""
    try:
        logger.info(f"Adding new documents from {knowledge_base_dir}")
        
        # Initialize components
        doc_processor = DocumentProcessor(knowledge_base_dir=knowledge_base_dir)
        vector_store = VectorStore(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            index_path="data/vector_index"
        )
        
        # Process new documents
        document_chunks = doc_processor.process_documents_for_rag(
            chunk_size=1000,
            overlap=200
        )
        
        if not document_chunks:
            logger.warning("No new documents found")
            return True
        
        # Add to existing index
        vector_store.add_documents(document_chunks)
        
        logger.info(f"Added {len(document_chunks)} new document chunks")
        return True
        
    except Exception as e:
        logger.error(f"Error adding new documents: {str(e)}")
        return False


def check_index_status():
    """Check the status of the current index"""
    try:
        vector_store = VectorStore(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            index_path="data/vector_index"
        )
        
        stats = vector_store.get_stats()
        
        print("\n=== Vector Store Status ===")
        print(f"Index exists: {stats['index_exists']}")
        print(f"Total vectors: {stats['total_vectors']}")
        print(f"Total documents: {stats.get('total_documents', 0)}")
        print(f"Embedding dimension: {stats['embedding_dimension']}")
        print(f"Model name: {stats['model_name']}")
        
        if stats['index_exists']:
            # Test a sample query
            results = vector_store.search("company policy", k=3)
            print(f"\nSample search results: {len(results)} found")
            for i, result in enumerate(results[:2]):
                print(f"  {i+1}. Score: {result['score']:.3f}, Source: {result.get('filename', 'Unknown')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking index status: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build and manage vector store for RAG system")
    parser.add_argument("--action", choices=["build", "rebuild", "add", "status"], 
                       default="build", help="Action to perform")
    parser.add_argument("--knowledge-base", default="knowledge_base", 
                       help="Path to knowledge base directory")
    
    args = parser.parse_args()
    
    if args.action == "build":
        success = main()
    elif args.action == "rebuild":
        success = rebuild_index()
    elif args.action == "add":
        success = add_new_documents(args.knowledge_base)
    elif args.action == "status":
        success = check_index_status()
    else:
        logger.error(f"Unknown action: {args.action}")
        success = False
    
    sys.exit(0 if success else 1)
