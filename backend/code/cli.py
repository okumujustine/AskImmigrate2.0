#!/usr/bin/env python3
"""
AskImmigrate 2.0 CLI - Simplified wrapper
Usage: python backend/code/cli.py --question "what is f1?"
"""

import argparse
import os
import sys
from dotenv import load_dotenv

# Add the project root to Python path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

# To avoid tokenizer parallelism warning from huggingface
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def main():
    parser = argparse.ArgumentParser(
        description="AskImmigrate 2.0 - US Immigration Assistant"
    )
    parser.add_argument(
        "-q", "--question", required=True, help="The immigration question to ask"
    )
    parser.add_argument(
        "-s",
        "--session_id",
        help="Optional session ID to continue a previous conversation",
    )
    parser.add_argument(
        "--list-sessions", action="store_true", help="List all stored session IDs"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run in test mode (no API key required)"
    )

    args = parser.parse_args()

    # Check for API key
    if not args.test and not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY environment variable not set.")
        print("\nTo fix this:")
        print("1. Get a free API key from: https://console.groq.com/keys")
        print("2. Create a .env file in the project root with:")
        print("   GROQ_API_KEY=your_actual_api_key_here")
        print("3. Or export it: export GROQ_API_KEY=your_actual_api_key_here")
        print(
            "\nTo test without an API key, use: python backend/code/cli.py --test --question 'your question'"
        )
        sys.exit(1)

    if args.test:
        print(f"🧪 Test Mode: Would process question: '{args.question}'")
        print("✅ Import test successful! The CLI is working correctly.")
        print("\nWhen you have a GROQ API key, remove --test to get real answers.")
        return

    if args.list_sessions:
        try:
            from backend.code.agent_nodes.rag_retrieval_agent.memory import (
                list_sessions,
            )

            sessions = list_sessions()
            print("📝 Available sessions:")
            for sid in sessions:
                print(f"  - {sid}")
        except Exception as e:
            print(f"❌ Error listing sessions: {e}")
        return

    try:
        from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat
        from backend.code.utils import slugify_chat_session

        session_id = args.session_id or slugify_chat_session(args.question)
        print(f"🤖 Processing question: {args.question}")
        print(f"📝 Session ID: {session_id}")
        print("=" * 50)

        answer = chat(session_id=session_id, question=args.question)
        print(answer)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
