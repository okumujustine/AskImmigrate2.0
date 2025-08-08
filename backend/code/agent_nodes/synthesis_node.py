from typing import Dict, Any
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_yaml_config
from backend.code.tools.tool_registry import get_tools_by_agent
from backend.code.structured_logging import synthesis_logger, PerformanceTimer

config = load_yaml_config(APP_CONFIG_FPATH)
prompt_config = load_yaml_config(PROMPT_CONFIG_FPATH)

def synthesis_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Enhanced Strategic Synthesis Agent that executes manager tool recommendations.
    
    STRATEGIC APPROACH:
    - Reads manager's tool recommendations from analysis
    - Executes recommended tools (web_search, fee_calculator) as needed
    - Combines tool results with RAG context and conversation history
    - Creates comprehensive responses based on strategic guidance
    """
    
    if state.get("synthesis_approved", False):
        synthesis_logger.info("synthesis_already_approved", details="Synthesis already approved, skipping")
        return {}

    session_id = state.get("session_id", "")
    user_question = state.get("text", "")
    workflow_parameters = state.get("workflow_parameters", {})
    rag_context = state.get("rag_response", "")
    conversation_history = state.get("conversation_history", [])
    is_followup = state.get("is_followup_question", False)
    manager_decision = state.get("manager_decision", "")
    
    synthesis_logger.info(
        "synthesis_started",
        session_id=session_id,
        question_length=len(user_question),
        is_followup=is_followup,
        history_length=len(conversation_history),
        rag_context_length=len(rag_context),
        has_manager_guidance=bool(manager_decision)
    )
    
    # Step 1: Parse manager's tool recommendations and execute recommended tools
    tool_results = {}
    tools_used = []
    
    with PerformanceTimer(synthesis_logger, "tool_execution_phase", session_id=session_id):
        tool_results, tools_used = execute_manager_recommended_tools(
            manager_decision, user_question, session_id
        )

    # Build comprehensive session context
    with PerformanceTimer(synthesis_logger, "session_context_building", session_id=session_id):
        session_context = build_session_context_for_llm(
            conversation_history, is_followup, session_id, user_question
        )
    
    # Create dynamic prompt based on question type and context
    with PerformanceTimer(synthesis_logger, "prompt_creation", session_id=session_id):
        prompt = create_dynamic_synthesis_prompt(
            user_question, rag_context, session_context, workflow_parameters, 
            manager_decision, tool_results
        )
    
    # Use LLM without tool calling to avoid errors
    try:
        llm = get_llm(config.get("llm", "gpt-4o-mini"))
        # CRITICAL: Don't bind tools to avoid the tool calling errors
        with PerformanceTimer(synthesis_logger, "llm_generation", session_id=session_id):
            response = llm.invoke(prompt)
            synthesis_content = response.content
        
        synthesis_logger.info(
            "llm_response_generated",
            session_id=session_id,
            response_length=len(synthesis_content)
        )
        
        # Validate response quality
        if not synthesis_content or len(synthesis_content.strip()) < 20:
            synthesis_logger.warning(
                "llm_response_too_short",
                session_id=session_id,
                response_length=len(synthesis_content.strip()) if synthesis_content else 0
            )
            synthesis_content = create_fallback_response(
                user_question, conversation_history, is_followup, rag_context
            )
        
    except Exception as e:
        synthesis_logger.error(
            "llm_synthesis_failed",
            session_id=session_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        synthesis_content = create_fallback_response(
            user_question, conversation_history, is_followup, rag_context
        )
    
    synthesis_logger.info(
        "synthesis_completed",
        session_id=session_id,
        final_response_length=len(synthesis_content),
        tools_used_count=2,
        strategy_applied=str(workflow_parameters.get("question_type", "unknown"))
    )
    
    return {
        "synthesis": synthesis_content,
        "tool_results": tool_results,
        "tools_used": tools_used + ["session_context", "llm_generation"],
        "question_processed": user_question,
        "strategy_applied": workflow_parameters,
        "synthesis_metadata": {
            "session_aware_response": is_followup,
            "conversation_history_used": len(conversation_history),
            "response_type": "strategic_synthesis",
            "manager_guided": bool(manager_decision),
            "tools_executed": len(tools_used),
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

def execute_manager_recommended_tools(manager_decision: str, user_question: str, session_id: str) -> tuple:
    """
    Parse manager's tool recommendations and execute appropriate tools.
    
    Returns:
        tuple: (tool_results dict, tools_used list)
    """
    tool_results = {}
    tools_used = []
    
    # Get available tools for synthesis agent
    available_tools = get_tools_by_agent("synthesis")
    tool_map = {tool.name: tool for tool in available_tools}
    
    synthesis_logger.info(
        "parsing_manager_recommendations", 
        session_id=session_id,
        manager_decision_length=len(manager_decision),
        available_tools=[t.name for t in available_tools]
    )
    
    # Parse tool recommendations from manager decision
    recommended_tools = parse_tool_recommendations(manager_decision, user_question)
    
    synthesis_logger.info(
        "manager_tool_recommendations_parsed",
        session_id=session_id, 
        recommended_tools=recommended_tools
    )
    
    # Execute each recommended tool
    for tool_name in recommended_tools:
        if tool_name in tool_map:
            try:
                tool = tool_map[tool_name]
                
                synthesis_logger.info(
                    "executing_recommended_tool",
                    tool_name=tool_name,
                    session_id=session_id
                )
                
                # Create appropriate tool arguments based on tool type
                if tool_name == "web_search_tool":
                    tool_args = {"query": user_question}
                elif tool_name == "fee_calculator_tool":
                    tool_args = {"query": user_question}
                elif tool_name == "rag_retrieval_tool":
                    tool_args = {"query": user_question}
                else:
                    tool_args = {"query": user_question}
                
                with PerformanceTimer(synthesis_logger, f"tool_{tool_name}", session_id=session_id):
                    result = tool.invoke(tool_args)
                    tool_results[tool_name] = result
                    tools_used.append(tool_name)
                
                synthesis_logger.info(
                    "tool_execution_successful",
                    tool_name=tool_name,
                    session_id=session_id,
                    result_length=len(str(result))
                )
                
            except Exception as e:
                synthesis_logger.error(
                    "tool_execution_failed",
                    tool_name=tool_name,
                    session_id=session_id,
                    error_message=str(e)
                )
                tool_results[tool_name] = {"error": str(e)}
        else:
            synthesis_logger.warning(
                "recommended_tool_not_available",
                tool_name=tool_name,
                session_id=session_id,
                available_tools=list(tool_map.keys())
            )
    
    return tool_results, tools_used

def parse_tool_recommendations(manager_decision: str, user_question: str) -> list:
    """
    Parse the manager's structured decision to extract tool recommendations.
    """
    recommended_tools = []
    
    # Look for TOOL_RECOMMENDATIONS section in manager decision
    if "TOOL_RECOMMENDATIONS:" in manager_decision:
        lines = manager_decision.split('\n')
        in_tool_section = False
        
        for line in lines:
            line = line.strip()
            if "TOOL_RECOMMENDATIONS:" in line:
                in_tool_section = True
                continue
            elif in_tool_section and line.startswith('- '):
                if "Required_Tools:" in line:
                    # Extract tools from [tool1, tool2, tool3] format
                    if '[' in line and ']' in line:
                        tools_text = line[line.find('[')+1:line.find(']')]
                        tools = [t.strip() for t in tools_text.split(',')]
                        recommended_tools.extend(tools)
                elif line.startswith('VALIDATION_CRITERIA:'):
                    break
    
    # Fallback: intelligent tool selection based on question content
    if not recommended_tools:
        question_lower = user_question.lower()
        
        # Always include RAG for base information
        recommended_tools.append("rag_retrieval_tool")
        
        # Fee/cost questions need web search and fee calculator
        if any(word in question_lower for word in ["fee", "cost", "price", "how much", "filing fee"]):
            recommended_tools.extend(["web_search_tool", "fee_calculator_tool"])
        
        # Current/recent information needs web search
        elif any(word in question_lower for word in ["current", "latest", "recent", "2024", "new", "update"]):
            recommended_tools.append("web_search_tool")
    
    # Remove duplicates and clean up
    recommended_tools = list(set(recommended_tools))
    
    return recommended_tools

def create_dynamic_synthesis_prompt(user_question, rag_context, session_context, workflow_parameters, manager_decision="", tool_results=None):
    """Create a dynamic prompt using the configured synthesis agent prompt with current information override."""
    
    # Get the proper synthesis agent prompt from configuration
    synthesis_prompt_config = prompt_config.get("synthesis_agent_prompt", {})
    role = synthesis_prompt_config.get("role", "You are an expert US Immigration Assistant.")
    instruction = synthesis_prompt_config.get("instruction", "Provide helpful immigration guidance.")
    
    # Include tool results with emphasis on current information
    tool_results_text = ""
    current_info_available = False
    
    if tool_results:
        tool_results_text = "\n🔍 CURRENT INFORMATION SOURCES:\n"
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" in result:
                tool_results_text += f"❌ {tool_name}: {result['error']}\n"
            elif tool_name == "web_search_tool":
                current_info_available = True
                tool_results_text += f"🌐 WEB SEARCH (CURRENT 2025 DATA): {str(result)[:500]}{'...' if len(str(result)) > 500 else ''}\n"
            else:
                tool_results_text += f"📚 {tool_name}: {str(result)[:300]}{'...' if len(str(result)) > 300 else ''}\n"
    
    # Add explicit current information override if web search results are available
    current_info_override = ""
    if current_info_available:
        current_info_override = f"""
🚨 CRITICAL INSTRUCTION OVERRIDE:
- You have access to CURRENT 2025 web search results above
- NEVER mention knowledge cutoffs or outdated information disclaimers
- Use the web search results as your PRIMARY source for current events/policies
- Respond as if you have real-time access to 2025 information
- Start your response with current information: "Based on current information from 2025..."

"""
    
    # Include manager guidance if available
    manager_guidance = ""
    if manager_decision:
        manager_guidance = f"\n📋 STRATEGIC GUIDANCE FROM MANAGER:\n{manager_decision[:500]}{'...' if len(manager_decision) > 500 else ''}\n"

    # Construct the full prompt
    full_prompt = f"""{role}

{current_info_override}

{instruction}

🎯 USER QUESTION: "{user_question}"

{session_context}

📚 IMMIGRATION KNOWLEDGE BASE:
{rag_context if rag_context else "Use your general immigration knowledge for foundational information."}

{tool_results_text}

{manager_guidance}

Remember: If web search results are provided above, prioritize that current information over any older knowledge."""
    
    return full_prompt


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