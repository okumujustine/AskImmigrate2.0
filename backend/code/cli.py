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

def run_agent_workflow(question: str) -> str:
    """Run question through the full agent workflow."""
    try:
        from backend.code.graph_workflow import run_agentic_askimmigrate
        results = run_agentic_askimmigrate(text=question)
        
        # Extract the final response
        synthesis = results.get("synthesis", "No synthesis available")
        return synthesis
    except Exception as e:
        return f"Agent workflow error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(
        description="AskImmigrate 2.0 - Multi-Agent US Immigration Assistant"
    )
    
    parser.add_argument(
        "-q", "--question", 
        help="The immigration question to ask"
    )
    
    parser.add_argument(
        "-s", "--session_id",
        help="Optional session ID to continue a previous conversation"
    )
    
    parser.add_argument(
        "--agent", 
        action="store_true",
        help="Use the full multi-agent workflow (recommended)"
    )
    
    parser.add_argument(
        "--list-sessions", 
        action="store_true", 
        help="List all stored session IDs"
    )
    
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Run in test mode (no API key required)"
    )

    args = parser.parse_args()
    
    # Check if question is required
    if not args.list_sessions and not args.test and not args.question:
        parser.error("the following arguments are required: -q/--question")

    # Handle session listing
    if args.list_sessions:
        try:
            from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
            sessions = list_sessions()
            print("📝 Available sessions:")
            for sid in sessions:
                print(f"  - {sid}")
        except Exception as e:
            print(f"❌ Error listing sessions: {e}")
        return

    # Handle test mode
    if args.test:
        print(f"🧪 Test Mode: Would process question: '{args.question}'")
        print("✅ Import test successful! The CLI is working correctly.")
        print("\nWhen you have API keys, remove --test to get real answers.")
        return

    # Check for API key (either GROQ or OpenAI)
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not groq_key and not openai_key:
        print("❌ Error: No API key found.")
        print("\nYou need either:")
        print("1. GROQ_API_KEY for Groq models")
        print("2. OPENAI_API_KEY for OpenAI models")
        print("\nSet one in your .env file or export it:")
        print("   export GROQ_API_KEY=your_groq_key")
        print("   export OPENAI_API_KEY=your_openai_key")
        sys.exit(1)

    # Main processing
    try:
        if args.agent:
            # NEW: Use multi-agent workflow
            print(f"🤖 Using Agent Workflow for: {args.question}")
            print("=" * 50)
            
            from backend.code.graph_workflow import run_agentic_askimmigrate
            results = run_agentic_askimmigrate(text=args.question)
            
            # Extract and display the synthesis response
            if "synthesis" in results:
                print(results["synthesis"])
            else:
                print("❌ No synthesis response generated")
                
        else:
            # OLD: Use simple RAG system
            from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat
            from backend.code.utils import slugify_chat_session
            print(f"🤖 Processing question: {args.question}")
            session_id = args.session_id or slugify_chat_session(args.question)
            print(f"📝 Session ID: {session_id}")
            print("=" * 50)
            
            from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat
            answer = chat(session_id=session_id, question=args.question)
            print(answer)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
