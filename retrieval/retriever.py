"""Course-specific content retriever from vector store."""

import logging
from typing import List, Dict, Any
from retrieval.vector_store import PineconeVectorStore
from config.settings import TOP_K_RESULTS

logger = logging.getLogger(__name__)


class CourseRetriever:
    """Retrieves course-specific content from vector store."""
    
    def __init__(self):
        """Initialize the retriever with vector store."""
        self.vector_store = PineconeVectorStore()
    
    def retrieve(
        self,
        query: str,
        course_name: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a course-specific query.
        
        Args:
            query: The user's query
            course_name: Name of the course to filter by
            top_k: Number of results to return (defaults to config setting)
            
        Returns:
            List of relevant document chunks
        """
        if top_k is None:
            top_k = TOP_K_RESULTS
        
        try:
            results = self.vector_store.query(
                query_text=query,
                course_name=course_name,
                top_k=top_k
            )
            return results
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    def format_context(self, results: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks as context for LLM."""
        if not results:
            return ""
        
        context_parts = []
        
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Source {i}] Page {result['page_number']} from {result['document_name']}:\n"
                f"{result['content']}\n"
            )
        
        return "\n".join(context_parts)
    
    def get_citations(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract unique citations from results."""
        citations = []
        seen = set()
        
        for result in results:
            citation_key = (result['document_name'], result['page_number'])
            if citation_key not in seen:
                citations.append({
                    "document": result['document_name'],
                    "page": result['page_number']
                })
                seen.add(citation_key)
        
        return citations

