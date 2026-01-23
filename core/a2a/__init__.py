"""Agent-to-Agent (A2A) Communication Framework."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.state import AgentState

logger = logging.getLogger(__name__)


class A2AMessage:
    """Message structure for A2A communication."""
    
    def __init__(
        self,
        sender: str,
        receiver: str,
        message_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.sender = sender
        self.receiver = receiver
        self.message_type = message_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for state storage."""
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "type": self.message_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class A2AManager:
    """Manages agent-to-agent communication."""
    
    def __init__(self):
        self.message_history: List[A2AMessage] = []
        self.max_history = 100  # Keep last 100 messages
    
    def send_message(
        self,
        sender: str,
        receiver: str,
        message_type: str,
        content: Any,
        state: AgentState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """
        Send a message from one agent to another.
        
        Args:
            sender: Name of the sending agent
            receiver: Name of the receiving agent
            message_type: Type of message (e.g., "content_retrieved", "query_refined")
            content: Message content (any serializable type)
            state: Current agent state
            metadata: Optional metadata dictionary
            
        Returns:
            Updated state with message added
        """
        message = A2AMessage(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content,
            metadata=metadata
        )
        
        # Add to history
        self.message_history.append(message)
        
        # Keep history size manageable
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        
        # Store in state for agent access
        if "a2a_messages" not in state:
            state["a2a_messages"] = []
        
        message_dict = message.to_dict()
        state["a2a_messages"].append(message_dict)
        
        # Keep state message list manageable
        if len(state["a2a_messages"]) > self.max_history:
            state["a2a_messages"] = state["a2a_messages"][-self.max_history:]
        
        # Log A2A message for debugging
        logger.debug(f"A2A Message: {sender} → {receiver} [{message_type}] (Total: {len(state['a2a_messages'])})")
        
        return state
    
    def get_messages_for_agent(
        self,
        agent_name: str,
        state: AgentState
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a specific agent.
        
        Args:
            agent_name: Name of the agent
            state: Current agent state
            
        Returns:
            List of messages for the agent
        """
        messages = state.get("a2a_messages", [])
        return [
            msg for msg in messages
            if msg.get("receiver") == agent_name
        ]
    
    def get_messages_from_agent(
        self,
        agent_name: str,
        state: AgentState
    ) -> List[Dict[str, Any]]:
        """
        Get all messages from a specific agent.
        
        Args:
            agent_name: Name of the agent
            state: Current agent state
            
        Returns:
            List of messages from the agent
        """
        messages = state.get("a2a_messages", [])
        return [
            msg for msg in messages
            if msg.get("sender") == agent_name
        ]
    
    def get_messages_by_type(
        self,
        message_type: str,
        state: AgentState
    ) -> List[Dict[str, Any]]:
        """
        Get all messages of a specific type.
        
        Args:
            message_type: Type of message to filter
            state: Current agent state
            
        Returns:
            List of messages of the specified type
        """
        messages = state.get("a2a_messages", [])
        return [
            msg for msg in messages
            if msg.get("type") == message_type
        ]
    
    def clear_history(self):
        """Clear message history."""
        self.message_history.clear()


# Global A2A manager instance
a2a_manager = A2AManager()
