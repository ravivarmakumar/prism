"""VTT (WebVTT) transcript loader for course materials."""

import os
import re
from typing import List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class VTTLoader:
    """Loads VTT (WebVTT) transcript files with timestamp extraction."""
    
    def __init__(self, course_name: str, document_path: str, module_name: str = None):
        """
        Initialize the VTT loader.
        
        Args:
            course_name: Name of the course
            document_path: Path to the VTT file
            module_name: Optional module name
        """
        self.course_name = course_name
        self.document_path = document_path
        self.document_name = Path(document_path).stem
        self.module_name = module_name
        
        if not os.path.exists(document_path):
            raise FileNotFoundError(f"Document not found: {document_path}")
    
    def parse_vtt(self) -> List[Dict[str, Any]]:
        """
        Parse VTT file and extract transcript chunks with timestamps.
        
        Returns:
            List of transcript chunks with metadata
        """
        chunks = []
        
        try:
            with open(self.document_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # VTT format: timestamp lines followed by text
            # Pattern: HH:MM:SS.mmm --> HH:MM:SS.mmm (or variations)
            timestamp_pattern = r'(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})'
            
            lines = content.split('\n')
            current_timestamp = None
            current_text = []
            segment_index = 0
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines and WEBVTT header
                if not line or line.startswith('WEBVTT') or line.startswith('NOTE'):
                    continue
                
                # Check if line is a timestamp
                timestamp_match = re.match(timestamp_pattern, line)
                if timestamp_match:
                    # Save previous segment if exists
                    if current_text and current_timestamp:
                        text_content = ' '.join(current_text).strip()
                        if text_content:
                            chunks.append({
                                "content": text_content,
                                "timestamp": current_timestamp,
                                "segment_index": segment_index,
                                "type": "transcript",
                                "course_name": self.course_name,
                                "module_name": self.module_name,
                                "document_name": self.document_name
                            })
                            segment_index += 1
                    
                    # Extract start timestamp
                    start_hour, start_min, start_sec, start_ms = timestamp_match.groups()[:4]
                    current_timestamp = f"{start_hour}:{start_min}:{start_sec}"
                    current_text = []
                
                # Check if line is speaker name (usually in brackets or after timestamp)
                elif line.startswith('<v ') or line.startswith('['):
                    # Extract speaker name if present
                    speaker_match = re.search(r'<v\s+([^>]+)>|\[([^\]]+)\]', line)
                    if speaker_match:
                        speaker = speaker_match.group(1) or speaker_match.group(2)
                        # Remove speaker tags and get text
                        text = re.sub(r'<v\s+[^>]+>|\[[^\]]+\]', '', line).strip()
                        if text:
                            current_text.append(f"[{speaker}]: {text}")
                    else:
                        # Just text with speaker tag removed
                        text = re.sub(r'<[^>]+>', '', line).strip()
                        if text:
                            current_text.append(text)
                
                # Regular text line
                elif current_timestamp and line:
                    # Remove any remaining HTML-like tags
                    text = re.sub(r'<[^>]+>', '', line).strip()
                    if text:
                        current_text.append(text)
            
            # Add last segment
            if current_text and current_timestamp:
                text_content = ' '.join(current_text).strip()
                if text_content:
                    chunks.append({
                        "content": text_content,
                        "timestamp": current_timestamp,
                        "segment_index": segment_index,
                        "type": "transcript",
                        "course_name": self.course_name,
                        "module_name": self.module_name,
                        "document_name": self.document_name
                    })
            
            logger.info(f"Parsed {len(chunks)} transcript segments from {self.document_name}")
            
        except Exception as e:
            logger.error(f"Error parsing VTT file: {e}", exc_info=True)
            raise
        
        return chunks
    
    def load(self, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Main loading method for VTT files.
        
        Args:
            chunk_size: Size of text chunks (in words)
            overlap: Overlap between chunks (in words)
            
        Returns:
            List of document chunks with metadata
        """
        logger.info(f"Loading VTT transcript: {self.document_path}")
        
        # Parse VTT file
        segments = self.parse_vtt()
        
        if not segments:
            logger.warning(f"No segments extracted from {self.document_path}")
            return []
        
        # Chunk segments if needed (combine multiple segments into chunks)
        chunked_docs = []
        current_chunk = []
        current_chunk_words = 0
        chunk_index = 0
        
        for segment in segments:
            segment_text = segment["content"]
            segment_words = segment_text.split()
            segment_word_count = len(segment_words)
            
            # If adding this segment would exceed chunk size, save current chunk
            if current_chunk_words + segment_word_count > chunk_size and current_chunk:
                # Combine segments in current chunk
                combined_text = ' '.join([s["content"] for s in current_chunk])
                first_timestamp = current_chunk[0]["timestamp"]
                last_timestamp = current_chunk[-1]["timestamp"]
                
                chunked_docs.append({
                    "content": combined_text,
                    "timestamp": f"{first_timestamp} - {last_timestamp}",
                    "type": "transcript",
                    "course_name": self.course_name,
                    "module_name": self.module_name,
                    "document_name": self.document_name,
                    "chunk_index": chunk_index,
                    "segment_count": len(current_chunk)
                })
                
                # Start new chunk with overlap
                overlap_segments = []
                overlap_words = 0
                for s in reversed(current_chunk):
                    seg_words = s["content"].split()
                    if overlap_words + len(seg_words) <= overlap:
                        overlap_segments.insert(0, s)
                        overlap_words += len(seg_words)
                    else:
                        break
                
                current_chunk = overlap_segments
                current_chunk_words = overlap_words
                chunk_index += 1
            
            # Add segment to current chunk
            current_chunk.append(segment)
            current_chunk_words += segment_word_count
        
        # Add final chunk
        if current_chunk:
            combined_text = ' '.join([s["content"] for s in current_chunk])
            first_timestamp = current_chunk[0]["timestamp"]
            last_timestamp = current_chunk[-1]["timestamp"]
            
            chunked_docs.append({
                "content": combined_text,
                "timestamp": f"{first_timestamp} - {last_timestamp}",
                "type": "transcript",
                "course_name": self.course_name,
                "module_name": self.module_name,
                "document_name": self.document_name,
                "chunk_index": chunk_index,
                "segment_count": len(current_chunk)
            })
        
        logger.info(f"Loaded {len(chunked_docs)} chunks from {self.document_name}")
        
        return chunked_docs

