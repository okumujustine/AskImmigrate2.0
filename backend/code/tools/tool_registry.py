from typing import List
from langchain_core.tools import BaseTool

from .rag_tool import rag_retrieval_tool
from .fee_calculator_tool import fee_calculator_tool
from .web_search_tool import web_search_tool


def get_all_tools() -> List[BaseTool]:
    """
    Get all available tools for the immigration assistant.
    
    Returns:
        List of all registered tools
    """
    return [
        rag_retrieval_tool,
        fee_calculator_tool,
        web_search_tool
    ]


def get_tools_by_agent(agent_name: str) -> List[BaseTool]:
    """
    Get tools available for a specific agent based on configuration.
    
    Args:
        agent_name: Name of the agent requesting tools
        
    Returns:
        List of tools available to the agent
    """
    tool_mapping = {
        "manager": [rag_retrieval_tool],
        "synthesis": [rag_retrieval_tool, web_search_tool, fee_calculator_tool],
        "reviewer": [fee_calculator_tool]
    }
    
    return tool_mapping.get(agent_name, [])