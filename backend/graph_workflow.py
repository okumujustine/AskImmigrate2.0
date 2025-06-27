from langgraph.graph import StateGraph
from backend.agentic_state import ImmigrationState
from backend.agent_nodes.intake import intake_node
from langchain_core.runnables.graph  import MermaidDrawMethod
import os
from dotenv import load_dotenv


load_dotenv()
if os.environ.get("LANGSMITH_TRACING") != "true":
    print("WARNING: LangSmith tracing is not enabled. Set LANGSMITH_TRACING=true in your environment.")



def visualize_graph(graph: StateGraph, save_path: str = "outputs/graph.png"):
    """
    Visualize the workflow graph as a PNG and save it.

    Args:
        graph (StateGraph): Your LangGraph StateGraph instance.
        save_path (str): Path to save the generated PNG.
    """
    import os
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    png = graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
    with open(save_path, "wb") as f:
        f.write(png)
    print(f"Workflow diagram saved to {save_path}")

def create_graph():
    graph = StateGraph(ImmigrationState)

    # Add agent nodes (start with intake)
    graph.add_node("intake", intake_node)
    # We shall add more nodes as we develop the workflow.
    # graph.add_node("research", research_node)
    # graph.add_node("tool", tool_node)
    # etc.

    # Set entry point to intake
    graph.set_entry_point("intake")

    # we shall Add the rest of our workflow here 
    # e.g., add edges to connect intake → research → tool → checklist → output

    return graph.compile()

if __name__ == "__main__":
    # Example state (simulate a user question)
    state = {"user_question": "Can I change from B-2 to F-1 if I am from Uganda?"}
    graph = create_graph()
    result = graph.invoke(state)
    print("Result:", result)
    visualize_graph(graph, save_path="outputs/graph.png")
