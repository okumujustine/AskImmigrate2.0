# New Synthesis code

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

# Multilingual imports (with graceful fallback)
try:
    from backend.code.multilingual.translation_service import translation_service
    MULTILINGUAL_AVAILABLE = True
except ImportError:
    MULTILINGUAL_AVAILABLE = False
    synthesis_logger.warning("Multilingual support not available")

import asyncio

def create_spanish_native_prompt(user_question: str, rag_context: str, session_context: str, 
                                workflow_parameters: Dict[str, Any], manager_decision: str = "", 
                                tool_results: Dict[str, Any] = None) -> str:
    """Create a native Spanish prompt for optimal Spanish responses."""
    
    # Build Spanish context
    spanish_context = ""
    if session_context:
        spanish_context = f"CONTEXTO DE LA CONVERSACIÓN:\n{session_context}\n\n"
    
    # Build knowledge context
    knowledge_context = ""
    if rag_context:
        knowledge_context = f"INFORMACIÓN RELEVANTE DE INMIGRACIÓN:\n{rag_context}\n\n"
    
    # Build tool results
    tools_context = ""
    if tool_results:
        tools_context = "RESULTADOS DE HERRAMIENTAS:\n"
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" not in result:
                tools_context += f"- {tool_name}: {str(result)[:200]}...\n"
        tools_context += "\n"
    
    # Manager guidance context
    manager_guidance = ""
    if manager_decision:
        manager_guidance = f"ORIENTACIÓN ESTRATÉGICA:\n{manager_decision[:300]}...\n\n"
    
    # Create comprehensive Spanish prompt using synthesis agent guidelines
    prompt = f"""Eres un asistente experto en inmigración estadounidense que proporciona respuestas precisas y confiables basadas en fuentes oficiales.

PREGUNTA DEL USUARIO: "{user_question}"

{spanish_context}{knowledge_context}{tools_context}{manager_guidance}

INSTRUCCIONES CRÍTICAS DE RESPUESTA:
1. VALIDACIÓN DE FUENTES (OBLIGATORIO):
   - SOLO usa fuentes gubernamentales oficiales (USCIS.gov, Travel.state.gov, DHS.gov)
   - Mantén nombres oficiales de formularios en inglés (I-20, I-94, I-485, etc.)
   - Para cualquier información no gubernamental, declara: "Esto debe verificarse en USCIS.gov"
   - Nunca digas "según mi conocimiento" o similares

2. CALIBRACIÓN DE CONFIANZA:
   - Inicia claramente: "Basado en la orientación oficial de USCIS..."
   - Para información definitiva (.gov): Sé directo y autoritativo
   - Para procesos generales: Reconoce posibles cambios
   - Para áreas inciertas: Recomienda verificación en USCIS

3. FORMATO DE RESPUESTA:
   - Declaración de autoridad (requerida): "Basado en [fuente] de [fecha]..."
   - Resumen ejecutivo: Un párrafo claro y autoritativo
   - Explicación detallada con viñetas (3-5 puntos clave)
   - Consideraciones importantes: Criterios de elegibilidad, restricciones, próximos pasos
   - Recursos adicionales: Páginas relevantes de USCIS, formularios requeridos

4. FUENTES AUTORIZADAS ÚNICAMENTE:
   - USCIS.gov (fuente principal)
   - Travel.state.gov (información de visas)
   - DHS.gov, DOL.gov, ICE.gov
   - NUNCA referencias sitios no gubernamentales, blogs, instituciones educativas

5. PROHIBIDO:
   - Referencias a sitios web no gubernamentales
   - Sitios web universitarios (incluso para visas de estudiante)
   - Sitios web de firmas de abogados de inmigración
   - Servicios de inmigración de terceros
   - "Según mi fecha límite de conocimiento" en cualquier forma

Usa terminología de inmigración precisa en español, mantén un tono formal profesional apropiado para comunicaciones gubernamentales, y organiza la información claramente con markdown.

Si esta es una pregunta de seguimiento basada en el contexto de conversación, refiérete específicamente a lo discutido anteriormente.

Responde de manera completa, precisa y útil en español profesional:"""
    
    return prompt

