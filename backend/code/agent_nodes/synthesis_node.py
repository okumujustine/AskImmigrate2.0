from typing import Dict, Any
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
from backend.code.tools.tool_registry import get_tools_by_agent
from backend.code.structured_logging import synthesis_logger, PerformanceTimer

# Language detection imports
from langdetect import detect, detect_langs
from langdetect.lang_detect_exception import LangDetectException

config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)

def detect_and_validate_language(user_question: str, conversation_history: list, session_id: str) -> Dict[str, Any]:
    """
    Detect the language of the user's question using session manager integration for better consistency.
    
    ENHANCED: Uses session manager for reliable language preference tracking and follow-up question handling.
    
    Returns:
        dict: {
            "language": "es",
            "language_name": "Spanish", 
            "confidence": 0.95,
            "supported": True,
            "detection_method": "session_context"
        }
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
    
    # STEP 1: Get session language preference from session manager
    session_language = session_manager.get_session_language_preference(session_id)
    
    synthesis_logger.info(
        "session_language_preference_retrieved",
        session_id=session_id,
        session_language=session_language,
        has_session_context=bool(session_language)
    )
    
    # STEP 2: Detect current question language
    current_question_language = None
    current_confidence = 0.0
    detection_method = "unknown"
    
    # Check for obvious English patterns first (optimization)
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
                # Get detection with confidence
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
                    method="langdetect",
                    all_detections=[(d.lang, d.prob) for d in detections[:3]]  # Top 3 for debugging
                )
                
        except LangDetectException as e:
            synthesis_logger.warning(
                "current_question_detection_failed_langdetect",
                session_id=session_id,
                error_message=str(e),
                question_length=len(user_question)
            )
            
            # Fallback: very short questions default to session language or English
            if len(user_question.strip()) < 10:
                current_question_language = session_language or "en"
                current_confidence = 0.6
                detection_method = "short_text_fallback"
                synthesis_logger.info(
                    "short_text_fallback_applied",
                    session_id=session_id,
                    fallback_language=current_question_language,
                    question_length=len(user_question)
                )
    
    # STEP 3: Use session manager to determine final language
    final_language = "en"  # Default fallback
    final_confidence = 0.5
    final_method = "fallback"
    decision_reason = "default"
    
    if session_language:
        # We have session context - use session manager logic
        should_maintain, determined_language = session_manager.should_maintain_session_language(
            session_id, current_question_language or "en", current_confidence
        )
        
        final_language = determined_language
        
        if should_maintain:
            final_confidence = 0.9  # High confidence for session continuity
            final_method = "session_context"
            decision_reason = "session_continuity"
            
            synthesis_logger.info(
                "maintaining_session_language",
                session_id=session_id,
                session_language=session_language,
                current_detected=current_question_language,
                current_confidence=current_confidence,
                final_language=final_language
            )
        else:
            final_confidence = current_confidence if current_confidence > 0 else 0.8
            final_method = detection_method
            decision_reason = "language_switch"
            
            synthesis_logger.info(
                "language_switch_approved",
                session_id=session_id,
                from_language=session_language,
                to_language=final_language,
                confidence=final_confidence
            )
            
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
        
        synthesis_logger.info(
            "new_session_language_detection",
            session_id=session_id,
            detected_language=final_language,
            confidence=final_confidence,
            method=final_method
        )
        
        # Set initial session language preference
        if final_language in SUPPORTED_LANGUAGES and final_confidence > 0.7:
            session_manager.set_session_language_preference(
                session_id, final_language, final_confidence
            )
            synthesis_logger.info(
                "initial_session_language_preference_set",
                session_id=session_id,
                language=final_language,
                confidence=final_confidence
            )
    
    # STEP 4: Validate final decision and prepare result
    is_supported = final_language in SUPPORTED_LANGUAGES
    language_name = SUPPORTED_LANGUAGES.get(final_language, "Unknown/Unsupported")
    
    # Handle unsupported languages
    if not is_supported:
        synthesis_logger.warning(
            "unsupported_language_detected",
            session_id=session_id,
            detected_language=final_language,
            confidence=final_confidence
        )
    
    result = {
        "language": final_language,
        "language_name": language_name,
        "confidence": final_confidence,
        "supported": is_supported,
        "detection_method": final_method
    }
    
    synthesis_logger.info(
        "language_detection_completed_session_manager",
        session_id=session_id,
        final_language=final_language,
        language_name=language_name,
        confidence=final_confidence,
        supported=is_supported,
        method=final_method,
        decision_reason=decision_reason,
        session_language=session_language,
        current_question_lang=current_question_language,
        current_confidence=current_confidence
    )
    
    return result   

def create_language_not_supported_response(detected_language: str, language_name: str, user_question: str, session_id: str) -> str:
    """
    Create a polite response for unsupported languages, encouraging English use.
    """
    
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
    Enhanced Strategic Synthesis Agent with multilingual support that executes manager tool recommendations.
    
    NEW FEATURES:
    - Language detection using langdetect
    - Multilingual response generation
    - Language validation and fallback handling
    - Session-aware language context
    
    STRATEGIC APPROACH:
    - Detect user's language first
    - Reads manager's tool recommendations from analysis
    - Executes recommended tools (web_search, fee_calculator) as needed
    - Combines tool results with RAG context and conversation history
    - Creates comprehensive responses in user's language based on strategic guidance
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
        "synthesis_started_with_language_detection",
        session_id=session_id,
        question_length=len(user_question),
        is_followup=is_followup,
        history_length=len(conversation_history),
        rag_context_length=len(rag_context),
        has_manager_guidance=bool(manager_decision)
    )
    
    # STEP 1: Language Detection
    with PerformanceTimer(synthesis_logger, "language_detection_phase", session_id=session_id):
        language_info = detect_and_validate_language(user_question, conversation_history, session_id)
    
    # Update state with language information
    detected_language = language_info["language"]
    language_name = language_info["language_name"]
    language_supported = language_info["supported"]
    language_confidence = language_info["confidence"]
    detection_method = language_info["detection_method"]
    
    synthesis_logger.info(
        "language_detection_completed",
        session_id=session_id,
        detected_language=detected_language,
        language_name=language_name,
        supported=language_supported,
        confidence=language_confidence,
        method=detection_method
    )
    
    # STEP 2: Handle unsupported languages
    if not language_supported:
        synthesis_logger.info(
            "handling_unsupported_language",
            session_id=session_id,
            detected_language=detected_language
        )
        
        unsupported_response = create_language_not_supported_response(
            detected_language, language_name, user_question, session_id
        )
        
        return {
            "synthesis": unsupported_response,
            "tool_results": {},
            "tools_used": ["language_detection"],
            "question_processed": user_question,
            "strategy_applied": {"question_type": "unsupported_language"},
            "detected_language": detected_language,
            "language_name": language_name,
            "language_confidence": language_confidence,
            "response_language": "en",  # Always respond in English for unsupported
            "language_supported": False,
            "detection_method": detection_method,
            "synthesis_metadata": {
                "response_type": "unsupported_language",
                "fallback_used": True
            }
        }
    
    # STEP 3: Parse manager's tool recommendations and execute recommended tools
    tool_results = {}
    tools_used = ["language_detection"]  # Always include language detection
    
    with PerformanceTimer(synthesis_logger, "tool_execution_phase", session_id=session_id):
        manager_tool_results, manager_tools_used = execute_manager_recommended_tools(
            manager_decision, user_question, session_id
        )
        tool_results.update(manager_tool_results)
        tools_used.extend(manager_tools_used)

    # STEP 4: Build comprehensive session context
    with PerformanceTimer(synthesis_logger, "session_context_building", session_id=session_id):
        session_context = build_session_context_for_llm(
            conversation_history, is_followup, session_id, user_question
        )
    
    # STEP 5: Create dynamic prompt with language support
    with PerformanceTimer(synthesis_logger, "prompt_creation", session_id=session_id):
        prompt = create_dynamic_synthesis_prompt(
            user_question, rag_context, session_context, workflow_parameters, 
            manager_decision, tool_results, target_language=detected_language
        )
    
    # STEP 6: Generate response using LLM
    try:
        llm = get_llm(config.get("llm", "gpt-4o-mini"))
        # CRITICAL: Don't bind tools to avoid tool calling errors
        with PerformanceTimer(synthesis_logger, "llm_generation", session_id=session_id):
            response = llm.invoke(prompt)
            synthesis_content = response.content
        
        synthesis_logger.info(
            "llm_response_generated_multilingual",
            session_id=session_id,
            response_length=len(synthesis_content),
            target_language=detected_language,
            language_name=language_name
        )
        
        # Validate response quality
        if not synthesis_content or len(synthesis_content.strip()) < 20:
            synthesis_logger.warning(
                "llm_response_too_short",
                session_id=session_id,
                response_length=len(synthesis_content.strip()) if synthesis_content else 0,
                target_language=detected_language
            )
            synthesis_content = create_fallback_response(
                user_question, conversation_history, is_followup, rag_context, detected_language
            )
        
    except Exception as e:
        synthesis_logger.error(
            "llm_synthesis_failed",
            session_id=session_id,
            error_type=type(e).__name__,
            error_message=str(e),
            target_language=detected_language
        )
        synthesis_content = create_fallback_response(
            user_question, conversation_history, is_followup, rag_context, detected_language
        )
    
    synthesis_logger.info(
        "synthesis_completed_multilingual",
        session_id=session_id,
        final_response_length=len(synthesis_content),
        tools_used_count=len(tools_used),
        strategy_applied=str(workflow_parameters.get("question_type", "unknown")),
        response_language=detected_language,
        language_confidence=language_confidence
    )
    
    return {
        "synthesis": synthesis_content,
        "tool_results": tool_results,
        "tools_used": tools_used,
        "question_processed": user_question,
        "strategy_applied": workflow_parameters,
        "detected_language": detected_language,
        "language_name": language_name,
        "language_confidence": language_confidence,
        "response_language": detected_language,
        "language_supported": language_supported,
        "detection_method": detection_method,
        "synthesis_metadata": {
            "session_aware_response": is_followup,
            "conversation_history_used": len(conversation_history),
            "response_type": "multilingual_synthesis",
            "manager_guided": bool(manager_decision),
            "tools_executed": len(tools_used),
            "language_detection_confidence": language_confidence,
            "target_language": detected_language
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

def create_dynamic_synthesis_prompt(user_question, rag_context, session_context, workflow_parameters, 
                                  manager_decision="", tool_results=None, target_language="en"):
    """Create a dynamic prompt with strict format consistency across all languages."""
    
    # Get the proper synthesis agent prompt from configuration
    synthesis_prompt_config = prompt_config.get("synthesis_agent_prompt", {})
    role = synthesis_prompt_config.get("role", "You are an expert US Immigration Assistant.")
    instruction = synthesis_prompt_config.get("instruction", "Provide helpful immigration guidance.")
    
    # ENHANCED LANGUAGE SUPPORT: Add language-specific instructions with format enforcement
    language_header = ""
    if target_language != "en":
        language_support = synthesis_prompt_config.get("language_support", {})
        lang_map = {"es": "spanish", "fr": "french", "pt": "portuguese"}
        
        if target_language in lang_map:
            lang_config = language_support.get(lang_map[target_language], {})
            if lang_config:
                language_header = f"""
