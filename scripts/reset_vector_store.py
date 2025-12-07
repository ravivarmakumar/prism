"""Script to delete and recreate Pinecone vector store."""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieval.vector_store import PineconeVectorStore
from config.settings import PINECONE_INDEX_NAME

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def reset_vector_store():
    """Delete existing Pinecone index and recreate it."""
    logger.info("Starting vector store reset process...")
    
    try:
        # Initialize Pinecone client
        from pinecone import Pinecone
        from config.settings import PINECONE_API_KEY, EMBEDDING_DIMENSION
        from pinecone import ServerlessSpec
        
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Check if index exists
        existing_indexes = pc.list_indexes().names()
        
        if PINECONE_INDEX_NAME in existing_indexes:
            logger.info(f"Deleting existing index: {PINECONE_INDEX_NAME}")
            pc.delete_index(PINECONE_INDEX_NAME)
            logger.info(f"Index {PINECONE_INDEX_NAME} deleted successfully")
        else:
            logger.info(f"Index {PINECONE_INDEX_NAME} does not exist. Nothing to delete.")
        
        # Recreate the index
        logger.info(f"Creating new index: {PINECONE_INDEX_NAME}")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        logger.info(f"Index {PINECONE_INDEX_NAME} created successfully")
        
        logger.info("Vector store reset complete! You can now run ingest_documents.py to populate it.")
        
    except Exception as e:
        logger.error(f"Error resetting vector store: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reset Pinecone vector store")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that you want to delete all existing vectors"
    )
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("WARNING: This will delete ALL vectors in the Pinecone index!")
        print("To confirm, run: python scripts/reset_vector_store.py --confirm")
        sys.exit(1)
    
    reset_vector_store()