def synthesis_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Strategic Synthesis Agent with English + Spanish support.
    
    Spanish: Native generation + English fallback
    English: Direct generation  
    Other languages: English response with explanation
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
        has_manager_guidance=bool(manager_decision),
        multilingual_available=MULTILINGUAL_AVAILABLE
    )
    
    try:
        # Step 1: Execute tools
        tool_results = {}
        tools_used = []
        
        with PerformanceTimer(synthesis_logger, "tool_execution_phase", session_id=session_id):
            try:
                tool_results, tools_used = execute_manager_recommended_tools(
                    manager_decision, user_question, session_id
                )
            except Exception as e:
                synthesis_logger.error("tool_execution_failed", session_id=session_id, error=str(e))
                tool_results, tools_used = {}, []

        # Step 2: Build session context
        with PerformanceTimer(synthesis_logger, "session_context_building", session_id=session_id):
            session_context = build_session_context_for_llm(
                conversation_history, is_followup, session_id, user_question
            )
        
      # Step 3: Get language info and determine response strategy
        language_info = state.get("language_info", {"language": "en"})
        target_language = language_info.get("language", "en")
        requires_multilingual = target_language != "en"

        # EXPLICIT DEBUG: Log each value separately
        synthesis_logger.info(f"DEBUG: language_info = {language_info}")
        synthesis_logger.info(f"DEBUG: target_language = '{target_language}'")
        synthesis_logger.info(f"DEBUG: requires_multilingual = {requires_multilingual}")
        synthesis_logger.info(f"DEBUG: state_keys = {list(state.keys())}")

        # Check if language_info is actually in the state
        if "language_info" in state:
            synthesis_logger.info(f"DEBUG: language_info found in state: {state['language_info']}")
        else:
            synthesis_logger.info("DEBUG: language_info NOT found in state!")
            synthesis_logger.info(f"DEBUG: Available state keys: {list(state.keys())}")
            
            # NEW: Check workflow_parameters for language_info
            workflow_params = state.get("workflow_parameters", {})
            synthesis_logger.info(f"DEBUG: workflow_parameters = {workflow_params}")
            
            if isinstance(workflow_params, dict) and "language_info" in workflow_params:
                backup_language_info = workflow_params["language_info"]
                synthesis_logger.info(f"DEBUG: Found language_info in workflow_parameters: {backup_language_info}")
                # Use the backup language info
                language_info = backup_language_info
                target_language = language_info.get("language", "en")
                requires_multilingual = target_language != "en"
                synthesis_logger.info(f"DEBUG: Updated target_language to '{target_language}' from workflow_parameters")
            else:
                synthesis_logger.info("DEBUG: language_info also NOT found in workflow_parameters!")
            
            # NEW: Check structured_analysis for language info
            structured_analysis = state.get("structured_analysis", {})
            synthesis_logger.info(f"DEBUG: structured_analysis = {structured_analysis}")
            
            if isinstance(structured_analysis, dict) and "user_language" in structured_analysis:
                user_lang = structured_analysis["user_language"]
                synthesis_logger.info(f"DEBUG: Found user_language in structured_analysis: {user_lang}")
                if user_lang != "en":
                    # Create language_info from structured_analysis
                    language_info = {
                        "language": user_lang,
                        "confidence": structured_analysis.get("language_confidence", 0.8),
                        "requires_translation": structured_analysis.get("requires_translation", True),
                        "detection_method": "from_structured_analysis"
                    }
                    target_language = user_lang
                    requires_multilingual = True
                    synthesis_logger.info(f"DEBUG: Updated target_language to '{target_language}' from structured_analysis")
            else:
                synthesis_logger.info("DEBUG: No user_language found in structured_analysis either!")

        synthesis_logger.info(
            "language_context_determined",
            session_id=session_id,
            target_language=target_language,
            requires_multilingual=requires_multilingual,
            multilingual_available=MULTILINGUAL_AVAILABLE
        )
                
        # Step 4: FIXED MULTILINGUAL GENERATION
        synthesis_content = ""
        translation_info = None
        
        if target_language == "es":
            # SPANISH: Native generation + English fallback
            synthesis_logger.info("using_native_spanish_generation", session_id=session_id)
            
            try:
                # Method 1: Direct Spanish generation (like English approach)
                spanish_prompt = create_spanish_native_prompt(
                    user_question, rag_context, session_context, workflow_parameters, 
                    manager_decision, tool_results
                )
                
                # Use same LLM as English generation
                llm = get_llm(config.get("llm", "gpt-4o-mini"))
                response = llm.invoke(spanish_prompt)
                synthesis_content = response.content if hasattr(response, 'content') else str(response)
                
                # Validate Spanish response
                if not synthesis_content or len(synthesis_content.strip()) < 50:
                    raise ValueError("Spanish response too short")
                
                translation_info = {
                    "method": "native_spanish_llm",
                    "confidence": 0.95,
                    "response_length": len(synthesis_content)
                }
                
                synthesis_logger.info(
                    "native_spanish_generation_successful", 
                    session_id=session_id,
                    response_length=len(synthesis_content)
                )
                    
            except Exception as e:
                # Method 2: English fallback
                synthesis_logger.warning(
                    "spanish_generation_failed_using_english_fallback",
                    session_id=session_id,
                    error=str(e)
                )
                synthesis_content = ""  # Will trigger English generation below
        
        elif target_language != "en":
            # OTHER LANGUAGES: English response with multilingual note
            synthesis_logger.info(
                "using_english_with_multilingual_note", 
                session_id=session_id, 
                target_language=target_language
            )
            
            # Note explaining language support
            multilingual_note = f"""*I detected your language preference, but I currently provide detailed responses in English and Spanish only. For maximum accuracy of immigration information, I'm responding in English. You can also ask your question in Spanish (español) for a native Spanish response.*

---

"""
            
            # Generate English response
            english_content = ""
            try:
                prompt = create_dynamic_synthesis_prompt(
                    user_question, rag_context, session_context, workflow_parameters, 
                    manager_decision, tool_results
                )
                
                llm = get_llm(config.get("llm", "gpt-4o-mini"))
                response = llm.invoke(prompt)
                english_content = response.content if hasattr(response, 'content') else str(response)
                
            except Exception as e:
                synthesis_logger.error("english_generation_failed", error=str(e))
                english_content = ""
            
            synthesis_content = multilingual_note + english_content if english_content else ""
            translation_info = {
                "method": f"english_with_{target_language}_note",
                "original_language": target_language,
                "response_language": "en"
            }
        
        # Step 5: English generation (original logic OR fallback)
        if not synthesis_content:
            synthesis_logger.info("using_english_generation", session_id=session_id)
            
            try:
                # Create English prompt (existing logic)
                prompt = create_dynamic_synthesis_prompt(
                    user_question, rag_context, session_context, workflow_parameters, 
                    manager_decision, tool_results
                )
                
                llm = get_llm(config.get("llm", "gpt-4o-mini"))
                with PerformanceTimer(synthesis_logger, "llm_generation", session_id=session_id):
                    response = llm.invoke(prompt)
                    synthesis_content = response.content if hasattr(response, 'content') else str(response)
                
                if not translation_info:
                    translation_info = {"method": "english_native"}
                elif translation_info.get("method") == "native_spanish_llm":
                    # This was a Spanish fallback
                    translation_info["method"] = "spanish_failed_english_fallback"
                    translation_info["spanish_error"] = "Spanish generation failed, using English"
                
                synthesis_logger.info(
                    "english_generation_successful", 
                    session_id=session_id,
                    response_length=len(synthesis_content)
                )
                
            except Exception as e:
                synthesis_logger.error(
                    "english_generation_failed",
                    session_id=session_id,
                    error=str(e)
                )
                synthesis_content = ""
        
        # Step 6: Fallback response if everything failed
        if not synthesis_content or len(synthesis_content.strip()) < 20:
            synthesis_logger.warning(
                "using_fallback_response",
                session_id=session_id,
                response_length=len(synthesis_content.strip()) if synthesis_content else 0
            )
            synthesis_content = create_fallback_response(
                user_question, conversation_history, is_followup, rag_context, target_language
            )
            if not translation_info:
                translation_info = {"method": "fallback_response"}
        
        # Step 7: Return results
        synthesis_logger.info(
            "synthesis_completed_successfully",
            session_id=session_id,
            final_response_length=len(synthesis_content),
            target_language=target_language,
            generation_method=translation_info.get("method", "unknown") if translation_info else "unknown",
            tools_used_count=len(tools_used)
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
                "response_type": "english_spanish_multilingual",
                "manager_guided": bool(manager_decision),
                "tools_executed": len(tools_used),
                "user_language": target_language,
                "response_language": target_language if target_language in ["en", "es"] else "en",
                "generation_metadata": translation_info,
                "multilingual_enabled": MULTILINGUAL_AVAILABLE,
                "processing_successful": True
            }
        }
        
    except Exception as e:
        synthesis_logger.error(
            "synthesis_node_critical_failure",
            session_id=session_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        
        return create_error_response(f"Synthesis failed: {str(e)}", session_id, state)

def create_error_response(error_message: str, session_id: str, state: ImmigrationState = None) -> Dict[str, Any]:
    """Create standardized error response with multilingual support"""
    
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
    elif language != "en":
        fallback_text = f"""*I detected your language preference, but I can currently provide detailed responses in English and Spanish only. For maximum accuracy of immigration information, I'm responding in English.*

---

# Processing Error

## Your Question: "{user_question}"

I apologize, but I encountered a technical issue processing your question: {error_message}

## Alternative Resources:
- **USCIS Website:** https://www.uscis.gov
- **USCIS Contact Center:** https://www.uscis.gov/contactcenter

Please try again later."""
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
            "verify": "Siempre verifique la información con fuentes oficiales de USCIS.",
            "understanding": "Entiendo que está preguntando sobre inmigración.",
            "no_specific_info": "Aunque no tengo información específica disponible inmediatamente, puedo guiarle a los recursos correctos.",
            "official_resources": "Recursos Oficiales:",
            "website": "Sitio Web de USCIS:",
            "contact_center": "Centro de Contacto de USCIS:",
            "forms_fees": "Formularios y Tarifas:"
        }
        uscis_url = "https://www.uscis.gov/es"
        contact_url = "https://www.uscis.gov/es/contactcenter"
        forms_url = "https://www.uscis.gov/es/formularios"
    elif language != "en":
        # For non-English, non-Spanish: English response with multilingual note
        templates = {
            "understanding": "I understand you're asking about immigration.",
            "language_note": f"*I detected your language preference, but I currently provide detailed responses in English and Spanish only. For maximum accuracy, I'm responding in English.*",
            "no_specific_info": "While I don't have specific information immediately available, I can guide you to the right resources.",
            "official_resources": "Official Resources:",
            "website": "USCIS Website:",
            "verify": "Always verify information with official USCIS sources."
        }
        uscis_url = "https://www.uscis.gov"
        contact_url = "https://www.uscis.gov/contactcenter"
        
        response_text = rag_context if rag_context else f"{templates['understanding']} {templates['no_specific_info']}"
        
        return f"""{templates["language_note"]}

---

# Immigration Information

## Your Question: "{user_question}"

{response_text}

## {templates["official_resources"]}
- **{templates["website"]}** {uscis_url}
- **Contact Center:** {contact_url}

{templates["verify"]}
"""
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
            "verify": "Always verify information with official USCIS sources for the most current requirements.",
            "understanding": "I understand you're asking about immigration.",
            "no_specific_info": "While I don't have specific information immediately available, I can guide you to the right resources.",
            "official_resources": "Official Resources:",
            "website": "USCIS Website:",
            "contact_center": "USCIS Contact Center:",
            "forms_fees": "Forms and Fees:"
        }
        uscis_url = "https://www.uscis.gov"
        contact_url = "https://www.uscis.gov/contactcenter"
        forms_url = "https://www.uscis.gov/forms"
    
    # Handle session reference questions (multilingual)
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
    
    # Default immigration info response (multilingual)
    else:
        response_text = rag_context if rag_context else f"{templates['understanding']} {templates['no_specific_info']}"
        
        return f"""# {templates.get("immigration_info", "Immigration Information")}

## {templates["your_question"]} "{user_question}"

{response_text}

## {templates["official_resources"]}
- **{templates["website"]}** {uscis_url}
- **{templates.get("contact_center", "Contact Center")}** {contact_url}
- **{templates.get("forms_fees", "Forms and Fees")}** {forms_url if language == "es" else "https://www.uscis.gov/forms"}

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
        if any(word in question_lower for word in ["fee", "cost", "price", "how much", "filing fee", "cuesta", "precio"]):
            recommended_tools.extend(["web_search_tool", "fee_calculator_tool"])
        
        # Current/recent information needs web search
        elif any(word in question_lower for word in ["current", "latest", "recent", "2024", "2025", "new", "update", "actual", "reciente"]):
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