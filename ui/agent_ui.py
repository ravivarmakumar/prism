"""Agent UI components for visualizing agent activity."""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime
import time


def get_status_message(current_node: str, state: Dict[str, Any]) -> str:
    """Get human-readable status message based on current node."""
    status_messages = {
        "start": "⏳ Received query, initializing...",
        "query_refinement": "🔍 Checking if query is vague...",
        "relevance": "✅ Query is clear. Checking relevance to course...",
        "course_rag": "📚 Searching course materials...",
        "web_search": "🌐 Searching the web for information...",
        "personalization": "🎯 Personalizing response for you...",
        "evaluation": "📊 Evaluating response quality...",
        "refinement": "🔧 Refining response..."
    }
    return status_messages.get(current_node, "⏳ Processing...")


def render_agent_dashboard_compact(state: Dict[str, Any], is_processing: bool = True):
    """
    Compact agent dashboard that appears below search box.
    Shows real-time updates and disappears when answer is ready.
    
    Args:
        state: Current agent state
        is_processing: Whether agent is still processing
    """
    # Only show if processing
    if not is_processing:
        return
    
    # Get current node and status
    current_node = state.get("current_node", "start")
    status_message = get_status_message(current_node, state)
    
    # Create rounded container with border using Streamlit container
    with st.container():
        st.markdown("""
        <div style='
            border: 2px solid #00853C;
            border-radius: 12px;
            padding: 16px;
            margin: 12px 0;
            background-color: #f8f9fa;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        '>
        """, unsafe_allow_html=True)
    
    # Title
    st.markdown("### 🤖 Agent Dashboard")
    
    # Status message (disappearing)
    if is_processing:
        st.info(f"**{status_message}**")
    
    # Metrics row (always visible)
    st.markdown("#### 📊 Status")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        is_relevant = state.get("is_relevant", False)
        if "is_relevant" in state:
            st.metric("Is Relevant", "✅ Yes" if is_relevant else "❌ No")
        else:
            st.metric("Is Relevant", "⏳ Pending")
    
    with col2:
        content_found = state.get("course_content_found", False)
        if "course_content_found" in state:
            st.metric("Content Found", "✅ Yes" if content_found else "❌ No")
        else:
            st.metric("Content Found", "⏳ Pending")
    
    with col3:
        is_vague = state.get("is_vague", False)
        if "is_vague" in state:
            st.metric("Is Vague", "⚠️ Yes" if is_vague else "✅ No")
        else:
            st.metric("Is Vague", "⏳ Pending")
    
    # A2A Messages (disappearing, show last 5)
    a2a_messages = state.get("a2a_messages", [])
    if a2a_messages and is_processing:
        st.markdown("#### 📨 Agent Communication")
        recent_messages = a2a_messages[-5:] if len(a2a_messages) > 5 else a2a_messages
        
        for msg in reversed(recent_messages):  # Most recent first
            sender = msg.get("sender", "unknown")
            receiver = msg.get("receiver", "unknown")
            msg_type = msg.get("type", "message")
            
            # Create human-readable message
            readable_messages = {
                "query_refined": f"Query refined and sent to {receiver}",
                "query_approved": f"Query approved, sent to {receiver}",
                "content_retrieved": f"Content found, sent to {receiver}",
                "content_not_found": f"No content found, sent to {receiver}",
                "web_search_completed": f"Web search completed, sent to {receiver}",
                "response_ready": f"Response ready, sent to {receiver}",
                "follow_up_needed": "Follow-up question needed",
                "not_relevant": "Query not relevant to course"
            }
            
            readable_msg = readable_messages.get(msg_type, f"{sender} → {receiver}: {msg_type}")
            
            # Format timestamp
            timestamp = msg.get("timestamp", "")
            time_display = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_display = dt.strftime("%H:%M:%S")
                except:
                    time_display = timestamp[:8] if len(timestamp) > 8 else ""
            
            # Show message with fade effect
            st.caption(f"🔄 {readable_msg} {time_display}")
        
        # Close container div
        st.markdown("</div>", unsafe_allow_html=True)


def render_agent_flow_simple(state: Dict[str, Any]):
    """
    Simple agent flow visualization without HTML issues.
    
    Args:
        state: Current agent state
    """
    current_node = state.get("current_node", "start")
    nodes = [
        ("query_refinement", "Query Refinement"),
        ("relevance", "Relevance Check"),
        ("course_rag", "Course Search"),
        ("web_search", "Web Search"),
        ("personalization", "Personalization")
    ]
    
    # Create simple text-based flow
    flow_parts = []
    node_ids = [n[0] for n in nodes]
    
    for node_id, node_name in nodes:
        if node_id == current_node:
            flow_parts.append(f"🟢 {node_name}")
        elif current_node != "start" and current_node in node_ids:
            current_index = node_ids.index(current_node)
            node_index = node_ids.index(node_id)
            if node_index < current_index:
                flow_parts.append(f"✅ {node_name}")
            else:
                flow_parts.append(f"⚪ {node_name}")
        else:
            flow_parts.append(f"⚪ {node_name}")
    
    flow_text = "**Flow:** " + " → ".join(flow_parts)
    st.markdown(flow_text)


def render_agent_decisions(state: Dict[str, Any]):
    """
    Render agent decisions and metrics (without evaluation).
    
    Args:
        state: Current agent state
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        is_relevant = state.get("is_relevant", False)
        if "is_relevant" in state:
            st.metric("Is Relevant", "✅ Yes" if is_relevant else "❌ No")
        else:
            st.metric("Is Relevant", "⏳ Pending")
    
    with col2:
        content_found = state.get("course_content_found", False)
        if "course_content_found" in state:
            st.metric("Content Found", "✅ Yes" if content_found else "❌ No")
        else:
            st.metric("Content Found", "⏳ Pending")
    
    with col3:
        is_vague = state.get("is_vague", False)
        if "is_vague" in state:
            st.metric("Is Vague", "⚠️ Yes" if is_vague else "✅ No")
        else:
            st.metric("Is Vague", "⏳ Pending")


def render_agent_dashboard(state: Dict[str, Any], show_details: bool = True):
    """
    Legacy dashboard - kept for compatibility.
    Use render_agent_dashboard_compact for new UI.
    """
    st.markdown("---")
    st.markdown("## 🤖 Agent Dashboard")
    
    # Agent decisions (no evaluation)
    render_agent_decisions(state)
    
    # Simple flow
    render_agent_flow_simple(state)
    
    # A2A messages
    a2a_messages = state.get("a2a_messages", [])
    if a2a_messages:
        st.markdown("### 📨 Agent-to-Agent Messages")
        recent_messages = a2a_messages[-10:] if len(a2a_messages) > 10 else a2a_messages
        
        for msg in reversed(recent_messages):
            sender = msg.get("sender", "unknown")
            receiver = msg.get("receiver", "unknown")
            msg_type = msg.get("type", "message")
            timestamp = msg.get("timestamp", "")
            
            time_display = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_display = dt.strftime("%H:%M:%S")
                except:
                    time_display = timestamp[:8] if len(timestamp) > 8 else timestamp
            
            st.caption(f"**{sender}** → **{receiver}**: `{msg_type}` {time_display}")
