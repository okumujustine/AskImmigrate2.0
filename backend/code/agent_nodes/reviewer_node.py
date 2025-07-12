from typing import Dict, Any, Literal

from backend.code.prompt_builder import build_prompt_from_config
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)
from backend.code.agentic_state import ImmigrationState, ReviewOutput
from backend.code.llm import get_llm


def reviewer_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Reviewer node that evaluates the quality and completeness of all processing results.
    """
    # Track revision rounds
    revision_round = state.get("revision_round", 0) + 1
    max_revisions = 2  # Limit to prevent infinite loops

    print(f"🔍 Reviewer: Evaluating processing results (Round {revision_round})")

    llm = get_llm(config.get("llm", "gpt-4o-mini")).with_structured_output(ReviewOutput)

    # Build comprehensive input data for review
    review_input = f"""
    Original Content Length: {len(state["text"])} characters
    Manager's Decision: {state.get("manager_decision", "N/A")}
    Revision Round: {revision_round} (Max: {max_revisions})

    Processing Results:
    - VisaType(s): {state.get("visa_type", "Not answered")}
    - visa_fee(s): {state.get("visa_fee", "Not answered")}
    - References: {state.get("references", [])}
    """

    prompt = build_prompt_from_config(
        config=prompt_config["reviewer_agent_prompt"], input_data=review_input
    )

    try:
        response = llm.invoke(prompt)

        # Handle individual component approvals
        overall_approved = (
                response.rag_retriever_approved
                and response.synthesis_approved
                and response.references_approved
        )

        # Force approval if we've reached max revisions to prevent infinite loops
        if revision_round >= max_revisions and not overall_approved:
            overall_approved = True  # Force approve all remaining components
            response.rag_retriever_approved = True
            response.synthesis_approved = True
            response.references_approved = True

        status = "approved" if overall_approved else "needs_revision"

        print()

        print(f"✅ Review completed: {status}")
        print(f"📋 Feedback: {response.model_dump()}")

        # Show individual component status
        components_status = [
            f"RAG: {'✅' if response.rag_retriever_approved else '❌'}",
            f"Synthesis: {'✅' if response.synthesis_approved else '❌'}",
            f"References: {'✅' if response.references_approved else '❌'}",
        ]
        print(f"📊 Component Status: {' | '.join(components_status)}")

        if not overall_approved:
            needs_revision_list = []
            if not response.rag_retriever_approved:
                needs_revision_list.append("RAG")
            if not response.synthesis_approved:
                needs_revision_list.append("Synthesis")
            if not response.references_approved:
                needs_revision_list.append("References")

            print(f"🔄 Components needing revision: {', '.join(needs_revision_list)}")

            return {
                "needs_revision": True,
                "revision_round": revision_round,
                "rag_retriever_feedback": response.rag_retriever_feedback,
                "synthesis_feedback": response.synthesis_feedback,
                "references_feedback": response.references_feedback,
                "rag_retriever_approved": response.rag_retriever_approved,
                "synthesis_approved": response.synthesis_approved,
                "references_approved": response.references_approved,
            }
        else:
            print("✅ All components approved - proceeding to final output")

            return {
                "needs_revision": False,
                "revision_round": revision_round,
                "rag_retriever_feedback": response.rag_retriever_feedback,
                "synthesis_feedback": response.synthesis_feedback,
                "references_feedback": response.references_feedback,
                "rag_retriever_approved": response.rag_retriever_approved,
                "synthesis_approved": response.synthesis_approved,
                "references_approved": response.references_approved,
            }
    except Exception as e:
        print(f"❌ Review failed: {e}")
        return {
            "review_feedback": "Review process failed.",
            "final_output": {},
            "needs_revision": False,
            "revision_round": revision_round,
        }

def route_from_reviewer(
        state: ImmigrationState,
) -> Literal["synthesis", "end"]:
    """
    Conditional routing function that determines whether to dispatch revisions or end.
    """
    needs_revision = state.get("needs_revision", False)
    rag_retriever_approved = state.get("rag_retriever_approved", False)
    synthesis_approved = state.get("synthesis_approved", False)
    references_approved = state.get("references_approved", False)

    if not needs_revision:
        print("✅ All components approved - routing to END")
        return "end"
    else:
        print("🔄 Some components need revision")
        # In the simplified architecture, all revisions go through synthesis
        # which will use appropriate tools (RAG, web search, fee calculator)
        print("🔄 Routing to synthesis for revision (will use appropriate tools)")
        return "synthesis"