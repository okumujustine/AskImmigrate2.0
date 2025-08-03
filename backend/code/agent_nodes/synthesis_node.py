from typing import Dict, Any
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
from backend.code.tools.tool_registry import get_tools_by_agent
from backend.code.structured_logging import synthesis_logger, PerformanceTimer

config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)

try:
    from backend.code.multilingual.translation_service import translation_service
    MULTILINGUAL_AVAILABLE = True
except ImportError:
    MULTILINGUAL_AVAILABLE = False
    synthesis_logger.warning("Multilingual support not available")

import asyncio

# Add this function to your existing synthesis_node.py
async def generate_multilingual_response(user_question: str, language_info: Dict[str, Any], 
                                       english_response: str, session_id: str) -> tuple:
    """Generate response in user's language"""
    
    target_language = language_info.get("language", "en")
    
    if not MULTILINGUAL_AVAILABLE or target_language == "en":
        return english_response, None
    
    try:
        if target_language == "es":
            # FIXED: Use the correct method name from your translation service
            result = await translation_service.get_native_response(user_question, "es")
            
            synthesis_logger.info(
                "native_spanish_response_generated",
                session_id=session_id,
                method=result.translation_method,
                confidence=result.confidence
            )
            
            return result.translated_text, {
                "method": result.translation_method,
                "confidence": result.confidence,
                "processing_time": result.processing_time,
                "native_response": True
            }
        
        else:
            # FIXED: Use the correct method for translation
            result = await translation_service.translate_text(
                text=english_response, 
                target_lang=target_language,
                source_lang="en",
                use_immigration_context=True
            )
            
            synthesis_logger.info(
                "translated_response_generated",
                session_id=session_id,
                target_language=target_language,
                method=result.translation_method,
                confidence=result.confidence
            )
            
            return result.translated_text, {
                "method": result.translation_method,
                "confidence": result.confidence,
                "processing_time": result.processing_time,
                "translated_from": "en"
            }
    
    except Exception as e:
        synthesis_logger.error(
            "multilingual_response_failed",
            session_id=session_id,
            target_language=target_language,
            error=str(e)
        )
        
        # Fallback to English
        return english_response, {
            "method": "english_fallback",
            "error": str(e),
            "fallback_used": True
        }
    
