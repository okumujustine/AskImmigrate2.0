from typing import Dict, Any
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.tools.tool_registry import get_tools_by_agent
from backend.code.structured_logging import manager_logger, PerformanceTimer
import re

config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)

def build_session_aware_prompt(user_question: str, state: ImmigrationState) -> str:
    base_prompt = build_prompt_from_config(
        config=prompt_config["manager_agent_prompt"], 
        input_data=user_question
    )
    
    # Simple, clean conversation context
    conversation_context = ""
    if state.get("conversation_history"):
        conversation_context = "CONVERSATION SO FAR:\n"
        for i, turn in enumerate(state["conversation_history"], 1):
            conversation_context += f"Q{i}: {turn.question}\n"
            conversation_context += f"A{i}: {turn.answer}\n\n"
        conversation_context += f"NEW QUESTION: {user_question}\n\n"
    
    return f"{conversation_context}{base_prompt}"
   

def manager_node(state: ImmigrationState) -> Dict[str, Any]:
    session_id = state.get("session_id")
    user_question = state.get("text", "")
    
    manager_logger.info(
        "manager_analysis_started",
        session_id=session_id,
        question_length=len(user_question),
        has_history=bool(state.get("conversation_history"))
    )
    
    # Get tools and LLM
    tools = get_tools_by_agent("manager")
    llm = get_llm(config.get("llm", "gpt-4o-mini"))
    llm_with_tools = llm.bind_tools(tools)

    manager_logger.info(
        "manager_tools_loaded", 
        tool_count=len(tools),
        llm_model=config.get("llm", "gpt-4o-mini"),
        session_id=session_id
    )

    with PerformanceTimer(manager_logger, "prompt_building", session_id=session_id):
        # Build simple prompt with conversation context
        prompt = build_session_aware_prompt(user_question, state)
    
    try:
        with PerformanceTimer(manager_logger, "llm_invocation", session_id=session_id):
            # Let LLM decide what to do
            response = llm_with_tools.invoke(prompt)
        
        # Execute tools if LLM requested them
        tool_calls = getattr(response, 'tool_calls', [])
        tool_results = {}
        rag_response_content = ""
        
        manager_logger.info(
            "manager_tool_calls_detected",
            tool_call_count=len(tool_calls),
            tool_names=[call['name'] for call in tool_calls] if tool_calls else [],
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
                
                # Find and execute the tool
                for tool in tools:
                    if tool.name == tool_name:
                        try:
                            with PerformanceTimer(manager_logger, f"tool_{tool_name}", session_id=session_id):
                                result = tool.invoke(tool_args)
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
                            manager_logger.error(
                                "tool_execution_failed",
                                tool_name=tool_name,
                                error_type=type(e).__name__,
                                error_message=str(e),
                                session_id=session_id
                            )
                            tool_results[tool_name] = {"error": str(e)}
                        break
        
        # Get strategic decision (simplified)
        strategic_decision = response.content or "Analysis completed."
        
        # Simplified analysis extraction (let LLM decide structure)
        basic_analysis = {
            "question_type": "immigration_inquiry",
            "tools_used": [call['name'] for call in tool_calls] if tool_calls else [],
            "session_aware": bool(session_id)
        }
        
        manager_logger.info(
            "manager_analysis_completed",
            decision_length=len(strategic_decision),
            tools_used_count=len(basic_analysis["tools_used"]),
            session_id=session_id
        )
        
        return {
            "manager_decision": strategic_decision,
            "structured_analysis": basic_analysis,
            "tool_results": tool_results,
            "tools_used": basic_analysis["tools_used"],
            "rag_response": rag_response_content,
            "workflow_parameters": basic_analysis
        }
        
    except Exception as e:
        manager_logger.error(
            "manager_analysis_failed",
            error_type=type(e).__name__,
            error_message=str(e),
            session_id=session_id
        )
        return {
            "manager_decision": f"Analysis failed: {str(e)}",
            "structured_analysis": {"question_type": "error"},
            "tool_results": {},
            "tools_used": [],
            "rag_response": "",
            "workflow_parameters": {"question_type": "error"}
        }