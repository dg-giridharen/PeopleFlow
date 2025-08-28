"""
Test script for RAG-powered policy query system
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.document_processor import DocumentProcessor
from backend.utils.vector_store import VectorStore
from backend.workflows.policy_query import PolicyQueryWorkflow


class TestRAGSystem(unittest.TestCase):
    """Test cases for the RAG system components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.knowledge_base_dir = "knowledge_base"
        self.test_index_path = "test_data/test_vector_index"
        
    def test_document_processor_initialization(self):
        """Test document processor initialization"""
        processor = DocumentProcessor(self.knowledge_base_dir)
        self.assertEqual(processor.knowledge_base_dir, self.knowledge_base_dir)
        self.assertIn('.pdf', processor.supported_extensions)
        self.assertIn('.docx', processor.supported_extensions)
        self.assertIn('.md', processor.supported_extensions)
    
    def test_text_chunking(self):
        """Test text chunking functionality"""
        processor = DocumentProcessor()
        
        # Test short text (no chunking needed)
        short_text = "This is a short text."
        chunks = processor.chunk_text(short_text, chunk_size=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], short_text)
        
        # Test long text (chunking needed)
        long_text = "This is a sentence. " * 100  # Create long text
        chunks = processor.chunk_text(long_text, chunk_size=200, overlap=50)
        self.assertGreater(len(chunks), 1)
        
        # Check overlap
        if len(chunks) > 1:
            # There should be some overlap between consecutive chunks
            self.assertTrue(len(chunks[0]) > 150)  # First chunk should be substantial
    
    def test_markdown_processing(self):
        """Test markdown text processing"""
        processor = DocumentProcessor()
        
        md_content = """
# Header
This is **bold** text and *italic* text.
- List item 1
- List item 2
[Link](http://example.com)
        """
        
        processed = processor._basic_markdown_to_text(md_content)
        
        # Should remove markdown formatting
        self.assertNotIn('#', processed)
        self.assertNotIn('**', processed)
        self.assertNotIn('*', processed)
        self.assertNotIn('[', processed)
        self.assertNotIn(']', processed)
        self.assertIn('Header', processed)
        self.assertIn('bold', processed)
        self.assertIn('italic', processed)
    
    @patch('backend.utils.vector_store.faiss')
    @patch('backend.utils.vector_store.SentenceTransformer')
    def test_vector_store_initialization(self, mock_sentence_transformer, mock_faiss):
        """Test vector store initialization"""
        # Mock the sentence transformer
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model
        
        vector_store = VectorStore(
            model_name="test-model",
            index_path=self.test_index_path
        )
        
        self.assertEqual(vector_store.model_name, "test-model")
        self.assertEqual(vector_store.index_path, self.test_index_path)
        self.assertEqual(vector_store.embedding_dim, 384)
    
    @patch('backend.utils.vector_store.faiss')
    @patch('backend.utils.vector_store.SentenceTransformer')
    def test_vector_store_stats(self, mock_sentence_transformer, mock_faiss):
        """Test vector store statistics"""
        # Mock the sentence transformer
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model
        
        vector_store = VectorStore(
            model_name="test-model",
            index_path=self.test_index_path
        )
        
        stats = vector_store.get_stats()
        
        self.assertIn('total_vectors', stats)
        self.assertIn('embedding_dimension', stats)
        self.assertIn('model_name', stats)
        self.assertIn('index_exists', stats)
        self.assertEqual(stats['embedding_dimension'], 384)
        self.assertEqual(stats['model_name'], "test-model")
    
    @patch('backend.workflows.policy_query.VectorStore')
    @patch('backend.workflows.policy_query.pipeline')
    def test_policy_query_workflow_initialization(self, mock_pipeline, mock_vector_store):
        """Test policy query workflow initialization"""
        # Mock the pipeline
        mock_pipeline.return_value = MagicMock()
        
        # Mock the vector store
        mock_vs_instance = MagicMock()
        mock_vector_store.return_value = mock_vs_instance
        
        workflow = PolicyQueryWorkflow(
            embedding_model="test-embedding-model",
            generation_model="test-generation-model",
            vector_index_path="test-index-path"
        )
        
        self.assertEqual(workflow.embedding_model, "test-embedding-model")
        self.assertEqual(workflow.generation_model, "test-generation-model")
        self.assertEqual(workflow.vector_index_path, "test-index-path")
    
    @patch('backend.workflows.policy_query.VectorStore')
    @patch('backend.workflows.policy_query.pipeline')
    def test_query_enhancement(self, mock_pipeline, mock_vector_store):
        """Test query enhancement functionality"""
        # Mock dependencies
        mock_pipeline.return_value = MagicMock()
        mock_vs_instance = MagicMock()
        mock_vector_store.return_value = mock_vs_instance
        
        workflow = PolicyQueryWorkflow()
        
        # Test work from home query enhancement
        enhanced = workflow._enhance_query("Can I work from home?")
        self.assertIn("remote work", enhanced.lower())
        self.assertIn("home office", enhanced.lower())
        
        # Test expense query enhancement
        enhanced = workflow._enhance_query("How do I submit expenses?")
        self.assertIn("expense reimbursement", enhanced.lower())
        self.assertIn("receipts", enhanced.lower())
    
    @patch('backend.workflows.policy_query.VectorStore')
    @patch('backend.workflows.policy_query.pipeline')
    def test_template_based_response(self, mock_pipeline, mock_vector_store):
        """Test template-based response fallback"""
        # Mock dependencies
        mock_pipeline.return_value = None  # Simulate no generation model
        mock_vs_instance = MagicMock()
        mock_vector_store.return_value = mock_vs_instance
        
        workflow = PolicyQueryWorkflow()
        
        # Test with retrieved documents
        retrieved_docs = [
            {
                'content': 'Work from home policy allows remote work with manager approval. Employees must have reliable internet connection.',
                'filename': 'work_from_home_policy.md',
                'score': 0.85
            }
        ]
        
        response = workflow._template_based_response("Can I work from home?", retrieved_docs)
        
        self.assertIn("work from home", response.lower())
        self.assertIn("policy", response.lower())
        self.assertTrue(len(response) > 50)  # Should be a substantial response
    
    @patch('backend.workflows.policy_query.VectorStore')
    @patch('backend.workflows.policy_query.pipeline')
    def test_confidence_calculation(self, mock_pipeline, mock_vector_store):
        """Test confidence score calculation"""
        # Mock dependencies
        mock_pipeline.return_value = MagicMock()
        mock_vs_instance = MagicMock()
        mock_vector_store.return_value = mock_vs_instance
        
        workflow = PolicyQueryWorkflow()
        
        # Test with high-score results
        high_score_docs = [
            {'score': 0.9},
            {'score': 0.8},
            {'score': 0.7}
        ]
        confidence = workflow._calculate_confidence(high_score_docs)
        self.assertGreater(confidence, 0.7)
        self.assertLessEqual(confidence, 1.0)
        
        # Test with low-score results
        low_score_docs = [
            {'score': 0.3},
            {'score': 0.2}
        ]
        confidence = workflow._calculate_confidence(low_score_docs)
        self.assertLess(confidence, 0.5)
        
        # Test with no results
        confidence = workflow._calculate_confidence([])
        self.assertEqual(confidence, 0.0)


