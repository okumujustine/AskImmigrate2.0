#!/usr/bin/env python3
"""
Test script to analyze the detailed flow of Session Context vs Conversation History
in AskImmigrate2.0

This script will trace exactly how the two are used throughout the system.
"""

import sys
import os
from datetime import datetime

# Add the backend code directory to Python path
backend_code_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_code_dir not in sys.path:
    sys.path.insert(0, backend_code_dir)

# Import the core components
from agentic_state import ImmigrationState, ConversationTurn, SessionContext
from session_manager import session_manager
from graph_workflow import create_initial_state, run_agentic_askimmigrate

def print_separator(title):
    """Print a nice separator for readability"""
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)

def analyze_empty_session():
    """Analyze what happens with a completely new session"""
    print_separator("STEP 1: NEW SESSION ANALYSIS")
    
    session_id = "test-flow-analysis"
    question = "What is an F-1 visa?"
    
    print(f"📝 Creating initial state for NEW session:")
    print(f"   Question: {question}")
    print(f"   Session ID: {session_id}")
    
    # Create initial state - this is where the magic happens
    state = create_initial_state(question, session_id)
    
    print(f"\n📊 INITIAL STATE ANALYSIS:")
    print(f"   Session ID: {state.get('session_id')}")
    print(f"   Turn Number: {state.get('conversation_turn_number')}")
    print(f"   Is Follow-up: {state.get('is_followup_question')}")
    print(f"   Conversation History: {len(state.get('conversation_history', []))} items")
    print(f"   Session Context: {type(state.get('session_context'))}")
    
    # Examine the session context in detail
    session_context = state.get('session_context')
    if session_context:
        print(f"\n🎯 SESSION CONTEXT DETAILS:")
        print(f"   Ongoing Topics: {session_context.ongoing_topics}")
        print(f"   Visa Types Mentioned: {session_context.visa_types_mentioned}")
        print(f"   User Situation: {session_context.user_situation}")
        print(f"   Previous Questions Summary: {session_context.previous_questions_summary}")
    
    return state, session_id

def analyze_session_with_history():
    """Create a session with some history and analyze the difference"""
    print_separator("STEP 2: SESSION WITH HISTORY ANALYSIS")
    
    session_id = "test-flow-with-history"
    
    # First, let's manually create some conversation history
    print("📝 Creating mock conversation history...")
    
    # Create some turns manually in the database
    turn1 = ConversationTurn(
        question="What is an F-1 visa?",
        answer="An F-1 visa is a non-immigrant student visa that allows foreign students to enter the United States to attend academic institutions. It's the most common visa type for international students pursuing higher education in the US.",
        timestamp=datetime.now().isoformat(),
        question_type="visa_inquiry",
        visa_focus=["F-1"],
        tools_used=["rag_retrieval"]
    )
    
    turn2 = ConversationTurn(
        question="How long is it valid for?",
        answer="F-1 visa validity depends on your program duration plus any Optional Practical Training (OPT). Typically, you're admitted for 'Duration of Status' (D/S), which means you can stay as long as you maintain valid student status.",
        timestamp=datetime.now().isoformat(),
        question_type="followup_inquiry", 
        visa_focus=["F-1"],
        tools_used=["rag_retrieval"]
    )
    
    # Create a mock state to save these turns
    mock_state = ImmigrationState(
        text="",
        session_id=session_id,
        structured_analysis={"question_type": "test", "visa_focus": ["F-1"]}
    )
    
    # Save the turns to create history
    session_manager.save_conversation_turn(session_id, turn1, mock_state)
    session_manager.save_conversation_turn(session_id, turn2, mock_state)
    
    print("✅ Created mock conversation history with 2 turns")
    
    # Now create initial state for a follow-up question
    followup_question = "How do I extend it?"
    
    print(f"\n📝 Creating initial state for FOLLOW-UP question:")
    print(f"   Question: {followup_question}")
    print(f"   Session ID: {session_id}")
    
    state = create_initial_state(followup_question, session_id)
    
    print(f"\n📊 FOLLOW-UP STATE ANALYSIS:")
    print(f"   Session ID: {state.get('session_id')}")
    print(f"   Turn Number: {state.get('conversation_turn_number')}")
    print(f"   Is Follow-up: {state.get('is_followup_question')}")
    print(f"   Conversation History: {len(state.get('conversation_history', []))} items")
    
    # Examine conversation history in detail
    history = state.get('conversation_history', [])
    print(f"\n📚 CONVERSATION HISTORY DETAILS:")
    for i, turn in enumerate(history, 1):
        print(f"   Turn {i}:")
        print(f"     Q: {turn.question}")
        print(f"     A: {turn.answer[:100]}...")
        print(f"     Visa Focus: {turn.visa_focus}")
    
    # Examine session context 
    session_context = state.get('session_context')
    if session_context:
        print(f"\n🎯 SESSION CONTEXT DETAILS:")
        print(f"   Ongoing Topics: {session_context.ongoing_topics}")
        print(f"   Visa Types Mentioned: {session_context.visa_types_mentioned}")
        print(f"   User Situation: {session_context.user_situation}")
        print(f"   Previous Questions Summary: {session_context.previous_questions_summary}")
    
    return state, session_id

