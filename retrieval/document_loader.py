"""Multimodal PDF document loader for course materials."""

import os
from typing import List, Dict, Any
from pathlib import Path
import pdfplumber
from unstructured.partition.pdf import partition_pdf
import logging
import yaml

logger = logging.getLogger(__name__)


class MultimodalPDFLoader:
    """Loads PDFs with multimodal content extraction."""
    
    def __init__(self, course_name: str, document_path: str):
        """
        Initialize the PDF loader.
        
        Args:
            course_name: Name of the course (folder name)
            document_path: Path to the PDF file
        """
        self.course_name = course_name
        self.document_path = document_path
        self.document_name = Path(document_path).stem
        
        if not os.path.exists(document_path):
            raise FileNotFoundError(f"Document not found: {document_path}")
        
        # Load config
        config_path = Path(__file__).parent.parent / "config" / "prompts.yaml"
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def extract_tables_with_pdfplumber(self) -> List[Dict[str, Any]]:
        """Extract tables using pdfplumber (more reliable for tables)."""
        table_chunks = []
        
        try:
            with pdfplumber.open(self.document_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(tables):
                        if table:
                            # Convert table to markdown-like format
                            table_text = "TABLE:\n"
                            for row in table:
                                if row:
                                    table_text += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
                            
                            table_chunks.append({
                                "content": f"Table {table_idx + 1} on page {page_num}:\n{table_text}",
                                "page_number": page_num,
                                "type": "table",
                                "course_name": self.course_name,
                                "document_name": self.document_name,
                                "table_index": table_idx + 1
                            })
        except Exception as e:
            logger.error(f"Error extracting tables with pdfplumber: {e}")
        
        return table_chunks
    
    def extract_table_references_from_text(self, text_chunks: List[Dict]) -> List[Dict[str, Any]]:
        """Extract table references from text chunks."""
        import re
        table_chunks = []
        
        for chunk in text_chunks:
            text = chunk["content"]
            page_num = chunk["page_number"]
            
            # Find all table references (Table 1, Tab. 2, etc.)
            table_patterns = [
                r'Table\s+(\d+)',
                r'Tab\.\s*(\d+)',
                r'TAB\.\s*(\d+)',
                r'TABLE\s+(\d+)'
            ]
            
            found_tables = set()
            for pattern in table_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    table_num = match.group(1)
                    found_tables.add(table_num)
            
            # If tables found, create a dedicated chunk
            if found_tables:
                table_text = f"Tables mentioned on page {page_num}: {', '.join(sorted(found_tables, key=int))}\n"
                # Get context around table mentions - capture more text for captions
                for table_num in found_tables:
                    # Find a larger context around table mentions (captions are usually after)
                    # Look for "Table X" and capture up to 3 sentences after
                    table_ref = re.search(
                        rf'(?:Table|Tab\.|TAB\.|TABLE)\s*{table_num}[^.]*(?:\.[^.]*){0,3}',
                        text,
                        re.IGNORECASE | re.DOTALL
                    )
                    if table_ref:
                        table_text += f"Table {table_num}: {table_ref.group(0)}\n"
                
                table_chunks.append({
                    "content": table_text + f"\nFull page context:\n{text[:800]}",  # Include more context
                    "page_number": page_num,
                    "type": "table",
                    "course_name": self.course_name,
                    "document_name": self.document_name,
                    "table_numbers": list(found_tables)
                })
        
        return table_chunks
    
    def extract_text_with_pages(self) -> List[Dict[str, Any]]:
        """Extract text with page numbers using pdfplumber - captures ALL text including figure/table references."""
        chunks = []
        
        try:
            with pdfplumber.open(self.document_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        # Include ALL text - don't filter, let it contain figure/table references
                        chunks.append({
                            "content": text.strip(),
                            "page_number": page_num,
                            "type": "text",  # Keep as text - contains all references
                            "course_name": self.course_name,
                            "document_name": self.document_name
                        })
        except Exception as e:
            logger.error(f"Error extracting text with pdfplumber: {e}")
        
        return chunks
    
    def extract_figures_from_text(self, text_chunks: List[Dict]) -> List[Dict[str, Any]]:
        """Extract figure references from text chunks with improved caption extraction."""
        import re
        figure_chunks = []
        
        for chunk in text_chunks:
            text = chunk["content"]
            page_num = chunk["page_number"]
            
            # Find all figure references (Figure 1, Fig. 2, etc.)
            figure_patterns = [
                r'Figure\s+(\d+)',
                r'Fig\.\s*(\d+)',
                r'FIG\.\s*(\d+)',
                r'FIGURE\s+(\d+)'
            ]
            
            found_figures = set()
            for pattern in figure_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    fig_num = match.group(1)
                    found_figures.add(fig_num)
            
            # If figures found, create a dedicated chunk
            if found_figures:
                figure_text = f"Figures mentioned on page {page_num}: {', '.join(sorted(found_figures, key=int))}\n"
                # Get context around figure mentions - capture more text for captions
                for fig_num in found_figures:
                    # Look for "Figure X" and capture up to 3 sentences after (captions are usually after)
                    # Also look for "Figure X:" pattern which often precedes captions
                    fig_ref = re.search(
                        rf'(?:Figure|Fig\.|FIG\.|FIGURE)\s*{fig_num}[:\.]?\s*[^.]*(?:\.[^.]*){0,3}',
                        text,
                        re.IGNORECASE | re.DOTALL
                    )
                    if fig_ref:
                        # Clean up the match
                        caption = fig_ref.group(0).strip()
                        figure_text += f"Figure {fig_num}: {caption}\n"
                    else:
                        # Fallback: just find the reference
                        fig_ref_simple = re.search(
                            rf'(?:Figure|Fig\.|FIG\.|FIGURE)\s*{fig_num}[^.]*\.',
                            text,
                            re.IGNORECASE
                        )
                        if fig_ref_simple:
                            figure_text += f"Figure {fig_num}: {fig_ref_simple.group(0)}\n"
                
                figure_chunks.append({
                    "content": figure_text + f"\nFull page context:\n{text[:800]}",  # Include more context
                    "page_number": page_num,
                    "type": "figure",
                    "course_name": self.course_name,
                    "document_name": self.document_name,
                    "figure_numbers": list(found_figures)
                })
        
        return figure_chunks
    
    def extract_multimodal_content(self) -> List[Dict[str, Any]]:
        """Extract multimodal content using unstructured and pdfplumber."""
        all_chunks = []
        
        # First, extract ALL text (this contains figure/table references)
        logger.info("Extracting all text with pdfplumber...")
        text_chunks = self.extract_text_with_pages()
        all_chunks.extend(text_chunks)
        logger.info(f"Extracted text from {len(text_chunks)} pages")
        
        # Extract tables using pdfplumber
        logger.info("Extracting tables with pdfplumber...")
        table_chunks = self.extract_tables_with_pdfplumber()
        all_chunks.extend(table_chunks)
        logger.info(f"Found {len(table_chunks)} tables with pdfplumber")
        
        # Extract table references from text (in case pdfplumber missed some)
        logger.info("Extracting table references from text...")
        table_ref_chunks = self.extract_table_references_from_text(text_chunks)
        all_chunks.extend(table_ref_chunks)
        logger.info(f"Found references to {len(table_ref_chunks)} table-containing pages")
        
        # Extract figure references from text
        logger.info("Extracting figure references from text...")
        figure_chunks = self.extract_figures_from_text(text_chunks)
        all_chunks.extend(figure_chunks)
        logger.info(f"Found references to {len(figure_chunks)} figure-containing pages")
        
        # Also try unstructured for additional content (but don't rely on it)
        try:
            logger.info("Trying unstructured for additional content...")
            elements = partition_pdf(
                filename=self.document_path,
                strategy="hi_res",
                infer_table_structure=True,
                extract_images_in_pdf=True,
                include_page_breaks=True
            )
            
            current_page = 1
            unstructured_chunks = []
            
            for element in elements:
                if hasattr(element, 'metadata') and element.metadata.page_number:
                    current_page = element.metadata.page_number
                
                element_text = str(element).strip()
                if not element_text:
                    continue
                
                element_category = getattr(element, 'category', 'text')
                
                # Skip tables (already extracted with pdfplumber)
                if element_category == "Table":
                    continue
                
                # Only add if it's a figure/image and we haven't seen it
                if element_category in ["Figure", "Image"]:
                    chunk_data = {
                        "content": f"Figure on page {current_page}: {element_text}",
                        "page_number": current_page,
                        "type": "figure",
                        "course_name": self.course_name,
                        "document_name": self.document_name
                    }
                    if hasattr(element.metadata, 'image_base64'):
                        chunk_data["image_base64"] = element.metadata.image_base64
                    unstructured_chunks.append(chunk_data)
            
            # Add unstructured chunks (they might have additional info)
            all_chunks.extend(unstructured_chunks)
            logger.info(f"Added {len(unstructured_chunks)} additional chunks from unstructured")
        
        except Exception as e:
            logger.warning(f"Error with unstructured extraction: {e}. Continuing with pdfplumber results.")
        
        return all_chunks
    
    def chunk_documents(
        self, 
        chunks: List[Dict], 
        chunk_size: int = 1000, 
        overlap: int = 200
    ) -> List[Dict]:
        """Chunk documents with overlap, preserving tables and figures."""
        chunked_docs = []
        
        doc_config = self.config.get('document_processing', {})
        table_chunk_size = doc_config.get('table_chunk_size', 2000)
        figure_chunk_size = doc_config.get('figure_chunk_size', 1500)
        
        for chunk in chunks:
            content = chunk["content"]
            chunk_type = chunk.get("type", "text")
            
            # Don't chunk tables or figures - keep them intact
            if chunk_type == "table":
                # Tables can be from pdfplumber extraction or text references
                chunked_docs.append({
                    **chunk,
                    "chunk_index": 0
                })
                continue
            
            if chunk_type in ["figure", "image", "figure_context"]:
                # Don't chunk figures - keep them intact
                chunked_docs.append({
                    **chunk,
                    "chunk_index": 0
                })
                continue
            
            # For regular text, chunk normally
            words = content.split()
            
            # If content is shorter than chunk_size, keep as is
            if len(words) <= chunk_size:
                chunked_docs.append({
                    **chunk,
                    "chunk_index": 0
                })
                continue
            
            # Split into chunks with overlap
            for i in range(0, len(words), chunk_size - overlap):
                chunk_text = " ".join(words[i:i + chunk_size])
                
                chunked_docs.append({
                    **chunk,
                    "content": chunk_text,
                    "chunk_index": i // (chunk_size - overlap)
                })
        
        return chunked_docs
    
    def load(self, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Main loading method.
        
        Args:
            chunk_size: Size of text chunks
            overlap: Overlap between chunks
            
        Returns:
            List of document chunks with metadata
        """
        logger.info(f"Loading document: {self.document_path}")
        
        # Extract multimodal content
        chunks = self.extract_multimodal_content()
        
        # Count what we found
        table_count = len([c for c in chunks if c.get('type') == 'table'])
        figure_count = len([c for c in chunks if c.get('type') in ['figure', 'image']])
        text_count = len(chunks) - table_count - figure_count
        logger.info(f"Extracted: {table_count} table chunks (from pdfplumber + text references), {figure_count} figure chunks, {text_count} text chunks")
        
        # Chunk the documents (preserving tables/figures)
        chunked_docs = self.chunk_documents(chunks, chunk_size, overlap)
        
        logger.info(f"Loaded {len(chunked_docs)} chunks from {self.document_name}")
        
        return chunked_docs
