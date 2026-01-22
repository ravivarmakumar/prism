"""MCP Client configuration and initialization for PRISM."""

import asyncio
from typing import Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClientManager:
    """Manager for MCP server connections."""

    def __init__(self):
        self.podcast_tts_session: Optional[ClientSession] = None
        self.podcast_tts_context = None

    async def initialize_podcast_tts(self):
        """Initialize the podcast-tts-mcp server connection."""
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@mcai/podcast-tts-mcp"],
            env=None
        )

        # Create and store the context manager
        self.podcast_tts_context = stdio_client(server_params)
        stdio, write = await self.podcast_tts_context.__aenter__()

        # Initialize the session
        self.podcast_tts_session = ClientSession(stdio, write)
        await self.podcast_tts_session.__aenter__()

        # Initialize the connection
        await self.podcast_tts_session.initialize()

        return self.podcast_tts_session

    async def close_podcast_tts(self):
        """Close the podcast-tts-mcp server connection."""
        if self.podcast_tts_session:
            await self.podcast_tts_session.__aexit__(None, None, None)
            self.podcast_tts_session = None

        if self.podcast_tts_context:
            await self.podcast_tts_context.__aexit__(None, None, None)
            self.podcast_tts_context = None

    async def generate_podcast_audio(
        self,
        script: str,
        voice1: str = "default",
        voice2: str = "default",
        output_path: str = "podcast.mp3"
    ) -> str:
        """
        Generate podcast audio using the MCP server.

        Args:
            script: The podcast script/dialogue
            voice1: Voice for the first speaker
            voice2: Voice for the second speaker
            output_path: Path to save the audio file

        Returns:
            Path to the generated audio file
        """
        if not self.podcast_tts_session:
            await self.initialize_podcast_tts()

        # Call the MCP tool to generate podcast
        result = await self.podcast_tts_session.call_tool(
            "generate_podcast",
            arguments={
                "script": script,
                "voice1": voice1,
                "voice2": voice2,
                "output_path": output_path
            }
        )

        return output_path


# Global MCP client manager instance
mcp_manager = MCPClientManager()


async def get_podcast_tts_client() -> ClientSession:
    """Get or initialize the podcast TTS MCP client."""
    if not mcp_manager.podcast_tts_session:
        await mcp_manager.initialize_podcast_tts()
    return mcp_manager.podcast_tts_session