🌍 CRITICAL LANGUAGE & FORMAT INSTRUCTION:
{lang_config.get('instruction', '')}

📋 MANDATORY FORMAT TEMPLATE TO FOLLOW:
{lang_config.get('format_template', '')}

⚠️ FORMAT ENFORCEMENT RULES:
- Use EXACTLY the same structure as shown in template
- Include ALL sections that would be in English version
- Maintain IDENTICAL depth of information
- Keep same number of procedural steps
- End with: "{lang_config.get('verification', '')}"

---

"""
    else:
        # English - still include format guidance for consistency
        language_header = f"""
📋 MANDATORY ENGLISH FORMAT STRUCTURE:
Follow the standard format as defined in instructions below.
Ensure all responses include appropriate sections (procedures, verification notes, sources).

---

"""

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

    # Determine response complexity for format guidance
    detail_depth = workflow_parameters.get("detail_depth", "standard")
    format_guidance = f"""
📐 RESPONSE COMPLEXITY LEVEL: {detail_depth.upper()}
- Follow the {detail_depth} format structure exactly as defined in instructions
- Ensure response depth matches the complexity level specified
"""

    # Construct the full prompt with enhanced format control
    full_prompt = f"""{language_header}{role}

{current_info_override}

{format_guidance}

{instruction}

