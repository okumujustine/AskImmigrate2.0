from typing import Dict, Any

from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState

from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH

from backend.code.utils import load_config

config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)

MAX_FEEDBACK = 10

def synthesis_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Node that drafts a concise summary of the content from RAG Retriever.
    """
    # Check if this component needs revision (skip if already approved)
    if state.get("rag_retriever_approved", False):
        print("📝 RAG Retrieval: Already approved, skipping...")
        return {}

    print("📝 RAG Retrieval: Creating summary...")

    llm = get_llm(config.get("llm", "gpt-4o-mini"))

    # Build context information
    context_info = f"""
    Manager's guidance: {state.get("manager_decision", "No specific guidance")}
    RAG-specific feedback: {state.get("rag_retriever_feedback", "No specific feedback")}
    Generate a list of {MAX_FEEDBACK} different content at most.
    """

    # Get the prompt config and add context
    synthesis_config = prompt_config["synthesis_agent_prompt"].copy()
    synthesis_config["context"] = context_info

    prompt = build_prompt_from_config(config=synthesis_config, input_data=state["text"])

    synthesis = llm.invoke(prompt).content
    print(f"✅ Summary generated: {synthesis[:100]}...")
    return {"synthesis": synthesis}