#!/usr/bin/env python3
"""
Session Context Debugging Script for AskImmigrate
This script helps debug session management and follow-up question detection issues.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.code.session_manager import session_manager
from backend.code.graph_workflow import run_agentic_askimmigrate
from backend.code.structured_logging import get_logger
import json
from datetime import datetime

# Setup logging
debug_logger = get_logger("session_debug")

def debug_session_context(session_id: str):
    """Debug the current state of a session."""
    
    print(f"\n🔍 DEBUGGING SESSION: {session_id}")
    print("=" * 60)
    
    try:
        # 1. Get session info
        session_info = session_manager.get_or_create_session(session_id)
        print(f"📋 Session Info:")
        print(f"   • Session ID: {session_info['session_id']}")
        print(f"   • Created: {session_info['created_at']}")
        print(f"   • Updated: {session_info['updated_at']}")
        print(f"   • Turn Count: {session_info['turn_count']}")
        
        # 2. Check session context
        session_context = session_info.get('session_context', {})
        print(f"\n📝 Session Context:")
        print(f"   • Context Keys: {list(session_context.keys())}")
        print(f"   • Ongoing Topics: {session_context.get('ongoing_topics', [])}")
        print(f"   • Visa Types: {session_context.get('visa_types_mentioned', [])}")
        print(f"   • Preferred Language: {session_context.get('preferred_language', 'None')}")
        print(f"   • Language Confidence: {session_context.get('language_confidence', 'None')}")
        
        # 3. Load conversation history
        conversation_history = session_manager.load_conversation_history(session_id)
        print(f"\n💬 Conversation History ({len(conversation_history)} turns):")
        
        for i, turn in enumerate(conversation_history, 1):
            print(f"   Turn {i}:")
            print(f"      Q: {turn.question[:100]}{'...' if len(turn.question) > 100 else ''}")
            print(f"      A: {turn.answer[:100]}{'...' if len(turn.answer) > 100 else ''}")
            print(f"      Type: {turn.question_type}")
            print(f"      Tools: {turn.tools_used}")
            print()
        
        # 4. Test language preference methods
        print(f"🌍 Language Testing:")
        current_lang = session_manager.get_session_language_preference(session_id)
        print(f"   • Current Language Preference: {current_lang}")
        
        # Test should_maintain_session_language
        test_cases = [
            ("en", 0.9),
            ("es", 0.9),
            ("fr", 0.8),
            ("pt", 0.7)
        ]
        
        for lang, confidence in test_cases:
            should_maintain, final_lang = session_manager.should_maintain_session_language(
                session_id, lang, confidence
            )
            print(f"   • Test {lang} ({confidence}): maintain={should_maintain}, final={final_lang}")
        
        # 5. Test follow-up detection
        print(f"\n🔗 Follow-up Detection Testing:")
        test_questions = [
            "how much will it cost",
            "what about the fees",
            "cuánto cuesta",
            "can I also apply for my family",
            "What is an F-1 visa"  # This should NOT be a follow-up
        ]
        
        for question in test_questions:
            is_followup = session_manager.detect_followup_question(question, session_context)
            print(f"   • '{question}' → Follow-up: {is_followup}")
        
    except Exception as e:
        print(f"❌ Error debugging session: {e}")
        import traceback
        traceback.print_exc()

def test_session_workflow_with_debugging():
    """Test the complete workflow with detailed debugging."""
    
    print("\n🧪 TESTING COMPLETE WORKFLOW WITH DEBUGGING")
    print("=" * 80)
    
    # Create a test session
    test_session_id = f"debug-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"🆔 Test Session ID: {test_session_id}")
    
    # Test conversation sequence
    test_conversations = [
        {
            "question": "Cómo puedo solicitar una visa EB-1?",
            "expected_language": "es",
            "expected_followup": False,
            "description": "First question in Spanish about EB-1 visa"
        },
        {
            "question": "how much will it cost",
            "expected_language": "es",  # Should maintain session language
            "expected_followup": True,
            "description": "Follow-up question about costs (should detect as follow-up)"
        },
        {
            "question": "and what about my family",
            "expected_language": "es",
            "expected_followup": True,
            "description": "Another follow-up question"
        },
        {
            "question": "What is an H-1B visa?",
            "expected_language": "en",  # New topic, language switch
            "expected_followup": False,
            "description": "New question about different visa (language switch)"
        }
    ]
    
    for i, test_case in enumerate(test_conversations, 1):
        print(f"\n🧪 TEST {i}/4: {test_case['description']}")
        print("-" * 60)
        
        question = test_case["question"]
        print(f"❓ Question: '{question}'")
        
        # Debug session state BEFORE processing
        print(f"\n📊 BEFORE Processing:")
        debug_session_context(test_session_id)
        
        try:
            # Run the workflow
            print(f"\n🚀 Processing question...")
            results = run_agentic_askimmigrate(text=question, session_id=test_session_id)
            
            # Extract results
            detected_language = results.get("detected_language", "unknown")
            is_followup = results.get("is_followup_question", False)
            synthesis_metadata = results.get("synthesis_metadata", {})
            
            print(f"\n✅ RESULTS:")
            print(f"   • Detected Language: {detected_language}")
            print(f"   • Expected Language: {test_case['expected_language']}")
            print(f"   • Language Match: {'✅' if detected_language == test_case['expected_language'] else '❌'}")
            print(f"   • Is Follow-up: {is_followup}")
            print(f"   • Expected Follow-up: {test_case['expected_followup']}")
            print(f"   • Follow-up Match: {'✅' if is_followup == test_case['expected_followup'] else '❌'}")
            print(f"   • Response Length: {len(results.get('synthesis', ''))}")
            
            # Check if synthesis metadata indicates session awareness
            session_aware = synthesis_metadata.get("session_aware_response", False)
            print(f"   • Session Aware: {session_aware}")
            
            # Debug session state AFTER processing
            print(f"\n📊 AFTER Processing:")
            debug_session_context(test_session_id)
            
            # Show part of the response
            response = results.get("synthesis", "")
            print(f"\n📝 Response Preview:")
            print(f"   {response[:200]}{'...' if len(response) > 200 else ''}")
            
        except Exception as e:
            print(f"❌ Test {i} failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60)
    
    # Final session summary
    print(f"\n📋 FINAL SESSION SUMMARY:")
    debug_session_context(test_session_id)

def manual_session_test():
    """Interactive session testing."""
    
    print("\n🎮 MANUAL SESSION TESTING")
    print("=" * 40)
    
    session_id = input("Enter session ID (or press Enter for new): ").strip()
    if not session_id:
        session_id = f"manual-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        print(f"Created new session: {session_id}")
    
    while True:
        print(f"\n📋 Current Session State:")
        debug_session_context(session_id)
        
        question = input("\nEnter your question (or 'quit' to exit): ").strip()
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        if not question:
            continue
        
        try:
            print(f"\n🚀 Processing: '{question}'")
            results = run_agentic_askimmigrate(text=question, session_id=session_id)
            
            print(f"\n✅ Results:")
            print(f"   • Language: {results.get('detected_language', 'unknown')}")
            print(f"   • Follow-up: {results.get('is_followup_question', False)}")
            print(f"   • Tools Used: {results.get('tools_used', [])}")
            
            response = results.get("synthesis", "")
            print(f"\n📝 Response:")
            print(response[:500] + "..." if len(response) > 500 else response)
            
        except Exception as e:
            print(f"❌ Error: {e}")

def check_database_integrity():
    """Check the database integrity and session data."""
    
    print("\n🗄️ DATABASE INTEGRITY CHECK")
    print("=" * 40)
    
    try:
        import sqlite3
        from backend.code.paths import OUTPUTS_DIR
        import os
        
        db_path = os.path.join(OUTPUTS_DIR, "agentic_sessions.db")
        print(f"📂 Database Path: {db_path}")
        print(f"📊 Database Exists: {os.path.exists(db_path)}")
        
        if os.path.exists(db_path):
            print(f"📏 Database Size: {os.path.getsize(db_path)} bytes")
            
            with sqlite3.connect(db_path) as conn:
                # Check tables
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                print(f"📋 Tables: {tables}")
                
                # Check sessions count
                sessions_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
                print(f"🗂️ Total Sessions: {sessions_count}")
                
                # Check turns count  
                turns_count = conn.execute("SELECT COUNT(*) FROM conversation_turns").fetchone()[0]
                print(f"💬 Total Conversation Turns: {turns_count}")
                
                # Check recent sessions
                recent_sessions = conn.execute("""
                    SELECT session_id, turn_count, updated_at 
                    FROM sessions 
                    ORDER BY updated_at DESC 
                    LIMIT 5
                """).fetchall()
                
                print(f"\n📅 Recent Sessions:")
                for session_id, turn_count, updated_at in recent_sessions:
                    print(f"   • {session_id}: {turn_count} turns (updated: {updated_at})")
                
                # Check for language preferences
                sessions_with_lang = conn.execute("""
                    SELECT session_id, session_context 
                    FROM sessions 
                    WHERE session_context LIKE '%preferred_language%'
                """).fetchall()
                
                print(f"\n🌍 Sessions with Language Preferences: {len(sessions_with_lang)}")
                for session_id, context in sessions_with_lang[:3]:  # Show first 3
                    try:
                        context_data = json.loads(context)
                        lang = context_data.get('preferred_language', 'None')
                        print(f"   • {session_id}: {lang}")
                    except:
                        print(f"   • {session_id}: Invalid JSON context")
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")

if __name__ == "__main__":
    print("🔧 SESSION DEBUGGING TOOLKIT")
    print("=" * 50)
    
    while True:
        print("\nChoose an option:")
        print("1. Test complete workflow with debugging")
        print("2. Debug specific session")
        print("3. Manual session testing")
        print("4. Check database integrity")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            test_session_workflow_with_debugging()
        elif choice == "2":
            session_id = input("Enter session ID to debug: ").strip()
            if session_id:
                debug_session_context(session_id)
        elif choice == "3":
            manual_session_test()
        elif choice == "4":
            check_database_integrity()
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-5.")