🎯 USER QUESTION: "{user_question}"

{session_context}

📚 IMMIGRATION KNOWLEDGE BASE:
{rag_context if rag_context else "Use your general immigration knowledge for foundational information."}

{tool_results_text}

{manager_guidance}

🔧 FINAL FORMAT REMINDER:
- Use the EXACT format structure specified above
- Include ALL required sections
- Maintain consistent depth across languages
- Keep official terms in English
- End with appropriate verification phrase

Remember: If web search results are provided above, prioritize that current information over any older knowledge."""
    
    return full_prompt

def create_fallback_response(user_question, conversation_history, is_followup, rag_context, target_language="en"):
    """Create a smart fallback response when LLM fails, with language support."""
    
    question_lower = user_question.lower()
    
    # Language-specific fallback responses
    if target_language == "es":
        return create_spanish_fallback_response(user_question, conversation_history, is_followup, rag_context)
    elif target_language == "fr":
        return create_french_fallback_response(user_question, conversation_history, is_followup, rag_context)
    elif target_language == "pt":
        return create_portuguese_fallback_response(user_question, conversation_history, is_followup, rag_context)
    
    # English fallback (existing logic)
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

def create_spanish_fallback_response(user_question, conversation_history, is_followup, rag_context):
    """Create Spanish fallback response."""
    
    if is_followup and conversation_history:
        first_turn = conversation_history[0]
        return f"""# Información de Inmigración

