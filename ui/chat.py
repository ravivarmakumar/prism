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


# AG-UI removed - keeping A2A and MCP only


def handle_user_input_with_updates(user_query, generate_response):
    """
    Handles user input - sets up state and triggers rerun.
    Generation continues in render_chat_interface.
    
    Args:
        user_query: The user's question/input
        generate_response: Function that generates the response based on query
    """
    if not user_query:
        return
    
    # Add user message to chat (show the actual question they asked)
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_query
    })

    # Store state for continuation after rerun (generation happens in render_chat_interface)
    st.session_state._query_generating = True
    st.session_state._query_text = user_query
    st.session_state._generate_response_func = generate_response

    # Rerun immediately to show user message
    # Generation will continue in render_chat_interface on next render
    st.rerun()


def handle_flashcard_generation(topic: str):
    """Handle flashcard generation request - sets up state and triggers rerun."""
    # Store topic
    st.session_state.flashcard_topic = topic

    # Get all existing flashcards from chat history to avoid duplicates
    all_existing_flashcards = []
    for msg in st.session_state.chat_history:
        if msg.get("role") == "assistant" and msg.get("flashcards"):
            all_existing_flashcards.extend(msg.get("flashcards", []))

    # Add user message to chat (show the actual question they asked)
    st.session_state.chat_history.append({
        "role": "user",
        "content": topic  # Show the actual topic/question
    })

    # Show generating message in chat
    generating_msg = {
        "role": "assistant",
        "content": "Generating flashcards... This may take a moment. 📚"
    }
    st.session_state.chat_history.append(generating_msg)

    # Store state for continuation after rerun (generation happens in render_chat_interface)
    st.session_state._flashcard_generating = True
    st.session_state._flashcard_generating_msg = generating_msg
    st.session_state._flashcard_topic = topic
    st.session_state._flashcard_existing = all_existing_flashcards

    # Rerun immediately to show user message and generating message
    # Generation will continue in render_chat_interface on next render
    st.rerun()


def handle_podcast_generation(topic: str, style: str = "conversational"):
    """Handle podcast generation request - sets up state and triggers rerun."""
    # Store topic
    st.session_state.podcast_topic = topic

    # Add user message to chat (show the actual question they asked)
    st.session_state.chat_history.append({
        "role": "user",
        "content": topic  # Show the actual topic/question
    })

    # Show generating message in chat with loading indicator
    generating_msg = {
        "role": "assistant",
        "content": "🎙️ Generating podcast... This may take a minute. ⏳"
    }
    st.session_state.chat_history.append(generating_msg)

    # Store state for continuation after rerun (generation happens in render_chat_interface)
    st.session_state._podcast_generating = True
    st.session_state._podcast_generating_msg = generating_msg
    st.session_state._podcast_topic = topic
    st.session_state._podcast_style = style

    # Rerun immediately to show user message and generating message
    # Generation will continue in render_chat_interface on next render
    st.rerun()


