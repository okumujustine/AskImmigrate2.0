from typing import Dict, Any, Optional, List
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from backend.code.agent_nodes.manager_node import manager_node
from backend.code.agent_nodes.synthesis_node import synthesis_node
from backend.code.agent_nodes.reviewer_node import reviewer_node, route_from_reviewer
from backend.code.agentic_state import ImmigrationState, ConversationTurn, SessionContext
from backend.code.session_manager import session_manager
from langchain_core.runnables.graph import MermaidDrawMethod
import os
from dotenv import load_dotenv
from backend.code.paths import OUTPUTS_DIR
from datetime import datetime

load_dotenv()
if os.environ.get("LANGSMITH_TRACING") != "true":
    print("WARNING: LangSmith tracing is not enabled. Set LANGSMITH_TRACING=true in your environment.")

def create_ask_immigrate_graph() -> CompiledStateGraph:
    """
    Creates the enhanced AskImmigrate2.0 graph with strategic manager coordination.
    """
    print("🔧 Building enhanced AskImmigrate workflow graph...")
    
    graph = StateGraph(ImmigrationState)

    # Add agent nodes
    graph.add_node("manager", manager_node)
    graph.add_node("synthesizer", synthesis_node)
    graph.add_node("reviewer", reviewer_node)

    # Build the workflow edges
    print("🔗 Connecting workflow edges...")
    
    graph.add_edge(START, "manager")
    graph.add_edge("manager", "synthesizer")
    graph.add_edge("synthesizer", "reviewer")
    
    graph.add_conditional_edges(
        "reviewer",
        route_from_reviewer,
        {
            "synthesis": "synthesizer",
            "end": END,
        },
    )

    print("✅ Graph structure completed")
    return graph.compile()

def create_initial_state(text: str, session_id: Optional[str] = None) -> ImmigrationState:
    """
    Create enhanced initial state with COMPLETE session support and debugging.
    
    CRITICAL FIXES:
    - Complete implementation with all session loading logic
    - Session ID sanitization to handle whitespace issues
    - Proper session context loading with validation
    - Enhanced debugging throughout the process
    - Better error handling for session operations
    - GUARANTEED to return a valid ImmigrationState object
    """
    
    print(f"🔧 Creating initial state for: '{text}'")
    
    # CRITICAL FIX: Sanitize session ID to remove whitespace
    actual_session_id = session_id
    if actual_session_id:
        actual_session_id = actual_session_id.strip()
        if actual_session_id != session_id:
            print(f"🔧 Fixed session ID whitespace: '{session_id}' -> '{actual_session_id}'")
    
    if actual_session_id is None or actual_session_id == "":
        from backend.code.utils import slugify_chat_session
        actual_session_id = slugify_chat_session(text)
        print(f"📱 Auto-created session: {actual_session_id}")
    else:
        print(f"📱 Using provided session: '{actual_session_id}'")
    
    # Initialize base state - GUARANTEED to be created
    state = ImmigrationState(
        text=text,
        user_question=text,
        session_id=actual_session_id,
        conversation_history=[],
        session_context=None,
        is_followup_question=False,
        conversation_turn_number=1,
        manager_decision=None,
        structured_analysis=None,
        workflow_parameters=None,
        synthesis="",
        rag_response="",
        tool_results={},
        tools_used=[],
        revision_round=0,
        needs_revision=None,
        synthesis_approved=None,
        rag_retriever_approved=None,
        references_approved=None,
        synthesis_feedback=None,
        rag_retriever_feedback=None,
        references_feedback=None,
        visa_type="",
        visa_fee=0.0,
        references=[],
        analysis_timestamp=datetime.now().isoformat(),
        strategy_applied=None,
        synthesis_metadata=None
    )
    
    print(f"✅ Base state created with session ID: {actual_session_id}")
    
    # CRITICAL FIX: Enhanced session context loading with proper debugging
    try:
        print(f"📱 Loading session context for: '{actual_session_id}'")
        
        # Get or create session with enhanced debugging
        session_info = session_manager.get_or_create_session(actual_session_id)
        print(f"📊 Session info retrieved: turn_count={session_info['turn_count']}")
        
        # Load conversation history with enhanced debugging
        conversation_history = session_manager.load_conversation_history(actual_session_id)
        print(f"📚 Loaded {len(conversation_history)} conversation turns")
        
        # Update state with session information
        state["conversation_history"] = conversation_history
        state["conversation_turn_number"] = session_info["turn_count"] + 1
        
        # CRITICAL FIX: Properly build session context only if we have history
        if conversation_history and len(conversation_history) > 0:
            print(f"📋 Building session context from {len(conversation_history)} turns")
            
            # Extract context data safely
            session_context_data = session_info.get("session_context", {})
            ongoing_topics = session_context_data.get("ongoing_topics", [])
            visa_types_mentioned = session_context_data.get("visa_types_mentioned", [])
            
            # Build session context object
            state["session_context"] = SessionContext(
                ongoing_topics=ongoing_topics,
                visa_types_mentioned=visa_types_mentioned,
                user_situation=session_context_data.get("user_situation"),
                previous_questions_summary=session_manager.build_session_context_string(actual_session_id)
            )
            
            # CRITICAL FIX: Enhanced follow-up question detection
            state["is_followup_question"] = session_manager.detect_followup_question(
                text, session_context_data
            )
            
            print(f"✅ Session context loaded successfully:")
            print(f"   📋 Turns: {len(conversation_history)}")
            print(f"   🔗 Follow-up: {state['is_followup_question']}")
            print(f"   🎯 Topics: {ongoing_topics}")
            print(f"   📋 Visas: {visa_types_mentioned}")
            
            # DEBUG: Show conversation history
            for i, turn in enumerate(conversation_history):
                print(f"   Q{i+1}: {turn.question[:30]}...")
                print(f"   A{i+1}: {turn.answer[:50]}...")
                
        else:
            print("📋 No conversation history found - treating as new session")
            state["session_context"] = SessionContext()
            state["is_followup_question"] = False
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR loading session context: {e}")
        import traceback
        traceback.print_exc()
        
        # Set safe defaults but don't fail - GUARANTEE state is valid
        state["session_context"] = SessionContext()
        state["is_followup_question"] = False
        state["conversation_history"] = []
        state["conversation_turn_number"] = 1
    
    print(f"✅ Initial state SUCCESSFULLY created for session: '{actual_session_id}'")
    print(f"   📊 Turn number: {state['conversation_turn_number']}")
    print(f"   🔗 Is follow-up: {state['is_followup_question']}")
    print(f"   📚 History length: {len(state.get('conversation_history', []))}")
    
    # CRITICAL: Guarantee we return a valid state object
    if state is None:
        print("❌ CRITICAL: State is None, creating emergency fallback")
        state = ImmigrationState(
            text=text,
            session_id=actual_session_id or "emergency-fallback",
            conversation_history=[],
            session_context=SessionContext(),
            is_followup_question=False,
            conversation_turn_number=1
        )
    
    return state

