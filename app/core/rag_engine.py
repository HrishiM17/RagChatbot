from groq import Groq
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.vector_store import vector_store

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self):
        self.groq_client = None
        self._initialize_groq()
    
    def _initialize_groq(self):
        """Initialize Groq client"""
        try:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not found in environment variables")
            
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info("Groq client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise
    
    def retrieve_context(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Retrieve relevant context from vector store"""
        try:
            # Search for relevant documents
            search_results = vector_store.search(query, n_results=max_results)
            
            # Filter results by relevance (distance threshold)
            relevant_docs = []
            relevant_sources = []
            
            for i, (doc, metadata, distance) in enumerate(zip(
                search_results["documents"],
                search_results["metadatas"],
                search_results["distances"]
            )):
                # Lower distance = more similar (cosine distance)
                if distance < 0.8:  # Adjust threshold as needed
                    relevant_docs.append(doc)
                    source = metadata.get("source", f"document_{i}")
                    if source not in relevant_sources:
                        relevant_sources.append(source)
            
            # Combine context with length limit
            combined_context = ""
            for doc in relevant_docs:
                if len(combined_context) + len(doc) > settings.MAX_CONTEXT_LENGTH:
                    break
                combined_context += doc + "\n\n"
            
            return {
                "context": combined_context.strip(),
                "sources": relevant_sources,
                "num_docs": len(relevant_docs)
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return {
                "context": "",
                "sources": [],
                "num_docs": 0
            }
    
    def generate_response(self, query: str, context: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate response using Groq"""
        try:
            # Build the prompt
            system_prompt = """You are a helpful AI assistant that can answer questions using both provided context and your general knowledge.

Guidelines:
- First, check if the provided context contains relevant information to answer the question
- If the context has relevant information, use it and mention the sources
- If the context doesn't contain enough information, you can use your general knowledge to provide a helpful answer
- Be clear about whether your answer comes from the provided documents or your general knowledge
- Maintain a friendly and professional tone
- If you're unsure about something, say so honestly"""

            # Prepare conversation history
            messages = [{"role": "system", "content": system_prompt}]
            
            if conversation_history:
                for msg in conversation_history[-3:]:  # Last 3 exchanges
                    messages.extend([
                        {"role": "user", "content": msg.get("user", "")},
                        {"role": "assistant", "content": msg.get("assistant", "")}
                    ])
            
            # Add current query with context
            user_message = f"""Context information:
{context}

Question: {query}

Please answer the question based on the context provided above."""
            
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            completion = self.groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                max_tokens=settings.MAX_TOKENS,
                temperature=settings.TEMPERATURE,
                top_p=1,
                stream=False
            )
            
            response = completion.choices[0].message.content
            logger.info("Response generated successfully")
            return response.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again later."
    
    def chat(self, query: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Main chat function combining retrieval and generation"""
        try:
            # Temporarily disable web search - uncomment when web_search.py is working
            web_context = ""
            # if web_search_service.should_search_web(query):
            #     logger.info(f"Query detected as needing web search: {query}")
            #     web_result = web_search_service.search_web(query)
            #     if web_result:
            #         web_context = f"\n\nReal-time web information:\n{web_result}"
            #         logger.info("Web search successful")
            #     else:
            #         logger.info("Web search returned no results")
            
            # Retrieve relevant context from documents
            context_info = self.retrieve_context(query)
            
            # Combine document context with web context
            combined_context = context_info["context"] + web_context
            
            # Generate response
            response = self.generate_response(
                query=query,
                context=combined_context,
                conversation_history=conversation_history
            )
            
            # Add web search indicator to sources
            sources = context_info["sources"].copy()
            if web_context:
                sources.append("Web Search")
            
            return {
                "response": response,
                "sources_used": sources,
                "num_sources": context_info["num_docs"] + (1 if web_context else 0),
                "has_context": bool(combined_context),
                "used_web_search": bool(web_context)
            }
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return {
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again later.",
                "sources_used": [],
                "num_sources": 0,
                "has_context": False,
                "used_web_search": False
            }
    
    def test_connection(self) -> Dict[str, str]:
        """Test Groq API connection"""
        try:
            # Simple test completion
            completion = self.groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": "Hello, please respond with 'Connection successful'"}],
                max_tokens=10,
                temperature=0
            )
            
            response = completion.choices[0].message.content
            if "successful" in response.lower():
                return {"status": "connected", "message": "Groq API connection successful"}
            else:
                return {"status": "warning", "message": f"Unexpected response: {response}"}
                
        except Exception as e:
            logger.error(f"Groq connection test failed: {e}")
            return {"status": "error", "message": str(e)}

# Global RAG engine instance
rag_engine = RAGEngine()