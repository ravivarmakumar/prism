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
            logger.info(f"Querying vector store with course filter: '{course_name}', query: '{query}'")
            results = self.vector_store.query(
                query_text=query,
                course_name=course_name,
                top_k=top_k
            )
            logger.info(f"Vector store returned {len(results)} results")
            if results:
                logger.info(f"Top result: score={results[0].get('score', 'N/A'):.4f}, doc={results[0].get('document_name', 'N/A')}, page={results[0].get('page_number', 'N/A')}")
                logger.info(f"Top result content preview: {results[0].get('content', '')[:150]}...")
            else:
                logger.warning(f"No results found for query: '{query}' in course: '{course_name}'")
            return results
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}", exc_info=True)
            return []
    
    def format_context(self, results: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks as context for LLM."""
        if not results:
            return ""
        
        context_parts = []
        
        for i, result in enumerate(results, 1):
            # Build source identifier
            source_parts = []
            if result.get('module_name'):
                source_parts.append(f"Module: {result['module_name']}")
            source_parts.append(f"Document: {result['document_name']}")
            
            # Add page number or timestamp
            if result.get('page_number'):
                source_parts.append(f"Page {result['page_number']}")
            elif result.get('timestamp'):
                source_parts.append(f"Timestamp: {result['timestamp']}")
            
            source_info = ", ".join(source_parts)
            context_parts.append(
                f"[Source {i}] {source_info}:\n"
                f"{result['content']}\n"
            )
        
        return "\n".join(context_parts)
    
    def get_citations(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract unique citations from results."""
        citations = []
        seen = set()
        
        for result in results:
            # Create citation key based on document type
            if result.get('page_number'):
                citation_key = (result['document_name'], result.get('module_name'), result['page_number'])
            elif result.get('timestamp'):
                citation_key = (result['document_name'], result.get('module_name'), result['timestamp'])
            else:
                citation_key = (result['document_name'], result.get('module_name'), None)
            
            if citation_key not in seen:
                citation = {
                    "document": result['document_name']
                }
                
                # Add module if present
                if result.get('module_name'):
                    citation["module"] = result['module_name']
                
                # Add page or timestamp
                if result.get('page_number'):
                    citation["page"] = result['page_number']
                elif result.get('timestamp'):
                    citation["timestamp"] = result['timestamp']
                
                citations.append(citation)
                seen.add(citation_key)
        
        return citations

