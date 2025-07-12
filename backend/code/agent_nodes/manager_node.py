from typing import Dict, Any
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH

from backend.code.utils import load_config

config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)

from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState


def manager_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Manager node that coordinates the workflow and makes decisions about processing.
    """
    print("👔 Manager: Analyzing content and coordinating processing...")

    llm = get_llm(config.get("llm", "gpt-4o-mini"))

    prompt = build_prompt_from_config(
        config=prompt_config["manager_agent_prompt"], input_data=state["text"]
    )

    response = llm.invoke(prompt)
    decision = response.content
    print(f"✅ Manager decision: {decision}")
    return {"manager_decision": decision}