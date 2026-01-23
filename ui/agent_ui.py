"""Agent UI components for visualizing agent activity."""

import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime


def render_agent_status(agent_name: str, status: str, details: Optional[Dict] = None):
    """
    Render status of a single agent.
    
    Args:
        agent_name: Name of the agent
        status: Status (active, processing, completed, error, idle)
        details: Optional details dictionary
    """
    status_colors = {
        "active": "🟢",
        "processing": "🟡",
        "completed": "✅",
        "error": "❌",
        "idle": "⚪"
    }
    
    icon = status_colors.get(status, "⚪")
    st.markdown(f"{icon} **{agent_name}**: {status}")
    
    if details:
        with st.expander(f"Details for {agent_name}"):
            for key, value in details.items():
                st.text(f"{key}: {value}")


def render_agent_flow(state: Dict[str, Any]):
    """
    Render the agent flow visualization.
    
    Args:
        state: Current agent state
    """
    st.markdown("### 🤖 Agent Flow Status")
    
    # Get current node from state
    current_node = state.get("current_node", "start")
    nodes = [
        "query_refinement",
        "relevance", 
        "course_rag",
        "web_search",
        "personalization",
        "evaluation",
        "refinement"
    ]
    
    # Create flow visualization
    flow_html = "<div style='display: flex; flex-direction: column; gap: 10px; margin: 10px 0;'>"
    
    # If no state or at start, show all as pending
    if current_node == "start" or current_node not in nodes:
        for node in nodes:
            node_display = node.replace('_', ' ').title()
            flow_html += f"""
            <div style='padding: 12px; background-color: #CCCCCC; color: white; border-radius: 8px; margin: 5px 0;'>
                ⚪ {node_display} (Waiting for query...)
            </div>
            """
    else:
        for i, node in enumerate(nodes):
            # Determine status
            node_index = nodes.index(current_node) if current_node in nodes else -1
            if i < node_index:
                status = "completed"
                color = "#4CAF50"  # Green
                icon = "✅"
            elif i == node_index:
                status = "active"
                color = "#00853C"  # UNT Green
                icon = "🟢"
            else:
                status = "pending"
                color = "#CCCCCC"  # Gray
                icon = "⚪"
            
            node_display = node.replace('_', ' ').title()
            flow_html += f"""
            <div style='padding: 12px; background-color: {color}; color: white; border-radius: 8px; margin: 5px 0;'>
                {icon} {node_display}
            </div>
            """
    
    flow_html += "</div>"
    st.markdown(flow_html, unsafe_allow_html=True)


def render_a2a_messages(a2a_messages: List[Dict[str, Any]]):
    """
    Render A2A communication messages.
    
    Args:
        a2a_messages: List of A2A messages
    """
    if not a2a_messages:
        return
    
    st.markdown("### 📨 Agent-to-Agent Messages")
    
    # Show last 10 messages
    recent_messages = a2a_messages[-10:] if len(a2a_messages) > 10 else a2a_messages
    
    for msg in reversed(recent_messages):  # Show most recent first
        sender = msg.get("sender", "unknown")
        receiver = msg.get("receiver", "unknown")
        msg_type = msg.get("type", "message")
        timestamp = msg.get("timestamp", "")
        
        # Format timestamp if available
        time_display = ""
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_display = dt.strftime("%H:%M:%S")
            except:
                time_display = timestamp[:8] if len(timestamp) > 8 else timestamp
        
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{sender}** → **{receiver}**: `{msg_type}`")
            with col2:
                if time_display:
                    st.caption(time_display)
            
            # Show content in expander
            content = msg.get("content")
            if content:
                with st.expander("Message content"):
                    if isinstance(content, dict):
                        for key, value in content.items():
                            st.text(f"{key}: {value}")
                    else:
                        st.text(str(content)[:500])
        
        st.markdown("---")


def render_agent_decisions(state: Dict[str, Any]):
    """
    Render agent decisions and metrics.
    
    Args:
        state: Current agent state
    """
    st.markdown("### 📊 Agent Decisions")
    
    col1, col2, col3, col4 = st.columns(4)
    
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
    
    with col4:
        eval_passed = state.get("evaluation_passed", False)
        if "evaluation_passed" in state:
            st.metric("Evaluation", "✅ Passed" if eval_passed else "⚠️ Failed")
        else:
            st.metric("Evaluation", "⏳ Pending")


def render_agent_dashboard(state: Dict[str, Any], show_details: bool = True):
    """
    Main agent dashboard component.
    
    Args:
        state: Current agent state
        show_details: Whether to show detailed information
    """
    st.markdown("---")
    st.markdown("## 🤖 Agent Dashboard")
    st.caption("AG-UI and A2A are always active. This dashboard shows real-time agent activity.")
    
    # Always show agent flow visualization (even if empty)
    render_agent_flow(state)
    
    # Always show agent decisions (will show defaults if no state)
    render_agent_decisions(state)
    
    # A2A messages - always show section, even if empty
    a2a_messages = state.get("a2a_messages", [])
    if a2a_messages:
        render_a2a_messages(a2a_messages)
    else:
        st.markdown("### 📨 Agent-to-Agent Messages")
        st.info("No A2A messages yet. Messages will appear here as agents communicate. Ask a question to see agent-to-agent communication.")
    
    # Additional details in expander
    if show_details:
        with st.expander("📋 Detailed State Information"):
            # Show relevant state fields
            relevant_fields = [
                "query", "refined_query", "relevance_reason",
                "course_context", "web_search_results", "final_response"
            ]
            
            for field in relevant_fields:
                value = state.get(field)
                if value:
                    st.markdown(f"**{field.replace('_', ' ').title()}:**")
                    if isinstance(value, str) and len(value) > 200:
                        st.text(value[:200] + "...")
                    else:
                        st.text(str(value))
                    st.markdown("---")