def save_conversation_result(final_state: ImmigrationState) -> None:
    """
    Save the conversation result to session history with improved error handling.
    """
    
    session_id = final_state.get("session_id")
    if not session_id:
        print("❌ No session ID found in final state - cannot save conversation")
        return
    
    user_question = final_state.get("text", "")
    synthesis_response = final_state.get("synthesis", "")
    
    print(f"💾 Attempting to save conversation:")
    print(f"   📱 Session: {session_id}")
    print(f"   ❓ Question: '{user_question[:50]}...'")
    print(f"   💬 Response: {len(synthesis_response)} chars")
    
    # IMPROVED: Better data validation
    if not user_question:
        print("❌ No user question found - cannot save conversation")
        return
        
    if not synthesis_response or len(synthesis_response.strip()) < 10:
        print(f"❌ Response too short or empty: '{synthesis_response[:50]}...'")
        return
    
    try:
        # IMPROVED: More robust conversation turn creation
        turn = ConversationTurn(
            question=user_question,
            answer=synthesis_response,
            timestamp=datetime.now().isoformat(),
            question_type=final_state.get("structured_analysis", {}).get("question_type"),
            visa_focus=final_state.get("structured_analysis", {}).get("visa_focus"),
            tools_used=final_state.get("tools_used", [])
        )
        
        # Save to session with enhanced error handling
        session_manager.save_conversation_turn(session_id, turn, final_state)
        
        print(f"✅ Conversation successfully saved to session: {session_id}")
        
    except Exception as e:
        print(f"❌ Failed to save conversation: {e}")
        print(f"   Session ID: {session_id}")
        print(f"   Question length: {len(user_question)}")
        print(f"   Response length: {len(synthesis_response)}")
        import traceback
        traceback.print_exc()

