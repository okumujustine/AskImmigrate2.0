from typing import Dict, Any
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_yaml_config
from backend.code.tools.tool_registry import get_tools_by_agent
from backend.code.structured_logging import synthesis_logger, PerformanceTimer
from langdetect import detect, detect_langs
from langdetect.lang_detect_exception import LangDetectException
config = load_yaml_config(APP_CONFIG_FPATH)
prompt_config = load_yaml_config(PROMPT_CONFIG_FPATH)

def detect_and_validate_language(user_question: str, conversation_history: list, session_id: str) -> Dict[str, Any]:
    """
    CRITICAL FIX: Enhanced language detection that properly preserves session language preferences.
    
    This fixes the specific issue where follow-up questions incorrectly overwrite session language preferences.
    """
    
    from backend.code.session_manager import session_manager
    
    synthesis_logger.info(
        "language_detection_started_with_session_manager",
        session_id=session_id,
        question_preview=user_question[:50],
        has_conversation_history=bool(conversation_history)
    )
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "es": "Spanish", 
        "fr": "French",
        "pt": "Portuguese"
    }
    
    # CRITICAL FIX: Check for follow-up patterns FIRST before any language detection
    is_likely_followup = False
    followup_confidence = 0.0
    
    if conversation_history and len(conversation_history) > 0:
        # Enhanced follow-up detection patterns
        strong_followup_patterns = [
            "how much", "cost", "fee", "price", "cuánto", "cuesto", "precio", "costo",
            "what about", "and what", "can i also", "additionally", "también", "además",
            "it", "that", "this", "ese", "eso", "este", "esta", "esa",
            "more details", "tell me more", "más detalles", "más información",
            "and", "y", "también", "also", "plus", "además"
        ]
        
        question_lower = user_question.lower()
        
        # Check for strong follow-up indicators
        followup_matches = [pattern for pattern in strong_followup_patterns if pattern in question_lower]
        
        if followup_matches:
            is_likely_followup = True
            followup_confidence = 0.95  # Very high confidence for strong patterns
            synthesis_logger.info(
                "strong_followup_patterns_detected",
                session_id=session_id,
                patterns_found=followup_matches,
                confidence=followup_confidence
            )
        
        # Also check for very short questions (often follow-ups)
        elif len(user_question.split()) <= 4:
            is_likely_followup = True
            followup_confidence = 0.8  # High confidence for short questions
            synthesis_logger.info(
                "short_question_followup_detected",
                session_id=session_id,
                word_count=len(user_question.split()),
                confidence=followup_confidence
            )
    
    # STEP 1: Get session language preference
    session_language = session_manager.get_session_language_preference(session_id)
    
    synthesis_logger.info(
        "session_language_preference_retrieved",
        session_id=session_id,
        session_language=session_language,
        has_session_context=bool(session_language),
        is_likely_followup=is_likely_followup,
        followup_confidence=followup_confidence
    )
    
    # CRITICAL FIX: If this is a follow-up and we have session language, ALWAYS USE IT
    if is_likely_followup and session_language and session_language in SUPPORTED_LANGUAGES:
        synthesis_logger.info(
            "maintaining_session_language_for_followup",
            session_id=session_id,
            session_language=session_language,
            question=user_question[:30],
            followup_confidence=followup_confidence
        )
        
        # DO NOT UPDATE SESSION PREFERENCE - just return the existing preference
        return {
            "language": session_language,
            "language_name": SUPPORTED_LANGUAGES[session_language],
            "confidence": followup_confidence,
            "supported": True,
            "detection_method": "session_context_followup",
            "is_followup": True,
            "preserve_session_language": True  # Flag to prevent updating
        }
    
    # STEP 2: Detect current question language (only for new conversations or uncertain cases)
    current_question_language = None
    current_confidence = 0.0
    detection_method = "unknown"
    
    # Check for obvious English patterns first
    english_indicators = [
        "what is", "how do", "can i", "do i need", "how much", "when can",
        "where do", "which", "should i", "am i eligible", "tell me about",
        "cost", "fee", "price", "apply", "application", "process", "requirements"
    ]
    
    question_lower = user_question.lower()
    if any(phrase in question_lower for phrase in english_indicators):
        current_question_language = "en"
        current_confidence = 0.9
        detection_method = "pattern"
        synthesis_logger.info(
            "current_question_detected_english_patterns",
            session_id=session_id,
            method="pattern_matching",
            indicators_found=[phrase for phrase in english_indicators if phrase in question_lower]
        )
    else:
        # Use langdetect for current question
        try:
            with PerformanceTimer(synthesis_logger, "language_detection_langdetect", session_id=session_id):
                detections = detect_langs(user_question)
                
                if not detections:
                    raise LangDetectException("No language detected")
                
                top_detection = detections[0]
                current_question_language = top_detection.lang
                current_confidence = top_detection.prob
                detection_method = "langdetect"
                
                synthesis_logger.info(
                    "current_question_language_detected",
                    session_id=session_id,
                    detected_language=current_question_language,
                    confidence=current_confidence,
                    method="langdetect"
                )
                
        except LangDetectException as e:
            synthesis_logger.warning(
                "current_question_detection_failed_langdetect",
                session_id=session_id,
                error_message=str(e),
                question_length=len(user_question)
            )
            
            # Fallback: Use session language or English
            current_question_language = session_language or "en"
            current_confidence = 0.6
            detection_method = "fallback"
    
    # STEP 3: Determine final language with enhanced logic
    final_language = "en"  # Default fallback
    final_confidence = 0.5
    final_method = "fallback"
    decision_reason = "default"
    should_update_session = False
    
    if session_language:
        # Check if this is a follow-up question FIRST
        followup_indicators = ["how much", "cost", "fee", "price", "what about", "and what", "also", "and"]
        question_lower = user_question.lower()
        is_followup = any(indicator in question_lower for indicator in followup_indicators)
        
        if is_followup and conversation_history:
            synthesis_logger.info(
                "preserving_session_language_for_followup",
                session_id=session_id,
                session_language=session_language,
                question=user_question[:30]
            )
            
            # PRESERVE session language - don't call session manager
            final_language = session_language
            final_confidence = 0.95
            final_method = "followup_preservation" 
            decision_reason = "followup_detected"
            
            # Skip updating session preference
        else:
            # Original logic for non-follow-up questions
            should_maintain, determined_language = session_manager.should_maintain_session_language(
                session_id, current_question_language or "en", current_confidence
            )
            
            final_language = determined_language
            should_update_session = True
            
            if should_maintain:
                final_confidence = 0.9
                final_method = "session_context"
                decision_reason = "session_continuity"
            else:
                final_confidence = current_confidence if current_confidence > 0 else 0.8
                final_method = detection_method
                decision_reason = "language_switch"
                
                # Update session preference for language switch
                if final_language in SUPPORTED_LANGUAGES and final_confidence > 0.7:
                    session_manager.set_session_language_preference(
                        session_id, final_language, final_confidence
                    )
                    synthesis_logger.info(
                        "session_language_preference_updated",
                        session_id=session_id,
                        new_language=final_language,
                        confidence=final_confidence
                    )
    else:
        # No session context - use current detection for new session
        final_language = current_question_language or "en"
        final_confidence = current_confidence if current_question_language else 0.5
        final_method = detection_method if current_question_language else "fallback"
        decision_reason = "new_session"
        should_update_session = True
        
        # Set initial session language preference
        if should_update_session and final_language in SUPPORTED_LANGUAGES and final_confidence > 0.7:
            session_manager.set_session_language_preference(
                session_id, final_language, final_confidence
            )
            synthesis_logger.info(
                "session_language_preference_updated",
                session_id=session_id,
                new_language=final_language,
                confidence=final_confidence
            )
    
    # STEP 4: Update session preference only if appropriate
    if should_update_session and final_language in SUPPORTED_LANGUAGES and final_confidence > 0.7:
        session_manager.set_session_language_preference(
            session_id, final_language, final_confidence
        )
        synthesis_logger.info(
            "session_language_preference_updated",
            session_id=session_id,
            new_language=final_language,
            confidence=final_confidence,
            reason=decision_reason
        )
    else:
        synthesis_logger.info(
            "session_language_preference_preserved",
            session_id=session_id,
            current_language=session_language,
            final_language=final_language,
            reason=decision_reason
        )
    
    # STEP 5: Prepare final result
    is_supported = final_language in SUPPORTED_LANGUAGES
    language_name = SUPPORTED_LANGUAGES.get(final_language, "Unknown/Unsupported")
    
    result = {
        "language": final_language,
        "language_name": language_name,
        "confidence": final_confidence,
        "supported": is_supported,
        "detection_method": final_method,
        "is_followup": is_likely_followup,
        "preserve_session_language": not should_update_session
    }
    
    synthesis_logger.info(
        "language_detection_completed_enhanced",
        session_id=session_id,
        **result,
        decision_reason=decision_reason
    )
    
    return result

