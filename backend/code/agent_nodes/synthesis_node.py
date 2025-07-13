from typing import Dict, Any
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
from backend.code.tools.tool_registry import get_tools_by_agent

config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)

def synthesis_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Dynamic Session-Aware Synthesis that handles ALL types of follow-up questions.
    
    DYNAMIC APPROACH:
    - Builds comprehensive context from conversation history
    - Uses session-aware prompting for the LLM
    - Handles any type of follow-up question intelligently
    - Falls back gracefully when session context isn't available
    """
    
    if state.get("synthesis_approved", False):
        print("📝 Synthesis: Already approved, skipping...")
        return {}

    print("📝 Synthesis: Creating dynamic session-aware response...")

    user_question = state.get("text", "")
    workflow_parameters = state.get("workflow_parameters", {})
    rag_context = state.get("rag_response", "")
    conversation_history = state.get("conversation_history", [])
    is_followup = state.get("is_followup_question", False)
    session_id = state.get("session_id", "")
    
    print(f"📄 Synthesis inputs:")
    print(f"   ❓ Question: {user_question[:50]}...")
    print(f"   🔗 Is follow-up: {is_followup}")
    print(f"   📚 History: {len(conversation_history)} turns")
    print(f"   📚 RAG context: {len(rag_context)} chars")

    # Build comprehensive session context
    session_context = build_session_context_for_llm(
        conversation_history, is_followup, session_id, user_question
    )
    
    # Create dynamic prompt based on question type and context
    prompt = create_dynamic_synthesis_prompt(
        user_question, rag_context, session_context, workflow_parameters
    )
    
    # Use LLM without tool calling to avoid errors
    try:
        llm = get_llm(config.get("llm", "gpt-4o-mini"))
        # CRITICAL: Don't bind tools to avoid the tool calling errors
        response = llm.invoke(prompt)
        synthesis_content = response.content
        
        print(f"✅ LLM generated response: {len(synthesis_content)} chars")
        
        # Validate response quality
        if not synthesis_content or len(synthesis_content.strip()) < 20:
            print("⚠️ LLM response too short, creating fallback")
            synthesis_content = create_fallback_response(
                user_question, conversation_history, is_followup, rag_context
            )
        
    except Exception as e:
        print(f"❌ LLM synthesis failed: {e}")
        synthesis_content = create_fallback_response(
            user_question, conversation_history, is_followup, rag_context
        )
    
    return {
        "synthesis": synthesis_content,
        "tool_results": {},
        "tools_used": ["session_context", "llm_generation"],
        "question_processed": user_question,
        "strategy_applied": workflow_parameters,
        "synthesis_metadata": {
            "session_aware_response": is_followup,
            "conversation_history_used": len(conversation_history),
            "response_type": "dynamic_synthesis",
            "fallback_used": "LLM" not in str(type(synthesis_content))
        }
    }

def build_session_context_for_llm(conversation_history, is_followup, session_id, current_question):
    """Build comprehensive session context for the LLM to use."""
    
    if not conversation_history or not is_followup:
        return ""
    
    context = f"""
📋 CONVERSATION CONTEXT (Session: {session_id})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 FOLLOW-UP DETECTED: This question appears to reference our previous conversation.

📝 PREVIOUS CONVERSATION:
"""
    
    for i, turn in enumerate(conversation_history, 1):
        context += f"""
Turn {i}:
Q: {turn.question}
A: {turn.answer[:300]}{'...' if len(turn.answer) > 300 else ''}
"""
    
    context += f"""
📊 SESSION STATS:
• Total previous turns: {len(conversation_history)}
• Current question: "{current_question}"
• First question was: "{conversation_history[0].question if conversation_history else 'None'}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return context

