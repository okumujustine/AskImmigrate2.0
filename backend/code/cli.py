#!/usr/bin/env python3
"""
AskImmigrate 2.0 CLI - Session-Aware Agentic Workflow with FIXED session handling
Usage: python backend/code/cli.py --agent --question "what is f1?" --session_id "my-session"

CRITICAL FIXES:
- Session ID sanitization to handle whitespace issues
- Better argument parsing and validation
- Enhanced error handling for session operations
- Improved session listing and management
"""

import argparse
import os
import sys
from typing import List, Dict, Any
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

def sanitize_session_id(session_id: str) -> str:
    """
    Sanitize session ID to handle common input issues.
    
    CHANGES: New function to fix session ID handling
    """
    if not session_id:
        return session_id
    
    # Remove leading/trailing whitespace
    cleaned = session_id.strip()
    
    # Remove quotes if present
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    if cleaned.startswith("'") and cleaned.endswith("'"):
        cleaned = cleaned[1:-1]
    
    # Remove extra spaces
    cleaned = ' '.join(cleaned.split())
    
    return cleaned

def main():
    parser = argparse.ArgumentParser(
        description="AskImmigrate 2.0 - Multi-Agent US Immigration Assistant with Session Support"
    )
    
    parser.add_argument(
        "-q", "--question", 
        help="The immigration question to ask"
    )
    
    parser.add_argument(
        "-s", "--session_id",
        help="Session ID to continue a previous conversation"
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
    
    # CRITICAL FIX: Sanitize session ID if provided
    session_id = None
    if args.session_id:
        session_id = sanitize_session_id(args.session_id)
        if session_id != args.session_id:
            print(f"🔧 Cleaned session ID: '{args.session_id}' -> '{session_id}'")
    
    # Check if question is required
    if not args.list_sessions and not args.test and not args.question:
        parser.error("the following arguments are required: -q/--question")

    # Handle session listing
    if args.list_sessions:
        try:
            if args.agent:
                # List agentic workflow sessions
                from backend.code.graph_workflow import list_sessions
                sessions = list_sessions()
                print("📝 Agentic Workflow Sessions:")
                if sessions:
                    for session in sessions:
                        print(f"  • {session['session_id']}: {session['turn_count']} turns, last active {session['updated_at']}")
                else:
                    print("  No agentic sessions found")
            else:
                # List RAG workflow sessions
                from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
                sessions = list_sessions()
                print("📝 RAG Workflow Sessions:")
                for sid in sessions:
                    print(f"  - {sid}")
        except Exception as e:
            print(f"❌ Error listing sessions: {e}")
        return

    # Handle test mode
    if args.test:
        print(f"🧪 Test Mode: Would process question: '{args.question}'")
        if session_id:
            print(f"📱 With session ID: {session_id}")
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
            # IMPROVED: Use session-aware multi-agent workflow with fixed session handling
            print(f"🤖 Using Session-Aware Agent Workflow for: {args.question}")
            if session_id:
                print(f"📱 Session ID: {session_id}")
            print("=" * 50)
            
            from backend.code.graph_workflow import run_agentic_askimmigrate
            results = run_agentic_askimmigrate(text=args.question, session_id=session_id)
            
            # Display the synthesis response
            if "synthesis" in results:
                print("\n" + "="*60)
                print("📝 IMMIGRATION ASSISTANT RESPONSE")
                print("="*60)
                print(results["synthesis"])
                print("="*60)
            
            # Session summary with enhanced information
            actual_session_id = results.get("session_id")
            if actual_session_id:
                turn_num = results.get("conversation_turn_number", 1)
                is_followup = results.get("is_followup_question", False)
                print(f"\n📱 Session: {actual_session_id} (Turn #{turn_num})")
                if is_followup:
                    print("🔗 Detected as follow-up question")
                
                # Show conversation context if available
                conv_history = results.get("conversation_history", [])
                if conv_history:
                    print(f"📚 Conversation history: {len(conv_history)} previous turns")
                
        else:
            # OLD: Use simple RAG system
            from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat
            from backend.code.utils import slugify_chat_session
            print(f"🤖 Processing question: {args.question}")
            rag_session_id = session_id or slugify_chat_session(args.question)
            print(f"📝 Session ID: {rag_session_id}")
            print("=" * 50)
            
            answer = chat(session_id=rag_session_id, question=args.question)
            print(answer)

    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\nDebugging information:")
        print(f"  Question: '{args.question}'")
        print(f"  Session ID: '{session_id}'")
        print(f"  Agent mode: {args.agent}")
        
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()