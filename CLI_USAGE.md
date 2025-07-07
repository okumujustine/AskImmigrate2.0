# AskImmigrate 2.0 CLI Usage## Quick Start### 1. Test the CLI (No API Key Required)```bashpython backend/code/cli.py --test --question "what is f1?"```### 2. Get a GROQ API Key1. Visit [https://console.groq.com/keys](https://console.groq.com/keys)2. Sign up for a free account3. Create a new API key### 3. Set up Environment VariablesCreate a `.env` file in the project root:```bashGROQ_API_KEY=your_actual_api_key_here```Or export the environment variable:```bashexport GROQ_API_KEY=your_actual_api_key_here```### 4. Run Real Queries```bash# Ask a questionpython backend/code/cli.py --question "what is f1?"# Continue a conversation with a specific sessionpython backend/code/cli.py --question "what are the requirements?" --session_id "my-session"# List all previous sessionspython backend/code/cli.py --list-sessions```## Command Options- `--question, -q`: The immigration question to ask (required)- `--session_id, -s`: Optional session ID to continue a conversation- `--list-sessions`: List all stored session IDs- `--test`: Run in test mode (no API key required)## Examples```bash# Basic questionspython backend/code/cli.py --question "what is an H-1B visa?"python backend/code/cli.py --question "how do I apply for a green card?"python backend/code/cli.py --question "what documents do I need for naturalization?"# Session managementpython backend/code/cli.py --question "tell me about F1 visas" --session_id "student-visa-info"python backend/code/cli.py --question "what about OPT?" --session_id "student-visa-info"```## Convenience ScriptFor easier usage, you can also use the convenience script:```bash./run_cli.sh "what is an H-1B visa?"```## Running from Different LocationsThe CLI can be run from any location within the project:```bash# From project rootpython backend/code/cli.py --question "your question"# From backend directorycd backendpython code/cli.py --question "your question"# From backend/code directorycd backend/codepython cli.py --question "your question"```## Troubleshooting
### Import Errors
If you get import errors, make sure you're running from the project root directory:
```bash
cd /path/to/AskImmigrate2.0
python backend/code/cli.py --question "your question"
```

### API Key Issues
- Make sure your GROQ API key is valid
- Check that the `.env` file is in the project root directory
- Try exporting the environment variable directly

### Vector Database Issues
If you get vector database errors, you may need to populate the database first. Check the project documentation for database setup instructions.

## Installation

Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

Required packages include:
- langchain-huggingface
- sentence-transformers
- chromadb
- pdfminer.six
- groq
- python-dotenv
