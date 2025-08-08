# AskImmigrate 2.0 CLI Usage Guide 🇺🇸

## Overview

AskImmigrate 2.0 features a **session-aware multi-agent workflow** that remembers your conversation history and provides contextual, follow-up responses for immigration questions.

## Quick Start

### 1. Test the CLI (No API Key Required)
```bash
python backend/code/cli.py --test --question "what is f1?"
```

### 2. Get API Keys

#### Option A: Gemini API (Default - Free)
1. Visit [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign up for a free account
3. Create a new API key

#### Option B: GROQ API (Fast Alternative)
1. Visit [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign up for a free account
3. Create a new API key

#### Option C: OpenAI API
1. Visit [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create an account and add billing
3. Generate an API key

### 3. Set up Environment Variables

Create a `.env` file in the project root:
```bash
# Option A: Use Gemini (default, free tier)
GEMINI_API_KEY=your_gemini_api_key_here

# Option B: Use GROQ (fast alternative, free tier)
GROQ_API_KEY=your_groq_api_key_here

# Option C: Use OpenAI 
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Enable LangSmith tracing for debugging
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=AskImmigrate2.0
```

Or export environment variables:
```bash
export GEMINI_API_KEY=your_gemini_api_key_here
```

## 🚀 Multi-Agent Workflow (Recommended)

The `--agent` flag activates the **session-aware multi-agent system** with:
- **Manager Agent**: Strategic analysis and workflow coordination
- **Synthesis Agent**: Contextual response generation with session awareness
- **Reviewer Agent**: Quality control and validation
- **Session Management**: Conversation memory and follow-up detection

### Basic Usage

```bash
# Ask a question (creates new session automatically)
python backend/code/cli.py --agent -q "What is an F-1 visa?"

# Continue conversation with specific session
python backend/code/cli.py --agent -q "How do I extend it?" -s "my-immigration-session"

# Session-aware follow-up questions
python backend/code/cli.py --agent -q "What was my first question?" -s "my-immigration-session"
```

### Session Management

```bash
# List all your conversation sessions
python backend/code/cli.py --agent --list-sessions

# Continue existing conversation
python backend/code/cli.py --agent -q "Tell me about the fees" -s "what-is-f-1-visa-abc123"
```

## 📋 Command Options

| Option | Short | Description |
|--------|--------|-------------|
| `--question` | `-q` | Your immigration question (required) |
| `--session_id` | `-s` | Session ID to continue a conversation |
| `--agent` | | Use multi-agent workflow (recommended) |
| `--list-sessions` | | List all stored session IDs |
| `--test` | | Test mode (no API key required) |

## 🎯 Session-Aware Examples

### Immigration Consultation Flow
```bash
# Start new immigration consultation
python backend/code/cli.py --agent -q "I'm on F-1, can I work?" -s "my-consultation"

# Follow-up questions naturally build on context
python backend/code/cli.py --agent -q "How many hours per week?" -s "my-consultation"
python backend/code/cli.py --agent -q "What about off-campus work?" -s "my-consultation"
python backend/code/cli.py --agent -q "What was my original question?" -s "my-consultation"
```

### Visa Application Process
```bash
# Learn about visa process step-by-step
python backend/code/cli.py --agent -q "How do I apply for H-1B?" -s "h1b-process"
python backend/code/cli.py --agent -q "What documents do I need?" -s "h1b-process"
python backend/code/cli.py --agent -q "How much does it cost?" -s "h1b-process"
python backend/code/cli.py --agent -q "How long does processing take?" -s "h1b-process"
```

### Family Immigration Planning
```bash
# Plan family immigration strategy
python backend/code/cli.py --agent -q "Can I bring my spouse on F-2?" -s "family-planning"
python backend/code/cli.py --agent -q "Can they work?" -s "family-planning"
python backend/code/cli.py --agent -q "What if we have children?" -s "family-planning"
```

## 🔄 Session Features

### **Conversation Memory**
- Remembers all previous questions and answers
- Tracks topics and visa types discussed
- Maintains context across multiple CLI runs

### **Smart Follow-up Detection**
- Automatically detects when questions refer to previous conversation
- Handles pronouns like "it", "that", "this"
- Recognizes session references like "my first question", "what did I ask before"

### **Contextual Responses**
- Builds on previous answers
- References earlier conversation naturally
- Provides continuity across immigration topics

## 🛠️ Advanced Usage

### Custom Session IDs
```bash
# Use meaningful session names
python backend/code/cli.py --agent -q "Tell me about OPT" -s "student-work-auth"
python backend/code/cli.py --agent -q "STEM extension details" -s "student-work-auth"
```

### Session Management
```bash
# View all sessions with details
python backend/code/cli.py --agent --list-sessions

# Example output:
# 📝 Agentic Workflow Sessions:
#   • my-consultation: 4 turns, last active 2025-01-13T10:30:45
#   • h1b-process: 6 turns, last active 2025-01-13T09:15:22
```

## 🔧 Troubleshooting

### Import Errors
If you get import errors, ensure you're running from the project root:
```bash
cd /path/to/AskImmigrate2.0
python backend/code/cli.py --agent -q "your question"
```

### API Key Issues
```bash
# Test your setup
python backend/code/cli.py --test -q "test question"

# Check environment variables
echo $GROQ_API_KEY
echo $OPENAI_API_KEY
```

### Session Issues
```bash
# List sessions to verify they're being saved
python backend/code/cli.py --agent --list-sessions

# Check session database location
ls backend/outputs/agentic_sessions.db
```

### Vector Database Issues
If you get database errors:
```bash
# Check if vector database exists
ls backend/outputs/vector_db/

# If missing, run database setup (if available)
python backend/code/embed_documents.py
```

## 🆚 Simple RAG Mode (Legacy)

For basic RAG without session awareness:
```bash
# Simple question-answer without sessions
python backend/code/cli.py -q "What is naturalization?"

# With custom session for simple mode
python backend/code/cli.py -q "Tell me about green cards" -s "simple-session"
```

## 📝 Best Practices

### **Session Naming**
- Use descriptive session names: `"f1-to-h1b-transition"`, `"family-immigration"`
- Keep sessions focused on related topics
- Create new sessions for different immigration paths

### **Question Flow**
- Start with broad questions, then get specific
- Use follow-up questions to dive deeper
- Reference previous conversation naturally

### **Session Continuity**
- Always use the same session ID for related questions
- Check `--list-sessions` to find existing conversations
- Session IDs are case-sensitive

## 🚀 Installation Requirements

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

Key dependencies include:
- `langchain-groq` or `langchain-openai` for LLM integration
- `langgraph` for multi-agent workflow
- `chromadb` for vector database
- `sentence-transformers` for embeddings
- `python-dotenv` for environment management

## 📊 Performance Tips

- **GROQ API**: Generally faster and has generous free tier
- **Session management**: Keeps context without re-processing previous questions
- **Multi-agent workflow**: More comprehensive but takes longer than simple RAG
- **Vector database**: First run may be slower as it initializes

---

**🎉 You now have a powerful, session-aware immigration assistant that remembers your conversation and provides contextual guidance throughout your immigration journey!**