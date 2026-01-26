"""Podcast Generator - Creates conversational podcasts from course content."""

import logging
import json
import asyncio
import tempfile
import os
import re
from typing import Dict, Any, Optional, List, Tuple
from openai import OpenAI
from config.settings import OPENAI_API_KEY, OPENAI_MODEL
from retrieval.retriever import CourseRetriever

logger = logging.getLogger(__name__)

# Try to import MCP client for fallback
MCP_AVAILABLE = False
mcp_manager = None
try:
    from config.mcp_client import mcp_manager
    MCP_AVAILABLE = True
    logger.info("MCP client available for fallback")
except ImportError:
    logger.info("MCP client not available - will use OpenAI TTS only")

# Try to import pydub and check if it works
PYDUB_AVAILABLE = False
try:
    from pydub import AudioSegment
    # Test if pydub can actually work (it needs ffmpeg for MP3)
    try:
        # Try a simple test to see if AudioSegment works
        test_segment = AudioSegment.empty()
        PYDUB_AVAILABLE = True
        logger.info("pydub imported successfully")
    except Exception as e:
        logger.warning(f"pydub imported but may not work properly: {e}")
        PYDUB_AVAILABLE = False
except ImportError as e:
    logger.warning(f"pydub not available: {e}. Audio combination may fail.")
    PYDUB_AVAILABLE = False


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
        style: str = "conversational",
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a conversational podcast script using LLM.

        Args:
            context: Retrieved course content
            topic: The topic for the podcast
            style: Style of podcast (always conversational)

        Returns:
            Formatted script for TTS generation
        """
        # Build personalization context
        personalization_note = ""
        if user_context:
            degree = user_context.get('degree', '')
            major = user_context.get('major', '')
            if degree or major:
                personalization_note = f"""
PERSONALIZATION: Tailor the content to the student's background:
- Degree Level: {degree}
- Major/Field: {major}
- Use examples and analogies relevant to their field of study
- Adjust complexity and terminology based on their degree level
- Connect concepts to applications in their major when possible
- Make the content relatable to their academic background"""
        
        style_instructions = {
            "conversational": """Create a natural, friendly conversation between two hosts discussing the topic.
- Host 1 (Alex): The primary explainer, knowledgeable and enthusiastic
- Host 2 (Sam): Asks clarifying questions, relates concepts to real-world examples
- Keep the tone casual but informative, like NotebookLM
- Use natural conversational fillers like "So...", "Right!", "That makes sense"
- Break down complex concepts into digestible parts
- Use analogies and examples to make content relatable"""
        }

        instruction = style_instructions.get(style, style_instructions["conversational"])
        if personalization_note:
            instruction += personalization_note

        system_prompt = f"""You are a podcast script writer. {instruction}

