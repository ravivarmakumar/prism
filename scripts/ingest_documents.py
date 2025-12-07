"""Script to ingest course documents into Pinecone vector store."""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieval.document_loader import MultimodalPDFLoader
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


def ingest_course_documents():
    """Ingest all PDFs from courses directory."""
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
        
        # Find all PDFs in course folder
        pdf_files = list(course_folder.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {course_folder}")
            continue
        
        for pdf_file in pdf_files:
            try:
                logger.info(f"Processing {pdf_file.name} for course {course_name}...")
                
                loader = MultimodalPDFLoader(
                    course_name=course_name,
                    document_path=str(pdf_file)
                )
                
                documents = loader.load()
                
                if documents:
                    vector_store.upsert_documents(documents)
                    total_documents += 1
                    total_chunks += len(documents)
                    logger.info(
                        f"✓ Ingested {len(documents)} chunks from {pdf_file.name}"
                    )
                else:
                    logger.warning(f"No chunks extracted from {pdf_file.name}")
                    
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                continue
    
    logger.info(
        f"Ingestion complete! Processed {total_documents} documents "
        f"with {total_chunks} total chunks."
    )


if __name__ == "__main__":
    ingest_course_documents()

