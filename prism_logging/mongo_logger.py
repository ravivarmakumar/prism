"""MongoDB Atlas logging for PRISM interactions."""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import streamlit as st
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import certifi

logger = logging.getLogger(__name__)


@st.cache_resource
def get_mongo_client():
    """
    Get or create MongoDB client instance (cached by Streamlit).
    
    Returns:
        MongoClient instance or None if connection fails
    """
    try:
        # Try to get URI from Streamlit secrets first (production)
        try:
            mongodb_uri = st.secrets.get("MONGODB_URI")
        except (AttributeError, KeyError, FileNotFoundError):
            # Fall back to environment variable (local dev)
            mongodb_uri = os.getenv("MONGODB_URI")
        
        if not mongodb_uri:
            logger.warning("MONGODB_URI not found in secrets or environment variables. MongoDB logging disabled.")
            return None
        
        # Create client with connection timeout and SSL certificate bundle
        client = MongoClient(
            mongodb_uri,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
            tlsCAFile=certifi.where()  # Use certifi's certificate bundle
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info("MongoDB connection established successfully")
        return client
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.warning(f"MongoDB connection failed: {e}. Logging will be skipped.")
        return None
    except Exception as e:
        logger.error(f"Error initializing MongoDB client: {e}")
        return None


def get_collection():
    """
    Get MongoDB collection handle for interactions.
    
    Returns:
        Collection object or None if connection fails
    """
    try:
        client = get_mongo_client()
        if client is None:
            return None
        
        db = client["prism"]
        collection = db["interactions"]
        return collection
    except Exception as e:
        logger.error(f"Error getting MongoDB collection: {e}")
        return None


def log_interaction(payload: Dict[str, Any]) -> Optional[str]:
    """
    Log an interaction to MongoDB Atlas.
    
    Args:
        payload: Dictionary with interaction data containing:
            - student_id (str)
            - degree (str)
            - major (str)
            - course (str)
            - source_type (str): "course" or "web"
            - question (str)
            - response_1 (str)
            - score_1 (float)
            - response_2 (str, optional)
            - score_2 (float, optional)
            - response_3 (str, optional)
            - score_3 (float, optional)
            - created_at (datetime, optional): UTC timestamp (auto-added if not provided)
    
    Returns:
        Inserted document ID (str) or None if insertion fails
    """
    try:
        collection = get_collection()
        if collection is None:
            logger.warning("MongoDB collection not available. Skipping log.")
            return None
        
        # Ensure created_at is set (UTC timestamp)
        if "created_at" not in payload:
            payload["created_at"] = datetime.now(timezone.utc)
        elif isinstance(payload["created_at"], datetime):
            # Ensure timezone-aware
            if payload["created_at"].tzinfo is None:
                payload["created_at"] = payload["created_at"].replace(tzinfo=timezone.utc)
        
        # Remove None values for optional fields (MongoDB will not store them)
        # Keep fields that are explicitly None to maintain schema consistency
        clean_payload = {}
        for key, value in payload.items():
            if value is not None:
                clean_payload[key] = value
            # If value is None, we skip it (MongoDB won't store the field)
        
        # Insert document
        result = collection.insert_one(clean_payload)
        logger.info(f"Logged interaction to MongoDB: {result.inserted_id}")
        return str(result.inserted_id)
        
    except Exception as e:
        logger.error(f"Error logging interaction to MongoDB: {e}", exc_info=True)
        # Don't break the app - just log the error
        return None
