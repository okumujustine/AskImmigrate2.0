from typing import Dict, Any

from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
from backend.code.tools.tool_registry import get_tools_by_agent

config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)

MAX_FEEDBACK = 10

def synthesis_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Synthesis agent that creates comprehensive immigration responses using available tools.
    """
    # Check if this component needs revision (skip if already approved)
    if state.get("synthesis_approved", False):
        print("📝 Synthesis: Already approved, skipping...")
        return {}

    print("📝 Synthesis: Creating comprehensive response using tools...")

    # Get tools available to synthesis agent
    tools = get_tools_by_agent("synthesis")
    llm = get_llm(config.get("llm", "gpt-4-turbo"))
    
    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(tools)

    # Build context information
    context_info = f"""
    Manager's guidance: {state.get("manager_decision", "No specific guidance")}
    Synthesis feedback: {state.get("synthesis_feedback", "No specific feedback")}
    RAG response: {state.get("rag_response", "No RAG response available")}
    
    Available tools: {[tool.name for tool in tools]}
    """

    # Get the prompt config and add context
    synthesis_config = prompt_config["synthesis_agent_prompt"].copy()
    synthesis_config["context"] = context_info

    prompt = build_prompt_from_config(config=synthesis_config, input_data=state["text"])

    try:
        response = llm_with_tools.invoke(prompt)
        
        # Check if the model wants to use tools
        tool_calls = getattr(response, 'tool_calls', [])
        tool_results = {}
        
        if tool_calls:
            print(f"🔧 Synthesis: Using {len(tool_calls)} tools...")
            for tool_call in tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                # Find and execute the tool
                for tool in tools:
                    if tool.name == tool_name:
                        result = tool.invoke(tool_args)
                        tool_results[tool_name] = result
                        print(f"✅ Tool {tool_name} executed successfully")
                        break
        
        synthesis_content = response.content
        
        # Merge tool results into the synthesis
        if tool_results:
            synthesis_content += f"\n\nTool Results: {tool_results}"
        
        print(f"✅ Synthesis completed: {synthesis_content[:100]}...")
        
        return {
            "synthesis": synthesis_content,
            "tool_results": tool_results,
            "tools_used": [tool_call['name'] for tool_call in tool_calls]
        }
        
    except Exception as e:
        print(f"❌ Synthesis failed: {e}")
        return {
            "synthesis": f"Error during synthesis: {str(e)}",
            "tool_results": {},
            "tools_used": []
        }