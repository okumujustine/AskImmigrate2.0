#!/usr/bin/env python3
"""
Fixed Session Test Script - Properly handles Python path setup
Usage: python backend/code/tests/test_agentic_session.py
OR: python test_agentic_session.py (from the tests directory)
"""

import sys
import os
from pathlib import Path

# CRITICAL FIX: Properly set up Python path regardless of where script is run from
def setup_python_path():
    """Set up Python path to find backend modules"""
    current_file = Path(__file__).resolve()
    
    # Find the project root (AskImmigrate2.0 directory)
    # Go up from backend/code/tests/ to project root
    project_root = current_file.parent.parent.parent
    
    # Alternative: look for the directory containing backend/
    search_path = current_file
    while search_path.parent != search_path:
        if (search_path / "backend").exists():
            project_root = search_path
            break
        search_path = search_path.parent
    else:
        # Fallback: assume we're 3 levels deep
        project_root = current_file.parent.parent.parent
    
    print(f"🔧 Project root detected: {project_root}")
    print(f"🔧 Backend path: {project_root / 'backend'}")
    print(f"🔧 Backend exists: {(project_root / 'backend').exists()}")
    
    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"✅ Added to Python path: {project_root}")
    
    return project_root

# Set up path before any imports
project_root = setup_python_path()

# Now try imports with better error handling
try:
    from backend.code.session_manager import session_manager
    from backend.code.agentic_state import ConversationTurn, ImmigrationState, SessionContext
    print("✅ Successfully imported backend modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Looking for backend in: {project_root}")
    
    # List what's actually in the project root
    if project_root.exists():
        print(f"Contents of {project_root}:")
        for item in project_root.iterdir():
            print(f"  - {item.name}")
    
    sys.exit(1)

from datetime import datetime
import uuid

def test_session_creation_and_sanitization():
    """Test session creation with various problematic session IDs"""
    print("🧪 Testing Session Creation and ID Sanitization")
    print("=" * 60)
    
    test_cases = [
        " what-is-f-1-visa-test123",  # Leading space
        "what-is-f-1-visa-test123 ",  # Trailing space
        " what-is-f-1-visa-test123 ",  # Both spaces
        '"what-is-f-1-visa-test123"',  # Quoted
        "'what-is-f-1-visa-test123'",  # Single quoted
        "normal-session-id",  # Normal case
    ]
    
    for i, test_id in enumerate(test_cases, 1):
        print(f"\nTest {i}: Testing session ID: '{test_id}'")
        try:
            session_info = session_manager.get_or_create_session(test_id)
            actual_id = session_info['session_id']
            print(f"  ✅ Created session: '{actual_id}'")
            print(f"  📊 Turn count: {session_info['turn_count']}")
            
            # Verify session can be retrieved
            retrieved = session_manager.get_or_create_session(actual_id)
            if retrieved['session_id'] == actual_id:
                print(f"  ✅ Session retrieval successful")
            else:
                print(f"  ❌ Session retrieval failed")
                
        except Exception as e:
            print(f"  ❌ Failed: {e}")

