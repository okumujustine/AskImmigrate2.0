from typing import Dict, Any
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_yaml_config
from backend.code.tools.tool_registry import get_tools_by_agent
from backend.code.structured_logging import synthesis_logger, PerformanceTimer
from fast_langdetect import detect
config = load_yaml_config(APP_CONFIG_FPATH)
prompt_config = load_yaml_config(PROMPT_CONFIG_FPATH)


def detect_and_validate_language(user_question: str, conversation_history: list, session_id: str) -> Dict[str, Any]:
    """
    FastText-based language detection with strict support for 4 languages only.
    
    Args:
        user_question: The user's question text
        conversation_history: List of previous conversation turns
        session_id: Session identifier
        
    Returns:
        Dict with language info including 'supported' boolean
    """
    
    from backend.code.session_manager import session_manager
    from fast_langdetect import detect, detect_multilingual
    
    synthesis_logger.info(
        "language_detection_started",
        session_id=session_id,
        question_length=len(user_question),
        has_conversation_history=bool(conversation_history)
    )
    
    # ONLY support these 4 languages
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "es": "Spanish", 
        "fr": "French",
        "pt": "Portuguese"
    }
    
    # STEP 1: Check for follow-up patterns (preserve session language)
    session_language = session_manager.get_session_language_preference(session_id)
    
    if conversation_history and session_language and session_language in SUPPORTED_LANGUAGES:
        followup_patterns = ["how much", "cost", "fee", "price", "cuánto", "costo", "what about", "también"]
        question_lower = user_question.lower()
        is_followup = any(pattern in question_lower for pattern in followup_patterns)
        
        if is_followup:
            synthesis_logger.info(
                "followup_detected_using_session_language",
                session_id=session_id,
                session_language=session_language
            )
            
            return {
                "language": session_language,
                "language_name": SUPPORTED_LANGUAGES[session_language],
                "confidence": 0.95,
                "supported": True,
                "detection_method": "session_followup",
                "is_followup": True
            }
    
    # STEP 2: Use FastText for detection
    detected_language = None
    confidence = 0.0
    detection_method = "unknown"
    
    try:
        with PerformanceTimer(synthesis_logger, "fasttext_detection", session_id=session_id):
            # FastText detection
            result = detect(user_question)
            detected_language = result['lang']
            confidence = result['score']
            detection_method = "fasttext"
            
            synthesis_logger.info(
                "fasttext_detection_successful",
                session_id=session_id,
                detected_language=detected_language,
                confidence=confidence
            )
                
    except Exception as e:
        synthesis_logger.warning(
            "fasttext_detection_failed",
            session_id=session_id,
            error_message=str(e),
            question_length=len(user_question)
        )
        
        # If FastText fails completely, return as unsupported
        return {
            "language": "unknown",
            "language_name": "Unknown",
            "confidence": 0.0,
            "supported": False,
            "detection_method": "fasttext_failed"
        }
    
    # STEP 3: Check if detected language is supported
    if detected_language:
        is_supported = detected_language in SUPPORTED_LANGUAGES
        
        if is_supported:
            # Language is supported - process normally
            language_name = SUPPORTED_LANGUAGES[detected_language]
            
            synthesis_logger.info(
                "supported_language_detected",
                session_id=session_id,
                detected_language=detected_language,
                confidence=confidence
            )
            
            # Update session preference for confident detections
            if confidence > 0.6:
                session_manager.set_session_language_preference(session_id, detected_language, confidence)
            
            return {
                "language": detected_language,
                "language_name": language_name,
                "confidence": confidence,
                "supported": True,
                "detection_method": detection_method
            }
        
        else:
            # Language detected but NOT supported
            synthesis_logger.info(
                "unsupported_language_detected",
                session_id=session_id,
                detected_language=detected_language,
                confidence=confidence,
                supported_languages=list(SUPPORTED_LANGUAGES.keys())
            )
            
            return {
                "language": detected_language,
                "language_name": detected_language.upper(),
                "confidence": confidence,
                "supported": False,
                "detection_method": detection_method
            }
    
    # STEP 4: Final fallback
    synthesis_logger.warning(
        "no_language_detected",
        session_id=session_id
    )
    
    return {
        "language": "unknown",
        "language_name": "Unknown",
        "confidence": 0.0,
        "supported": False,
        "detection_method": "no_detection"
    }

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

