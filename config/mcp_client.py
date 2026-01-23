"""MCP Client configuration and initialization for PRISM."""

import asyncio
import logging
import shutil
from typing import Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClientManager:
    """Manager for MCP server connections."""

    def __init__(self):
        self.podcast_tts_session: Optional[ClientSession] = None
        self.podcast_tts_context = None

    def _find_node_path(self):
        """Find Node.js path, checking nvm if not in PATH."""
        import os
        
        # First try to find node in PATH
        node_path = shutil.which("node")
        if node_path:
            npx_path = shutil.which("npx")
            if npx_path:
                return node_path, npx_path
        
        # If not found, try to use nvm's node
        nvm_dir = os.path.expanduser("~/.nvm")
        if os.path.exists(nvm_dir):
            # Try to find current node version
            versions_dir = os.path.join(nvm_dir, "versions", "node")
            if os.path.exists(versions_dir):
                # Get the latest/current version
                versions = [d for d in os.listdir(versions_dir) if os.path.isdir(os.path.join(versions_dir, d))]
                if versions:
                    # Sort to get latest version
                    versions.sort(reverse=True)
                    node_version_dir = os.path.join(versions_dir, versions[0])
                    node_bin = os.path.join(node_version_dir, "bin", "node")
                    npx_bin = os.path.join(node_version_dir, "bin", "npx")
                    
                    if os.path.exists(node_bin) and os.path.exists(npx_bin):
                        logger.info(f"Found Node.js via nvm: {node_bin}")
                        return node_bin, npx_bin
        
        return None, None

    async def initialize_podcast_tts(self):
        """Initialize the podcast-tts-mcp server connection."""
        try:
            # Find Node.js and npx
            node_path, npx_path = self._find_node_path()
            
            if not node_path or not npx_path:
                error_msg = "Node.js is not installed or not in PATH. Please install Node.js 18+ from https://nodejs.org/ or restart your terminal after installing."
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(f"Using Node.js: {node_path}")
            logger.info(f"Using npx: {npx_path}")
            logger.info("Initializing podcast TTS MCP server...")
            
            # Update environment to include Node.js path
            import os
            env = os.environ.copy()
            node_bin_dir = os.path.dirname(node_path)
            if "PATH" in env:
                env["PATH"] = f"{node_bin_dir}:{env['PATH']}"
            else:
                env["PATH"] = node_bin_dir
            
            server_params = StdioServerParameters(
                command=npx_path,
                args=["-y", "@mcai/podcast-tts-mcp"],
                env=env
            )

            # Create and store the context manager
            self.podcast_tts_context = stdio_client(server_params)
            stdio, write = await self.podcast_tts_context.__aenter__()

            # Initialize the session
            self.podcast_tts_session = ClientSession(stdio, write)
            await self.podcast_tts_session.__aenter__()

            # Initialize the connection
            await self.podcast_tts_session.initialize()
            
            logger.info("Podcast TTS MCP server initialized successfully")
            return self.podcast_tts_session
        except Exception as e:
            logger.error(f"Failed to initialize podcast TTS MCP server: {e}", exc_info=True)
            raise

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
    ) -> Optional[str]:
        """
        Generate podcast audio using the MCP server.

        Args:
            script: The podcast script/dialogue
            voice1: Voice for the first speaker
            voice2: Voice for the second speaker
            output_path: Path to save the audio file

        Returns:
            Path to the generated audio file, or None if failed
        """
        try:
            if not self.podcast_tts_session:
                await self.initialize_podcast_tts()

            logger.info(f"Calling MCP tool 'generate_podcast' with output_path: {output_path}")
            
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

            # Check if the result indicates success
            if result and hasattr(result, 'content'):
                logger.info(f"MCP tool call completed. Result: {result}")
            elif result:
                logger.info(f"MCP tool call completed. Result type: {type(result)}")
            else:
                logger.warning("MCP tool call returned None or empty result")

            # Verify the file was created
            import os
            if os.path.exists(output_path):
                logger.info(f"Audio file created successfully at: {output_path}")
                return output_path
            else:
                logger.error(f"Audio file not found at expected path: {output_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling MCP tool to generate podcast audio: {e}", exc_info=True)
            return None


# Global MCP client manager instance
mcp_manager = MCPClientManager()


async def get_podcast_tts_client() -> ClientSession:
    """Get or initialize the podcast TTS MCP client."""
    if not mcp_manager.podcast_tts_session:
        await mcp_manager.initialize_podcast_tts()
    return mcp_manager.podcast_tts_session
