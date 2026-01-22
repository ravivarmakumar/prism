"""Podcast Generator - Creates conversational podcasts from course content."""

import logging
import json
import asyncio
import tempfile
import os
from typing import Dict, Any, Optional
from openai import OpenAI
from config.settings import OPENAI_API_KEY, OPENAI_MODEL
from config.mcp_client import mcp_manager
from retrieval.retriever import CourseRetriever

logger = logging.getLogger(__name__)


class PodcastGenerator:
    """Generates conversational podcasts from course content."""

    def __init__(self):
        """Initialize the podcast generator."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.retriever = CourseRetriever()
        self.temp_dir = tempfile.gettempdir()

    def _create_conversational_script(
        self,
        context: str,
        topic: str,
        style: str = "conversational"
    ) -> str:
        """
        Generate a conversational podcast script using LLM.

        Args:
            context: Retrieved course content
            topic: The topic for the podcast
            style: Style of podcast (conversational or interview)

        Returns:
            Formatted script for TTS generation
        """
        style_instructions = {
            "conversational": """Create a natural, friendly conversation between two hosts discussing the topic.
- Host 1 (Alex): The primary explainer, knowledgeable and enthusiastic
- Host 2 (Sam): Asks clarifying questions, relates concepts to real-world examples
- Keep the tone casual but informative, like NotebookLM
- Use natural conversational fillers like "So...", "Right!", "That makes sense"
- Break down complex concepts into digestible parts
- Use analogies and examples to make content relatable""",

            "interview": """Create an interview-style podcast.
- Host (Interviewer): Asks probing questions to explore the topic
- Guest (Expert): Provides detailed explanations and insights
- Keep the tone professional but engaging
- Host should guide the conversation and ask follow-up questions
- Expert should provide comprehensive answers based on the content"""
        }

        instruction = style_instructions.get(style, style_instructions["conversational"])

        system_prompt = f"""You are a podcast script writer. {instruction}

Format the script with clear speaker labels:
- Use "Alex:" and "Sam:" for conversational style
- Use "Host:" and "Guest:" for interview style
- Each line should be a natural, complete thought
- Keep individual speaking segments to 2-3 sentences max
- Ensure smooth transitions between speakers
- Make the content engaging and easy to follow
- Total podcast should be informative but not too long

IMPORTANT: Base all content ONLY on the provided course material. Do not make up information."""

        user_prompt = f"""Create an engaging podcast script about '{topic}' based on the following course content.

Course Content:
{context}

Topic: {topic}
Style: {style}

Generate a natural, flowing conversation that:
1. Introduces the topic engagingly
2. Covers key concepts from the course content
3. Explains complex ideas in simple terms
4. Includes relevant examples or analogies
5. Concludes with a summary of key takeaways

Keep the script conversational and dynamic. Format each line as:
Speaker: [dialogue]

Example:
Alex: Hey Sam, today we're diving into something really fascinating - {topic}!
Sam: Oh, I've been curious about this! What's the main idea here?
Alex: Well, let me break it down for you...