## Su Pregunta: "{user_question}"

Puedo ver que esta es una pregunta de seguimiento a nuestra conversación anterior donde preguntó sobre: **"{conversation_history[-1].question}"**

{rag_context if rag_context else "Estaré encantado de ayudarle con su pregunta de seguimiento. ¿Podría proporcionar un poco más de detalle sobre qué aspecto específico le gustaría que aborde?"}

## Recursos Oficiales de Inmigración
- **Sitio Web de USCIS:** https://www.uscis.gov - Información completa de inmigración
- **Centro de Contacto de USCIS:** https://www.uscis.gov/contactcenter - Soporte telefónico
- **Formularios y Tarifas:** https://www.uscis.gov/forms - Formularios oficiales y tarifas actuales

## Próximos Pasos
1. Visite el sitio web de USCIS para información detallada
2. Contacte a USCIS directamente para orientación específica
3. Considere consultar con un abogado de inmigración calificado

*Siempre verifique la información con fuentes oficiales de USCIS para los requisitos más actuales.*

Verifica la información actual en uscis.gov
"""
    else:
        return f"""# Información de Inmigración

## Su Pregunta: "{user_question}"

{rag_context if rag_context else f"Entiendo que está preguntando sobre {user_question}. Aunque no tengo información específica disponible inmediatamente, puedo guiarle a los recursos correctos."}

## Recursos Oficiales de Inmigración
- **Sitio Web de USCIS:** https://www.uscis.gov - Información completa de inmigración
- **Centro de Contacto de USCIS:** https://www.uscis.gov/contactcenter - Soporte telefónico
- **Formularios y Tarifas:** https://www.uscis.gov/forms - Formularios oficiales y tarifas actuales

## Próximos Pasos
1. Visite el sitio web de USCIS para información detallada
2. Contacte a USCIS directamente para orientación específica
3. Considere consultar con un abogado de inmigración calificado

*Siempre verifique la información con fuentes oficiales de USCIS para los requisitos más actuales.*

Verifica la información actual en uscis.gov
"""

def create_french_fallback_response(user_question, conversation_history, is_followup, rag_context):
    """Create French fallback response."""
    
    if is_followup and conversation_history:
        return f"""# Informations d'Immigration

## Votre Question: "{user_question}"

Je peux voir que c'est une question de suivi à notre conversation précédente où vous avez demandé: **"{conversation_history[-1].question}"**

