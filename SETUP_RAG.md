# RAG System Setup Guide

This guide will help you set up and use the PRISM RAG system with Pinecone.

## Prerequisites

1. **Environment Variables**: Make sure your `.env` file contains:
   ```
   OPENAI_API_KEY=your_openai_key
   PINECONE_API_KEY=your_pinecone_key
   PINECONE_ENVIRONMENT=us-east-1
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Setup Steps

### 1. Reset Vector Store (Optional - if you need to start fresh)

If you need to delete all existing vectors and recreate the index:

```bash
python scripts/reset_vector_store.py --confirm
```

**WARNING:** This will delete ALL vectors in the Pinecone index. Only run this if you want to start completely fresh.

### 2. Ingest Documents

Before using the app, you need to ingest your course documents into Pinecone:

```bash
python scripts/ingest_documents.py
```

This script will:
- Scan the `courses/` directory
- Process all PDF files in each course folder
- Extract text, tables, images, and other multimodal content
- **Tables**: Extracted using pdfplumber (more reliable)
- **Figures**: Detected and preserved with context
- **Text**: Extracted with page numbers
- Create embeddings using `text-embedding-3-large`
- Store everything in Pinecone with metadata (course name, page number, document name, type)

**Note:** Tables and figures are NOT chunked - they are kept intact to preserve context.

### 3. Run the Streamlit App

```bash
streamlit run app.py
```

### 4. Using the App

1. **Select Course**: Choose "Neuroquest" (or any course from the dropdown)
2. **Fill User Context**: Enter Student ID, Degree, and Major
3. **Start Session**: Click "Start PRISM Session"
4. **Ask Questions**: Type questions about the course material

The system will:
- Retrieve relevant chunks from Pinecone filtered by course name
- Generate responses using GPT-4o
- Include citations with page numbers and document names

## Course Structure

Your courses should be organized like this:

```
courses/
├── Neuroquest/
│   └── NeuroQuest_ Paper.pdf
├── Course_Name_2/
│   └── document.pdf
└── ...
```

The folder name becomes the course name used in the system.

## Configuration

### Prompts Configuration

Prompts and settings are stored in `config/prompts.yaml`. You can customize:
- System prompts for different response types
- User prompt templates
- Response settings (temperature, max_tokens)
- Document processing settings (chunk sizes, etc.)

### Resetting Vector Store

If you need to recreate the vector store (e.g., after improving extraction):

1. **Delete and recreate index:**
   ```bash
   python scripts/reset_vector_store.py --confirm
   ```

2. **Re-ingest documents:**
   ```bash
   python scripts/ingest_documents.py
   ```

## Troubleshooting

### Tables/Figures not detected correctly
- Make sure you've run the reset script and re-ingested: `python scripts/reset_vector_store.py --confirm && python scripts/ingest_documents.py`
- Check the ingestion logs to see how many tables/figures were found
- The system now uses pdfplumber for tables (more reliable) and preserves them intact

### No results found
- Make sure documents have been ingested: `python scripts/ingest_documents.py`
- Check that the course name matches the folder name exactly
- Verify Pinecone index exists and has data

### Import errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Check that `.env` file has all required keys

### Pinecone errors
- Verify your Pinecone API key is correct
- Check that the index name matches in `.env` (default: `prism-course-materials`)

### UI white box issue
- This has been fixed by removing the chat-container styling
- If you still see issues, clear your browser cache

