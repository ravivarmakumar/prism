"""Test script for MongoDB Atlas connection."""

import os
import sys
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import certifi

# Load environment variables from .env file
load_dotenv()

def test_mongo_connection():
    """Test MongoDB connection and insert a test document."""
    
    # Get MongoDB URI from environment variable
    mongodb_uri = os.getenv("MONGODB_URI")
    
    if not mongodb_uri:
        print("ERROR: MONGODB_URI environment variable not set.")
        print("Please set it in your .env file or using:")
        print('export MONGODB_URI="mongodb+srv://prism_user:YOUR_PASSWORD@prismtest.ffvupey.mongodb.net/?retryWrites=true&w=majority&appName=PRISMTEST"')
        sys.exit(1)
    
    print(f"Connecting to MongoDB Atlas...")
    print(f"URI: {mongodb_uri.split('@')[0]}@***")  # Hide password in output
    
    try:
        # Create client with connection timeout and SSL certificate bundle
        client = MongoClient(
            mongodb_uri,
            serverSelectionTimeoutMS=10000,  # 10 second timeout
            connectTimeoutMS=10000,
            tlsCAFile=certifi.where()  # Use certifi's certificate bundle
        )
        
        # Test connection by pinging
        print("\nPinging MongoDB...")
        client.admin.command('ping')
        print("✓ Connection successful!")
        
        # Get database and collection
        db = client["prism"]
        collection = db["interactions"]
        
        # Insert a test document
        print("\nInserting test document...")
        test_doc = {
            "student_id": "test_student",
            "degree": "Bachelor of Science",
            "major": "Computer Science",
            "course": "Test Course",
            "source_type": "course",
            "question": "This is a test question",
            "response_1": "This is a test response",
            "score_1": 0.85,
            "created_at": datetime.now(timezone.utc)
        }
        
        result = collection.insert_one(test_doc)
        inserted_id = result.inserted_id
        print(f"✓ Test document inserted successfully!")
        print(f"  Inserted ID: {inserted_id}")
        
        # Verify the document was inserted
        print("\nVerifying document...")
        retrieved = collection.find_one({"_id": inserted_id})
        if retrieved:
            print("✓ Document retrieved successfully!")
            print(f"  Student ID: {retrieved.get('student_id')}")
            print(f"  Question: {retrieved.get('question')}")
            print(f"  Score: {retrieved.get('score_1')}")
        else:
            print("✗ Failed to retrieve document")
            sys.exit(1)
        
        # Clean up test document (optional)
        print("\nCleaning up test document...")
        collection.delete_one({"_id": inserted_id})
        print("✓ Test document deleted")
        
        print("\n✓ All tests passed! MongoDB connection is working correctly.")
        return True
        
    except ConnectionFailure as e:
        print(f"\n✗ Connection failed: {e}")
        print("Please check:")
        print("  1. Your internet connection")
        print("  2. MongoDB Atlas cluster is running")
        print("  3. IP address is whitelisted in MongoDB Atlas")
        print("  4. Username and password are correct")
        sys.exit(1)
        
    except ServerSelectionTimeoutError as e:
        print(f"\n✗ Server selection timeout: {e}")
        print("Please check:")
        print("  1. Your internet connection")
        print("  2. MongoDB Atlas cluster is running")
        print("  3. Network firewall settings")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_mongo_connection()
