"""PPT/PPTX presentation loader for course materials.

Uses the unstructured library to extract text from PowerPoint files.
Supports .pptx (Office Open XML). Legacy .ppt may be supported if
unstructured[pptx] provides partition_ppt.
"""

import os
from typing import List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

try:
    from unstructured.partition.pptx import partition_pptx
except ImportError:
    partition_pptx = None

try:
    from unstructured.partition.ppt import partition_ppt
except ImportError:
    partition_ppt = None


class PPTLoader:
    """Loads PPT/PPTX files with slide-level extraction."""

    def __init__(self, course_name: str, document_path: str, module_name: str = None):
        """
        Initialize the PPT/PPTX loader.

        Args:
            course_name: Name of the course (folder name)
            document_path: Path to the PPT or PPTX file
            module_name: Optional module name
        """
        self.course_name = course_name
        self.document_path = document_path
        self.document_name = Path(document_path).stem
        self.module_name = module_name

        if not os.path.exists(document_path):
            raise FileNotFoundError(f"Document not found: {document_path}")

    def _partition_file(self) -> List:
        """Partition the presentation into elements using unstructured."""
        path = Path(self.document_path)
        suffix = path.suffix.lower()

        if suffix == ".pptx":
            if partition_pptx is None:
                raise ImportError(
                    "PPTX support requires unstructured[pptx]. "
                    "Install with: pip install 'unstructured[pptx]'"
                )
            return partition_pptx(filename=str(path))
        if suffix == ".ppt":
            if partition_ppt is not None:
                return partition_ppt(filename=str(path))
            raise ValueError(
                "Legacy .ppt format is not supported by the installed unstructured version. "
                "Please convert the file to .pptx (e.g. open and save as in PowerPoint)."
            )
        raise ValueError(f"Unsupported extension: {suffix}. Use .ppt or .pptx")

    def load(self, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Load the presentation and return chunks compatible with the vector store.

        Each slide's content is emitted as one or more chunks with page_number
        set to the slide number so existing vector store logic works unchanged.

        Args:
            chunk_size: Max words per chunk for long slides (unused if slides are short)
            overlap: Overlap in words between chunks (unused if no splitting)

        Returns:
            List of document chunks with content, page_number (slide), type, course_name,
            module_name, document_name, chunk_index.
        """
        logger.info(f"Loading presentation: {self.document_path}")

        try:
            elements = self._partition_file()
        except Exception as e:
            logger.error(f"Error partitioning presentation: {e}", exc_info=True)
            raise

        if not elements:
            logger.warning(f"No elements extracted from {self.document_path}")
            return []

        # Group elements by slide (page_number in metadata)
        slides: Dict[int, List[str]] = {}
        for element in elements:
            text = str(element).strip()
            if not text:
                continue
            page_num = 1
            if hasattr(element, "metadata") and element.metadata is not None:
                page_num = getattr(element.metadata, "page_number", None) or 1
            if page_num not in slides:
                slides[page_num] = []
            slides[page_num].append(text)

        # Build chunks: one chunk per slide (or split long slides by chunk_size)
        chunked_docs: List[Dict[str, Any]] = []
        for slide_num in sorted(slides.keys()):
            slide_text = "\n".join(slides[slide_num])
            if not slide_text.strip():
                continue

            words = slide_text.split()
            if len(words) <= chunk_size:
                chunked_docs.append({
                    "content": slide_text,
                    "page_number": slide_num,
                    "type": "slide",
                    "course_name": self.course_name,
                    "module_name": self.module_name,
                    "document_name": self.document_name,
                    "chunk_index": 0,
                })
                continue

            # Split long slide into chunks with overlap
            for i in range(0, len(words), chunk_size - overlap):
                chunk_words = words[i : i + chunk_size]
                chunk_text = " ".join(chunk_words)
                chunk_index = i // (chunk_size - overlap)
                chunked_docs.append({
                    "content": chunk_text,
                    "page_number": slide_num,
                    "type": "slide",
                    "course_name": self.course_name,
                    "module_name": self.module_name,
                    "document_name": self.document_name,
                    "chunk_index": chunk_index,
                })

        logger.info(f"Loaded {len(chunked_docs)} chunks from {self.document_name} ({len(slides)} slides)")
        return chunked_docs
