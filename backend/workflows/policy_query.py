"""
Policy Query Workflow Implementation
RAG-powered system for answering employee questions about company policies
"""
import logging
from typing import Dict, Any, List, Optional
import re
from datetime import datetime

# PDF RAG imports
try:
    from langchain.vectorstores.cassandra import Cassandra
    from langchain.indexes.vectorstore import VectorStoreIndexWrapper
    from langchain.llms import OpenAI
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.text_splitter import CharacterTextSplitter
    import cassio
    from PyPDF2 import PdfReader
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain dependencies not available. Install with: pip install cassio langchain openai tiktoken PyPDF2")

# Fallback transformers (disabled for now)
pipeline = None
AutoTokenizer = None
AutoModelForSeq2SeqLM = None

# Disable old vector store for now
VectorStore = None

logger = logging.getLogger(__name__)


class PolicyQueryWorkflow:
    """Handles policy-related queries using RAG (Retrieval Augmented Generation)"""
    
    def __init__(self,
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 generation_model: str = "google/flan-t5-base",
                 vector_index_path: str = "data/vector_index",
                 astra_db_token: str = None,
                 astra_db_id: str = None,
                 astra_db_endpoint: str = None,
                 openai_api_key: str = None):
        """
        Initialize the Policy Query Workflow

        Args:
            embedding_model: Model for document embeddings
            generation_model: Model for text generation
            vector_index_path: Path to the FAISS vector index
            astra_db_token: Astra DB token for LangChain integration
            astra_db_id: Astra DB database ID
            openai_api_key: OpenAI API key for embeddings and LLM
        """
        self.embedding_model = embedding_model
        self.generation_model = generation_model
        self.vector_index_path = vector_index_path

        # Initialize PDF RAG system if available
        self.pdf_rag_available = False
        self.astra_vector_store = None
        self.astra_vector_index = None
        self.llm = None

        if LANGCHAIN_AVAILABLE and (astra_db_token or astra_db_endpoint) and astra_db_id and openai_api_key:
            try:
                # Initialize Astra DB connection
                if astra_db_token:
                    cassio.init(token=astra_db_token, database_id=astra_db_id)
                elif astra_db_endpoint:
                    # For endpoint-based connection, we'll need to extract token from endpoint or use a different method
                    # For now, let's try with the endpoint as a fallback
                    logger.warning("Using endpoint-based connection - may need token for full functionality")
                    cassio.init(database_id=astra_db_id)

                # Create LangChain components
                self.llm = OpenAI(openai_api_key=openai_api_key)
                embedding = OpenAIEmbeddings(openai_api_key=openai_api_key)

                # Create Astra vector store
                self.astra_vector_store = Cassandra(
                    embedding=embedding,
                    table_name="hr_policy_documents",
                    session=None,
                    keyspace=None,
                )

                self.astra_vector_index = VectorStoreIndexWrapper(vectorstore=self.astra_vector_store)
                self.pdf_rag_available = True
                logger.info("PDF RAG system initialized successfully with Astra DB")

            except Exception as e:
                logger.warning(f"Could not initialize PDF RAG system: {str(e)}")
                self.pdf_rag_available = False
        else:
            logger.info("PDF RAG system not available - using fallback mock responses")

        # Initialize old vector store as fallback (if available)
        if VectorStore:
            try:
                self.vector_store = VectorStore(
                    model_name=embedding_model,
                    index_path=vector_index_path
                )
            except Exception as e:
                logger.warning(f"Could not initialize fallback vector store: {str(e)}")
                self.vector_store = None
        else:
            logger.warning("VectorStore not available - RAG functionality will be limited")
            self.vector_store = None
        
        # Initialize generation pipeline
        self._init_generation_pipeline()

        # Query preprocessing patterns
        self.query_patterns = {
            'work_from_home': [
                r'work from home', r'remote work', r'wfh', r'working remotely',
                r'home office', r'telecommute', r'telework'
            ],
            'expenses': [
                r'expense', r'reimbursement', r'travel cost', r'meal allowance',
                r'receipt', r'per diem', r'business travel'
            ],
            'conduct': [
                r'code of conduct', r'behavior', r'ethics', r'harassment',
                r'discrimination', r'workplace conduct', r'professional behavior'
            ],
            'leave': [
                r'vacation', r'time off', r'sick leave', r'personal leave',
                r'pto', r'holiday', r'absence'
            ]
        }

    def upload_pdf_document(self, pdf_path: str, document_name: str = None) -> Dict[str, Any]:
        """
        Upload and process a PDF document into the vector store

        Args:
            pdf_path: Path to the PDF file
            document_name: Optional name for the document

        Returns:
            Dictionary with upload status and details
        """
        if not self.pdf_rag_available:
            return {
                'success': False,
                'message': 'PDF RAG system not available',
                'chunks_added': 0
            }

        try:
            # Read PDF content
            pdf_reader = PdfReader(pdf_path)
            raw_text = ''

            for i, page in enumerate(pdf_reader.pages):
                content = page.extract_text()
                if content:
                    raw_text += content

            if not raw_text.strip():
                return {
                    'success': False,
                    'message': 'No text content found in PDF',
                    'chunks_added': 0
                }

            # Split text into chunks
            text_splitter = CharacterTextSplitter(
                separator="\n",
                chunk_size=800,
                chunk_overlap=200,
                length_function=len,
            )

            texts = text_splitter.split_text(raw_text)

            # Add metadata to chunks
            metadatas = []
            for i, text in enumerate(texts):
                metadata = {
                    'source': document_name or pdf_path,
                    'chunk_id': i,
                    'document_type': 'policy_document'
                }
                metadatas.append(metadata)

            # Add texts to vector store
            self.astra_vector_store.add_texts(texts, metadatas=metadatas)

            logger.info(f"Successfully uploaded PDF: {pdf_path} with {len(texts)} chunks")

            return {
                'success': True,
                'message': f'Successfully processed PDF document',
                'chunks_added': len(texts),
                'document_name': document_name or pdf_path
            }

        except Exception as e:
            logger.error(f"Error uploading PDF document: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing PDF: {str(e)}',
                'chunks_added': 0
            }
    
    def _init_generation_pipeline(self):
        """Initialize the text generation pipeline"""
        if pipeline is None:
            logger.error("transformers library not available. Install with: pip install transformers")
            self.generator = None
            return
        
        try:
            logger.info(f"Loading generation model: {self.generation_model}")
            self.generator = pipeline(
                "text2text-generation",
                model=self.generation_model,
                tokenizer=self.generation_model,
                max_length=512,
                do_sample=True,
                temperature=0.7,
                top_p=0.9
            )
            logger.info("Generation pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing generation pipeline: {str(e)}")
            self.generator = None
    
    def process_policy_query(self, query: str, employee_id: str = None) -> Dict[str, Any]:
        """
        Process a policy-related query using RAG
        
        Args:
            query: User's question about company policies
            employee_id: Optional employee ID for personalized responses
            
        Returns:
            Dict containing the response and metadata
        """
        try:
            logger.info(f"Processing policy query: {query[:100]}...")
            
            # Step 1: Preprocess and enhance the query
            enhanced_query = self._enhance_query(query)
            
            # Step 2: Retrieve relevant documents
            retrieved_docs = self._retrieve_documents(enhanced_query)
            
            if not retrieved_docs:
                return {
                    "success": False,
                    "message": "I couldn't find relevant information about that topic in our policy documents. Please try rephrasing your question or contact HR directly.",
                    "query": query,
                    "sources": []
                }
            
            # Step 3: Generate response using retrieved context
            response = self._generate_response(query, retrieved_docs)
            
            # Step 4: Post-process and format response
            formatted_response = self._format_response(response, retrieved_docs)
            
            return {
                "success": True,
                "message": formatted_response["answer"],
                "query": query,
                "sources": formatted_response["sources"],
                "confidence": self._calculate_confidence(retrieved_docs)
            }
            
        except Exception as e:
            logger.error(f"Error processing policy query: {str(e)}")
            return {
                "success": False,
                "message": "I encountered an error while processing your question. Please try again or contact HR for assistance.",
                "query": query,
                "sources": []
            }

    def process_policy_query_with_pdf(self, query: str, employee_id: str = None) -> Dict[str, Any]:
        """
        Process query using PDF RAG system with Astra DB and LangChain

        Args:
            query: The user's policy question
            employee_id: Optional employee ID for personalized responses

        Returns:
            Dictionary containing the response and metadata
        """
        if not self.pdf_rag_available:
            logger.warning("PDF RAG system not available, falling back to standard processing")
            return self.process_policy_query(query, employee_id)

        try:
            logger.info(f"Processing PDF RAG query: {query[:50]}...")

            # Query the vector index
            answer = self.astra_vector_index.query(query, llm=self.llm).strip()

            # Get relevant documents with scores
            relevant_docs = self.astra_vector_store.similarity_search_with_score(query, k=4)

            # Format sources
            sources = []
            for doc, score in relevant_docs:
                source_info = {
                    'content': doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content,
                    'score': float(score),
                    'metadata': doc.metadata if hasattr(doc, 'metadata') else {}
                }
                sources.append(source_info)

            # Calculate confidence based on similarity scores
            confidence = self._calculate_pdf_confidence(relevant_docs)

            return {
                'success': True,
                'message': answer,
                'query': query,
                'sources': sources,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat(),
                'method': 'pdf_rag'
            }

        except Exception as e:
            logger.error(f"Error in PDF RAG processing: {str(e)}")
            # Fallback to standard processing
            return self.process_policy_query(query, employee_id)

    def _calculate_pdf_confidence(self, relevant_docs: list) -> float:
        """
        Calculate confidence score based on similarity scores from PDF RAG

        Args:
            relevant_docs: List of (document, score) tuples

        Returns:
            Confidence score between 0 and 1
        """
        if not relevant_docs:
            return 0.0

        # Get the best similarity score
        best_score = min([score for _, score in relevant_docs])  # Lower is better for similarity

        # Convert to confidence (inverse relationship)
        # Assuming similarity scores are typically between 0.0 and 2.0
        confidence = max(0.0, min(1.0, 1.0 - (best_score / 2.0)))

        return round(confidence, 3)

    def _enhance_query(self, query: str) -> str:
        """
        Enhance the query with synonyms and related terms
        
        Args:
            query: Original user query
            
        Returns:
            Enhanced query string
        """
        enhanced = query.lower()
        
        # Add related terms based on detected patterns
        for category, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, enhanced):
                    # Add category-specific terms to improve retrieval
                    if category == 'work_from_home':
                        enhanced += " remote work policy home office telecommute"
                    elif category == 'expenses':
                        enhanced += " expense reimbursement travel costs receipts"
                    elif category == 'conduct':
                        enhanced += " code of conduct ethics behavior workplace"
                    elif category == 'leave':
                        enhanced += " leave policy vacation time off PTO"
                    break
        
        return enhanced
    
    def _retrieve_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from the vector store

        Args:
            query: Search query
            k: Number of documents to retrieve

        Returns:
            List of relevant document chunks
        """
        try:
            # Check if vector store is available
            if not self.vector_store:
                logger.warning("Vector store not available - returning mock data")
                return self._get_mock_documents(query)

            stats = self.vector_store.get_stats()
            if not stats['index_exists'] or stats['total_vectors'] == 0:
                logger.warning("Vector store index not available - returning mock data")
                return self._get_mock_documents(query)

            # Perform similarity search
            results = self.vector_store.search(query, k=k, score_threshold=0.1)

            logger.info(f"Retrieved {len(results)} relevant documents")
            return results

        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)} - returning mock data")
            return self._get_mock_documents(query)
    
    def _generate_response(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Generate response using the language model and retrieved context
        
        Args:
            query: Original user query
            retrieved_docs: Retrieved document chunks
            
        Returns:
            Generated response text
        """
        if self.generator is None:
            # Fallback to simple template-based response
            return self._template_based_response(query, retrieved_docs)
        
        try:
            # Prepare context from retrieved documents
            context = self._prepare_context(retrieved_docs)
            
            # Create prompt for the generation model
            prompt = self._create_prompt(query, context)
            
            # Generate response
            response = self.generator(prompt, max_length=300, num_return_sequences=1)
            
            if response and len(response) > 0:
                return response[0]['generated_text'].strip()
            else:
                return self._template_based_response(query, retrieved_docs)
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._template_based_response(query, retrieved_docs)
    
    def _prepare_context(self, retrieved_docs: List[Dict[str, Any]], max_length: int = 1500) -> str:
        """
        Prepare context from retrieved documents
        
        Args:
            retrieved_docs: List of retrieved document chunks
            max_length: Maximum length of context
            
        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0
        
        for doc in retrieved_docs:
            content = doc['content']
            if current_length + len(content) > max_length:
                # Truncate to fit within limit
                remaining = max_length - current_length
                content = content[:remaining] + "..."
                context_parts.append(content)
                break
            
            context_parts.append(content)
            current_length += len(content)
        
        return "\n\n".join(context_parts)
    
    def _create_prompt(self, query: str, context: str) -> str:
        """
        Create prompt for the generation model
        
        Args:
            query: User's question
            context: Retrieved context
            
        Returns:
            Formatted prompt
        """
        prompt = f"""Based on the following company policy information, please answer the employee's question accurately and helpfully.