def trace_workflow_usage(state):
    """Trace how session context and conversation history are used in the workflow"""
    print_separator("STEP 3: WORKFLOW USAGE ANALYSIS")
    
    print("🔄 Analyzing how Manager Node uses the data...")
    
    # Look at what gets passed to the manager
    user_question = state.get("text", "")
    conversation_history = state.get("conversation_history", [])
    session_context = state.get("session_context")
    is_followup = state.get("is_followup_question", False)
    
    print(f"📋 Data available to Manager Node:")
    print(f"   User Question: {user_question}")
    print(f"   Has History: {len(conversation_history)} turns")
    print(f"   Has Session Context: {bool(session_context)}")
    print(f"   Is Follow-up: {is_followup}")
    
    # Simulate how session-aware prompt is built (from manager_node.py)
    print(f"\n🏗️ Building Session-Aware Prompt:")
    
    if conversation_history:
        print("   ✅ CONVERSATION HISTORY used for:")
        print("      - Building conversation context string")
        print("      - Showing exact Q&A pairs to LLM")
        print("      - Providing complete interaction history")
        
        # Show what the conversation context looks like
        conversation_context = "CONVERSATION SO FAR:\n"
        for i, turn in enumerate(conversation_history, 1):
            conversation_context += f"Q{i}: {turn.question}\n"
            conversation_context += f"A{i}: {turn.answer}\n\n"
        conversation_context += f"NEW QUESTION: {user_question}\n\n"
        
        print(f"\n📝 Conversation Context String (first 200 chars):")
        print(f"   {conversation_context[:200]}...")
    
    if session_context:
        print(f"\n   ✅ SESSION CONTEXT used for:")
        print(f"      - Follow-up detection: {is_followup}")
        print(f"      - Understanding ongoing topics: {session_context.ongoing_topics}")
        print(f"      - Visa type continuity: {session_context.visa_types_mentioned}")
        print(f"      - User situation awareness: {bool(session_context.user_situation)}")
    
    print(f"\n🔄 Analyzing how Synthesis Node uses the data...")
    
    print(f"📋 Data available to Synthesis Node:")
    print(f"   - Same conversation history for session-aware responses")
    print(f"   - Session context for intelligent follow-up handling")
    print(f"   - Manager's analysis results")
    print(f"   - RAG retrieval results")
    
    return state

if __name__ == "__main__":
    print("🚀 AskImmigrate2.0 Flow Analysis")
    print("This script will trace exactly how Session Context and Conversation History flow through the system")
    
    try:
        # Test 1: New session (no history)
        new_state, new_session_id = analyze_empty_session()
        
        # Test 2: Session with history  
        history_state, history_session_id = analyze_session_with_history()
        
        # Test 3: Trace workflow usage
        trace_workflow_usage(history_state)
        
        print_separator("SUMMARY: KEY DIFFERENCES IN USAGE")
        
        print("📚 CONVERSATION HISTORY is used for:")
        print("   1. Building exact conversation context for LLM prompts")
        print("   2. Providing complete audit trail of interactions")
        print("   3. Enabling reference queries ('What was my first question?')")
        print("   4. Maintaining complete session reconstruction capability")
        
        print("\n🎯 SESSION CONTEXT is used for:")
        print("   1. Efficient follow-up question detection")
        print("   2. Maintaining topic continuity without overwhelming LLM")
        print("   3. Intelligent visa type tracking across turns")
        print("   4. User situation inference for personalized responses")
        print("   5. Compact representation for AI processing")
        
        print("\n🔄 WORKFLOW FLOW:")
        print("   1. create_initial_state() loads BOTH from database")
        print("   2. Manager uses HISTORY for session-aware prompts")
        print("   3. Manager uses CONTEXT for follow-up detection")
        print("   4. Synthesis uses HISTORY for response generation")
        print("   5. Synthesis uses CONTEXT for topic continuity")
        print("   6. Final response saved back to HISTORY")
        print("   7. CONTEXT updated based on new interaction")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