Format the script with clear speaker labels:
- Use "Alex:" and "Sam:" for conversational style
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

    def _parse_script(self, script: str, style: str = "conversational") -> List[Tuple[str, str]]:
        """
        Parse the script into speaker-dialogue pairs.
        
        Args:
            script: The podcast script with speaker labels
            style: Podcast style (always conversational now)
            
        Returns:
            List of (speaker, dialogue) tuples
        """
        lines = []
        # Only conversational style now
        # More flexible patterns: "Alex:", "Sam:", or variations
        patterns = [
            r'^(Alex|Sam):\s*(.+)$',  # Standard format
            r'^(Alex|Sam)\s*:\s*(.+)$',  # With spaces around colon
            r'^(Alex|Sam)\s+-\s*(.+)$',  # With dash
        ]
        speakers = ["Alex", "Sam"]
        
        current_speaker = None
        current_dialogue = []
        
        for line in script.split('\n'):
            line = line.strip()
            if not line:
                # Empty line - save current dialogue if any
                if current_speaker and current_dialogue:
                    dialogue_text = " ".join(current_dialogue)
                    if dialogue_text:
                        lines.append((current_speaker, dialogue_text))
                    current_dialogue = []
                continue
            
            # Try to match any pattern
            matched = False
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous dialogue if any
                    if current_speaker and current_dialogue:
                        dialogue_text = " ".join(current_dialogue)
                        if dialogue_text:
                            lines.append((current_speaker, dialogue_text))
                    
                    # Start new dialogue
                    speaker = match.group(1)
                    dialogue = match.group(2).strip() if len(match.groups()) >= 2 else ""
                    
                    # Normalize speaker name (always conversational)
                    if speaker.lower() in ["alex", "host 1"]:
                        current_speaker = "Alex"
                    elif speaker.lower() in ["sam", "host 2"]:
                        current_speaker = "Sam"
                    else:
                        # Default to first speaker if unknown
                        current_speaker = "Alex"
                    
                    current_dialogue = [dialogue] if dialogue else []
                    matched = True
                    break
            
            if not matched:
                # Continuation of current dialogue
                if current_speaker:
                    current_dialogue.append(line)
                else:
                    # No speaker identified yet, use default (Alex)
                    current_speaker = "Alex"
                    current_dialogue = [line]
        
        # Save last dialogue
        if current_speaker and current_dialogue:
            dialogue_text = " ".join(current_dialogue)
            if dialogue_text:
                lines.append((current_speaker, dialogue_text))
        
        return lines

    def _try_mcp_fallback(
        self,
        script: str,
        session_id: str,
        style: str,
        output_path: str
    ) -> Optional[str]:
        """
        Try to generate audio using MCP as fallback if OpenAI TTS failed.
        
        Args:
            script: The podcast script
            session_id: Session ID for unique file naming
            style: Podcast style
            output_path: Path to save the audio file
            
        Returns:
            Path to generated audio file or None if failed
        """
        if not MCP_AVAILABLE or not mcp_manager:
            logger.warning("MCP fallback not available")
            return None
        
        try:
            logger.info("Attempting MCP fallback for audio generation...")
            
            # Voice selection for MCP (always conversational)
            voice1 = "default"  # Alex (Host 1)
            voice2 = "default"  # Sam (Host 2)
            
            # Run async MCP call
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_path = loop.run_until_complete(
                    mcp_manager.generate_podcast_audio(
                        script=script,
                        voice1=voice1,
                        voice2=voice2,
                        output_path=output_path
                    )
                )
            finally:
                loop.close()
            
            if audio_path and os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                logger.info(f"MCP fallback succeeded: {audio_path} (size: {file_size} bytes)")
                return audio_path
            else:
                logger.error("MCP fallback failed - file not created")
                return None
                
        except Exception as e:
            logger.error(f"MCP fallback error: {e}", exc_info=True)
            return None

    def _generate_audio_segment(self, text: str, voice: str) -> Optional[bytes]:
        """
        Generate audio for a single text segment using OpenAI TTS.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Audio bytes or None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for audio generation")
            return None
        
        # Limit text length to avoid API errors (OpenAI TTS has a limit)
        max_length = 4096  # OpenAI TTS character limit
        if len(text) > max_length:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_length}")
            text = text[:max_length]
        
        try:
            logger.debug(f"Calling OpenAI TTS API with voice: {voice}, text length: {len(text)}")
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            if response and hasattr(response, 'content'):
                audio_bytes = response.content
                logger.debug(f"Successfully generated audio segment ({len(audio_bytes)} bytes)")
                return audio_bytes
            else:
                logger.error("OpenAI TTS API returned invalid response")
                return None
                
        except Exception as e:
            logger.error(f"Error generating audio segment with OpenAI TTS: {e}", exc_info=True)
            # Check for specific error types
            if "rate_limit" in str(e).lower():
                logger.error("Rate limit exceeded. Please wait and try again.")
            elif "invalid" in str(e).lower() or "bad_request" in str(e).lower():
                logger.error(f"Invalid request to OpenAI TTS API. Voice: {voice}, Text length: {len(text)}")
            return None

    def _generate_audio(
        self,
        script: str,
        session_id: str,
        style: str = "conversational"
    ) -> Optional[str]:
        """
        Generate audio from script using OpenAI TTS API.

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

            logger.info(f"Generating audio with OpenAI TTS API...")
            logger.info(f"Script length: {len(script)} characters")
            logger.info(f"Output path: {output_path}")

            # Voice selection based on style
            # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
            if style == "conversational":
                voice1 = "nova"  # Alex (Host 1) - friendly, warm
                voice2 = "echo"  # Sam (Host 2) - clear, engaging
            # Always conversational style
            voice1 = "nova"  # Alex (Host 1) - friendly, warm
            voice2 = "echo"  # Sam (Host 2) - clear, engaging

            # Parse script into speaker-dialogue pairs
            logger.info(f"Parsing script (first 200 chars): {script[:200]}...")
            script_lines = self._parse_script(script, style)
            
            if not script_lines:
                logger.error(f"No valid script lines found after parsing. Script preview: {script[:500]}")
                logger.error("Script might not be in the expected format. Expected format: 'Speaker: dialogue'")
                return None

            logger.info(f"Parsed {len(script_lines)} script segments")
            logger.info(f"First few segments: {script_lines[:3]}")

            # Generate audio for each segment and collect bytes
            audio_segments_bytes = []
            for i, (speaker, dialogue) in enumerate(script_lines):
                # Determine which voice to use based on speaker
                if style == "conversational":
                    voice = voice1 if speaker.lower() == "alex" else voice2
                else:
                    voice = voice1 if speaker.lower() == "host" else voice2
                
                logger.info(f"Generating audio for {speaker} (segment {i+1}/{len(script_lines)})...")
                logger.debug(f"Dialogue text (first 100 chars): {dialogue[:100]}...")
                
                try:
                    audio_bytes = self._generate_audio_segment(dialogue, voice)
                except Exception as e:
                    logger.error(f"Exception generating audio segment {i+1}: {e}", exc_info=True)
                    audio_bytes = None
                
                if audio_bytes:
                    audio_segments_bytes.append(audio_bytes)
                    logger.info(f"Successfully generated segment {i+1} ({len(audio_bytes)} bytes)")
                else:
                    logger.warning(f"Failed to generate audio for segment {i+1} (speaker: {speaker}, voice: {voice})")

            if not audio_segments_bytes:
                logger.error(f"No audio segments were generated successfully out of {len(script_lines)} script lines")
                logger.error("This might indicate an issue with OpenAI TTS API calls")
                return None

            # Combine all audio segments by concatenating MP3 bytes directly
            # OpenAI TTS generates MP3 files that can be concatenated if they have the same format
            logger.info(f"Combining {len(audio_segments_bytes)} audio segments by concatenating MP3 bytes...")
            
            try:
                # Simple concatenation: MP3 files from OpenAI TTS are typically compatible
                # We'll concatenate them directly without pydub/ffmpeg
                # This works because OpenAI TTS generates consistent MP3 format files
                combined_bytes = b''.join(audio_segments_bytes)
                
                # Write combined audio to file
                with open(output_path, 'wb') as f:
                    f.write(combined_bytes)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    file_size = os.path.getsize(output_path)
                    logger.info(f"Audio combined successfully: {output_path} (size: {file_size} bytes)")
                    logger.info("Note: Used direct MP3 byte concatenation. Audio should play correctly in Streamlit.")
                    return output_path
                else:
                    logger.error("Combined audio file not created or empty")
                    # Try MCP fallback if OpenAI TTS failed
                    return self._try_mcp_fallback(script, session_id, style, output_path)
                    
            except Exception as e:
                logger.error(f"Error combining audio segments: {e}", exc_info=True)
                # Try MCP fallback if OpenAI TTS failed
                return self._try_mcp_fallback(script, session_id, style, output_path)

        except Exception as e:
            logger.error(f"Error generating podcast audio: {e}", exc_info=True)
            return None

    async def generate_podcast(
        self,
        topic: str,
        course_name: str,
        session_id: str,
        style: str = "conversational",
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a podcast for a given topic.

        Args:
            topic: The topic/question for the podcast
            course_name: Name of the course
            session_id: Session ID for unique file naming
            style: Style of podcast (always conversational)

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

            # Generate conversational script with user context for personalization
            logger.info("Generating podcast script...")
            script = self._create_conversational_script(
                context=context,
                topic=topic,
                style=style,
                user_context=user_context
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
            try:
                audio_path = self._generate_audio(
                script=script,
                session_id=session_id,
                style=style
            )
            except Exception as e:
                logger.error(f"Exception during audio generation: {e}", exc_info=True)
                return {
                    "audio_path": None,
                    "script": script,
                    "success": False,
                    "message": f"Error generating audio: {str(e)}. Script was generated successfully."
                }

            if not audio_path or not os.path.exists(audio_path):
                # Provide more specific error message
                error_msg = "Failed to generate podcast audio. Script generated successfully."
                error_msg += " Please check the application logs for detailed error information."
                
                return {
                    "audio_path": None,
                    "script": script,
                    "success": False,
                    "message": error_msg
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


def run_async_podcast_generation(topic: str, course_name: str, session_id: str, style: str = "conversational", user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
            generator.generate_podcast(topic, course_name, session_id, style, user_context)
        )
        return result
    finally:
        # Don't close the loop as it might be used by other parts of the application
        pass
