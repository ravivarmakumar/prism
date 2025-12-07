"""Response generator using GPT-4o with RAG."""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any
from openai import OpenAI
from config.settings import OPENAI_API_KEY, OPENAI_MODEL
from retrieval.retriever import CourseRetriever

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generates responses using GPT-4o with RAG."""
    
    def __init__(self):
        """Initialize the response generator."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.retriever = CourseRetriever()
        
        # Load prompts from YAML
        config_path = Path(__file__).parent.parent / "config" / "prompts.yaml"
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def _is_analysis_query(self, query: str) -> bool:
        """Check if query is asking for document analysis (tables, figures, etc.)."""
        analysis_keywords = [
            "how many tables", "how many figures", "how many images",
            "count tables", "count figures", "number of tables",
            "number of figures", "list tables", "list figures",
            "what tables", "what figures", "describe tables",
            "describe figures"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in analysis_keywords)
    
    def generate_response(
        self,
        query: str,
        course_name: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate response with RAG and citations.
        
        Args:
            query: User's question
            course_name: Name of the course
            user_context: User context (degree, major, etc.)
            
        Returns:
            Dictionary with response and citations
        """
        try:
            # Retrieve relevant context - get more results for analysis queries
            top_k = 10 if self._is_analysis_query(query) else 5
            retrieved_chunks = self.retriever.retrieve(query, course_name, top_k=top_k)
            
            if not retrieved_chunks:
                return {
                    "response": (
                        "I couldn't find relevant information in the course materials for your question. "
                        "Please try rephrasing your question or ensure the course materials have been ingested."
                    ),
                    "citations": []
                }
            
            # Format context
            context = self.retriever.format_context(retrieved_chunks)
            citations = self.retriever.get_citations(retrieved_chunks)
            
            # Determine which prompt template to use
            is_analysis = self._is_analysis_query(query)
            
            if is_analysis:
                system_prompt = self.config['system_prompts']['detailed_analysis'].format(
                    course_name=course_name
                )
                user_prompt = self.config['user_prompts']['analysis_query'].format(
                    context=context,
                    query=query,
                    degree=user_context.get('degree', 'N/A'),
                    major=user_context.get('major', 'N/A')
                )
            else:
                system_prompt = self.config['system_prompts']['default'].format(
                    course_name=course_name
                )
                user_prompt = self.config['user_prompts']['default'].format(
                    context=context,
                    query=query,
                    degree=user_context.get('degree', 'N/A'),
                    major=user_context.get('major', 'N/A')
                )
            
            # Get response settings from config
            response_settings = self.config.get('response_settings', {})
            temperature = response_settings.get('temperature', 0.7)
            max_tokens = response_settings.get('max_tokens', 2000)
            
            # Generate response
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            
            return {
                "response": answer,
                "citations": citations
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response": (
                    "I encountered an error while generating a response. "
                    "Please try again or contact support if the issue persists."
                ),
                "citations": []
            }
