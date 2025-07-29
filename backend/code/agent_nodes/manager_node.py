from typing import Dict, Any
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.tools.tool_registry import get_tools_by_agent
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
    print("👔 Manager: Analyzing immigration question...")
    
    user_question = state.get("text", "")
    session_id = state.get("session_id")
    
    # Get tools and LLM
    tools = get_tools_by_agent("manager")
    llm = get_llm(config.get("llm", "gpt-4o-mini"))
    llm_with_tools = llm.bind_tools(tools)

    # Build simple prompt with conversation context
    prompt = build_session_aware_prompt(user_question, state)
    
    print(f"🔧 Manager: Using {len(tools)} tools for analysis")
    
    try:
        # Let LLM decide what to do
        response = llm_with_tools.invoke(prompt)
        
        # Execute tools if LLM requested them
        tool_calls = getattr(response, 'tool_calls', [])
        tool_results = {}
        rag_response_content = ""
        
        print(f"🔧 Manager: Detected {len(tool_calls)} tool calls")
        
        if tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                print(f"⚙️ Executing: {tool_name}")
                
                # Find and execute the tool
                for tool in tools:
                    if tool.name == tool_name:
                        try:
                            result = tool.invoke(tool_args)
                            tool_results[tool_name] = result
                            
                            # Extract RAG content for synthesis
                            if tool_name == "rag_retrieval_tool":
                                if isinstance(result, dict):
                                    rag_response_content = result.get("response", "")
                                else:
                                    rag_response_content = str(result)
                            
                            print(f"✅ Tool {tool_name} executed successfully")
                            
                        except Exception as e:
                            print(f"❌ Tool {tool_name} failed: {e}")
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
        
        print(f"✅ Manager analysis completed")
        
        return {
            "manager_decision": strategic_decision,
            "structured_analysis": basic_analysis,
            "tool_results": tool_results,
            "tools_used": basic_analysis["tools_used"],
            "rag_response": rag_response_content,
            "workflow_parameters": basic_analysis
        }
        
    except Exception as e:
        print(f"❌ Manager error: {e}")
        return {
            "manager_decision": f"Analysis failed: {str(e)}",
            "structured_analysis": {"question_type": "error"},
            "tool_results": {},
            "tools_used": [],
            "rag_response": "",
            "workflow_parameters": {"question_type": "error"}
        }