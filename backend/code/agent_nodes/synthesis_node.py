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
    llm = get_llm(config.get("llm", "gpt-4o-mini"))
    
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
        
        # Extract key information from tool results for state
        rag_response = ""
        visa_type = ""
        visa_fee = 0.0
        references = []
        
        # Extract from RAG tool results
        if "rag_retrieval_tool" in tool_results:
            rag_data = tool_results["rag_retrieval_tool"]
            rag_response = rag_data.get("response", "")
            references.extend(rag_data.get("references", []))
        
        # Extract from fee calculator results
        fee_tool_results = [v for k, v in tool_results.items() if "fee_calculator_tool" in k]
        if fee_tool_results:
            fee_data = fee_tool_results[0]  # Take first fee result
            if fee_data.get("success", False):
                visa_type = fee_data.get("visa_type", "")
                visa_fee = fee_data.get("fees", {}).get("total", 0.0)
        
        return {
            "synthesis": synthesis_content,
            "rag_response": rag_response,
            "visa_type": visa_type, 
            "visa_fee": visa_fee,
            "references": references,
            "tool_results": tool_results,
            "tools_used": [tool_call['name'] for tool_call in tool_calls]
        }
        
    except Exception as e:
        print(f"❌ Synthesis failed: {e}")
        return {
            "synthesis": f"Error during synthesis: {str(e)}",
            "rag_response": f"Error during synthesis: {str(e)}",
            "visa_type": "",
            "visa_fee": 0.0,
            "references": [],
            "tool_results": {},
            "tools_used": []
        }