def create_language_not_supported_response(detected_language: str, language_name: str, user_question: str, session_id: str) -> str:
    """Create a polite response for unsupported languages, encouraging English use."""
    
    synthesis_logger.info(
        "creating_unsupported_language_response",
        session_id=session_id,
        detected_language=detected_language,
        language_name=language_name
    )
    
    # Basic responses in common unsupported languages
    unsupported_responses = {
        "de": {
            "title": "# Sprache nicht unterstützt / Language Not Supported",
            "message": "Entschuldigung, ich kann nur auf Englisch, Spanisch, Französisch und Portugiesisch antworten.",
            "request": "**Bitte stellen Sie Ihre Frage auf Englisch.**"
        },
        "it": {
            "title": "# Lingua non supportata / Language Not Supported", 
            "message": "Mi dispiace, posso rispondere solo in inglese, spagnolo, francese e portoghese.",
            "request": "**Si prega di fare la domanda in inglese.**"
        },
        "zh": {
            "title": "# 不支持的语言 / Language Not Supported",
            "message": "抱歉，我只能用英语、西班牙语、法语和葡萄牙语回答。",
            "request": "**请用英语提问。**"
        },
        "ar": {
            "title": "# اللغة غير مدعومة / Language Not Supported",
            "message": "آسف، يمكنني الإجابة فقط باللغة الإنجليزية أو الإسبانية أو الفرنسية أو البرتغالية.",
            "request": "**يرجى طرح سؤالك باللغة الإنجليزية.**"
        }
    }
    
    # Get language-specific response or use generic English
    if detected_language in unsupported_responses:
        lang_response = unsupported_responses[detected_language]
        response = f"""{lang_response['title']}

{lang_response['message']}

{lang_response['request']}

---

**Sorry, I can only respond in English, Spanish, French, and Portuguese.**

Please ask your question in English so I can provide you with accurate US immigration information.

## Supported Languages / Idiomas Soportados
- 🇺🇸 **English** - Full support
- 🇪🇸 **Español** - Soporte completo  
- 🇫🇷 **Français** - Support complet
- 🇧🇷 **Português** - Suporte completo

## Official Resources
- **USCIS Website**: https://www.uscis.gov
- **Contact USCIS**: https://www.uscis.gov/contactcenter"""
    else:
        # Generic response for unknown languages
        response = f"""# Language Not Supported

**Sorry, I can only respond in English, Spanish, French, and Portuguese.**

I detected that your question might be in **{language_name}**, but I cannot provide accurate immigration information in this language.

**Please ask your question in English** so I can provide you with precise US immigration guidance.

## Supported Languages / Idiomas Soportados
- 🇺🇸 **English** - Full support
- 🇪🇸 **Español** - Soporte completo  
- 🇫🇷 **Français** - Support complet
- 🇧🇷 **Português** - Suporte completo

## Official Resources
- **USCIS Website**: https://www.uscis.gov
- **Contact USCIS**: https://www.uscis.gov/contactcenter"""

    return response

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