def render_chat_interface(generate_response):
    """Renders the main chat interface."""
    # Main chat area - no header, just chat
    display_chat_history()
    
    # Check if we need to continue podcast generation after rerun
    if st.session_state.get('_podcast_generating'):
        from core.podcast_generator import run_async_podcast_generation
        import uuid
        
        generating_msg = st.session_state.get('_podcast_generating_msg')
        topic = st.session_state.get('_podcast_topic')
        style = st.session_state.get('_podcast_style', 'conversational')
        
        # Generate podcast with visible spinner
        with st.chat_message("assistant", avatar="🧠"):
            # Show loading indicator with spinner
            with st.spinner("🎙️ Generating podcast audio... This may take a minute."):
                # Generate unique session ID for this podcast
                session_id = str(uuid.uuid4())[:8]

                # Run podcast generation with user context for personalization
                result = run_async_podcast_generation(
                    topic=topic,
                    course_name=st.session_state.user_context.get('course'),
                    session_id=session_id,
                    style=style,
                    user_context=st.session_state.user_context
                )

                # Remove the "generating" message from chat history
                if st.session_state.chat_history and st.session_state.chat_history[-1] == generating_msg:
                    st.session_state.chat_history.pop()

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

        # Clear flags
        st.session_state._podcast_generating = False
        if '_podcast_generating_msg' in st.session_state:
            del st.session_state._podcast_generating_msg
        if '_podcast_topic' in st.session_state:
            del st.session_state._podcast_topic
        if '_podcast_style' in st.session_state:
            del st.session_state._podcast_style
        
        # Auto-deselect podcast mode after generation
        st.session_state.podcast_mode = False
        
        # Clear processing flag when done
        st.session_state.is_processing_input = False
        st.rerun()
        return
    
    # Check if we need to continue regular query generation after rerun
    if st.session_state.get('_query_generating'):
        user_query = st.session_state.get('_query_text')
        generate_response = st.session_state.get('_generate_response_func')
        
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
            
            # Check if still needs follow-up (conversational flow)
            if result.get("needs_follow_up"):
                # Still vague, ask another follow-up question
                follow_up_questions = result.get("follow_up_questions", [])
                if follow_up_questions:
                    follow_up_question = follow_up_questions[0]
                    response = f"I need a bit more information. {follow_up_question}"
                    # Keep follow-up state active for next question
                    st.session_state.original_query = st.session_state.original_query + " " + user_query
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
            
            # Store response in chat history
            st.session_state.chat_history.append({"role": "assistant", "content": response})
        else:
            # Regular query - clear any lingering follow-up state
            st.session_state.follow_up_needed = False
            if 'follow_up_questions' in st.session_state:
                del st.session_state.follow_up_questions
            if 'original_query' in st.session_state:
                del st.session_state.original_query
            
            # Generate response with streaming
            with st.chat_message("assistant", avatar="🧠"):
                # Show spinner while generating response
                spinner_placeholder = st.empty()
                web_search_placeholder = st.empty()
                
                with spinner_placeholder.container():
                    with st.spinner("Processing your question..."):
                        # Generate response
                        response = generate_response(user_query)
                        
                        # Check if web search was used by checking agent state and A2A messages
                        web_search_used = False
                        try:
                            from core.agent import get_prism_agent
                            agent = get_prism_agent()
                            if agent and agent.graph:
                                thread_id = f"session_{st.session_state.user_context.get('student_id', 'default')}"
                                config = {"configurable": {"thread_id": thread_id}}
                                current_state = agent.graph.get_state(config)
                                if current_state and current_state.values:
                                    state_values = current_state.values
                                    
                                    # Method 1: Check if web_search_results exist (most reliable)
                                    has_web_results = bool(state_values.get("web_search_results"))
                                    
                                    # Method 2: Check if course_content_found is False (indicates web search was needed)
                                    course_content_found = state_values.get("course_content_found", True)
                                    needs_web_search = not course_content_found
                                    
                                    # Method 3: Check A2A messages for web search trigger
                                    # Look for message from course_rag to web_search with type "content_not_found"
                                    a2a_messages = state_values.get("a2a_messages", [])
                                    has_web_search_a2a = False
                                    for msg in a2a_messages:
                                        # Check both dict format and A2AMessage format
                                        if isinstance(msg, dict):
                                            receiver = msg.get("receiver") or msg.get("receiver")
                                            msg_type = msg.get("type") or msg.get("message_type")
                                        else:
                                            receiver = getattr(msg, "receiver", None)
                                            msg_type = getattr(msg, "message_type", None) or getattr(msg, "type", None)
                                        
                                        if receiver == "web_search" and (msg_type == "content_not_found" or msg_type == "web_search_completed"):
                                            has_web_search_a2a = True
                                            break
                                    
                                    # Web search was used if any of these conditions are true
                                    web_search_used = bool(
                                        has_web_results or 
                                        (needs_web_search and state_values.get("is_relevant", True)) or
                                        has_web_search_a2a
                                    )
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Error checking web search state: {e}")
                            pass
                
                # Clear spinner and show web search indicator if web search was used
                spinner_placeholder.empty()
                if web_search_used:
                    web_search_placeholder.info("🌐 Searching the internet for current information...")
                
                # Stream the response word by word for better UX
                def stream_response(text):
                    """Generator that yields text in chunks for streaming effect."""
                    words = text.split(' ')
                    for i, word in enumerate(words):
                        if i == 0:
                            yield word
                        else:
                            yield ' ' + word
                        # Small delay for smoother streaming (optional)
                        import time
                        time.sleep(0.02)  # 20ms delay between words
                
                # Stream the response
                response_placeholder = st.empty()
                full_response = ""
                for chunk in stream_response(response):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                    # Clear web search indicator once streaming starts
                    if web_search_used and web_search_placeholder:
                        web_search_placeholder.empty()
                        web_search_used = False  # Prevent clearing again
                
                # Final update without cursor
                response_placeholder.markdown(full_response)
            
            # Store Agent Response in State
            st.session_state.chat_history.append({"role": "assistant", "content": response})

        # Clear flags
        st.session_state._query_generating = False
        if '_query_text' in st.session_state:
            del st.session_state._query_text
        if '_generate_response_func' in st.session_state:
            del st.session_state._generate_response_func
        
        # Clear processing flag when done
        st.session_state.is_processing_input = False
        st.rerun()
        return
    
    # Check if we need to continue flashcard generation after rerun
    if st.session_state.get('_flashcard_generating'):
        from core.flashcard_generator import FlashcardGenerator
        
        generating_msg = st.session_state.get('_flashcard_generating_msg')
        topic = st.session_state.get('_flashcard_topic')
        existing_flashcards = st.session_state.get('_flashcard_existing', [])
        
        # Generate flashcards with visible spinner
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Generating flashcards..."):
                generator = FlashcardGenerator()
                result = generator.generate_flashcards(
                    topic=topic,
                    course_name=st.session_state.user_context.get('course'),
                    existing_flashcards=existing_flashcards,
                    num_flashcards=5
                )

                # Remove the "generating" message from chat history
                if st.session_state.chat_history and st.session_state.chat_history[-1] == generating_msg:
                    st.session_state.chat_history.pop()

                if result['flashcards']:
                    # Show response
                    response = f"Generated {len(result['flashcards'])} flashcards for '{topic}'! 📚"
                    if result['has_more']:
                        response += " Click 'Generate 5 More' to get additional flashcards."
                    else:
                        response += " " + (result.get('message', '') or '')

                    st.markdown(response)

                    # Store assistant response with flashcards attached
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

        # Clear flags
        st.session_state._flashcard_generating = False
        if '_flashcard_generating_msg' in st.session_state:
            del st.session_state._flashcard_generating_msg
        if '_flashcard_topic' in st.session_state:
            del st.session_state._flashcard_topic
        if '_flashcard_existing' in st.session_state:
            del st.session_state._flashcard_existing
        
        # Auto-deselect flashcard mode after generation
        st.session_state.flashcard_mode = False
        
        # Clear processing flag when done
        st.session_state.is_processing_input = False
        st.rerun()
        return
    
    # Note: AG-UI removed. A2A and MCP are still active in the background.
    
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
        # Hide options when processing (podcast/flashcard generation in progress)
        if st.session_state.show_flashcard_options and not st.session_state.is_processing_input:
            with st.container():
                st.markdown("---")
                st.markdown("**Options:**")

                # Use radio buttons for mutually exclusive selection
                content_type = st.radio(
                    "Content Type:",
                    options=["Regular Query", "📚 Generate Flashcards", "🎙️ Generate Podcast"],
                    index=0 if not st.session_state.flashcard_mode and not st.session_state.podcast_mode 
                          else (1 if st.session_state.flashcard_mode else 2),
                    key="content_type_radio",
                    horizontal=True
                )
                
                # Update session state based on selection
                if content_type == "Regular Query":
                    if st.session_state.flashcard_mode or st.session_state.podcast_mode:
                        st.session_state.flashcard_mode = False
                        st.session_state.podcast_mode = False
                        st.rerun()
                elif content_type == "📚 Generate Flashcards":
                    if not st.session_state.flashcard_mode or st.session_state.podcast_mode:
                        st.session_state.flashcard_mode = True
                        st.session_state.podcast_mode = False
                        st.rerun()
                elif content_type == "🎙️ Generate Podcast":
                    if not st.session_state.podcast_mode or st.session_state.flashcard_mode:
                        st.session_state.podcast_mode = True
                        st.session_state.flashcard_mode = False
                        st.rerun()

                # Podcast style is always conversational (no selector needed)
                if st.session_state.podcast_mode:
                    st.session_state.podcast_style = "conversational"
        
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

                    # Set processing flag (for tracking, not for UI)
                    st.session_state.is_processing_input = True

                    # Close options panel when submitting
                    st.session_state.show_flashcard_options = False

                    # Process the input (A2A and MCP work in background)
                    # Note: User message is added inside handle functions for flashcard/podcast
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
                        # Process regular query (user message added in handle function)
                        handle_user_input_with_updates(current_input, generate_response)
    else:
        st.chat_input("Enter details on the left to activate the chat.", disabled=True)