async def synthesis_node(state: ImmigrationState) -> Dict[str, Any]:
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
    
    # IMPROVEMENT: Validate inputs early
    if not user_question or len(user_question.strip()) < 3:
        synthesis_logger.warning("invalid_user_question", session_id=session_id, question_length=len(user_question))
        return create_error_response("Invalid or empty question provided", session_id)
    
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
        has_manager_guidance=bool(manager_decision),
        multilingual_available=MULTILINGUAL_AVAILABLE
    )
    
    try:
        # Step 1: Execute tools with better error handling
        tool_results = {}
        tools_used = []
        
        with PerformanceTimer(synthesis_logger, "tool_execution_phase", session_id=session_id):
            try:
                tool_results, tools_used = execute_manager_recommended_tools(
                    manager_decision, user_question, session_id
                )
            except Exception as e:
                synthesis_logger.error("tool_execution_failed", session_id=session_id, error=str(e))
                # Continue with empty tool results instead of failing
                tool_results, tools_used = {}, []

        # Step 2: Build session context
        with PerformanceTimer(synthesis_logger, "session_context_building", session_id=session_id):
            session_context = build_session_context_for_llm(
                conversation_history, is_followup, session_id, user_question
            )
        
        # Step 3: Create prompt
        with PerformanceTimer(synthesis_logger, "prompt_creation", session_id=session_id):
            prompt = create_dynamic_synthesis_prompt(
                user_question, rag_context, session_context, workflow_parameters, 
                manager_decision, tool_results
            )
        
        # Step 4: Generate response with better error handling
        synthesis_content = ""
        try:
            llm = get_llm(config.get("llm", "gpt-4o-mini"))
            with PerformanceTimer(synthesis_logger, "llm_generation", session_id=session_id):
                response = llm.invoke(prompt)
                synthesis_content = response.content if hasattr(response, 'content') else str(response)
            
            synthesis_logger.info(
                "llm_response_generated",
                session_id=session_id,
                response_length=len(synthesis_content)
            )
            
        except Exception as e:
            synthesis_logger.error(
                "llm_generation_failed",
                session_id=session_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            # Don't return immediately, let fallback handle it
            synthesis_content = ""
        
        # Step 5: Validate and handle poor responses
        if not synthesis_content or len(synthesis_content.strip()) < 20:
            synthesis_logger.warning(
                "poor_llm_response_using_fallback",
                session_id=session_id,
                response_length=len(synthesis_content.strip()) if synthesis_content else 0
            )
            synthesis_content = create_fallback_response(
                user_question, conversation_history, is_followup, rag_context
            )
        
        # Step 6: MULTILINGUAL PROCESSING
        language_info = state.get("language_info", {"language": "en"})
        translation_info = None
        
        # IMPROVED: Better language detection and processing
        target_language = language_info.get("language", "en")
        requires_multilingual = (
            target_language != "en" or 
            language_info.get("requires_translation", False)
        )
        
        if requires_multilingual and MULTILINGUAL_AVAILABLE:
            try:
                synthesis_logger.info(
                    "attempting_multilingual_response",
                    session_id=session_id,
                    target_language=target_language,
                    requires_translation=language_info.get("requires_translation", False)
                )
                
                multilingual_content, translation_info = await generate_multilingual_response(
                    user_question, language_info, synthesis_content, session_id
                )
                
                if multilingual_content and multilingual_content != synthesis_content:
                    original_length = len(synthesis_content)
                    synthesis_content = multilingual_content
                    
                    synthesis_logger.info(
                        "multilingual_response_applied",
                        session_id=session_id,
                        target_language=target_language,
                        original_length=original_length,
                        translated_length=len(multilingual_content)
                    )
                
            except Exception as e:
                synthesis_logger.error(
                    "multilingual_processing_failed",
                    session_id=session_id,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                # Keep English response as fallback
                translation_info = {
                    "method": "english_fallback_due_to_error",
                    "error": str(e),
                    "fallback_used": True
                }
        
        elif requires_multilingual and not MULTILINGUAL_AVAILABLE:
            synthesis_logger.warning(
                "multilingual_requested_but_unavailable",
                session_id=session_id,
                target_language=target_language
            )
            translation_info = {
                "method": "multilingual_service_unavailable",
                "fallback_used": True
            }

        # IMPROVEMENT: Enhanced logging for completion
        synthesis_logger.info(
            "synthesis_completed_successfully",
            session_id=session_id,
            final_response_length=len(synthesis_content),
            tools_used_count=len(tools_used),
            strategy_applied=str(workflow_parameters.get("question_type", "unknown")),
            target_language=target_language,
            translation_applied=bool(translation_info)
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
                "fallback_used": len(synthesis_content) < 100,  # Better fallback detection
                "user_language": target_language,
                "requires_translation": requires_multilingual,
                "translation_info": translation_info,
                "multilingual_enabled": MULTILINGUAL_AVAILABLE,
                "processing_successful": True
            }
        }
        
    except Exception as e:
        # IMPROVEMENT: Comprehensive error handling
        synthesis_logger.error(
            "synthesis_node_critical_failure",
            session_id=session_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        
        return create_error_response(f"Synthesis failed: {str(e)}", session_id, state)

# 3. NEW: Helper function for error responses
def create_error_response(error_message: str, session_id: str, state: ImmigrationState = None) -> Dict[str, Any]:
    """Create standardized error response"""
    
    user_question = state.get("text", "") if state else ""
    language = state.get("language_info", {}).get("language", "en") if state else "en"
    
    # Language-specific error messages
    if language == "es":
        fallback_text = f"""# Error en el Procesamiento

## Su Pregunta: "{user_question}"

Disculpe, pero encontré un problema técnico procesando su pregunta: {error_message}

## Recursos Alternativos:
- **USCIS:** https://www.uscis.gov/es
- **Centro de Contacto:** https://www.uscis.gov/es/contactcenter

Por favor, intente de nuevo más tarde."""
    else:
        fallback_text = f"""# Processing Error

## Your Question: "{user_question}"

I apologize, but I encountered a technical issue processing your question: {error_message}

## Alternative Resources:
- **USCIS Website:** https://www.uscis.gov
- **USCIS Contact Center:** https://www.uscis.gov/contactcenter

Please try again later."""
    
    return {
        "synthesis": fallback_text,
        "tool_results": {},
        "tools_used": ["error_handler"],
        "question_processed": user_question,
        "strategy_applied": {"error": "processing_failed"},
        "synthesis_metadata": {
            "response_type": "error_response",
            "error_message": error_message,
            "processing_successful": False,
            "user_language": language,
            "multilingual_enabled": MULTILINGUAL_AVAILABLE
        }
    }

# 4. IMPROVEMENT: Enhanced fallback with multilingual support
def create_fallback_response(user_question, conversation_history, is_followup, rag_context, language="en"):
    """Create a smart fallback response with multilingual support"""
    
    question_lower = user_question.lower()
    
    # Determine response language and templates
    if language == "es":
        templates = {
            "session_title": "Su Historial de Conversación",
            "your_question": "Su Pregunta:",
            "first_question": "Su primera pregunta fue:",
            "conversation_so_far": "Hemos tenido {} {} en esta conversación:",
            "turn": "turno", "turns": "turnos",
            "current_session": "Sesión Actual:",
            "immigration_info": "Información de Inmigración",
            "resources": "Recursos Oficiales de Inmigración:",
            "verify": "Siempre verifique la información con fuentes oficiales de USCIS."
        }
    else:
        templates = {
            "session_title": "Your Conversation History",
            "your_question": "Your Question:",
            "first_question": "Your first question was:",
            "conversation_so_far": "We've had {} {} in this conversation:",
            "turn": "turn", "turns": "turns",
            "current_session": "Current Session:",
            "immigration_info": "Immigration Information",
            "resources": "Official Immigration Resources:",
            "verify": "Always verify information with official USCIS sources for the most current requirements."
        }
    
    # Handle session reference questions
    if is_followup and conversation_history and any(phrase in question_lower for phrase in [
        "first question", "what did i ask", "previous", "earlier", "what was",
        "primera pregunta", "qué pregunté", "anterior", "antes"
    ]):
        first_turn = conversation_history[0]
        count = len(conversation_history)
        turn_word = templates["turn"] if count == 1 else templates["turns"]
        
        return f"""# {templates["session_title"]}

## {templates["your_question"]} "{user_question}"

### {templates["first_question"]}
**"{first_turn.question}"**

### {templates["conversation_so_far"].format(count, turn_word)}
""" + "\n".join([f"**Turn {i+1}:** {turn.question}" for i, turn in enumerate(conversation_history)]) + f"""

### {templates["current_session"]}
- Session ID: {conversation_history[0].timestamp.split('T')[0] if conversation_history else 'Unknown'}
- Total questions: {len(conversation_history)}

{templates["verify"]}
"""
    
    # Default immigration info response
    else:
        return f"""# {templates["immigration_info"]}

## {templates["your_question"]} "{user_question}"

{rag_context if rag_context else f"I understand you're asking about immigration. While I don't have specific information immediately available, I can guide you to the right resources."}

## {templates["resources"]}
- **USCIS Website:** https://www.uscis.gov{"" if language == "en" else "/es"}
- **USCIS Contact Center:** https://www.uscis.gov/{"contactcenter" if language == "en" else "es/contactcenter"}
- **Forms and Fees:** https://www.uscis.gov/{"forms" if language == "en" else "es/formularios"}

{templates["verify"]}
"""

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
    
    # Include tool results if available
    tool_results_text = ""
    if tool_results:
        tool_results_text = "\nTOOL RESULTS:\n"
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" in result:
                tool_results_text += f"- {tool_name}: ERROR - {result['error']}\n"
            else:
                tool_results_text += f"- {tool_name}: {str(result)[:200]}{'...' if len(str(result)) > 200 else ''}\n"
    
    # Include manager guidance if available
    manager_guidance = ""
    if manager_decision:
        manager_guidance = f"\nMANAGER STRATEGIC GUIDANCE:\n{manager_decision[:500]}{'...' if len(manager_decision) > 500 else ''}\n"

    # Base instruction
    base_instruction = f"""You are an expert US Immigration Assistant. Answer the user's question: "{user_question}"

{session_context}

IMMIGRATION KNOWLEDGE:
{rag_context if rag_context else "Use your general immigration knowledge."}

{tool_results_text}

{manager_guidance}

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