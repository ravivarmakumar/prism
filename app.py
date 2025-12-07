import streamlit as st
import logging
from pathlib import Path

# Import UI components
from ui import styling, sidebar, chat, session
from generation.response_generator import ResponseGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize response generator (singleton pattern for Streamlit)
@st.cache_resource
def get_response_generator():
    """Get or create response generator instance."""
    try:
        return ResponseGenerator()
    except Exception as e:
        logger.error(f"Error initializing response generator: {e}")
        return None


def get_available_courses():
    """Get list of available courses from courses directory."""
    from config.settings import COURSES_PATH
    
    courses_dir = Path(COURSES_PATH)
    if not courses_dir.exists():
        return ["Select Course..."]
    
    courses = ["Select Course..."]
    for course_folder in courses_dir.iterdir():
        if course_folder.is_dir():
            # Use folder name as course name
            courses.append(course_folder.name)
    
    return courses if len(courses) > 1 else ["Select Course...", "Neuroquest"]


def generate_response(user_query):
    """
    Generate response using RAG system.
    
    Args:
        user_query: User's question
        
    Returns:
        Formatted response with citations
    """
    try:
        generator = get_response_generator()
        if generator is None:
            return "Error: Response generator not available. Please check your configuration."
        
        course_name = st.session_state.user_context.get('course')
        user_context = st.session_state.user_context
        
        if not course_name or course_name == "Select Course...":
            return "Please select a course to ask questions."
        
        # Generate response
        result = generator.generate_response(
            query=user_query,
            course_name=course_name,
            user_context=user_context
        )
        
        # Format response with citations
        response = result["response"]
        
        if result["citations"]:
            citations_text = "\n\n**Citations:**\n"
            for citation in result["citations"]:
                citations_text += f"- {citation['document']}, Page {citation['page']}\n"
            response += citations_text
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return f"I encountered an error while processing your question. Please try again. Error: {str(e)}"


# --- Main Application Layout ---
def main():
    # Initialize styling
    styling.set_streamlit_config()
    
    # Initialize session state
    session.initialize_session_state()
    
    # Get available courses from courses directory
    COURSE_OPTIONS = get_available_courses()
    
    DEGREE_OPTIONS = [
        "Select Degree...",
        "Bachelor of Science",
        "Master of Science",
        "Doctor of Philosophy"
    ]
    
    # Render sidebar
    sidebar.render_sidebar(
        COURSE_OPTIONS,
        DEGREE_OPTIONS,
        session.handle_start_session
    )
    
    # Render main chat interface
    chat.render_chat_interface(generate_response)
    
    # --- Copyright Footer ---
    st.markdown(
        '<div class="footer">© PRISM Adaptive Learning System 2025 (UNT Dissertation POC)</div>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
