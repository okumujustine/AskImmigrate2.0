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
from tools.web_search_tool import web_search_tool

# Add the project root to Python path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

# Import structured logging
from backend.code.structured_logging import cli_logger, start_request_tracking

# To avoid tokenizer parallelism warning from huggingface
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def sanitize_session_id(session_id: str) -> str:
    """
    Sanitize session ID to handle common input issues.
    
    CHANGES: New function to fix session ID handling
    """
    if not session_id:
        return session_id

    correlation_id = start_request_tracking()
    cli_logger.info("Session ID sanitization started", extra={
        "event": "session_id_sanitization_started",
        "original_session_id": session_id,
        "correlation_id": correlation_id
    })

    # Remove leading/trailing whitespace
    cleaned = session_id.strip()

    # Remove quotes if present
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    if cleaned.startswith("'") and cleaned.endswith("'"):
        cleaned = cleaned[1:-1]

    # Remove extra spaces
    cleaned = ' '.join(cleaned.split())
    
    cli_logger.info("Session ID sanitized successfully", extra={
        "event": "session_id_sanitized",
        "original_session_id": session_id,
        "sanitized_session_id": cleaned,
        "correlation_id": correlation_id
    })
    
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
            correlation_id = start_request_tracking()
            cli_logger.info("Session ID cleaned", extra={
                "event": "session_id_cleaned",
                "original_session_id": args.session_id,
                "cleaned_session_id": session_id,
                "correlation_id": correlation_id
            })
    
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
                
                correlation_id = start_request_tracking()
                cli_logger.info("Listing agentic workflow sessions", extra={
                    "event": "agentic_sessions_list_started",
                    "session_count": len(sessions),
                    "correlation_id": correlation_id
                })
                
                if sessions:
                    for session in sessions:
                        cli_logger.info("Agentic session found", extra={
                            "event": "agentic_session_listed",
                            "session_id": session['session_id'],
                            "turn_count": session['turn_count'],
                            "last_active": session['updated_at'],
                            "correlation_id": correlation_id
                        })
                else:
                    cli_logger.info("No agentic sessions found", extra={
                        "event": "no_agentic_sessions_found",
                        "correlation_id": correlation_id
                    })
            else:
                # List RAG workflow sessions
                from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
                sessions = list_sessions()
                
                correlation_id = start_request_tracking()
                cli_logger.info("Listing RAG workflow sessions", extra={
                    "event": "rag_sessions_list_started",
                    "session_count": len(sessions),
                    "correlation_id": correlation_id
                })
                
                for sid in sessions:
                    cli_logger.info("RAG session found", extra={
                        "event": "rag_session_listed",
                        "session_id": sid,
                        "correlation_id": correlation_id
                    })
        except Exception as e:
            correlation_id = start_request_tracking()
            cli_logger.error("Error listing sessions", extra={
                "event": "session_listing_error",
                "error": str(e),
                "error_type": type(e).__name__,
                "correlation_id": correlation_id
            })
        return

    # Handle test mode
    if args.test:
        correlation_id = start_request_tracking()
        cli_logger.info("Test mode initiated", extra={
            "event": "test_mode_started",
            "question": args.question,
            "session_id": session_id,
            "correlation_id": correlation_id
        })
        
        if session_id:
            cli_logger.info("Test mode with session", extra={
                "event": "test_mode_session_provided",
                "session_id": session_id,
                "correlation_id": correlation_id
            })
            
        cli_logger.info("Import test successful", extra={
            "event": "import_test_success",
            "correlation_id": correlation_id
        })
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
        
        correlation_id = start_request_tracking()
        cli_logger.error("Application exiting due to missing API key", extra={
            "event": "app_exit_no_api_key",
            "correlation_id": correlation_id
        })
        sys.exit(1)

    # Main processing
    try:
        if args.agent:
            # IMPROVED: Use session-aware multi-agent workflow with fixed session handling
            correlation_id = start_request_tracking()
            cli_logger.info("Starting session-aware agent workflow", extra={
                "event": "agent_workflow_started",
                "question": args.question,
                "session_id": session_id,
                "correlation_id": correlation_id
            })
            
            if session_id:
                cli_logger.info("Agent workflow using session", extra={
                    "event": "agent_workflow_session_provided",
                    "session_id": session_id,
                    "correlation_id": correlation_id
                })
            
            from backend.code.graph_workflow import run_agentic_askimmigrate
            results = run_agentic_askimmigrate(text=args.question, session_id=session_id)
            
            # Display the synthesis response
            if "synthesis" in results:
                cli_logger.info("Synthesis response generated", extra={
                    "event": "synthesis_response_ready",
                    "has_synthesis": True,
                    "correlation_id": correlation_id
                })
            
            # Session summary with enhanced information
            actual_session_id = results.get("session_id")
            if actual_session_id:
                turn_num = results.get("conversation_turn_number", 1)
                is_followup = results.get("is_followup_question", False)
                
                cli_logger.info("Session processing completed", extra={
                    "event": "session_processing_completed",
                    "session_id": actual_session_id,
                    "turn_number": turn_num,
                    "is_followup": is_followup,
                    "correlation_id": correlation_id
                })
                
                # Show conversation context if available
                conv_history = results.get("conversation_history", [])
                if conv_history:
                    cli_logger.info("Conversation history available", extra={
                        "event": "conversation_history_found",
                        "history_length": len(conv_history),
                        "correlation_id": correlation_id
                    })
                
        else:
            # OLD: Use simple RAG system
            from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat
            from backend.code.utils import slugify_chat_session
            
            correlation_id = start_request_tracking()
            cli_logger.info("Starting RAG workflow", extra={
                "event": "rag_workflow_started",
                "question": args.question,
                "correlation_id": correlation_id
            })
            
            rag_session_id = session_id or slugify_chat_session(args.question)
            cli_logger.info("RAG session initialized", extra={
                "event": "rag_session_initialized",
                "session_id": rag_session_id,
                "correlation_id": correlation_id
            })
            
            answer = chat(session_id=rag_session_id, question=args.question)
            
            cli_logger.info("RAG answer generated", extra={
                "event": "rag_answer_generated",
                "session_id": rag_session_id,
                "correlation_id": correlation_id
            })

    except Exception as e:
        correlation_id = start_request_tracking()
        cli_logger.error("CLI execution error", extra={
            "event": "cli_execution_error",
            "error": str(e),
            "error_type": type(e).__name__,
            "question": args.question,
            "session_id": session_id,
            "agent_mode": args.agent,
            "correlation_id": correlation_id
        })
        
        import traceback
        cli_logger.error("Full traceback", extra={
            "event": "cli_traceback",
            "traceback": traceback.format_exc(),
            "correlation_id": correlation_id
        })
        sys.exit(1)


if __name__ == "__main__":
    main()