from groq import Groq
import logging
from typing import List, Dict, Any, Optional, Set
from app.core.config import settings
from app.core.vector_store import vector_store
import re

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
    
    def retrieve_context(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Enhanced retrieval with multi-strategy search and aggressive fallbacks"""
        try:
            # Strategy 1: Multi-level query expansion
            all_queries = self._generate_comprehensive_queries(query)
            
            # Strategy 2: Multi-round search with different parameters
            all_docs = []
            search_rounds = [
                {"queries": all_queries[:3], "n_results": max_results, "strict": True},
                {"queries": all_queries[3:6], "n_results": max_results * 2, "strict": False},
                {"queries": [query], "n_results": max_results * 3, "strict": False}  # Fallback with original query
            ]
            
            for round_config in search_rounds:
                round_docs = self._execute_search_round(round_config)
                all_docs.extend(round_docs)
                
                # Early termination if we have enough high-quality results
                if len(all_docs) >= 5 and any(doc['distance'] < 0.6 for doc in all_docs):
                    break
            
            # Strategy 3: Intelligent deduplication and ranking
            final_docs = self._deduplicate_and_rank(all_docs)
            
            # Strategy 4: Aggressive fallback if still no results
            if not final_docs:
                logger.warning(f"No results from multi-strategy search, using desperate fallback for: {query}")
                final_docs = self._desperate_fallback_search(query, max_results)
            
            # Combine context intelligently
            context, sources = self._build_context(final_docs)
            
            logger.info(f"Retrieved {len(final_docs)} documents using multi-strategy search for: '{query}'")
            
            return {
                "context": context,
                "sources": sources,
                "num_docs": len(final_docs),
                "best_distance": final_docs[0]["distance"] if final_docs else 1.0,
                "search_strategy": "multi-strategy-enhanced"
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return {"context": "", "sources": [], "num_docs": 0, "best_distance": 1.0}
    
    def _generate_comprehensive_queries(self, query: str) -> List[str]:
        """Generate comprehensive query variations using multiple strategies"""
        queries = [query.strip()]
        query_lower = query.lower().strip()
        
        # Strategy 1: Linguistic variations
        queries.extend(self._generate_linguistic_variations(query))
        
        # Strategy 2: Semantic expansions
        queries.extend(self._generate_semantic_expansions(query_lower))
        
        # Strategy 3: Contextual variations
        queries.extend(self._generate_contextual_variations(query_lower))
        
        # Strategy 4: Structural variations
        queries.extend(self._generate_structural_variations(query))
        
        # Remove duplicates while preserving order
        unique_queries = []
        seen = set()
        for q in queries:
            if q.strip() and q.lower() not in seen and len(q.strip()) > 1:
                unique_queries.append(q.strip())
                seen.add(q.lower())
        
        return unique_queries[:12]  # Limit to prevent overload
    
    def _generate_linguistic_variations(self, query: str) -> List[str]:
        """Generate linguistic variations (plurals, synonyms, etc.)"""
        variations = []
        words = query.split()
        
        # Plural/singular variations
        for i, word in enumerate(words):
            if len(word) > 3:
                if word.endswith('s') and not word.endswith('ss'):
                    singular_words = words.copy()
                    singular_words[i] = word[:-1]
                    variations.append(' '.join(singular_words))
                elif not word.endswith('s'):
                    plural_words = words.copy()
                    plural_words[i] = word + 's'
                    variations.append(' '.join(plural_words))
        
        # Common word substitutions
        substitutions = {
            'education': ['degree', 'qualification', 'academic', 'study'],
            'experience': ['work', 'job', 'employment', 'career'],
            'skill': ['ability', 'expertise', 'competency', 'knowledge'],
            'project': ['work', 'development', 'application', 'system'],
            'university': ['college', 'school', 'institution', 'academy'],
            'degree': ['qualification', 'education', 'diploma', 'certificate']
        }
        
        for original, replacements in substitutions.items():
            if original in query.lower():
                for replacement in replacements:
                    variations.append(query.lower().replace(original, replacement))
        
        return variations
    
    def _generate_semantic_expansions(self, query_lower: str) -> List[str]:
        """Generate semantic expansions based on context"""
        expansions = []
        words = query_lower.split()
        
        # Context-aware expansions
        semantic_clusters = {
            'academic': ['education', 'degree', 'university', 'college', 'study', 'qualification', 'academic', 'learning'],
            'work': ['experience', 'job', 'work', 'employment', 'career', 'position', 'role'],
            'technical': ['skill', 'technology', 'programming', 'development', 'technical', 'expertise'],
            'personal': ['name', 'contact', 'personal', 'information', 'details', 'profile'],
            'achievement': ['project', 'achievement', 'accomplishment', 'success', 'award', 'certification']
        }
        
        for cluster_name, cluster_words in semantic_clusters.items():
            if any(word in words for word in cluster_words):
                for expansion_word in cluster_words:
                    if expansion_word not in query_lower:
                        expansions.append(f"{query_lower} {expansion_word}")
                        expansions.append(f"{expansion_word} {query_lower}")
        
        return expansions
    
    def _generate_contextual_variations(self, query_lower: str) -> List[str]:
        """Generate contextual variations based on query structure"""
        variations = []
        
        # Question word variations
        if any(q in query_lower for q in ['what', 'where', 'when', 'who', 'how']):
            base_query = re.sub(r'\b(what|where|when|who|how)\b.*?(is|are|was|were|did)?\s*', '', query_lower).strip()
            if base_query:
                variations.extend([
                    base_query,
                    f"information about {base_query}",
                    f"details of {base_query}",
                    f"tell me about {base_query}"
                ])
        
        # Possessive variations
        if "'s" in query_lower or "of" in query_lower:
            # Convert "John's education" to "John education" and "education of John"
            possessive_cleaned = re.sub(r"'s\b", "", query_lower)
            variations.append(possessive_cleaned)
            
            words = possessive_cleaned.split()
            if len(words) >= 2:
                variations.append(f"{words[-1]} {' '.join(words[:-1])}")
        
        return variations
    
    def _generate_structural_variations(self, query: str) -> List[str]:
        """Generate structural variations (word order, etc.)"""
        variations = []
        words = query.split()
        
        if len(words) >= 2:
            # Reverse word order
            variations.append(' '.join(reversed(words)))
            
            # Extract key terms (nouns, important words)
            important_words = [w for w in words if len(w) > 3 and w.lower() not in ['the', 'and', 'or', 'but', 'with', 'from', 'about']]
            if important_words:
                variations.append(' '.join(important_words))
        
        return variations
    
    def _execute_search_round(self, config: Dict) -> List[Dict]:
        """Execute a search round with specific configuration"""
        round_docs = []
        seen_hashes = set()
        
        for query in config["queries"]:
            try:
                results = vector_store.search(query, n_results=config["n_results"])
                
                if not results["documents"]:
                    continue
                
                # Determine threshold based on strictness
                if config["strict"] and results["distances"]:
                    threshold = min(1.0, min(results["distances"]) * 2.0)  # Adaptive strict threshold
                else:
                    threshold = 2.0  # Very lenient threshold
                
                for doc, metadata, distance in zip(
                    results["documents"], results["metadatas"], results["distances"]
                ):
                    doc_hash = hash(doc[:100])  # Hash first 100 chars
                    
                    if doc_hash not in seen_hashes and distance <= threshold:
                        round_docs.append({
                            "content": doc,
                            "metadata": metadata,
                            "distance": distance,
                            "query": query
                        })
                        seen_hashes.add(doc_hash)
            
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue
        
        return round_docs
    
    def _desperate_fallback_search(self, query: str, max_results: int) -> List[Dict]:
        """Last resort: return best available documents regardless of similarity"""
        try:
            logger.info(f"Executing desperate fallback search for: {query}")
            results = vector_store.search(query, n_results=max_results * 4)  # Cast wide net
            
            fallback_docs = []
            for doc, metadata, distance in zip(
                results["documents"][:max_results], 
                results["metadatas"][:max_results], 
                results["distances"][:max_results]
            ):
                fallback_docs.append({
                    "content": doc,
                    "metadata": metadata,
                    "distance": distance,
                    "query": query
                })
            
            if fallback_docs:
                logger.info(f"Fallback search returned {len(fallback_docs)} documents")
            
            return fallback_docs
            
        except Exception as e:
            logger.error(f"Even desperate fallback failed: {e}")
            return []
    
    def _deduplicate_and_rank(self, docs: List[Dict]) -> List[Dict]:
        """Intelligent deduplication and ranking"""
        if not docs:
            return []
        
        # Step 1: Remove exact duplicates
        unique_docs = []
        seen_content = set()
        
        for doc in docs:
            content_key = doc["content"][:200]  # First 200 chars as key
            if content_key not in seen_content:
                unique_docs.append(doc)
                seen_content.add(content_key)
        
        # Step 2: Sort by distance (best first)
        unique_docs.sort(key=lambda x: x["distance"])
        
        # Step 3: Apply quality filtering with adaptive thresholds
        if unique_docs:
            best_distance = unique_docs[0]["distance"]
            
            # Dynamic quality threshold
            if best_distance < 0.5:
                quality_threshold = 1.0
            elif best_distance < 1.0:
                quality_threshold = 1.5
            else:
                quality_threshold = 2.0
            
            quality_docs = [doc for doc in unique_docs if doc["distance"] <= quality_threshold]
            
            # If quality filtering removes too much, be more lenient
            if len(quality_docs) < 2 and len(unique_docs) >= 2:
                quality_docs = unique_docs[:5]  # Keep top 5
            
            return quality_docs[:8]  # Maximum 8 documents
        
        return unique_docs[:8]
    
    def _build_context(self, docs: List[Dict]) -> tuple[str, List[str]]:
        """Build context from documents with intelligent merging"""
        if not docs:
            return "", []
        
        context_parts = []
        sources = []
        total_length = 0
        
        for doc in docs:
            content = doc["content"].strip()
            if not content:
                continue
            
            # Add content if within limit
            if total_length + len(content) <= settings.MAX_CONTEXT_LENGTH:
                context_parts.append(content)
                total_length += len(content)
                
                # Track sources
                source = doc["metadata"].get("source", "unknown")
                if source not in sources:
                    sources.append(source)
            else:
                # Add partial content if possible
                remaining_space = settings.MAX_CONTEXT_LENGTH - total_length
                if remaining_space > 100:  # Only if meaningful space left
                    partial_content = content[:remaining_space-3] + "..."
                    context_parts.append(partial_content)
                break
        
        return "\n\n".join(context_parts), sources
    
    def generate_response(self, query: str, context: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate response with context-aware prompting"""
        try:
            # Analyze context quality and adapt system prompt
            context_quality = "high" if context and len(context) > 200 else "low"
            has_context = bool(context and context.strip())
            
            if has_context and context_quality == "high":
                system_prompt = """You are an expert AI assistant that excels at finding and using relevant information from provided documents.

Key Instructions:
- The user has provided specific documents for you to reference
- Carefully analyze the provided context to find information relevant to the user's question
- Use the document information as your primary source for answering
- Be specific and cite details from the documents when available
- If the context contains partial information, use it and acknowledge what might be missing
- If multiple pieces of information are relevant, provide a comprehensive answer using all relevant details
- Always indicate when you're using information from the provided documents

Response Style:
- Be direct and informative
- Structure your answer clearly
- Use specific details and examples from the documents
- Acknowledge the source of your information"""

            elif has_context and context_quality == "low":
                system_prompt = """You are a helpful AI assistant working with limited document context.

Key Instructions:
- You have some document context, but it may be incomplete for this question
- Use any relevant information from the provided context
- Supplement carefully with your general knowledge when the context is insufficient
- Be honest about the limitations of the available information
- Clearly distinguish between information from documents vs. your general knowledge

Response Style:
- Be helpful and comprehensive
- Acknowledge when information is limited
- Provide the best answer possible with available information"""

            else:
                system_prompt = """You are a knowledgeable AI assistant.

Since no relevant document context was found for this specific question, I'll use my general knowledge to provide a helpful response.

Response Style:
- Be informative and accurate
- Provide comprehensive answers based on general knowledge
- Acknowledge when you're using general knowledge rather than specific documents
- Suggest ways the user might find more specific information if needed"""

            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-3:]:
                    if msg.get("user"):
                        messages.append({"role": "user", "content": msg["user"]})
                    if msg.get("assistant"):
                        messages.append({"role": "assistant", "content": msg["assistant"]})
            
            # Create user message with context
            if has_context:
                user_message = f"""Based on the following document information, please answer my question:

DOCUMENT CONTEXT:
{context}

QUESTION: {query}

Please provide a comprehensive answer using the document information above."""
            else:
                user_message = f"""I couldn't find specific document context for this question, but please help me with:

{query}

Please provide the best answer you can based on your knowledge."""
            
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            completion = self.groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                max_tokens=settings.MAX_TOKENS,
                temperature=settings.TEMPERATURE,
                top_p=0.9,
                stream=False
            )
            
            response = completion.choices[0].message.content
            logger.info(f"Generated response successfully (context_quality: {context_quality})")
            return response.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Please try rephrasing your question or try again later."
    
    def chat(self, query: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Main chat function with comprehensive error handling"""
        try:
            # Retrieve context using enhanced multi-strategy approach
            context_info = self.retrieve_context(query)
            
            # Generate response
            response = self.generate_response(
                query=query,
                context=context_info["context"],
                conversation_history=conversation_history
            )
            
            return {
                "response": response,
                "sources_used": context_info["sources"],
                "num_sources": context_info["num_docs"],
                "has_context": bool(context_info["context"]),
                "context_quality": "high" if context_info["best_distance"] < 0.6 else "medium" if context_info["best_distance"] < 1.0 else "low",
                "search_strategy": context_info.get("search_strategy", "standard")
            }
            
        except Exception as e:
            logger.error(f"Chat function failed: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your question. Please try rephrasing your question or try again later.",
                "sources_used": [],
                "num_sources": 0,
                "has_context": False,
                "context_quality": "none",
                "search_strategy": "failed"
            }
    
    def test_connection(self) -> Dict[str, str]:
        """Test Groq API connection"""
        try:
            completion = self.groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": "Respond with exactly: 'Connection test successful'"}],
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