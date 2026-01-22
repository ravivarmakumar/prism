# PRISM - Agentic RAG-Based Learning System

PRISM: Personalized Retrieval-Integrated System for Multimodal Adaptive Learning

PRISM is an adaptive learning application designed for students, leveraging an agentic retrieval-augmented generation (RAG) system to answer questions based on course materials or internet search when necessary.

## Features

- **Course-Relevant Answers**: Generates responses based on course materials from vector store
- **Internet Search**: Uses Tavily API for questions related to course topics but not in materials
- **Query Classification**: Intelligently routes queries (course-relevant, out-of-scope, irrelevant)
- **Follow-up Questions**: Handles vague queries by asking clarifying questions
- **Response Evaluation**: Evaluates and refines responses using mathematical metrics
- **Personalization**: Tailors responses to student's academic level and major
- **Flashcard Generation**: Create study flashcards from course content on any topic
- **Podcast Generation**: Generate conversational-style podcasts (NotebookLM-like) from course content

## Setup

### 1. Prerequisites

For podcast generation, you need Node.js and npm installed:
- Node.js 18+ and npm (required for podcast TTS via MCP server)

Check if you have them installed:
```bash
node --version
npm --version
```

If not installed, download from [nodejs.org](https://nodejs.org/)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the `.env.example` file to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your:
- `OPENAI_API_KEY`: Your OpenAI API key
- `TAVILY_API_KEY`: Your Tavily API key for internet search

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Project Structure

```
PRISM Code/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── ui/                             # UI components
│   ├── styling.py                  # Theme and CSS styling
│   ├── sidebar.py                  # Sidebar components
│   ├── chat.py                     # Chat interface
│   └── session.py                  # Session management
├── config/                         # Configuration management
├── core/                           # Core agentic RAG logic
├── retrieval/                      # Vector store and retrieval
├── generation/                     # LLM and response generation
├── search/                         # Internet search integration
└── utils/                          # Utility functions
```

## Usage

### Basic Chat

1. Fill out the sidebar form with:
   - Student ID
   - Degree level
   - Major
   - Course

2. Click "Start PRISM Session"

3. Ask questions about your course material in the chat interface

### Generate Flashcards

1. Click the **➕** button next to the input field
2. Check **📚 Generate Flashcards**
3. Enter a topic (e.g., "Machine Learning")
4. Press Enter or click **➤**
5. View generated flashcards with sources
6. Click **Generate 5 More** for additional flashcards on the same topic

### Generate Podcasts

1. Click the **➕** button next to the input field
2. Check **🎙️ Generate Podcast**
3. Select style:
   - **Conversational**: NotebookLM-style dialogue between two hosts (default)
   - **Interview**: Interview format with host and expert
4. Enter a topic (e.g., "Neural Networks")
5. Press Enter or click **➤**
6. Wait for podcast generation (may take 1-2 minutes)
7. Use the audio player controls to play/pause/seek
8. Click **View Transcript** to see the dialogue script

**Note**: Podcasts are generated as temporary files and will be cleaned up after the session.

## Future Enhancements

- Knowledge graph integration
- Database support for session persistence
- Advanced evaluation metrics
- Multi-modal support

## License

© PRISM Adaptive Learning System 2025 (UNT Dissertation POC)
