from typing import Dict, Any

from langgraph.constants import START, END
from langgraph.graph import StateGraph

from backend.code.agent_nodes.manager_node import manager_node
from backend.code.agent_nodes.synthesis_node import synthesis_node
from backend.code.agent_nodes.reviewer_node import reviewer_node, route_from_reviewer
from backend.code.agentic_state import ImmigrationState
from langchain_core.runnables.graph import MermaidDrawMethod
import os
from dotenv import load_dotenv

from backend.code.paths import OUTPUTS_DIR

load_dotenv()
if os.environ.get("LANGSMITH_TRACING") != "true":
    print("WARNING: LangSmith tracing is not enabled. Set LANGSMITH_TRACING=true in your environment.")

def create_ask_immigrate_graph() -> StateGraph:
    """
    Creates and returns the agentic AskImmigrate2.0 graph with clean agent/tool separation.
    Agents: manager, synthesis, reviewer (coordinate and make decisions)
    Tools: registered via tool_registry and used by agents as needed
    """
    # Create the graph
    graph = StateGraph(ImmigrationState)

    # Add agent nodes (no tools as nodes)
    # Level 1: Manager (coordinates workflow)
    graph.add_node("manager", manager_node)

    # Level 2: Processing agent (uses tools)
    graph.add_node("synthesis", synthesis_node)

    # Level 3: Reviewer (quality control)
    graph.add_node("reviewer", reviewer_node)

    # Add edges - simplified structure
    # START -> Manager (Level 1)
    graph.add_edge(START, "manager")

    # Manager -> Synthesis (Level 2)
    graph.add_edge("manager", "synthesis")

    # Synthesis -> Reviewer (Level 3)
    graph.add_edge("synthesis", "reviewer")

    # Conditional edges from reviewer
    graph.add_conditional_edges(
        "reviewer",
        route_from_reviewer,
        {
            "synthesis": "synthesis",  # Route back to synthesis for revision
            "end": END,                # Or end if approved
        },
    )

    return graph.compile()

def visualize_graph(graph: StateGraph, save_path: str = OUTPUTS_DIR):
    """
      Visualize the workflow graph as a PNG and save it.

      Args:
          graph (StateGraph): Your LangGraph StateGraph instance.
          save_path (str): Path to save the generated PNG.
    """

    print("📊 Visualizing the content processing graph...")
    print(graph.get_graph().draw_mermaid())

    # Save the graph as PNG
    try:
        png = graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
        with open(os.path.join(save_path, "content_processing_graph.png"), "wb") as f:
            f.write(png)
        print(
            f"✅ Graph saved to {os.path.join(save_path, 'content_processing_graph.png')}"
        )
    except Exception as e:
        print(f"⚠️ Could not save graph image: {e}")


def run_agentic_askimmigrate(text: str) -> Dict[str, Any]:
    """
    Convenience function to run the agentic authoring graph.

    Args:
        text: The text content to process

    Returns:
        Dictionary containing all processing results
    """
    # Create initial state
    initial_state = ImmigrationState(
        text=text,
        visa_type=None,
        visa_fee=0.0,
        references=[],
        manager_decision=None,
        revision_round=0,
        needs_revision=None,
        synthesis_feedback=None,
        rag_retriever_feedback=None,
        references_feedback=None,
        synthesis_approved=None,
        rag_retriever_approved=None,
        references_approved=False
    )

    # Create and run the graph
    graph = create_ask_immigrate_graph()
    visualize_graph(graph)
    final_state = graph.invoke(initial_state)

    return final_state

if __name__ == "__main__":
    print("=" * 80)
    print("ASK US IMMIGRATION AGENT")
    print("=" * 80)

    results = run_agentic_askimmigrate(text="What is F-1 visa")

    print("\n" + "=" * 80)
    print("📋 FINAL PROCESSING RESULTS")
    print("=" * 80)

    if results:
        print(f"\n\n📌 visa_type: {results.get('visa_type', 'N/A')}")
        print(f"\n\n📚 References: {(results.get('references', []))}")
