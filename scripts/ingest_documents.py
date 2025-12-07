"""Script to ingest course documents into Pinecone vector store.
Supports PDF files and VTT transcript files, with optional module structure."""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieval.document_loader import MultimodalPDFLoader
from retrieval.vtt_loader import VTTLoader
from retrieval.vector_store import PineconeVectorStore
from config.settings import COURSES_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_course_name_from_folder(folder_name: str) -> str:
    """Convert folder name to course name format."""
    # Keep folder name as is, or normalize if needed
    return folder_name


def process_file(file_path: Path, course_name: str, module_name: str, vector_store: PineconeVectorStore):
    """
    Process a single file (PDF or VTT) and ingest into vector store.
    
    Args:
        file_path: Path to the file
        course_name: Name of the course
        module_name: Optional module name
        vector_store: Vector store instance
    """
    file_ext = file_path.suffix.lower()
    
    try:
        if file_ext == '.pdf':
            logger.info(f"Processing PDF: {file_path.name} for course {course_name}" + (f", module {module_name}" if module_name else ""))
            loader = MultimodalPDFLoader(
                course_name=course_name,
                document_path=str(file_path),
                module_name=module_name
            )
        elif file_ext == '.vtt':
            logger.info(f"Processing VTT transcript: {file_path.name} for course {course_name}" + (f", module {module_name}" if module_name else ""))
            loader = VTTLoader(
                course_name=course_name,
                document_path=str(file_path),
                module_name=module_name
            )
        else:
            logger.warning(f"Unsupported file type: {file_ext} for file {file_path.name}")
            return 0, 0
        
        documents = loader.load()
        
        if documents:
            vector_store.upsert_documents(documents)
            logger.info(f"✓ Ingested {len(documents)} chunks from {file_path.name}")
            return 1, len(documents)
        else:
            logger.warning(f"No chunks extracted from {file_path.name}")
            return 0, 0
            
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        return 0, 0


def ingest_course_documents():
    """Ingest all documents from courses directory, supporting modules and multiple file types."""
    logger.info("Starting document ingestion process...")
    
    courses_dir = Path(COURSES_PATH)
    
    if not courses_dir.exists():
        logger.error(f"Courses directory not found: {COURSES_PATH}")
        return
    
    vector_store = PineconeVectorStore()
    
    total_documents = 0
    total_chunks = 0
    
    # Iterate through course folders
    for course_folder in courses_dir.iterdir():
        if not course_folder.is_dir():
            continue
        
        course_name = get_course_name_from_folder(course_folder.name)
        logger.info(f"Processing course: {course_name}")
        
        # Check if course has modules (subfolders) or direct files
        subfolders = [f for f in course_folder.iterdir() if f.is_dir()]
        pdf_files = list(course_folder.glob("*.pdf"))
        vtt_files = list(course_folder.glob("*.vtt"))
        
        # If there are subfolders, assume they are modules
        if subfolders:
            logger.info(f"Course {course_name} has {len(subfolders)} modules")
            
            # Process each module
            for module_folder in subfolders:
                module_name = module_folder.name
                logger.info(f"Processing module: {module_name}")
                
                # Find PDF and VTT files in module folder
                module_pdfs = list(module_folder.glob("*.pdf"))
                module_vtts = list(module_folder.glob("*.vtt"))
                
                # Process PDFs in module
                for pdf_file in module_pdfs:
                    docs, chunks = process_file(pdf_file, course_name, module_name, vector_store)
                    total_documents += docs
                    total_chunks += chunks
                
                # Process VTT files in module
                for vtt_file in module_vtts:
                    docs, chunks = process_file(vtt_file, course_name, module_name, vector_store)
                    total_documents += docs
                    total_chunks += chunks
        
        # Also process files directly in course folder (for courses without modules)
        if pdf_files or vtt_files:
            logger.info(f"Processing files directly in course folder (no modules)")
            
            # Process PDFs
            for pdf_file in pdf_files:
                docs, chunks = process_file(pdf_file, course_name, None, vector_store)
                total_documents += docs
                total_chunks += chunks
            
            # Process VTT files
            for vtt_file in vtt_files:
                docs, chunks = process_file(vtt_file, course_name, None, vector_store)
                total_documents += docs
                total_chunks += chunks
        
        # If no files found at all
        if not subfolders and not pdf_files and not vtt_files:
            logger.warning(f"No PDF or VTT files found in {course_folder}")
    
    logger.info(
        f"Ingestion complete! Processed {total_documents} documents "
        f"with {total_chunks} total chunks."
    )


if __name__ == "__main__":
    ingest_course_documents()
