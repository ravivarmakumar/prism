"""Course RAG Agent - Retrieves and checks course content."""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any
import yaml
from openai import OpenAI
from retrieval.retriever import CourseRetriever
from core.a2a import a2a_manager
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)

# Max context length to send to answerability check (avoid token limits)
ANSWERABILITY_CONTEXT_MAX_CHARS = 8000


class CourseRAGAgent:
    """Agent that retrieves course content and checks if it answers the question."""
    
    def __init__(self):
        """Initialize the course RAG agent."""
        self.retriever = CourseRetriever()
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        config_path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def _check_answerability(self, query: str, context: str) -> bool:
        """
        Check if the retrieved course context actually answers the user's question.
        Used to trigger web search when the question is relevant but not covered in materials.
        
        Returns True if context answers the question, False otherwise.
        """
        if not context or not context.strip():
            return False
        try:
            prompt_config = self.config.get("course_rag_answerability", {})
            system_prompt = prompt_config.get(
                "system",
                "Determine if the context answers the question. Respond with JSON: {\"answers_question\": true/false, \"reason\": \"brief explanation\"}"
            )
            user_template = prompt_config.get("user_template", "Question: {query}\n\nContext:\n{context}\n\nJSON only.")
            # Truncate context to avoid token limits
            context_for_check = context[:ANSWERABILITY_CONTEXT_MAX_CHARS]
            if len(context) > ANSWERABILITY_CONTEXT_MAX_CHARS:
                context_for_check += "\n\n[Context truncated...]"
            user_prompt = user_template.format(query=query, context=context_for_check)
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            answers = result.get("answers_question", False)
            reason = result.get("reason", "")
            logger.info(f"Answerability check: answers_question={answers}, reason={reason[:100] if reason else ''}")
            return answers
        except Exception as e:
            logger.warning(f"Answerability check failed: {e}. Defaulting to found=True (use course content).")
            return True  # On error, use course content rather than failing over to web search
    
    def retrieve_and_check(
        self,
        query: str,
        course_name: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve course content and check if it answers the question.
        
        Args:
            query: User's question
            course_name: Name of the course
            top_k: Number of chunks to retrieve
            
        Returns:
            Dictionary with content, citations, and found flag
        """
        try:
            logger.info(f"Retrieving content for query: '{query}' in course: '{course_name}'")
            
            # Retrieve relevant chunks - try with original query first
            retrieved_chunks = self.retriever.retrieve(
                query=query,
                course_name=course_name,
                top_k=top_k
            )
            
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks from vector store for query: '{query}'")
            
            # Check if query is about a specific module and enhance it
            query_lower = query.lower()
            module_match = re.search(r'module\s+(\d+|[a-z]+)', query_lower, re.IGNORECASE)
            if module_match:
                module_ref = module_match.group(1)
                logger.info(f"Query mentions module {module_ref}. Enhancing query with module context...")
                # Add module-related terms to improve retrieval
                enhanced_query = f"{query} module {module_ref} content topics"
                logger.info(f"Enhanced query: '{enhanced_query}'")
                # Try enhanced query first
                enhanced_chunks = self.retriever.retrieve(
                    query=enhanced_query,
                    course_name=course_name,
                    top_k=top_k
                )
                if enhanced_chunks:
                    retrieved_chunks = enhanced_chunks
                    logger.info(f"Found {len(retrieved_chunks)} chunks with module-enhanced query")
            
            # For queries about lists, counts, or "all" items, try additional queries to get comprehensive results
            needs_comprehensive = any(keyword in query_lower for keyword in [
                "all", "different", "various", "list", "what are", "how many", "name", "types", "kinds"
            ])
            
            if needs_comprehensive and retrieved_chunks:
                logger.info("Query requires comprehensive results. Retrieving additional chunks...")
                # Extract the main topic/keyword from the query (generic approach)
                # Remove common question words and get the core topic
                question_words = ["what", "are", "the", "different", "various", "all", "how", "many", "list", "name"]
                words = [w for w in query_lower.split() if w not in question_words and len(w) > 2]
                
                if words:
                    # Use the main topic word(s) for broader retrieval
                    main_topic = words[0]  # Primary keyword
                    additional_queries = [
                        main_topic,  # Singular/plural variations
                        main_topic + "s" if not main_topic.endswith("s") else main_topic[:-1],  # Pluralize or singularize
                    ]
                    
                    # If there's a second significant word, combine it
                    if len(words) > 1:
                        combined = f"{words[0]} {words[1]}"
                        additional_queries.append(combined)
                    
                    # Retrieve additional chunks with broader queries
                    all_chunks = list(retrieved_chunks)  # Start with existing chunks
                    seen_ids = {chunk.get('content', '')[:50] for chunk in all_chunks}  # Track seen chunks
                    
                    for alt_query in additional_queries:
                        if alt_query == query_lower:  # Skip if same as original
                            continue
                        alt_chunks = self.retriever.retrieve(
                            query=alt_query,
                            course_name=course_name,
                            top_k=top_k
                        )
                        # Add unique chunks
                        for chunk in alt_chunks:
                            chunk_id = chunk.get('content', '')[:50]
                            if chunk_id not in seen_ids:
                                all_chunks.append(chunk)
                                seen_ids.add(chunk_id)
                    
                    if len(all_chunks) > len(retrieved_chunks):
                        logger.info(f"Expanded from {len(retrieved_chunks)} to {len(all_chunks)} chunks for comprehensive query")
                        retrieved_chunks = all_chunks[:top_k * 2]  # Allow up to 2x top_k for comprehensive queries
            
            # If no results, try with a simplified/expanded query
            if not retrieved_chunks:
                logger.info(f"No chunks found with original query. Trying alternative query formulations...")
                # Try alternative query formulations
                alternative_queries = [
                    query.lower(),  # Lowercase
                    query + " " + course_name,  # Add course name
                ]
                
                for alt_query in alternative_queries:
                    logger.info(f"Trying alternative query: '{alt_query}'")
                    alt_chunks = self.retriever.retrieve(
                        query=alt_query,
                        course_name=course_name,
                        top_k=top_k
                    )
                    if alt_chunks:
                        retrieved_chunks = alt_chunks
                        logger.info(f"Found {len(retrieved_chunks)} chunks with alternative query")
                        break
            
            if not retrieved_chunks:
                logger.warning(f"No chunks retrieved for query: '{query}' in course: '{course_name}' after trying alternatives")
                # Even if no chunks found, check if query asks for current/updated information
                # Such queries should go to web search even if course mentions the topic
                query_lower = query.lower()
                needs_current_info = any(keyword in query_lower for keyword in [
                    "latest", "current", "recent", "new", "updated", "now", "today", "2024", "2025"
                ])
                if needs_current_info:
                    logger.info(f"Query asks for current/updated information. Marking as not found to trigger web search.")
                return {
                    "found": False,
                    "context": None,
                    "citations": []
                }
            
            # Log scores for debugging
            scores = [chunk.get("score", 0) for chunk in retrieved_chunks]
            logger.info(f"Retrieval scores: {scores}")
            
            # Format context
            context = self.retriever.format_context(retrieved_chunks)
            citations = self.retriever.get_citations(retrieved_chunks)
            
            logger.info(f"Formatted context length: {len(context)} characters")
            logger.info(f"Found {len(citations)} citations")
            
            # Check if content is relevant - if we got results, they're relevant
            # However, if query asks for current/updated info, we should still check web search
            query_lower = query.lower()
            needs_current_info = any(keyword in query_lower for keyword in [
                "latest", "current", "recent", "new", "updated", "now", "today", "2024", "2025"
            ])
            
            # If query asks for current info and we have chunks, prefer web search (course may be outdated)
            if needs_current_info and retrieved_chunks:
                logger.info(f"Query asks for current/updated information. Even though chunks found, will check web search for latest info.")
                found = False
            elif retrieved_chunks:
                # Check if the retrieved context actually answers the question (not just topically related).
                # If not, trigger web search so we get an answer (relevant to course but not in materials).
                found = self._check_answerability(query, context)
                if not found:
                    logger.info(f"Retrieved context does not fully answer the question - routing to web search.")
            else:
                found = False
            
            if found:
                logger.info(f"Content found! Using {len(retrieved_chunks)} chunks with context length {len(context)} chars")
            else:
                if needs_current_info:
                    logger.info(f"Query asks for current info - routing to web search for latest information")
                else:
                    logger.warning(f"Course content does not answer query - routing to web search: '{query}'")
            
            return {
                "found": found,
                "context": context,
                "citations": citations,
                "retrieved_chunks": retrieved_chunks
            }
            
        except Exception as e:
            logger.error(f"Error in course RAG: {e}")
            return {
                "found": False,
                "context": None,
                "citations": []
            }


def course_rag_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for course RAG.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state
    """
    agent = CourseRAGAgent()
    
    query = state.get("refined_query", state["query"])
    
    # Retrieve and check course content - use more chunks for better context
    result = agent.retrieve_and_check(
        query=query,
        course_name=state["course_name"],
        top_k=10  # Increased from 5 to get more context
    )
    
    state["course_content_found"] = result["found"]
    state["course_context"] = result["context"]
    state["course_citations"] = result["citations"]
    state["retrieved_chunks"] = result.get("retrieved_chunks", [])
    state["current_node"] = "course_rag"
    
    if state["course_content_found"]:
        # Content found in course, proceed to personalization
        state["should_continue"] = True
        state["next_node"] = "personalization"
        logger.info(f"Course content found ({len(result.get('retrieved_chunks', []))} chunks). Proceeding to personalization.")
        logger.info(f"Context preview: {state.get('course_context', '')[:200]}...")
        
        # Send A2A message to personalization agent
        logger.info("Sending A2A message: course_rag → personalization (content_retrieved)")
        state = a2a_manager.send_message(
            sender="course_rag",
            receiver="personalization",
            message_type="content_retrieved",
            content={
                "chunks_count": len(result.get('retrieved_chunks', [])),
                "found": True,
                "context_preview": state.get('course_context', '')[:200]
            },
            state=state
        )
        logger.info(f"A2A message sent. Total A2A messages in state: {len(state.get('a2a_messages', []))}")
    else:
        # Content not found, need web search
        state["should_continue"] = True
        state["next_node"] = "web_search"
        logger.warning(f"Course content NOT found for query: '{query}' in course: '{state['course_name']}'. Proceeding to web search.")
        
        # Send A2A message to web search agent
        logger.info("Sending A2A message: course_rag → web_search (content_not_found)")
        state = a2a_manager.send_message(
            sender="course_rag",
            receiver="web_search",
            message_type="content_not_found",
            content={"query": query, "course_name": state["course_name"]},
            state=state
        )
        logger.info(f"A2A message sent. Total A2A messages in state: {len(state.get('a2a_messages', []))}")
    
    return state

