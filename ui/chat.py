"""Chat UI components for PRISM."""

import hashlib
import os
import streamlit as st


def display_flashcards(flashcards):
    """Display flashcards in an interactive format."""
    if not flashcards:
        return

    st.markdown("### 📚 Flashcards")

    for i, card in enumerate(flashcards, 1):
        with st.expander(f"Card {i}: {card['question'][:60]}...", expanded=False):
            st.markdown(f"**Q:** {card['question']}")
            st.markdown("---")
            st.markdown(f"**A:** {card['answer']}")

            # Show source if available
            if card.get('source'):
                source = card['source']
                source_parts = []
                if source.get('module'):
                    source_parts.append(f"Module: {source['module']}")
                source_parts.append(f"Document: {source['document']}")
                if source.get('page'):
                    source_parts.append(f"Page {source['page']}")
                elif source.get('timestamp'):
                    source_parts.append(f"Timestamp: {source['timestamp']}")

                st.caption(f"Source: {', '.join(source_parts)}")


def display_podcast_player(podcast_data):
    """Display podcast audio player with controls."""
    if not podcast_data or not podcast_data.get('audio_path'):
        return

    st.markdown("### 🎙️ Podcast")

    audio_path = podcast_data['audio_path']

    # Check if file exists
    if os.path.exists(audio_path):
        # Read audio file
        with open(audio_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()

        # Display audio player with controls
        st.audio(audio_bytes, format='audio/mp3', start_time=0)

        # Show transcript/script in expander if available
        if podcast_data.get('script'):
            with st.expander("📄 View Transcript", expanded=False):
                st.text(podcast_data['script'])
    else:
        st.error("Audio file not found. Please regenerate the podcast.")


def display_chat_history():
    """Renders the chat history from session state with user messages on right and AI on left."""
    for message in st.session_state.chat_history:
        role = message["role"]
        content = message["content"]
        flashcards = message.get("flashcards", [])  # Get flashcards if present
        podcast = message.get("podcast")  # Get podcast if present

        # User messages appear on the right with person icon
        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(content)
        # Assistant messages appear on the left with brain icon
        elif role == "assistant":
            with st.chat_message("assistant", avatar="🧠"):
                st.markdown(content)
                # Display flashcards if this message has them
                if flashcards:
                    st.markdown("---")
                    display_flashcards(flashcards)
                # Display podcast player if this message has a podcast
                if podcast:
                    st.markdown("---")
                    display_podcast_player(podcast)


def _show_agent_dashboard_if_processing():
    """Show agent dashboard if currently processing a query."""
    if not st.session_state.user_context.get('is_ready'):
        return
    
    # Check if we're processing (user just submitted but no response yet)
    is_processing_flag = st.session_state.get('is_processing_input', False)
    
    if not is_processing_flag:
        return
    
    # Check agent state - try to get latest state
    try:
        from ui.agent_ui import render_agent_dashboard_compact
        from core.agent import get_prism_agent
        
        agent = get_prism_agent()
        if agent and agent.graph:
            try:
                thread_id = f"session_{st.session_state.user_context.get('student_id', 'default')}"
                config = {"configurable": {"thread_id": thread_id}}
                current_state = agent.graph.get_state(config)
                
                if current_state and current_state.values:
                    state_values = current_state.values
                    # Check if processing (has query but no final response yet)
                    has_query = bool(state_values.get("query") or state_values.get("refined_query"))
                    has_final_response = bool(state_values.get("final_response"))
                    
                    # Show dashboard if we have a query and no final response yet
                    if has_query and not has_final_response:
                        # Use a placeholder that can be updated
                        dashboard_placeholder = st.empty()
                        with dashboard_placeholder.container():
                            render_agent_dashboard_compact(state_values, is_processing=True)
                        return
            except Exception as e:
                # If error getting state, still show initial dashboard
                pass
        
        # If state not available yet but we're processing, show initial dashboard
        initial_state = {
            "current_node": "start",
            "is_vague": False,
            "is_relevant": False,
            "course_content_found": False,
            "a2a_messages": []
        }
        render_agent_dashboard_compact(initial_state, is_processing=True)
    except Exception:
        pass


def handle_user_input_with_updates(user_query, generate_response):
    """
    Handles user input with real-time dashboard updates.
    Uses a placeholder that updates as agents work.
    
    Args:
        user_query: The user's question/input
        generate_response: Function that generates the response based on query
    """
    if not user_query:
        return
    
    # Note: User message already added to chat_history in form handler
    
    # Check if this is a follow-up answer
    if st.session_state.get('follow_up_needed', False):
        # This is an answer to a follow-up question
        from core.agent import PRISMAgent
        
        agent = PRISMAgent()
        course_name = st.session_state.user_context.get('course')
        user_context = st.session_state.user_context
        thread_id = f"session_{st.session_state.user_context.get('student_id', 'default')}"
        
        # Refine and process
        result = agent.refine_query_with_follow_up(
            original_query=st.session_state.original_query,
            follow_up_answer=user_query,
            course_name=course_name,
            user_context=user_context,
            thread_id=thread_id
        )
        
        # Follow-up answer - user message already in chat from rerun, skip adding again
        
        # Check if still needs follow-up (conversational flow)
        if result.get("needs_follow_up"):
            # Still vague, ask another follow-up question
            follow_up_questions = result.get("follow_up_questions", [])
            if follow_up_questions:
                follow_up_question = follow_up_questions[0]
                response = f"I need a bit more information. {follow_up_question}"
                # Keep follow-up state active for next question
                st.session_state.original_query = st.session_state.original_query + " " + user_query  # Accumulate context
                st.session_state.follow_up_questions = [follow_up_question]
            else:
                response = result.get("response", "Processing your refined question...")
                # Clear follow-up state
                st.session_state.follow_up_needed = False
                if 'follow_up_questions' in st.session_state:
                    del st.session_state.follow_up_questions
                if 'original_query' in st.session_state:
                    del st.session_state.original_query
        else:
            # Query is now clear, show response
            response = result.get("response", "Processing your refined question...")
            # Clear follow-up state
            st.session_state.follow_up_needed = False
            if 'follow_up_questions' in st.session_state:
                del st.session_state.follow_up_questions
            if 'original_query' in st.session_state:
                del st.session_state.original_query
        
        # Display response
        with st.chat_message("assistant", avatar="🧠"):
            st.markdown(response)
    else:
        # Regular query - clear any lingering follow-up state
        # This ensures that each new query starts fresh
        st.session_state.follow_up_needed = False
        if 'follow_up_questions' in st.session_state:
            del st.session_state.follow_up_questions
        if 'original_query' in st.session_state:
            del st.session_state.original_query
        
        # User message already in chat, now generate response
        # Create assistant message placeholder that will be updated
        with st.chat_message("assistant", avatar="🧠"):
            # Show thinking indicator
            thinking_placeholder = st.empty()
            with thinking_placeholder.container():
                st.info("🤔 PRISM Agent is thinking...")
            
            # Generate response in background with periodic dashboard updates
            # Use a container that can be updated
            response_placeholder = st.empty()
            
            # Generate response (this is blocking, but dashboard will show initial state)
            response = generate_response(user_query)
            
            # Clear thinking indicator and show response
            thinking_placeholder.empty()
            with response_placeholder.container():
                st.markdown(response)
        
        # Store Agent Response in State
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        # Clear processing flag - answer is ready (dashboard will disappear)
        st.session_state.is_processing_input = False
        st.rerun()


def handle_flashcard_generation(topic: str):
    """Handle flashcard generation request."""
    from core.flashcard_generator import FlashcardGenerator

    # Store topic
    st.session_state.flashcard_topic = topic

    # Get all existing flashcards from chat history to avoid duplicates
    all_existing_flashcards = []
    for msg in st.session_state.chat_history:
        if msg.get("role") == "assistant" and msg.get("flashcards"):
            all_existing_flashcards.extend(msg.get("flashcards", []))

    # Add user message to chat
    st.session_state.chat_history.append({
        "role": "user",
        "content": f"Generate flashcards for: {topic}"
    })

    # Generate flashcards
    with st.chat_message("assistant", avatar="🧠"):
        with st.spinner("Generating flashcards..."):
            generator = FlashcardGenerator()
            result = generator.generate_flashcards(
                topic=topic,
                course_name=st.session_state.user_context.get('course'),
                existing_flashcards=all_existing_flashcards,
                num_flashcards=5
            )

            if result['flashcards']:
                # Show response
                response = f"Generated {len(result['flashcards'])} flashcards for '{topic}'! 📚"
                if result['has_more']:
                    response += " Click 'Generate 5 More' to get additional flashcards."
                else:
                    response += " " + (result.get('message', '') or '')

                st.markdown(response)

                # Store assistant response with flashcards attached (will be displayed by display_chat_history)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response,
                    "flashcards": result['flashcards']
                })
            else:
                error_msg = result.get('message', 'Could not generate flashcards. Please try a different topic.')
                st.markdown(error_msg)
                # Store assistant response without flashcards
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": error_msg
                })

    st.rerun()


