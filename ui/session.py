"""Session state management for PRISM."""

import streamlit as st


def initialize_session_state():
    """Initializes session state variables for user context and chat history."""
    if 'user_context' not in st.session_state:
        st.session_state.user_context = {
            'student_id': None,
            'course': None,
            'major': None,
            'degree': None,
            'is_ready': False
        }
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Welcome to PRISM! Please fill out the form on the left to start your adaptive learning session."}
        ]
    
    # Initialize flashcard state
    if 'flashcards' not in st.session_state:
        st.session_state.flashcards = []
    
    if 'flashcard_topic' not in st.session_state:
        st.session_state.flashcard_topic = None


def handle_start_session(course_options, degree_options):
    """
    Validates user input and transitions the application state to 'ready'.
    Student ID must be digits only. Major must be letters only (no numbers).
    """
    # Grab values from the sidebar input fields
    student_id = (st.session_state.student_id_input or "").strip()
    major = (st.session_state.major_input or "").strip()
    course = st.session_state.course_dropdown
    degree = st.session_state.degree_dropdown
    
    if not student_id or not major or course == course_options[0] or degree == degree_options[0]:
        st.error("Please fill in all required fields to start the session.")
        return
    
    # Student ID: digits only (no letters or symbols)
    if not student_id.isdigit():
        st.error("Student ID must contain only numbers (no letters or symbols).")
        return
    
    # Major: letters only, no numbers (spaces allowed for names like "Computer Science")
    if any(c.isdigit() for c in major):
        st.error("Major must contain only letters (no numbers).")
        return
    
    # Update session state with validated context
    st.session_state.user_context.update({
        'student_id': student_id,
        'course': course,
        'major': major,
        'degree': degree,
        'is_ready': True
    })
    
    # Add a system message indicating successful context load
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": f"Session started for **{student_id}** in **{course}** ({degree}/{major}). How may I help you learn today? Ask me about your course material!"
    })
    st.rerun()