def test_language_detection(session_id="test"):
    """Test function to verify language detection is working"""
    test_questions = [
        "¿Cuál es el costo de la visa EB-1?",  # Spanish
        "What is the cost of EB1 visa?",       # English
        "Quel est le coût du visa EB-1?",      # French
        "Qual é o custo do visto EB-1?"        # Portuguese
    ]
    
    synthesis_logger.info(
        "language_detection_test_starting",
        session_id=session_id,
        test_questions_count=len(test_questions)
    )
    
    for i, question in enumerate(test_questions):
        try:
            synthesis_logger.info(
                f"testing_question_{i+1}",
                session_id=session_id,
                question=question,
                question_length=len(question)
            )
            
            # Test the language detection function directly
            result = detect_and_validate_language(question, [], session_id)
            
            synthesis_logger.info(
                f"test_result_{i+1}",
                session_id=session_id,
                question=question[:30],
                detected_language=result.get("language", "unknown"),
                confidence=result.get("confidence", 0),
                supported=result.get("supported", False),
                detection_method=result.get("detection_method", "unknown")
            )
            
        except Exception as e:
            synthesis_logger.error(
                f"test_failed_{i+1}",
                session_id=session_id,
                question=question[:30],
                error_type=type(e).__name__,
                error_message=str(e)
            )
    
    synthesis_logger.info(
        "language_detection_test_completed",
        session_id=session_id
    )