def test_conversation_flow():
    """Test a complete conversation flow"""
    print("\n🧪 Testing Complete Conversation Flow")
    print("=" * 50)
    
    # Create a unique session for this test
    test_session_id = f"test-conversation-{uuid.uuid4().hex[:8]}"
    print(f"Using test session: {test_session_id}")
    
    # Test conversation turns
    conversations = [
        {
            "question": "What is an F-1 visa?",
            "answer": "The F-1 visa is a non-immigrant student visa that allows international students to study in the United States.",
            "question_type": "factual",
            "visa_focus": ["F-1"]
        },
        {
            "question": "How do I extend my F-1 visa?",
            "answer": "To extend your F-1 visa, you need to file Form I-539 with USCIS before your current status expires.",
            "question_type": "procedural", 
            "visa_focus": ["F-1"]
        },
        {
            "question": "What was my first question?",
            "answer": "Your first question was 'What is an F-1 visa?'",
            "question_type": "session_reference",
            "visa_focus": []
        }
    ]
    
    # Save each conversation turn
    for i, conv in enumerate(conversations, 1):
        print(f"\nSaving conversation turn {i}...")
        
        try:
            # Create conversation turn
            turn = ConversationTurn(
                question=conv["question"],
                answer=conv["answer"],
                timestamp=datetime.now().isoformat(),
                question_type=conv["question_type"],
                visa_focus=conv["visa_focus"],
                tools_used=["rag_retrieval_tool"]
            )
            
            # Create mock final state
            final_state = ImmigrationState(
                text=conv["question"],
                synthesis=conv["answer"],
                structured_analysis={
                    "question_type": conv["question_type"],
                    "visa_focus": conv["visa_focus"],
                    "primary_focus": f"Response to: {conv['question']}"
                }
            )
            
            # Save the turn
            session_manager.save_conversation_turn(test_session_id, turn, final_state)
            print(f"  ✅ Saved turn {i}: {conv['question'][:30]}...")
            
        except Exception as e:
            print(f"  ❌ Failed to save turn {i}: {e}")
            import traceback
            traceback.print_exc()
    
    # Test loading conversation history
    print(f"\nLoading conversation history for {test_session_id}...")
    try:
        history = session_manager.load_conversation_history(test_session_id)
        print(f"✅ Loaded {len(history)} conversation turns")
        
        for i, turn in enumerate(history, 1):
            print(f"  Turn {i}: {turn.question[:40]}...")
            
    except Exception as e:
        print(f"❌ Failed to load conversation history: {e}")
    
    # Test session context building
    print(f"\nTesting session context building...")
    try:
        context_string = session_manager.build_session_context_string(test_session_id)
        print(f"✅ Built session context ({len(context_string)} chars)")
        print("Context preview:")
        print(context_string[:200] + "..." if len(context_string) > 200 else context_string)
        
    except Exception as e:
        print(f"❌ Failed to build session context: {e}")
    
    return test_session_id

def test_followup_detection():
    """Test follow-up question detection"""
    print("\n🧪 Testing Follow-up Question Detection")
    print("=" * 50)
    
    # Mock session context with some conversation history
    session_context = {
        "ongoing_topics": ["F-1 visa", "student visa requirements"],
        "visa_types_mentioned": ["F-1"],
        "last_question_type": "factual"
    }
    
    test_questions = [
        ("What is an F-1 visa?", False, "New factual question"),
        ("How do I extend it?", True, "Refers to 'it' from previous context"),
        ("What was my first question?", True, "Explicit session reference"),
        ("Can I work on F-1?", False, "New question with immigration terms"),
        ("Tell me more", True, "Short question without immigration terms"),
        ("What about the fees?", True, "Follow-up indicator 'what about'"),
        ("How much does H-1B cost?", False, "New question about different visa"),
    ]
    
    for question, expected, reason in test_questions:
        detected = session_manager.detect_followup_question(question, session_context)
        status = "✅" if detected == expected else "❌"
        print(f"{status} '{question}' -> {detected} (expected: {expected})")
        print(f"    Reason: {reason}")

def test_database_operations():
    """Test basic database operations"""
    print("\n🧪 Testing Database Operations")
    print("=" * 40)
    
    try:
        # Test session listing
        sessions = session_manager.list_all_sessions()
        print(f"✅ Found {len(sessions)} sessions in database")
        
        # Show recent sessions
        for session in sessions[:3]:
            print(f"  • {session['session_id']}: {session['turn_count']} turns")
            
    except Exception as e:
        print(f"❌ Database operations failed: {e}")

def main():
    """Run all session tests"""
    print("🔬 AGENTIC SESSION MANAGEMENT TEST SUITE")
    print("=" * 70)
    print(f"Running from: {os.getcwd()}")
    print(f"Python path includes: {len(sys.path)} directories")
    
    try:
        # Test 1: Session creation and sanitization
        test_session_creation_and_sanitization()
        
        # Test 2: Complete conversation flow
        test_session_id = test_conversation_flow()
        
        # Test 3: Follow-up detection
        test_followup_detection()
        
        # Test 4: Database operations
        test_database_operations()
        
        print("\n🎉 ALL TESTS COMPLETED!")
        print(f"Test session created: {test_session_id}")
        
    except Exception as e:
        print(f"\n💥 TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()