def handle_podcast_generation(topic: str, style: str = "conversational"):
    """Handle podcast generation request."""
    # Clear processing flag when done
    st.session_state.is_processing_input = False
    from core.podcast_generator import run_async_podcast_generation
    import uuid

    # Store topic
    st.session_state.podcast_topic = topic

    # Add user message to chat
    st.session_state.chat_history.append({
        "role": "user",
        "content": f"Generate podcast for: {topic}"
    })

    # Generate podcast
    with st.chat_message("assistant", avatar="🧠"):
        with st.spinner("Generating podcast... This may take a minute."):
            # Generate unique session ID for this podcast
            session_id = str(uuid.uuid4())[:8]

            # Run podcast generation
            result = run_async_podcast_generation(
                topic=topic,
                course_name=st.session_state.user_context.get('course'),
                session_id=session_id,
                style=st.session_state.get('podcast_style', 'conversational')
            )

            if result['success'] and result['audio_path']:
                # Show response
                response = f"Generated podcast for '{topic}'! 🎙️"
                st.markdown(response)

                # Store assistant response with podcast attached
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response,
                    "podcast": {
                        "audio_path": result['audio_path'],
                        "script": result.get('script'),
                        "topic": topic
                    }
                })
            else:
                error_msg = result.get('message', 'Could not generate podcast. Please try a different topic.')
                st.markdown(error_msg)
                # Store assistant response without podcast
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": error_msg
                })

    st.rerun()