def synthesis_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Enhanced Strategic Synthesis Agent with extensive logging for debugging.
    """
    
    # TEMPORARY: Test language detection
    test_language_detection(state.get("session_id", "debug"))

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
        "synthesis_started_with_debugging",
        session_id=session_id,
        question_length=len(user_question),
        question_preview=user_question[:50],
        is_followup=is_followup,
        history_length=len(conversation_history),
        rag_context_length=len(rag_context),
        has_manager_guidance=bool(manager_decision)
    )
    
    # Step 1: Parse manager's tool recommendations and execute recommended tools
    synthesis_logger.info(
        "step_1_starting_tool_execution",
        session_id=session_id
    )
    
    tool_results = {}
    tools_used = []
    
    with PerformanceTimer(synthesis_logger, "tool_execution_phase", session_id=session_id):
        tool_results, tools_used = execute_manager_recommended_tools(
            manager_decision, user_question, session_id
        )

    synthesis_logger.info(
        "step_1_completed_tool_execution",
        session_id=session_id,
        tools_executed=len(tools_used)
    )

    # Step 2: Build comprehensive session context
    synthesis_logger.info(
        "step_2_starting_session_context",
        session_id=session_id
    )
    
    with PerformanceTimer(synthesis_logger, "session_context_building", session_id=session_id):
        session_context = build_session_context_for_llm(
            conversation_history, is_followup, session_id, user_question
        )
    
    synthesis_logger.info(
        "step_2_completed_session_context",
        session_id=session_id,
        context_length=len(session_context)
    )
    
    # Step 3: LANGUAGE DETECTION AND VALIDATION
    synthesis_logger.info(
        "step_3_starting_language_detection",
        session_id=session_id,
        user_question_for_detection=user_question
    )
    
    language_info = None
    try:
        with PerformanceTimer(synthesis_logger, "language_detection", session_id=session_id):
            synthesis_logger.info(
                "calling_detect_and_validate_language",
                session_id=session_id,
                question_chars=len(user_question),
                question_sample=user_question[:20]
            )
            
            language_info = detect_and_validate_language(user_question, conversation_history, session_id)
            
            synthesis_logger.info(
                "language_detection_result_received",
                session_id=session_id,
                language_info_keys=list(language_info.keys()) if language_info else [],
                detected_language=language_info.get("language", "unknown") if language_info else "unknown",
                confidence=language_info.get("confidence", 0) if language_info else 0,
                supported=language_info.get("supported", False) if language_info else False
            )
        
        # Handle unsupported languages
        if language_info and not language_info.get("supported", True):
            synthesis_logger.info(
                "unsupported_language_detected_returning_early",
                session_id=session_id,
                detected_language=language_info.get("language"),
                language_name=language_info.get("language_name")
            )
            
            # Return early with language not supported response
            unsupported_response = create_language_not_supported_response(
                language_info.get("language", "unknown"),
                language_info.get("language_name", "Unknown"),
                user_question,
                session_id
            )
            
            return {
                "synthesis": unsupported_response,
                "tool_results": tool_results,
                "tools_used": tools_used + ["language_detection"],
                "question_processed": user_question,
                "strategy_applied": workflow_parameters,
                "synthesis_metadata": {
                    "language_detected": language_info.get("language"),
                    "language_supported": False,
                    "response_type": "language_not_supported"
                }
            }
        
    except Exception as e:
        synthesis_logger.error(
            "language_detection_failed_with_exception",
            session_id=session_id,
            error_type=type(e).__name__,
            error_message=str(e),
            continuing_with_default="en"
        )
        # Continue with default English if language detection fails
        language_info = {"language": "en", "confidence": 0.5, "supported": True}
    
    synthesis_logger.info(
        "step_3_completed_language_detection",
        session_id=session_id,
        final_language=language_info.get("language", "unknown") if language_info else "unknown",
        final_confidence=language_info.get("confidence", 0) if language_info else 0
    )
    
    # Step 4: Create dynamic prompt based on question type and context
    synthesis_logger.info(
        "step_4_starting_prompt_creation",
        session_id=session_id,
        language_for_prompt=language_info.get("language", "unknown") if language_info else "unknown"
    )
    
    with PerformanceTimer(synthesis_logger, "prompt_creation", session_id=session_id):
        prompt = create_dynamic_synthesis_prompt(
            user_question, rag_context, session_context, workflow_parameters, 
            manager_decision, tool_results, language_info
        )
    
    synthesis_logger.info(
        "step_4_completed_prompt_creation",
        session_id=session_id,
        prompt_length=len(prompt),
        prompt_preview=prompt[:100] + "..." if len(prompt) > 100 else prompt
    )
    
    # Step 5: Use LLM without tool calling to avoid errors
    synthesis_logger.info(
        "step_5_starting_llm_generation",
        session_id=session_id
    )
    
    try:
        llm = get_llm(config.get("llm", "gpt-4o-mini"))
        # CRITICAL: Don't bind tools to avoid the tool calling errors
        with PerformanceTimer(synthesis_logger, "llm_generation", session_id=session_id):
            response = llm.invoke(prompt)
            synthesis_content = response.content
        
        synthesis_logger.info(
            "step_5_llm_response_received",
            session_id=session_id,
            response_length=len(synthesis_content),
            detected_language=language_info.get("language", "unknown") if language_info else "unknown",
            language_confidence=language_info.get("confidence", 0) if language_info else 0,
            response_preview=synthesis_content[:100] + "..." if len(synthesis_content) > 100 else synthesis_content
        )
        
        # Validate response quality
        if not synthesis_content or len(synthesis_content.strip()) < 20:
            synthesis_logger.warning(
                "llm_response_too_short_using_fallback",
                session_id=session_id,
                response_length=len(synthesis_content.strip()) if synthesis_content else 0
            )
            synthesis_content = create_fallback_response(
                user_question, conversation_history, is_followup, rag_context
            )
        
    except Exception as e:
        synthesis_logger.error(
            "step_5_llm_generation_failed",
            session_id=session_id,
            error_type=type(e).__name__,
            error_message=str(e),
            using_fallback=True
        )
        synthesis_content = create_fallback_response(
            user_question, conversation_history, is_followup, rag_context
        )
    
    synthesis_logger.info(
        "synthesis_completed_successfully",
        session_id=session_id,
        final_response_length=len(synthesis_content),
        tools_used_count=len(tools_used) + 1,  # +1 for language_detection
        strategy_applied=str(workflow_parameters.get("question_type", "unknown")),
        language_used=language_info.get("language", "unknown") if language_info else "unknown",
        language_detection_successful=bool(language_info)
    )
    
    return {
        "synthesis": synthesis_content,
        "tool_results": tool_results,
        "tools_used": tools_used + ["language_detection", "llm_generation"],
        "question_processed": user_question,
        "strategy_applied": workflow_parameters,
        "synthesis_metadata": {
            "session_aware_response": is_followup,
            "conversation_history_used": len(conversation_history),
            "response_type": "strategic_synthesis",
            "manager_guided": bool(manager_decision),
            "tools_executed": len(tools_used),
            "language_detected": language_info.get("language", "unknown") if language_info else "unknown",
            "language_confidence": language_info.get("confidence", 0) if language_info else 0,
            "language_supported": language_info.get("supported", True) if language_info else True,
            "language_detection_worked": bool(language_info),
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

def create_dynamic_synthesis_prompt(user_question, rag_context, session_context, workflow_parameters, manager_decision="", tool_results=None, language_info=None):
    """Universal prompt creation that works for all languages automatically."""
    
    # Get the universal synthesis agent prompt from configuration
    synthesis_prompt_config = prompt_config.get("synthesis_agent_prompt", {})
    
    # Use universal role and instruction
    role = synthesis_prompt_config.get("role", "You are an expert US Immigration Assistant.")
    instruction = synthesis_prompt_config.get("instruction", "Provide helpful immigration guidance.")
    
    # Detect language for logging purposes
    detected_language = language_info.get("language", "unknown") if language_info else "unknown"
    language_confidence = language_info.get("confidence", 0) if language_info else 0
    
    synthesis_logger.info(
        "universal_prompt_creation",
        detected_language=detected_language,
        confidence=language_confidence,
        user_question_preview=user_question[:30],
        approach="universal_multilingual"
    )
    
    # Get appropriate verification phrase for detected language
    verification_phrases = synthesis_prompt_config.get("verification_phrases", {})
    verification_note = verification_phrases.get(detected_language, verification_phrases.get("en", "Verify current information on uscis.gov"))
    
    # Include tool results (language-neutral)
    tool_results_text = ""
    current_info_available = False
    
    if tool_results:
        tool_results_text = "\n🔍 CURRENT INFORMATION SOURCES:\n"
        
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" in result:
                tool_results_text += f"❌ {tool_name}: {result['error']}\n"
            elif tool_name == "web_search_tool":
                current_info_available = True
                # Truncate to prevent verbose responses
                result_preview = str(result)[:300] + "..." if len(str(result)) > 300 else str(result)
                tool_results_text += f"🌐 WEB SEARCH (2025): {result_preview}\n"
            elif tool_name == "fee_calculator_tool":
                result_preview = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                tool_results_text += f"💰 FEE CALCULATOR: {result_preview}\n"
            else:
                tool_results_text += f"📚 {tool_name}: {str(result)[:300]}{'...' if len(str(result)) > 300 else ''}\n"
    
    # Add current information override if web search available
    current_info_override = ""
    if current_info_available:
        current_info_override = """
