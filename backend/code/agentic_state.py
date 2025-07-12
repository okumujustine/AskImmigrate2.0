
from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ImmigrationState(TypedDict, total=False):
    """State class for the content processing graph."""

    text: str
    visa_type: Optional[str]
    visa_fee: Optional[float]
    references: Optional[List[str]]
    manager_decision: Optional[str]
    revision_round: Optional[int]
    needs_revision: Optional[bool]
    # Individual feedback for level 2 nodes
    synthesis_feedback: Optional[str]
    rag_retriever_feedback: Optional[str]
    references_feedback: Optional[str]
    # Individual approval status for components
    synthesis_approved: Optional[bool]
    rag_retriever_approved: Optional[bool]
    references_approved: Optional[bool]

class SearchQueries(BaseModel):
    queries: List[str] = Field(
        description="The search queries to find relevant references"
    )

class Reference(BaseModel):
    url: str = Field(description="The URL of the reference")
    title: str = Field(description="The title of the reference")

class References(BaseModel):
    references: List[Reference] = Field(description="List of references.")

class ReviewOutput(BaseModel):
    # Individual component approval and feedback
    rag_retriever_approved: bool = Field(description="Whether the RAG summary is approved")
    rag_retriever_feedback: str = Field(description="Specific feedback for the RAG summary")
    synthesis_approved: bool = Field(description="Whether the synthesis is approved")
    synthesis_feedback: str = Field(description="Specific feedback for the synthesis")
    references_approved: bool = Field(description="Whether the references are approved")
    references_feedback: str = Field(description="Specific feedback for the references")




