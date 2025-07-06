import argparse
import os
import sys

from dotenv import load_dotenv

from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat
from agent_nodes.memory import list_sessions
from app.utils import slugify_chat_session

load_dotenv()

# To avoid tokenizer parallelism warning from huggingface
os.environ["TOKENIZERS_PARALLELISM"] = "false"


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="AskImmigrate CLI.")
    parser.add_argument(
        "-q", "--question", help="The question to ask the chat assistant"
    )
    parser.add_argument(
        "-s", "--session_id", help="Optional session ID to continue a previous session"
    )
    parser.add_argument(
        "-l", "--list_sessions", action="store_true", help="List all stored session IDs"
    )
    args = parser.parse_args()

    if args.list_sessions:
        sessions = list_sessions()
        print("Available sessions:")
        for sid in sessions:
            print(f"- {sid}")
        sys.exit()

    session_id = args.session_id or slugify_chat_session(args.question)
    answer = chat(session_id=session_id, question=args.question)
    print(answer)
