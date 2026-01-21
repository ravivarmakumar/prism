"""Refinement Agent - Improves responses based on evaluation feedback."""

import logging
from typing import Dict, Any
from openai import OpenAI
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)


class RefinementAgent:
    """Agent that refines responses based on evaluation feedback."""
    
    def __init__(self):
        """Initialize the refinement agent."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def refine_response(
        self,
        query: str,
        answer: str,
        evaluation_scores: Dict[str, float],
        user_context: Dict[str, Any],
        course_name: str,
        is_from_web: bool = False
    ) -> str:
        """
        Refine response based on evaluation scores.
        
        Args:
            query: Original query
            answer: Current answer
            evaluation_scores: Evaluation scores dict
            user_context: User context
            course_name: Course name
            is_from_web: Whether answer is from web sources
            
        Returns:
            Refined answer
        """
        try:
            degree = user_context.get("degree", "N/A")
            major = user_context.get("major", "N/A")
            
            # Identify weak areas
            weak_areas = []
            if evaluation_scores.get("relevance", 1.0) < 0.7:
                weak_areas.append("relevance to the question")
            if evaluation_scores.get("readability", 1.0) < 0.7:
                weak_areas.append(f"readability for {degree} level")
            if evaluation_scores.get("coherence", 1.0) < 0.7:
                weak_areas.append("coherence and logical flow")
            if evaluation_scores.get("coverage", 1.0) < 0.7:
                weak_areas.append("completeness of coverage")
            
            if is_from_web:
                if evaluation_scores.get("credibility", 1.0) < 0.7:
                    weak_areas.append("source credibility")
                if evaluation_scores.get("consensus", 1.0) < 0.7:
                    weak_areas.append("consensus across sources")
            
            weak_areas_str = ", ".join(weak_areas) if weak_areas else "general quality"
            
            system_prompt = f"""You are an expert teaching assistant for {course_name}.
Your task is to refine and improve an answer based on evaluation feedback.

Student Background:
- Degree Level: {degree}
- Major: {major}

Focus on improving: {weak_areas_str}

Maintain factual accuracy while improving clarity, completeness, and coherence."""

            user_prompt = f"""Original Question: {query}

Current Answer:
{answer}

Evaluation Scores:
- Relevance: {evaluation_scores.get('relevance', 0):.2f}
- Readability: {evaluation_scores.get('readability', 0):.2f}
- Coherence: {evaluation_scores.get('coherence', 0):.2f}
- Coverage: {evaluation_scores.get('coverage', 0):.2f}
{f"- Credibility: {evaluation_scores.get('credibility', 0):.2f}" if is_from_web else ""}
{f"- Consensus: {evaluation_scores.get('consensus', 0):.2f}" if is_from_web else ""}

Please revise the answer to improve the weak areas while:
1. Maintaining all factual information
2. Keeping citations intact
3. Improving clarity and coherence
4. Ensuring completeness
5. Matching {degree} level complexity

Provide the refined answer:"""

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for refinement
                max_tokens=2000
            )
            
            refined = response.choices[0].message.content
            logger.info("Response refined successfully")
            return refined
            
        except Exception as e:
            logger.error(f"Error refining response: {e}", exc_info=True)
            # Return original answer on error
            return answer


def refinement_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for refinement.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with refined response
    """
    agent = RefinementAgent()
    
    query = state.get("refined_query", state["query"])
    answer = state.get("final_response", "")
    evaluation_scores = state.get("evaluation_scores", {})
    user_context = state.get("user_context", {})
    course_name = state.get("course_name", "")
    course_content_found = state.get("course_content_found", False)
    
    # Refine the response
    refined_answer = agent.refine_response(
        query=query,
        answer=answer,
        evaluation_scores=evaluation_scores,
        user_context=user_context,
        course_name=course_name,
        is_from_web=not course_content_found
    )
    
    # Update state
    state["final_response"] = refined_answer
    state["refinement_attempts"] = state.get("refinement_attempts", 0) + 1
    
    logger.info(f"Refinement attempt {state['refinement_attempts']} completed")
    
    return state
