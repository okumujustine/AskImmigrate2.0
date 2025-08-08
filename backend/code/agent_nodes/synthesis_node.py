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
    # CRITICAL FIX: Check if this is a follow-up question FIRST
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
            should_update_preference = True
            
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
        
        # Set initial session language preference
        if should_update_preference and final_language in SUPPORTED_LANGUAGES and final_confidence > 0.7:
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
            synthesis_logger.info(
                "session_language_preference_preserved",
                session_id=session_id,
                preserved_language=session_language,
                reason="followup_question"
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

def build_enhanced_session_context_for_llm(conversation_history, is_followup, session_id, current_question):
    """
    CRITICAL FIX: Build comprehensive session context that emphasizes follow-up relationships.
    """
    
    if not conversation_history:
        return ""
    
    # ENHANCED: Build rich context for follow-up questions
    context = f"""
📋 CONVERSATION CONTEXT (Session: {session_id})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 {'FOLLOW-UP DETECTED' if is_followup else 'CONVERSATION HISTORY'}: 
Current question: "{current_question}"

📝 PREVIOUS CONVERSATION:
"""
    
    # Get the most recent conversation for immediate context
    for i, turn in enumerate(conversation_history[-3:], 1):  # Last 3 turns
        context += f"""
Turn {len(conversation_history) - 3 + i}:
❓ Q: {turn.question}
✅ A: {turn.answer[:200]}{'...' if len(turn.answer) > 200 else ''}
"""
    
    # CRITICAL: If this is a follow-up, emphasize the connection
    if is_followup and conversation_history:
        last_turn = conversation_history[-1]
        context += f"""

🎯 FOLLOW-UP ANALYSIS:
• This question appears to be a follow-up to: "{last_turn.question}"
• Previous answer focused on: {last_turn.answer[:100]}...
• Current question "{current_question}" likely relates to this previous topic
• INSTRUCTION: Build upon the previous context, don't start from scratch

"""
    
    context += f"""
📊 SESSION STATS:
• Total conversation turns: {len(conversation_history)}
• Session type: {'Follow-up conversation' if is_followup else 'New topic'}
• First question was: "{conversation_history[0].question if conversation_history else 'None'}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return context

def synthesis_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    CRITICAL FIX: Enhanced synthesis node that properly handles session context and follow-up questions.
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
    
    # CRITICAL: Use manager's tool results instead of re-executing
    manager_tool_results = state.get("tool_results", {})
    
    synthesis_logger.info(
        "synthesis_started_enhanced",
        session_id=session_id,
        question_length=len(user_question),
        is_followup=is_followup,
        history_length=len(conversation_history),
        has_manager_results=bool(manager_tool_results)
    )
    
    # STEP 1: Enhanced Language Detection with Session Context
    with PerformanceTimer(synthesis_logger, "language_detection_enhanced", session_id=session_id):
        language_info = detect_and_validate_language(
            user_question, conversation_history, session_id
        )
    
    detected_language = language_info["language"]
    language_name = language_info["language_name"]
    language_supported = language_info["supported"]
    language_confidence = language_info["confidence"]
    detection_method = language_info["detection_method"]
    is_detected_followup = language_info.get("is_followup", False)
    
    synthesis_logger.info(
        "language_detection_completed_enhanced",
        session_id=session_id,
        detected_language=detected_language,
        supported=language_supported,
        is_detected_followup=is_detected_followup,
        method=detection_method
    )
    
    # STEP 2: Handle unsupported languages (but consider session context)
    if not language_supported:
        # CRITICAL FIX: Even for unsupported languages, check if we have session context
        if conversation_history and is_detected_followup:
            synthesis_logger.info(
                "unsupported_language_but_has_session_context",
                session_id=session_id,
                detected_language=detected_language
            )
            
            # Try to respond in English but acknowledge the multilingual context
            detected_language = "en"  # Override to English for follow-up
            language_supported = True
            language_name = "English"
            
            synthesis_logger.info(
                "language_override_for_followup",
                session_id=session_id,
                original_language=language_info["language"],
                override_language="en"
            )
        else:
            # Standard unsupported language response
            unsupported_response = create_language_not_supported_response(
                detected_language, language_name, user_question, session_id
            )
            
            return {
                "synthesis": unsupported_response,
                "tool_results": manager_tool_results,
                "tools_used": ["language_detection"],
                "question_processed": user_question,
                "strategy_applied": {"question_type": "unsupported_language"},
                "detected_language": detected_language,
                "language_name": language_name,
                "language_confidence": language_confidence,
                "response_language": "en",
                "language_supported": False,
                "detection_method": detection_method,
                "synthesis_metadata": {
                    "response_type": "unsupported_language",
                    "fallback_used": True
                }
            }
    
    # STEP 3: Use manager's tool results (don't re-execute tools)
    tool_results = manager_tool_results.copy()
    tools_used = state.get("tools_used", [])
    
    # Only add language detection if not already present
    if "language_detection" not in tools_used:
        tools_used.append("language_detection")
    
    synthesis_logger.info(
        "using_manager_tool_results",
        session_id=session_id,
        tool_count=len(tool_results),
        tools_available=list(tool_results.keys())
    )
    
    # STEP 4: Build enhanced session context
    with PerformanceTimer(synthesis_logger, "session_context_building_enhanced", session_id=session_id):
        session_context = build_enhanced_session_context_for_llm(
            conversation_history, is_followup or is_detected_followup, session_id, user_question
        )
    
    # STEP 5: Create enhanced dynamic prompt
    with PerformanceTimer(synthesis_logger, "prompt_creation_enhanced", session_id=session_id):
        prompt = create_enhanced_dynamic_synthesis_prompt(
            user_question, rag_context, session_context, workflow_parameters, 
            manager_decision, tool_results, target_language=detected_language,
            is_followup=(is_followup or is_detected_followup)
        )
    
    # STEP 6: Generate response using LLM
    try:
        llm = get_llm(config.get("llm", "gpt-4o-mini"))
        with PerformanceTimer(synthesis_logger, "llm_generation_enhanced", session_id=session_id):
            response = llm.invoke(prompt)
            synthesis_content = response.content
        
        synthesis_logger.info(
            "llm_response_generated_enhanced",
            session_id=session_id,
            response_length=len(synthesis_content),
            target_language=detected_language,
            is_followup=(is_followup or is_detected_followup)
        )
        
        # Validate response quality
        if not synthesis_content or len(synthesis_content.strip()) < 20:
            synthesis_logger.warning(
                "llm_response_too_short_enhanced",
                session_id=session_id,
                response_length=len(synthesis_content.strip()) if synthesis_content else 0
            )
            synthesis_content = create_enhanced_fallback_response(
                user_question, conversation_history, is_followup or is_detected_followup, 
                rag_context, detected_language, tool_results
            )
        
    except Exception as e:
        synthesis_logger.error(
            "llm_synthesis_failed_enhanced",
            session_id=session_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        synthesis_content = create_enhanced_fallback_response(
            user_question, conversation_history, is_followup or is_detected_followup, 
            rag_context, detected_language, tool_results
        )
    
    synthesis_logger.info(
        "synthesis_completed_enhanced",
        session_id=session_id,
        final_response_length=len(synthesis_content),
        tools_used_count=len(tools_used),
        response_language=detected_language,
        session_context_used=bool(session_context)
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
            "session_aware_response": is_followup or is_detected_followup,
            "conversation_history_used": len(conversation_history),
            "response_type": "enhanced_multilingual_synthesis",
            "manager_guided": bool(manager_decision),
            "tools_executed": len(tools_used),
            "language_detection_confidence": language_confidence,
            "target_language": detected_language,
            "followup_detected": is_detected_followup
        }
    }

def create_enhanced_dynamic_synthesis_prompt(user_question, rag_context, session_context, 
                                           workflow_parameters, manager_decision="", 
                                           tool_results=None, target_language="en", is_followup=False):
    """
    CRITICAL FIX: Enhanced prompt creation that emphasizes follow-up context.
    """
    
    synthesis_prompt_config = prompt_config.get("synthesis_agent_prompt", {})
    role = synthesis_prompt_config.get("role", "You are an expert US Immigration Assistant.")
    instruction = synthesis_prompt_config.get("instruction", "Provide helpful immigration guidance.")
    
    # Enhanced language header with follow-up context
    language_header = ""
    if target_language != "en":
        language_support = synthesis_prompt_config.get("language_support", {})
        lang_map = {"es": "spanish", "fr": "french", "pt": "portuguese"}
        
        if target_language in lang_map:
            lang_config = language_support.get(lang_map[target_language], {})
            if lang_config:
                language_header = f"""
🌍 CRITICAL LANGUAGE & CONTEXT INSTRUCTION:
{lang_config.get('instruction', '')}

📋 MANDATORY FORMAT TEMPLATE:
{lang_config.get('format_template', '')}

🔗 FOLLOW-UP CONTEXT: {'This is a follow-up question - build upon previous context' if is_followup else 'This is a new conversation'}

---

"""
    else:
        language_header = f"""
📋 ENGLISH RESPONSE WITH CONTEXT:
{'🔗 FOLLOW-UP DETECTED: Build upon the previous conversation context' if is_followup else '🆕 NEW CONVERSATION: Provide comprehensive standalone answer'}

---

"""

    # Enhanced tool results section
    tool_results_text = ""
    if tool_results:
        tool_results_text = "\n🔍 AVAILABLE INFORMATION:\n"
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" not in result:
                tool_results_text += f"📚 {tool_name}: {str(result)[:300]}{'...' if len(str(result)) > 300 else ''}\n"
    
    # Enhanced manager guidance
    manager_guidance = ""
    if manager_decision:
        manager_guidance = f"\n📋 STRATEGIC GUIDANCE:\n{manager_decision[:400]}{'...' if len(manager_decision) > 400 else ''}\n"

    # Critical follow-up instruction
    followup_instruction = ""
    if is_followup and session_context:
        followup_instruction = f"""
🚨 CRITICAL FOLLOW-UP INSTRUCTION:
This question is a follow-up to a previous conversation. You MUST:
1. Reference the previous context naturally
2. Build upon the previous answer
3. Connect this question to the previous topic
4. Don't start from scratch - continue the conversation

"""

    # Construct the enhanced prompt
    full_prompt = f"""{language_header}{role}

{followup_instruction}

{instruction}

🎯 USER QUESTION: "{user_question}"

{session_context}

📚 IMMIGRATION KNOWLEDGE BASE:
{rag_context if rag_context else "Use your general immigration knowledge for foundational information."}

{tool_results_text}

{manager_guidance}

🔧 RESPONSE REQUIREMENTS:
- {'Build upon previous context naturally' if is_followup else 'Provide comprehensive standalone answer'}
- Use official sources and current information
- Maintain consistent format structure
- End with appropriate verification phrase

Remember: {'This is a follow-up question - connect to previous conversation' if is_followup else 'This is a new conversation - provide complete information'}"""
    
    return full_prompt

def create_enhanced_fallback_response(user_question, conversation_history, is_followup, 
                                    rag_context, target_language="en", tool_results=None):
    """
    CRITICAL FIX: Enhanced fallback that considers session context.
    """
    
    if is_followup and conversation_history:
        last_turn = conversation_history[-1]
        
        if target_language == "es":
            return f"""# Respuesta de Seguimiento

## Su Pregunta: "{user_question}"

Veo que esta es una pregunta de seguimiento sobre: **"{last_turn.question}"**

En nuestra conversación anterior sobre {last_turn.question[:50]}..., discutimos los aspectos principales del proceso.

{rag_context if rag_context else "Para obtener información específica sobre costos y tarifas actuales, le recomiendo verificar directamente en uscis.gov."}

## Recursos Oficiales
- **Sitio Web de USCIS:** https://www.uscis.gov
- **Formularios y Tarifas:** https://www.uscis.gov/forms

Verifica la información actual en uscis.gov
"""
        else:
            return f"""# Follow-up Response

## Your Question: "{user_question}"

I can see this is a follow-up to our previous discussion about: **"{last_turn.question}"**

In our previous conversation about {last_turn.question[:50]}..., we covered the main aspects of the process.

{rag_context if rag_context else "For specific information about current costs and fees, I recommend checking directly on uscis.gov."}

## Official Resources
- **USCIS Website:** https://www.uscis.gov
- **Forms and Fees:** https://www.uscis.gov/forms

*Always verify current information on uscis.gov.*
"""
    
    # Standard fallback for new questions
    return f"""# Immigration Information

## Your Question: "{user_question}"

{rag_context if rag_context else "I understand you're asking about immigration procedures. For the most current and accurate information, please visit the official USCIS website."}

## Official Resources
- **USCIS Website:** https://www.uscis.gov
- **Contact USCIS:** https://www.uscis.gov/contactcenter

*Always verify information with official USCIS sources.*
"""

# Keep other existing functions unchanged...
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