def create_dynamic_synthesis_prompt(user_question, rag_context, session_context, workflow_parameters):
    """Create a dynamic prompt that can handle any type of follow-up question."""
    
    # Detect question type for tailored response
    question_lower = user_question.lower()
    
    if any(phrase in question_lower for phrase in ["first question", "what did i ask", "previous", "earlier"]):
        instruction_type = "session_reference"
    elif any(phrase in question_lower for phrase in ["extend", "renew", "how do i", "what about"]):
        instruction_type = "follow_up_immigration"
    elif any(phrase in question_lower for phrase in ["fee", "cost", "price", "how much"]):
        instruction_type = "fee_inquiry"
    else:
        instruction_type = "general"
    
    # Base instruction
    base_instruction = f"""You are an expert US Immigration Assistant. Answer the user's question: "{user_question}"

{session_context}

IMMIGRATION KNOWLEDGE:
{rag_context if rag_context else "Use your general immigration knowledge."}

TASK INSTRUCTIONS:
"""
    
    # Add specific instructions based on question type
    if instruction_type == "session_reference":
        base_instruction += """
🎯 SESSION REFERENCE QUESTION: The user is asking about our previous conversation.
- Use the conversation context above to answer their question
- Be specific about what was discussed before
- Reference exact questions and topics from the session
- If they ask about "first question", tell them exactly what it was
"""
    
    elif instruction_type == "follow_up_immigration":
        base_instruction += """
🎯 IMMIGRATION FOLLOW-UP: The user is asking a follow-up immigration question.
- Use both the conversation context AND immigration knowledge
- Reference what was discussed before when relevant
- Build upon previous answers to provide continuity
- Provide specific immigration guidance for their follow-up
"""
    
    elif instruction_type == "fee_inquiry":
        base_instruction += """
🎯 FEE QUESTION: The user is asking about immigration costs.
- Reference any visa types discussed in previous conversation
- Provide current fee information
- Explain what the fees cover
- Include disclaimer about checking official sources
"""
    
    else:
        base_instruction += """
🎯 GENERAL IMMIGRATION QUESTION: Provide comprehensive immigration guidance.
- Use the immigration knowledge provided
- Reference conversation context if relevant
- Provide accurate, helpful information
- Include appropriate disclaimers
"""
    
    base_instruction += """

RESPONSE FORMAT:
- Use clear markdown formatting
- Start with a direct answer to their question
- Include relevant details and context
- Add official resource links
- Keep it conversational and helpful

CRITICAL: If this is a follow-up question, reference the previous conversation naturally.
"""
    
    return base_instruction

def create_fallback_response(user_question, conversation_history, is_followup, rag_context):
    """Create a smart fallback response when LLM fails."""
    
    question_lower = user_question.lower()
    
    # Handle session reference questions directly
    if is_followup and conversation_history and any(phrase in question_lower for phrase in [
        "first question", "what did i ask", "previous", "earlier", "what was"
    ]):
        
        first_turn = conversation_history[0]
        
        return f"""# Your Conversation History

## Your Question: "{user_question}"

Based on our conversation history, here's what I can tell you:

### Your First Question
Your first question was: **"{first_turn.question}"**

### Our Conversation So Far
We've had {len(conversation_history)} {'turn' if len(conversation_history) == 1 else 'turns'} in this conversation:

""" + "\n".join([f"**Turn {i+1}:** {turn.question}" for i, turn in enumerate(conversation_history)]) + f"""

### Current Session
- Session ID: {conversation_history[0].timestamp.split('T')[0] if conversation_history else 'Unknown'}
- Total questions asked: {len(conversation_history)}

Is there anything specific about our previous conversation you'd like me to clarify or expand on?
"""
    
    # Handle general follow-up questions
    elif is_followup and conversation_history:
        return f"""# Follow-up Response

## Your Question: "{user_question}"

I can see this is a follow-up to our previous conversation where you asked about: **"{conversation_history[-1].question}"**

{rag_context if rag_context else "I'd be happy to help with your follow-up question. Could you provide a bit more detail about what specific aspect you'd like me to address?"}

### Previous Context
""" + "\n".join([f"- **Q{i+1}:** {turn.question}" for i, turn in enumerate(conversation_history[-2:])]) + """

### How I Can Help
Feel free to ask more specific questions about any of the topics we've discussed, or let me know if you need clarification on anything!
"""
    
    # Handle new questions
    else:
        return f"""# Immigration Information

## Your Question: "{user_question}"

{rag_context if rag_context else f"I understand you're asking about {user_question}. While I don't have specific information immediately available, I can guide you to the right resources."}

## Official Immigration Resources
- **USCIS Website:** https://www.uscis.gov - Complete immigration information
- **USCIS Contact Center:** https://www.uscis.gov/contactcenter - Phone support  
- **Forms and Fees:** https://www.uscis.gov/forms - Official forms and current fees

## Next Steps
1. Visit the USCIS website for detailed information
2. Contact USCIS directly for specific guidance
3. Consider consulting with a qualified immigration attorney

*Always verify information with official USCIS sources for the most current requirements.*
"""