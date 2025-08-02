from typing import Dict, Any, Literal

from backend.code.prompt_builder import build_prompt_from_config
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)
from backend.code.agentic_state import ImmigrationState, ReviewOutput
from backend.code.llm import get_llm
from backend.code.structured_logging import reviewer_logger, PerformanceTimer


def reviewer_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Reviewer node that evaluates the quality and completeness of all processing results.
    """
    # Track revision rounds
    revision_round = state.get("revision_round", 0) + 1
    max_revisions = 2  # Limit to prevent infinite loops
    session_id = state.get("session_id", "")

    reviewer_logger.info(
        "reviewer_evaluation_started",
        session_id=session_id,
        revision_round=revision_round,
        max_revisions=max_revisions
    )

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
        with PerformanceTimer(reviewer_logger, "llm_review", session_id=session_id):
            response = llm.invoke(prompt)

        # Handle individual component approvals
        overall_approved = (
                response.rag_retriever_approved
                and response.synthesis_approved
                and response.references_approved
        )

        # Force approval if we've reached max revisions to prevent infinite loops
        if revision_round >= max_revisions and not overall_approved:
            reviewer_logger.warning(
                "max_revisions_reached_forcing_approval",
                session_id=session_id,
                revision_round=revision_round,
                max_revisions=max_revisions
            )
            overall_approved = True  # Force approve all remaining components
            response.rag_retriever_approved = True
            response.synthesis_approved = True
            response.references_approved = True

        status = "approved" if overall_approved else "needs_revision"

        reviewer_logger.info(
            "review_completed",
            session_id=session_id,
            status=status,
            revision_round=revision_round,
            rag_approved=response.rag_retriever_approved,
            synthesis_approved=response.synthesis_approved,
            references_approved=response.references_approved
        )

        if not overall_approved:
            needs_revision_list = []
            if not response.rag_retriever_approved:
                needs_revision_list.append("RAG")
            if not response.synthesis_approved:
                needs_revision_list.append("Synthesis")
            if not response.references_approved:
                needs_revision_list.append("References")

            reviewer_logger.info(
                "components_need_revision",
                session_id=session_id,
                revision_round=revision_round,
                components_needing_revision=needs_revision_list
            )

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
            reviewer_logger.info(
                "all_components_approved",
                session_id=session_id,
                revision_round=revision_round
            )

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
        reviewer_logger.error(
            "review_process_failed",
            session_id=session_id,
            revision_round=revision_round,
            error_type=type(e).__name__,
            error_message=str(e)
        )
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
    session_id = state.get("session_id", "")

    if not needs_revision:
        reviewer_logger.info("routing_to_end", session_id=session_id)
        return "end"
    else:
        reviewer_logger.info(
            "routing_to_revision",
            session_id=session_id,
            rag_approved=rag_retriever_approved,
            synthesis_approved=synthesis_approved,
            references_approved=references_approved
        )
        # In the simplified architecture, all revisions go through synthesis
        # which will use appropriate tools (RAG, web search, fee calculator)
        reviewer_logger.info("routing_to_synthesis_for_revision", session_id=session_id)
        return "synthesis"