def visualize_graph(graph: StateGraph, save_path: str = OUTPUTS_DIR):
    """
    Visualize the enhanced workflow graph and save it.
    """
    print("📊 Visualizing the enhanced immigration workflow graph...")
    
    try:
        mermaid_text = graph.get_graph().draw_mermaid()
        print("\n📋 Workflow Structure:")
        print(mermaid_text)
        
        png = graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
        graph_path = os.path.join(save_path, "enhanced_immigration_workflow.png")
        
        with open(graph_path, "wb") as f:
            f.write(png)
        print(f"✅ Enhanced workflow graph saved to {graph_path}")
        
    except Exception as e:
        print(f"⚠️ Could not save graph visualization: {e}")
        print("💡 Graph structure is still functional, just visualization failed")

def run_agentic_askimmigrate(text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Enhanced function to run the strategic immigration workflow with COMPLETE session support.
    
    CRITICAL FIXES:
    - Guaranteed to handle None return from create_initial_state
    - Better session ID persistence throughout workflow
    - Improved error handling and recovery
    - Enhanced state management
    - More detailed logging and debugging
    - Robust conversation saving with fallbacks
    """
    print(f"🚀 Starting enhanced AskImmigrate workflow...")
    print(f"📋 Question: {text}")
    if session_id:
        print(f"📱 Session ID: {session_id}")
    print("-" * 60)
    
    # CRITICAL FIX: Handle potential None return from create_initial_state
    try:
        initial_state = create_initial_state(text, session_id)
        
        # GUARANTEE we have a valid state
        if initial_state is None:
            print("❌ CRITICAL: create_initial_state returned None, creating emergency state")
            initial_state = ImmigrationState(
                text=text,
                session_id=session_id or f"emergency-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                conversation_history=[],
                session_context=SessionContext(),
                is_followup_question=False,
                conversation_turn_number=1
            )
        
        actual_session_id = initial_state.get("session_id")
        
        if not actual_session_id:
            print("❌ No session ID in initial state, creating fallback")
            actual_session_id = f"fallback-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            initial_state["session_id"] = actual_session_id
            print(f"🔧 Using fallback session ID: {actual_session_id}")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR in create_initial_state: {e}")
        import traceback
        traceback.print_exc()
        
        # Create emergency fallback state
        actual_session_id = f"emergency-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        initial_state = ImmigrationState(
            text=text,
            session_id=actual_session_id,
            conversation_history=[],
            session_context=SessionContext(),
            is_followup_question=False,
            conversation_turn_number=1
        )
        print(f"🆘 Created emergency state with session: {actual_session_id}")
    
    try:
        # Create and run the enhanced graph
        graph = create_ask_immigrate_graph()
        
        # Visualize only on first run to avoid spam
        if not session_id or initial_state.get("conversation_turn_number", 1) == 1:
            visualize_graph(graph)
        
        print("🔄 Executing strategic workflow...")
        final_state = graph.invoke(initial_state)
        
        print("✅ Strategic workflow completed successfully!")
        
        # CRITICAL FIX: Ensure session ID is preserved in final state
        if actual_session_id and actual_session_id not in [None, ""]:
            final_state["session_id"] = actual_session_id
            print(f"📱 Preserving session ID in final state: {actual_session_id}")
            
            # IMPROVED: Save conversation with enhanced error handling
            try:
                save_conversation_result(final_state)
            except Exception as save_error:
                print(f"❌ Conversation save failed: {save_error}")
                print("⚠️ Workflow completed but conversation not saved to session")
        else:
            print("📱 No valid session ID - conversation not saved")
        
        # IMPROVED: Enhanced result summary with better data extraction
        print("\n📊 WORKFLOW EXECUTION SUMMARY:")
        print("-" * 50)
        
        # Session info
        if actual_session_id:
            turn_num = final_state.get("conversation_turn_number", 1)
            is_followup = final_state.get("is_followup_question", False)
            print(f"📱 Session: {actual_session_id}")
            print(f"🔢 Turn: #{turn_num}")
            print(f"🔗 Follow-up: {is_followup}")
        
        # Manager analysis
        structured_analysis = final_state.get("structured_analysis", {})
        if structured_analysis:
            print(f"🎯 Question Type: {structured_analysis.get('question_type', 'unknown')}")
            print(f"🎯 Complexity: {structured_analysis.get('complexity', 'unknown')}")
            print(f"🎯 Primary Focus: {structured_analysis.get('primary_focus', 'general')}")
            print(f"🎯 Visa Focus: {structured_analysis.get('visa_focus', [])}")
        
        # Tool usage
        tools_used = final_state.get("tools_used", [])
        print(f"🔧 Tools Used: {len(tools_used)} ({', '.join(tools_used) if tools_used else 'none'})")
        
        # Quality control
        revision_round = final_state.get("revision_round", 0)
        print(f"🔍 Review Rounds: {revision_round}")
        
        # Response metrics
        synthesis = final_state.get("synthesis", "")
        print(f"📝 Response Length: {len(synthesis)} characters")
        
        # IMPROVED: Add session ID to return data for external use
        final_state["session_id"] = actual_session_id
        
        return final_state
        
    except Exception as e:
        error_msg = f"Strategic workflow execution failed: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        
        # IMPROVED: Better error state with session preservation
        error_state = {
            "synthesis": f"""# Immigration Assistant Error

## ⚠️ Processing Issue

I encountered an issue while processing your question: "{text}"

**Error Details:** {error_msg}

## 📋 What You Can Do

1. **Try rephrasing your question** - Sometimes a slight rewording helps
2. **Check for typos** - Ensure your question is clear and complete
3. **Ask a more specific question** - Break complex questions into parts
4. **Contact support** if the issue persists

## 🔗 Official Resources

For immediate help with immigration questions:
- Visit [USCIS.gov](https://www.uscis.gov) for official forms and information
- Use the [USCIS Contact Center](https://www.uscis.gov/contactcenter) for specific cases
- Consult with a qualified immigration attorney for legal advice

*This error has been logged. Our team will work to improve the system.*
""",
            "error": error_msg,
            "manager_decision": "Workflow failed during execution",
            "tool_results": {},
            "tools_used": [],
            "text": text,
            "session_id": actual_session_id,  # Preserve session even in error
            "workflow_parameters": {
                "question_type": "error",
                "complexity": "unknown",
                "primary_focus": "error handling"
            }
        }
        
        # IMPROVED: Still try to save error to session for debugging
        if actual_session_id:
            try:
                save_conversation_result(error_state)
                print(f"📱 Error state saved to session: {actual_session_id}")
            except:
                print("📱 Could not save error state to session")
        
        return error_state

def list_sessions() -> List[Dict[str, Any]]:
    """
    List all agentic workflow sessions.
    """
    try:
        return session_manager.list_all_sessions()
    except Exception as e:
        print(f"❌ Error listing sessions: {e}")
        return []

if __name__ == "__main__":
    print("=" * 80)
    print("ENHANCED ASKIMMIGRATE 2.0 - SESSION-AWARE STRATEGIC WORKFLOW TEST")
    print("=" * 80)

    # Test the enhanced workflow with sessions
    test_session_id = f"test-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    test_conversations = [
        ("What is an F-1 visa?", "First question about F-1 visa"),
        ("How do I extend it?", "Follow-up question about extension"),
        ("What are the fees involved?", "Follow-up about fees"),
        ("Can I work while on F-1?", "Follow-up about work authorization"),
    ]
    
    print(f"🧪 Testing with session: {test_session_id}")
    
    for i, (question, description) in enumerate(test_conversations, 1):
        print(f"\n🧪 TEST {i}/{len(test_conversations)}: {description}")
        print("=" * 60)
        
        try:
            results = run_agentic_askimmigrate(text=question, session_id=test_session_id)
            
            if "error" not in results:
                response_length = len(results.get("synthesis", ""))
                tools_used = len(results.get("tools_used", []))
                print(f"✅ Test {i} completed successfully")
                print(f"   📝 Response: {response_length} chars")
                print(f"   🔧 Tools: {tools_used}")
                print(f"   📱 Session: {results.get('session_id', 'N/A')}")
            else:
                print(f"❌ Test {i} failed: {results.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Test {i} crashed: {e}")
        
        print("\n" + "="*60)

    print("\n🎉 Enhanced session-aware workflow testing completed!")
    
    # List final session state
    print(f"\n📱 Final Session State for {test_session_id}:")
    try:
        sessions = list_sessions()
        test_session = next((s for s in sessions if s['session_id'] == test_session_id), None)
        if test_session:
            print(f"  • Turns: {test_session['turn_count']}")
            print(f"  • Last active: {test_session['updated_at']}")
        else:
            print("  • Session not found in database")
    except Exception as e:
        print(f"  • Error checking session: {e}")
    
    print("\n🔗 Check outputs/ directory for workflow visualization")