def render_chat_interface(generate_response):
    """Renders the main chat interface."""
    # Main chat area - no header, just chat
    display_chat_history()
    
    # Show agent dashboard if processing (appears below chat history, above input)
    _show_agent_dashboard_if_processing()
    
    # Check if we should show "Generate 5 More" button
    # Only show if the last assistant message has flashcards and has_more flag
    show_generate_more = False
    if st.session_state.chat_history:
        last_message = st.session_state.chat_history[-1]
        if (last_message.get("role") == "assistant" and 
            last_message.get("flashcards") and 
            st.session_state.get('flashcard_topic')):
            # Check if there might be more flashcards available
            show_generate_more = True
    
    # Generate More button (only show if applicable)
    if show_generate_more:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Generate 5 More", use_container_width=True, key="generate_more_flashcards"):
                if st.session_state.get('flashcard_topic'):
                    # Get all existing flashcards from chat history
                    all_existing_flashcards = []
                    for msg in st.session_state.chat_history:
                        if msg.get("role") == "assistant" and msg.get("flashcards"):
                            all_existing_flashcards.extend(msg.get("flashcards", []))
                    
                    # Add user message for "Generate 5 More"
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": "Generate 5 more flashcards"
                    })
                    
                    # Generate more flashcards
                    from core.flashcard_generator import FlashcardGenerator
                    generator = FlashcardGenerator()
                    result = generator.generate_flashcards(
                        topic=st.session_state.flashcard_topic,
                        course_name=st.session_state.user_context.get('course'),
                        existing_flashcards=all_existing_flashcards,
                        num_flashcards=5
                    )
                    
                    if result['flashcards']:
                        response = f"Generated {len(result['flashcards'])} more flashcards! 📚"
                        if not result['has_more']:
                            response += " " + (result.get('message', 'We\'ve covered everything available for this topic!') or '')
                        
                        # Store assistant response with new flashcards
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": response,
                            "flashcards": result['flashcards']
                        })
                    else:
                        error_msg = result.get('message', 'No more flashcards available for this topic.')
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                    st.rerun()
    
    # Chat input with flashcard toggle button inside
    if st.session_state.user_context['is_ready']:
        # Initialize flashcard and podcast modes in session state if not exists
        if 'flashcard_mode' not in st.session_state:
            st.session_state.flashcard_mode = False
        if 'podcast_mode' not in st.session_state:
            st.session_state.podcast_mode = False
        if 'podcast_style' not in st.session_state:
            st.session_state.podcast_style = "conversational"
        if 'show_flashcard_options' not in st.session_state:
            st.session_state.show_flashcard_options = False
        if 'is_processing_input' not in st.session_state:
            st.session_state.is_processing_input = False
        if 'last_input_value' not in st.session_state:
            st.session_state.last_input_value = ""
        
        # Don't auto-reset processing flag here - let it be controlled by handle_user_input
        # The flag will be cleared when response is ready
        
        # Show options popover OUTSIDE the form (only when plus was clicked)
        # This ensures it's visible and doesn't get hidden during form submission
        if st.session_state.show_flashcard_options:
            with st.container():
                st.markdown("---")
                st.markdown("**Options:**")

                # Flashcard option
                flashcard_mode = st.checkbox(
                    "📚 Generate Flashcards",
                    value=st.session_state.flashcard_mode,
                    key="flashcard_option_checkbox"
                )
                if flashcard_mode != st.session_state.flashcard_mode:
                    st.session_state.flashcard_mode = flashcard_mode
                    # Disable podcast mode if flashcard is enabled
                    if flashcard_mode:
                        st.session_state.podcast_mode = False
                    st.rerun()

                # Podcast option
                podcast_mode = st.checkbox(
                    "🎙️ Generate Podcast",
                    value=st.session_state.podcast_mode,
                    key="podcast_option_checkbox"
                )
                if podcast_mode != st.session_state.podcast_mode:
                    st.session_state.podcast_mode = podcast_mode
                    # Disable flashcard mode if podcast is enabled
                    if podcast_mode:
                        st.session_state.flashcard_mode = False
                    st.rerun()

                # Show podcast style selector if podcast mode is active
                if st.session_state.podcast_mode:
                    podcast_style = st.radio(
                        "Podcast Style:",
                        options=["conversational", "interview"],
                        index=0 if st.session_state.podcast_style == "conversational" else 1,
                        key="podcast_style_radio",
                        horizontal=True
                    )
                    if podcast_style != st.session_state.podcast_style:
                        st.session_state.podcast_style = podcast_style
                        st.rerun()
        
        # Use a form to create custom chat input with plus button inside
        with st.form(key="chat_form", clear_on_submit=True):
            # Create a custom input that looks like chat_input with plus button inside
            # Use columns to simulate the input box layout
            input_col1, input_col2, input_col3 = st.columns([0.06, 0.84, 0.1])
            
            with input_col1:
                # Plus button - styled to look like it's inside the input
                plus_clicked = st.form_submit_button(
                    "➕",
                    key="plus_button",
                    use_container_width=True,
                    help="Click to show flashcard options"
                )
            
            with input_col2:
                # Text input - styled to look like chat input
                # Enter key will submit the form automatically
                placeholder_text = "Ask your questions here..."
                if st.session_state.flashcard_mode:
                    placeholder_text = "Enter a topic for flashcards..."
                elif st.session_state.podcast_mode:
                    placeholder_text = "Enter a topic for podcast..."

                user_input = st.text_input(
                    "",
                    placeholder=placeholder_text,
                    key="custom_chat_input",
                    label_visibility="collapsed"
                )
            
            with input_col3:
                # Send button - smaller size
                submit = st.form_submit_button(
                    "➤",
                    use_container_width=True,
                    type="primary"
                )
            
            # Handle plus button click (only when clicked alone, not during Enter submission)
            # When Enter is pressed, both plus_clicked and submit become True, so we check for input
            if plus_clicked and not user_input:
                st.session_state.show_flashcard_options = not st.session_state.show_flashcard_options
                st.rerun()
            
            # Handle form submission (works with Enter key or send button)
            # The challenge: detecting Enter key vs button clicks in Streamlit forms
            # Strategy: Track if input changed to detect any form submission with input
            current_input = user_input.strip() if user_input else ""
            input_changed = current_input and current_input != st.session_state.get('last_input_value', '')
            
            # Process if:
            # 1. We have input
            # 2. Form was submitted (submit button clicked OR Enter pressed OR input changed)
            # 3. Not already processing
            # 4. Not just the plus button clicked alone (which has no input)
            should_process = (
                current_input and 
                (submit or input_changed) and 
                not st.session_state.is_processing_input and
                not (plus_clicked and not submit and not current_input)  # Exclude plus-only click
            )
            
            if should_process:
                # Check if this input is already the last user message (prevent duplicates)
                is_duplicate = False
                if st.session_state.chat_history:
                    last_msg = st.session_state.chat_history[-1]
                    if (last_msg.get("role") == "user" and 
                        last_msg.get("content") == current_input):
                        is_duplicate = True
                
                if not is_duplicate:
                    # Update last input value to track form submissions
                    st.session_state.last_input_value = current_input

                    # Set processing flag IMMEDIATELY so dashboard shows right away
                    st.session_state.is_processing_input = True

                    # Close options panel when submitting
                    st.session_state.show_flashcard_options = False

                    # Store user message immediately so it appears in chat
                    if not st.session_state.flashcard_mode and not st.session_state.podcast_mode:
                        st.session_state.chat_history.append({"role": "user", "content": current_input})

                    # Rerun immediately to show dashboard and user message
                    st.rerun()
                    
                    # After rerun, process the input
                    if st.session_state.flashcard_mode:
                        handle_flashcard_generation(current_input)
                        st.session_state.flashcard_mode = False
                    elif st.session_state.podcast_mode:
                        handle_podcast_generation(
                            current_input,
                            style=st.session_state.podcast_style
                        )
                        st.session_state.podcast_mode = False
                    else:
                        # Process regular query (user message already added above)
                        handle_user_input_with_updates(current_input, generate_response)
    else:
        st.chat_input("Enter details on the left to activate the chat.", disabled=True)

