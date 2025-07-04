
from typing import TypedDict, List, Dict, Any, Optional

class ImmigrationState(TypedDict, total=False):
    # ---- User Input & Core Context ----
    user_question: str
    """The current user’s main question or request, as typed in the chat or CLI."""

   # visa_type: Optional[str]
    """Short code for the user’s current or target visa/status (e.g., 'F-1', 'J-1', 'B-2', 'H-1B')."""

   # country: Optional[str]
    """User’s country of origin or nationality (used for eligibility/rules)."""

    # ---- RAG & Retrieval ----
    retrieved_chunks: List[str]
    """Relevant text snippets or passages pulled from ChromaDB, PDFs, or web search to help answer the question."""

    # ---- Form & Checklist Suggestions ----
    #forms: List[str]
    """List of official immigration forms (e.g., 'I-20', 'I-485') recommended for the user’s scenario."""

    #checklist: List[str]
    """Step-by-step tasks or document list generated for the user (e.g., 'Collect bank statements', 'Submit DS-160')."""

    # ---- Conversation & Output ----
    #answer: Optional[str]
    """The final summarized answer or advice to return to the user."""

    messages: List[Dict[str, Any]]
    """History of all messages exchanged in the session (user, bot, agents)."""

    #completed: Optional[bool]
    """Flag: True if the user has finished or exited this session, False/None otherwise."""

    # ---- (For Future Expansion) ----
    # timeline: List[str]
    # """Optional: Key immigration dates/events. Placeholder for future timeline features."""