class TestRAGIntegration(unittest.TestCase):
    """Integration tests for the complete RAG system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.test_documents = [
            {
                'content': 'Remote work policy allows employees to work from home with manager approval. Requirements include reliable internet and dedicated workspace.',
                'source': 'test_policy.md',
                'filename': 'remote_work_policy.md',
                'chunk_id': 'test_chunk_1'
            },
            {
                'content': 'Expense reimbursement requires original receipts and manager approval. Submit within 30 days of expense.',
                'source': 'test_expense.md',
                'filename': 'expense_policy.md',
                'chunk_id': 'test_chunk_2'
            }
        ]
    
    @patch('backend.workflows.policy_query.VectorStore')
    @patch('backend.workflows.policy_query.pipeline')
    def test_end_to_end_policy_query(self, mock_pipeline, mock_vector_store):
        """Test complete policy query workflow"""
        # Mock the generation pipeline
        mock_gen = MagicMock()
        mock_gen.return_value = [{'generated_text': 'Based on company policy, you can work from home with manager approval and proper setup.'}]
        mock_pipeline.return_value = mock_gen
        
        # Mock the vector store
        mock_vs_instance = MagicMock()
        mock_vs_instance.get_stats.return_value = {'index_exists': True, 'total_vectors': 10}
        mock_vs_instance.search.return_value = [
            {
                'content': 'Remote work policy allows employees to work from home with manager approval.',
                'filename': 'remote_work_policy.md',
                'score': 0.85
            }
        ]
        mock_vector_store.return_value = mock_vs_instance
        
        workflow = PolicyQueryWorkflow()
        
        result = workflow.process_policy_query("Can I work from home?", "EMP001")
        
        self.assertTrue(result['success'])
        self.assertIn('message', result)
        self.assertIn('sources', result)
        self.assertIn('confidence', result)
        self.assertGreater(len(result['message']), 20)


if __name__ == '__main__':
    # Create test data directory
    os.makedirs('test_data', exist_ok=True)
    
    # Run the tests
    unittest.main(verbosity=2)
