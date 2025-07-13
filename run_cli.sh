#!/bin/bash
# AskImmigrate 2.0 CLI convenience script
# Usage: ./run_cli.sh -q "what is f1?"



# Run the CLI with all arguments passed through
python backend/code/cli.py "$@"