{rag_context if rag_context else "Je serais ravi de vous aider avec votre question de suivi. Pourriez-vous fournir un peu plus de détails sur l'aspect spécifique que vous aimeriez que j'aborde?"}

## Ressources Officielles d'Immigration
- **Site Web USCIS:** https://www.uscis.gov - Informations complètes sur l'immigration
- **Centre de Contact USCIS:** https://www.uscis.gov/contactcenter - Support téléphonique
- **Formulaires et Frais:** https://www.uscis.gov/forms - Formulaires officiels et frais actuels

## Prochaines Étapes
1. Visitez le site web USCIS pour des informations détaillées
2. Contactez USCIS directement pour des conseils spécifiques
3. Considérez consulter un avocat d'immigration qualifié

*Vérifiez toujours les informations avec les sources officielles USCIS pour les exigences les plus récentes.*

Vérifiez les informations actuelles sur uscis.gov
"""
    else:
        return f"""# Informations d'Immigration

## Votre Question: "{user_question}"

{rag_context if rag_context else f"Je comprends que vous posez des questions sur {user_question}. Bien que je n'aie pas d'informations spécifiques immédiatement disponibles, je peux vous guider vers les bonnes ressources."}

## Ressources Officielles d'Immigration
- **Site Web USCIS:** https://www.uscis.gov - Informations complètes sur l'immigration
- **Centre de Contact USCIS:** https://www.uscis.gov/contactcenter - Support téléphonique
- **Formulaires et Frais:** https://www.uscis.gov/forms - Formulaires officiels et frais actuels

## Prochaines Étapes
1. Visitez le site web USCIS pour des informations détaillées
2. Contactez USCIS directement pour des conseils spécifiques
3. Considérez consulter un avocat d'immigration qualifié

*Vérifiez toujours les informations avec les sources officielles USCIS pour les exigences les plus récentes.*

Vérifiez les informations actuelles sur uscis.gov
"""

def create_portuguese_fallback_response(user_question, conversation_history, is_followup, rag_context):
    """Create Portuguese fallback response."""
    
    if is_followup and conversation_history:
        return f"""# Informações de Imigração

## Sua Pergunta: "{user_question}"

Posso ver que esta é uma pergunta de acompanhamento à nossa conversa anterior onde você perguntou sobre: **"{conversation_history[-1].question}"**

{rag_context if rag_context else "Ficarei feliz em ajudá-lo com sua pergunta de acompanhamento. Você poderia fornecer um pouco mais de detalhes sobre o aspecto específico que gostaria que eu abordasse?"}

## Recursos Oficiais de Imigração
- **Site do USCIS:** https://www.uscis.gov - Informações completas sobre imigração
- **Centro de Contato do USCIS:** https://www.uscis.gov/contactcenter - Suporte telefônico
- **Formulários e Taxas:** https://www.uscis.gov/forms - Formulários oficiais e taxas atuais

## Próximos Passos
1. Visite o site do USCIS para informações detalhadas
2. Contate o USCIS diretamente para orientação específica
3. Considere consultar um advogado de imigração qualificado

*Sempre verifique as informações com fontes oficiais do USCIS para os requisitos mais atuais.*

Verifique as informações atuais em uscis.gov
"""
    else:
        return f"""# Informações de Imigração

## Sua Pergunta: "{user_question}"

{rag_context if rag_context else f"Entendo que você está perguntando sobre {user_question}. Embora eu não tenha informações específicas imediatamente disponíveis, posso guiá-lo para os recursos certos."}

## Recursos Oficiais de Imigração
- **Site do USCIS:** https://www.uscis.gov - Informações completas sobre imigração
- **Centro de Contato do USCIS:** https://www.uscis.gov/contactcenter - Suporte telefônico
- **Formulários e Taxas:** https://www.uscis.gov/forms - Formulários oficiais e taxas atuais

## Próximos Passos
1. Visite o site do USCIS para informações detalhadas
2. Contate o USCIS diretamente para orientação específica
3. Considere consultar um advogado de imigração qualificado

*Sempre verifique as informações com fontes oficiais do USCIS para os requisitos mais atuais.*

Verifique as informações atuais em uscis.gov
"""