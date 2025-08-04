from typing import Dict, Any, Optional
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.tools.tool_registry import get_all_tools
from backend.code.structured_logging import manager_logger, PerformanceTimer
from backend.code.input_validation import validate_immigration_query, check_rate_limit
from backend.code.retry_logic import (
    wrap_llm_call_with_retry,
    wrap_tool_call_with_retry,
    LLMRetryableError,
    ToolRetryableError
)
import re

# Multilingual imports (with graceful fallback)
try:
    from backend.code.multilingual.translation_service import translation_service, SupportedLanguage
    MULTILINGUAL_AVAILABLE = True
except ImportError:
    MULTILINGUAL_AVAILABLE = False
    manager_logger.warning("Multilingual support not available")

import asyncio

config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)

def validate_and_sanitize_input(state: ImmigrationState) -> Dict[str, Any]:
    """
    Validate and sanitize user input before processing.
    
    Args:
        state: Immigration state with user input
        
    Returns:
        Dictionary with validation results and sanitized state
    """
    session_id = state.get("session_id")
    user_question = state.get("text", "")
    
    manager_logger.info(
        "input_validation_started",
        session_id=session_id,
        original_length=len(user_question)
    )
    
    # Step 1: Rate limiting check
    if session_id and not check_rate_limit(session_id):
        manager_logger.warning(
            "rate_limit_exceeded",
            session_id=session_id
        )
        return {
            "is_valid": False,
            "error_type": "rate_limit",
            "error_message": "Rate limit exceeded. Please wait before sending another request.",
            "sanitized_state": state
        }
    
    # Step 2: Input validation
    validation_result = validate_immigration_query(user_question, session_id)
    
    if not validation_result.is_valid:
        manager_logger.warning(
            "input_validation_failed",
            session_id=session_id,
            errors=validation_result.errors,
            warnings=validation_result.warnings
        )
        return {
            "is_valid": False,
            "error_type": "validation",
            "error_message": "; ".join(validation_result.errors),
            "warnings": validation_result.warnings,
            "sanitized_state": state
        }
    
    # Step 3: Update state with sanitized input
    sanitized_state = state.copy()
    sanitized_state["text"] = validation_result.sanitized_input
    
    # Log any warnings
    if validation_result.warnings:
        manager_logger.info(
            "input_validation_warnings",
            session_id=session_id,
            warnings=validation_result.warnings
        )
    
    manager_logger.info(
        "input_validation_completed",
        session_id=session_id,
        sanitized_length=len(validation_result.sanitized_input),
        warnings_count=len(validation_result.warnings)
    )
    
    return {
        "is_valid": True,
        "sanitized_state": sanitized_state,
        "validation_warnings": validation_result.warnings
    }

def detect_user_language(user_question: str, session_id: str) -> Dict[str, Any]:
    """Detect user language synchronously"""
    
    if not MULTILINGUAL_AVAILABLE:
        return {
            "language": "en",
            "confidence": 1.0,
            "detection_method": "multilingual_disabled",
            "requires_translation": False
        }
    
    try:
        question_lower = user_question.lower()
        
        # Spanish detection patterns
        spanish_patterns = ['¿', '¡', 'ñ', 'inmigración', 'visa', 'cómo', 'qué', 'cuándo', 'dónde']
        spanish_score = sum(1 for pattern in spanish_patterns if pattern in question_lower)
        
        if spanish_score > 0:
            confidence = min(0.6 + (spanish_score * 0.1), 0.95)
            return {
                "language": "es", 
                "confidence": confidence,
                "detection_method": "pattern",
                "requires_translation": True
            }
        
        # French patterns
        if any(pattern in question_lower for pattern in ['ç', 'où', 'français']):
            return {
                "language": "fr",
                "confidence": 0.7,
                "detection_method": "pattern", 
                "requires_translation": True
            }
        
        # Portuguese patterns
        if any(pattern in question_lower for pattern in ['ção', 'português', 'imigração']):
            return {
                "language": "pt",
                "confidence": 0.7,
                "detection_method": "pattern",
                "requires_translation": True
            }
        
        # Default to English
        return {
            "language": "en",
            "confidence": 0.9,
            "detection_method": "default",
            "requires_translation": False
        }
        
    except Exception as e:
        manager_logger.error(f"Language detection failed: {e}")
        return {
            "language": "en",
            "confidence": 0.0,
            "detection_method": "error_fallback",
            "requires_translation": False,
            "error": str(e)
        }