Return ONLY the script with speaker labels, no additional commentary."""

        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,  # Higher temperature for more natural variation
                max_tokens=2000
            )

            script = response.choices[0].message.content.strip()
            logger.info(f"Generated podcast script ({len(script)} chars)")
            return script

        except Exception as e:
            logger.error(f"Error generating podcast script: {e}", exc_info=True)
            return ""

    async def _generate_audio(
        self,
        script: str,
        session_id: str,
        style: str = "conversational"
    ) -> Optional[str]:
        """
        Generate audio from script using MCP TTS service.

        Args:
            script: The podcast script
            session_id: Session ID for unique file naming
            style: Podcast style (affects voice selection)

        Returns:
            Path to generated audio file or None if failed
        """
        try:
            # Create temp file path
            output_filename = f"podcast_{session_id}.mp3"
            output_path = os.path.join(self.temp_dir, output_filename)

            # Voice selection based on style
            if style == "conversational":
                voice1 = "default"  # Alex (Host 1)
                voice2 = "default"  # Sam (Host 2)
            else:  # interview
                voice1 = "default"  # Interviewer
                voice2 = "default"  # Expert

            logger.info(f"Generating audio with MCP TTS service...")

            # Generate audio using MCP client
            audio_path = await mcp_manager.generate_podcast_audio(
                script=script,
                voice1=voice1,
                voice2=voice2,
                output_path=output_path
            )

            logger.info(f"Audio generated successfully: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Error generating podcast audio: {e}", exc_info=True)
            return None

    async def generate_podcast(
        self,
        topic: str,
        course_name: str,
        session_id: str,
        style: str = "conversational"
    ) -> Dict[str, Any]:
        """
        Generate a podcast for a given topic.

        Args:
            topic: The topic/question for the podcast
            course_name: Name of the course
            session_id: Session ID for unique file naming
            style: Style of podcast (conversational or interview)

        Returns:
            Dictionary with audio_path, script, and status/message
        """
        try:
            # Retrieve relevant content
            logger.info(f"Retrieving content for podcast topic: '{topic}'")
            retrieved_chunks = self.retriever.retrieve(
                query=topic,
                course_name=course_name,
                top_k=10  # Get enough content for a comprehensive podcast
            )

            if not retrieved_chunks:
                # If no course content found, try with enhanced query
                logger.info("No content found, trying enhanced query...")
                enhanced_query = f"{topic} overview concepts explanation"
                retrieved_chunks = self.retriever.retrieve(
                    query=enhanced_query,
                    course_name=course_name,
                    top_k=10
                )

            if not retrieved_chunks:
                return {
                    "audio_path": None,
                    "script": None,
                    "success": False,
                    "message": f"No content found for '{topic}'. Please try a different topic or the system will search the internet."
                }

            # Format context from retrieved chunks
            context = self.retriever.format_context(retrieved_chunks)

            # Generate conversational script
            logger.info("Generating podcast script...")
            script = self._create_conversational_script(
                context=context,
                topic=topic,
                style=style
            )

            if not script:
                return {
                    "audio_path": None,
                    "script": None,
                    "success": False,
                    "message": "Failed to generate podcast script."
                }

            # Generate audio from script
            logger.info("Generating podcast audio...")
            audio_path = await self._generate_audio(
                script=script,
                session_id=session_id,
                style=style
            )

            if not audio_path or not os.path.exists(audio_path):
                return {
                    "audio_path": None,
                    "script": script,
                    "success": False,
                    "message": "Failed to generate podcast audio. Script generated successfully."
                }

            return {
                "audio_path": audio_path,
                "script": script,
                "success": True,
                "message": "Podcast generated successfully!"
            }

        except Exception as e:
            logger.error(f"Error generating podcast: {e}", exc_info=True)
            return {
                "audio_path": None,
                "script": None,
                "success": False,
                "message": f"Error generating podcast: {str(e)}"
            }

    def cleanup_audio(self, audio_path: str):
        """
        Clean up temporary audio file.

        Args:
            audio_path: Path to audio file to delete
        """
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Cleaned up audio file: {audio_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup audio file {audio_path}: {e}")


def run_async_podcast_generation(topic: str, course_name: str, session_id: str, style: str = "conversational") -> Dict[str, Any]:
    """
    Synchronous wrapper for async podcast generation.

    Args:
        topic: The topic for the podcast
        course_name: Name of the course
        session_id: Session ID for unique file naming
        style: Style of podcast (conversational or interview)

    Returns:
        Dictionary with generation results
    """
    generator = PodcastGenerator()

    # Create new event loop for this thread
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            generator.generate_podcast(topic, course_name, session_id, style)
        )
        return result
    finally:
        # Don't close the loop as it might be used by other parts of the application
        pass