🚨 CRITICAL INSTRUCTION OVERRIDE:
- You have access to CURRENT 2025 web search results above
- NEVER mention knowledge cutoffs or outdated information disclaimers
- Use the web search results as your PRIMARY source for current events/policies
- Respond as if you have real-time access to 2025 information
- Start your response with current information based on the detected language

"""
    
    # Include manager guidance if available
    manager_guidance = ""
    if manager_decision:
        manager_guidance = f"\n📋 STRATEGIC GUIDANCE:\n{manager_decision[:500]}{'...' if len(manager_decision) > 500 else ''}\n"

    # Construct the universal prompt
    full_prompt = f"""{role}

{current_info_override}

{instruction}

🎯 USER QUESTION: "{user_question}"

{session_context}

📚 IMMIGRATION KNOWLEDGE BASE:
{rag_context[:300] + "..." if rag_context and len(rag_context) > 300 else rag_context or "Use your general immigration knowledge for foundational information."}

{tool_results_text}

{manager_guidance}

IMPORTANT: Follow the length guidelines and respond in the same language as the user's question.
Final verification: {verification_note}"""
    
    synthesis_logger.info(
        "universal_prompt_completed",
        detected_language=detected_language,
        prompt_length=len(full_prompt),
        has_current_info=current_info_available,
        verification_language=detected_language
    )
    
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