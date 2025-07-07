#!/bin/bash
# AskImmigrate 2.0 CLI convenience script
# Usage: ./run_cli.sh "what is f1?"

# Set the API key
export GROQ_API_KEY=

# Run the CLI with all arguments passed through
python backend/code/cli.py "$@"