Context from company policies:
{context}

Employee question: {query}

Please provide a clear, accurate answer based on the policy information above. If the information is not sufficient to answer the question completely, mention that the employee should contact HR for more details.

Answer:"""
        
        return prompt
    
    def _template_based_response(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        Fallback template-based response when generation model is not available
        
        Args:
            query: User's question
            retrieved_docs: Retrieved documents
            
        Returns:
            Template-based response
        """
        if not retrieved_docs:
            return "I couldn't find specific information about that topic in our policy documents."
        
        # Extract key information from the most relevant document
        top_doc = retrieved_docs[0]
        content = top_doc['content']
        
        # Simple extraction of relevant sentences
        sentences = content.split('.')
        relevant_sentences = []
        
        query_words = set(query.lower().split())
        
        for sentence in sentences[:5]:  # Check first 5 sentences
            sentence_words = set(sentence.lower().split())
            if len(query_words.intersection(sentence_words)) > 0:
                relevant_sentences.append(sentence.strip())
        
        if relevant_sentences:
            response = ". ".join(relevant_sentences[:2])  # Use top 2 relevant sentences
            response += f". For more detailed information, please refer to the {top_doc.get('filename', 'policy document')} or contact HR."
        else:
            response = f"Based on our policy documents, here's what I found: {content[:200]}... For complete details, please refer to the {top_doc.get('filename', 'policy document')} or contact HR."
        
        return response
    
    def _format_response(self, response: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format the final response with sources
        
        Args:
            response: Generated response text
            retrieved_docs: Retrieved documents used for context
            
        Returns:
            Formatted response with sources
        """
        # Extract unique sources
        sources = []
        seen_sources = set()
        
        for doc in retrieved_docs[:3]:  # Include top 3 sources
            source_info = {
                'filename': doc.get('filename', 'Unknown'),
                'score': round(doc.get('score', 0), 3)
            }
            
            source_key = source_info['filename']
            if source_key not in seen_sources:
                sources.append(source_info)
                seen_sources.add(source_key)
        
        return {
            'answer': response,
            'sources': sources
        }
    
    def _calculate_confidence(self, retrieved_docs: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence score based on retrieval results
        
        Args:
            retrieved_docs: Retrieved documents
            
        Returns:
            Confidence score between 0 and 1
        """
        if not retrieved_docs:
            return 0.0
        
        # Base confidence on top result score and number of results
        top_score = retrieved_docs[0].get('score', 0)
        num_results = len(retrieved_docs)
        
        # Normalize and combine factors
        confidence = min(top_score * 0.8 + (num_results / 10) * 0.2, 1.0)
        
        return round(confidence, 3)

    def _get_mock_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Get mock documents when vector store is not available

        Args:
            query: Search query

        Returns:
            List of mock document chunks
        """
        # Simple keyword matching for mock responses
        query_lower = query.lower()

        mock_docs = []

        if any(keyword in query_lower for keyword in ['work from home', 'remote work', 'wfh']):
            mock_docs.append({
                'content': 'Work from home policy allows employees to work remotely with manager approval. Requirements include reliable internet connection, dedicated workspace, and maintaining regular communication with the team.',
                'filename': 'work_from_home_policy.md',
                'score': 0.85
            })

        if any(keyword in query_lower for keyword in ['expense', 'reimbursement', 'receipt']):
            mock_docs.append({
                'content': 'Expense reimbursement requires original receipts and manager approval. Submit expenses within 30 days through the HR portal. Business meals, travel, and office supplies are eligible for reimbursement.',
                'filename': 'expense_policy.md',
                'score': 0.80
            })

        if any(keyword in query_lower for keyword in ['conduct', 'behavior', 'ethics']):
            mock_docs.append({
                'content': 'Code of conduct emphasizes respect, integrity, and professionalism. All employees must treat colleagues with dignity, maintain confidentiality, and report any violations to HR.',
                'filename': 'code_of_conduct.md',
                'score': 0.75
            })

        if any(keyword in query_lower for keyword in ['leave', 'vacation', 'time off', 'pto']):
            mock_docs.append({
                'content': 'Leave policy provides 20 days annual leave, 10 days sick leave, and 5 days personal leave per year. Requests must be submitted at least 2 weeks in advance and approved by your manager.',
                'filename': 'leave_policy.md',
                'score': 0.78
            })

        # Default response if no specific keywords match
        if not mock_docs:
            mock_docs.append({
                'content': 'For specific policy questions, please contact HR directly or refer to the employee handbook. Our HR team is available to assist with any questions about company policies and procedures.',
                'filename': 'general_policy.md',
                'score': 0.60
            })

        return mock_docs