def build_session_aware_prompt(user_question: str, state: ImmigrationState, 
                              language_info: Optional[Dict[str, Any]] = None) -> str:
    """
    Build prompt with session context and language awareness
    """
    base_prompt = build_prompt_from_config(
        config=prompt_config["manager_agent_prompt"], 
        input_data=user_question
    )
    
    conversation_context = ""
    if state.get("conversation_history"):
        conversation_context = "CONVERSATION SO FAR:\n"
        for i, turn in enumerate(state["conversation_history"], 1):
            conversation_context += f"Q{i}: {turn.question}\n"
            conversation_context += f"A{i}: {turn.answer}\n\n"
        conversation_context += f"NEW QUESTION: {user_question}\n\n"
    
    # Add language context if non-English
    language_context = ""
    if language_info and language_info.get("language") != "en":
        language_context = f"""
LANGUAGE CONTEXT:
- User's detected language: {language_info['language']}
- Question language confidence: {language_info['confidence']:.2f}
- Response should be generated in {language_info['language']} for best user experience

"""
    
    return f"{conversation_context}{language_context}{base_prompt}"

def manager_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Manager node with validation, retry logic, error handling, and multilingual support.
    
    Args:
        state: Immigration state with user input
        
    Returns:
        Manager analysis results with tool recommendations, execution results, and language information
    """
    session_id = state.get("session_id")
    
    manager_logger.info(
        "manager_analysis_started",
        session_id=session_id,
        has_history=bool(state.get("conversation_history"))
    )
    
    try:
        # Step 1: Input validation and sanitization
        validation_result = validate_and_sanitize_input(state)
        
        if not validation_result["is_valid"]:
            return {
                "manager_decision": f"Input validation failed: {validation_result['error_message']}",
                "structured_analysis": {"question_type": "validation_error"},
                "tool_results": {},
                "tools_used": [],
                "rag_response": "",
                "workflow_parameters": {"question_type": "validation_error"},
                "validation_errors": [validation_result["error_message"]],
                "validation_warnings": validation_result.get("warnings", [])
            }
        
        # Use sanitized state
        sanitized_state = validation_result["sanitized_state"]
        user_question = sanitized_state.get("text", "")
        
        # Step 2: Language Detection (NEW)
        language_info = detect_user_language(user_question, session_id)
        
        # Step 3: Get ALL tools (manager orchestrates so needs access to everything)
        tools = get_all_tools()
        llm = get_llm(config.get("llm", "gpt-4o-mini"))
        llm_with_tools = llm.bind_tools(tools)
        
        manager_logger.info(
            "manager_tools_loaded", 
            tool_count=len(tools),
            available_tools=[t.name for t in tools],
            llm_model=config.get("llm", "gpt-4o-mini"),
            user_language=language_info["language"],
            session_id=session_id
        )
        
        # Step 4: Build prompt with session and language awareness (UPDATED)
        with PerformanceTimer(manager_logger, "prompt_building", session_id=session_id):
            prompt = build_session_aware_prompt(user_question, sanitized_state, language_info)
        
        # Step 5: LLM analysis with retry logic
        try:
            wrapped_llm_call = wrap_llm_call_with_retry(
                llm_with_tools.invoke, 
                session_id=session_id
            )
            
            with PerformanceTimer(manager_logger, "llm_invocation", session_id=session_id):
                response = wrapped_llm_call(prompt)
        
        except Exception as e:
            manager_logger.error(
                "llm_invocation_failed_final",
                error_type=type(e).__name__,
                error_message=str(e),
                session_id=session_id
            )
            return {
                "manager_decision": f"LLM analysis failed: {str(e)}",
                "structured_analysis": {"question_type": "llm_error"},
                "tool_results": {},
                "tools_used": [],
                "rag_response": "",
                "workflow_parameters": {"question_type": "llm_error"},
                "language_info": language_info  # NEW
            }
        
        # Step 6: Execute tools if LLM requested them
        tool_calls = getattr(response, 'tool_calls', [])
        tool_results = {}
        rag_response_content = ""
        
        manager_logger.info(
            "manager_tool_calls_detected",
            tool_call_count=len(tool_calls),
            tool_names=[call['name'] for call in tool_calls] if tool_calls else [],
            user_language=language_info["language"],
            session_id=session_id
        )
        
        if tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                manager_logger.info(
                    "tool_execution_started",
                    tool_name=tool_name,
                    tool_args_keys=list(tool_args.keys()),
                    session_id=session_id
                )
                
                # Find and execute the tool with retry logic
                tool_found = False
                for tool in tools:
                    if tool.name == tool_name:
                        tool_found = True
                        try:
                            # Wrap tool call with retry logic
                            wrapped_tool_call = wrap_tool_call_with_retry(
                                tool.invoke, 
                                session_id=session_id
                            )
                            
                            with PerformanceTimer(manager_logger, f"tool_{tool_name}", session_id=session_id):
                                result = wrapped_tool_call(tool_args)
                                tool_results[tool_name] = result
                                
                                # Extract RAG content for synthesis
                                if tool_name == "rag_retrieval_tool":
                                    if isinstance(result, dict):
                                        rag_response_content = result.get("response", "")
                                    else:
                                        rag_response_content = str(result)
                                
                                manager_logger.info(
                                    "tool_execution_success",
                                    tool_name=tool_name,
                                    response_length=len(str(result)),
                                    session_id=session_id
                                )
                            
                        except Exception as e:
                            # Classify and handle the error
                            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                                error_type = "network_error"
                            elif "rate limit" in str(e).lower():
                                error_type = "rate_limit"
                            else:
                                error_type = "tool_error"
                            
                            manager_logger.error(
                                "tool_execution_failed",
                                tool_name=tool_name,
                                error_type=error_type,
                                error_message=str(e),
                                session_id=session_id
                            )
                            
                            tool_results[tool_name] = {
                                "error": str(e),
                                "error_type": error_type,
                                "retry_attempted": True
                            }
                        break
                
                if not tool_found:
                    manager_logger.warning(
                        "tool_not_found",
                        tool_name=tool_name,
                        available_tools=[t.name for t in tools],
                        session_id=session_id
                    )
                    tool_results[tool_name] = {
                        "error": f"Tool '{tool_name}' not found",
                        "error_type": "configuration_error"
                    }
        
        # Step 7: Create strategic analysis with language information (UPDATED)
        strategic_decision = response.content or "Analysis completed."
        
        structured_analysis = {
            "question_type": "immigration_inquiry",
            "tools_used": [call['name'] for call in tool_calls] if tool_calls else [],
            "session_aware": bool(sanitized_state.get("conversation_history")),
            "complexity": "complex" if len(tool_calls) > 1 else "simple",
            "analysis_confidence": "high" if tool_calls else "medium",
            "user_language": language_info["language"],  # NEW
            "language_confidence": language_info["confidence"],  # NEW
            "requires_translation": language_info["requires_translation"]  # NEW
        }
        
        # Step 8: Compile final results with language information (UPDATED)
        final_result = {
            "manager_decision": strategic_decision,
            "structured_analysis": structured_analysis,
            "tool_results": tool_results,
            "tools_used": structured_analysis["tools_used"],
            "rag_response": rag_response_content,
            "workflow_parameters": structured_analysis,
            "validation_warnings": validation_result.get("validation_warnings", []),
            "language_info": language_info  # NEW: Pass language info to synthesis
        }
        
        manager_logger.info(
            "manager_analysis_completed",
            decision_length=len(final_result["manager_decision"]),
            tools_used_count=len(final_result["tools_used"]),
            successful_tools=sum(1 for result in final_result["tool_results"].values() if "error" not in result),
            user_language=language_info["language"],  # NEW
            language_detection_confidence=language_info["confidence"],  # NEW
            requires_translation=language_info["requires_translation"],  # NEW
            session_id=session_id
        )
        
        return final_result
        
    except Exception as e:
        manager_logger.error(
            "manager_analysis_failed",
            error_type=type(e).__name__,
            error_message=str(e),
            session_id=session_id
        )
        
        return {
            "manager_decision": f"Analysis failed: {str(e)}",
            "structured_analysis": {"question_type": "system_error"},
            "tool_results": {},
            "tools_used": [],
            "rag_response": "",
            "workflow_parameters": {"question_type": "system_error"},
            "system_error": str(e),
            "language_info": {"language": "en", "error": True}  # NEW
        }