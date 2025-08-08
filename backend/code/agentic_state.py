from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class ConversationTurn(BaseModel):
    """Single conversation turn (question + answer)"""
    question: str
    answer: str
    timestamp: str
    question_type: Optional[str] = None
    visa_focus: Optional[List[str]] = None
    tools_used: Optional[List[str]] = None
    
    class Config:
        arbitrary_types_allowed = True

class SessionContext(BaseModel):
    """Summarized context from conversation history"""
    ongoing_topics: List[str] = Field(default_factory=list, description="Topics discussed in session")
    visa_types_mentioned: List[str] = Field(default_factory=list, description="Visa types mentioned")
    user_situation: Optional[str] = Field(default=None, description="User's immigration situation")
    previous_questions_summary: Optional[str] = Field(default=None, description="Summary of previous questions")
    
    class Config:
        arbitrary_types_allowed = True

class ImmigrationState(TypedDict, total=False):
    """Enhanced state class for immigration processing workflow with session and language support."""

    # Core input
    text: str  # User's immigration question
    user_question: Optional[str]  # Processed question
    
    # SESSION SUPPORT
    session_id: Optional[str]  # Session identifier for conversation tracking
    conversation_history: Optional[List[ConversationTurn]]  # Previous Q&A pairs
    session_context: Optional[SessionContext]  # Summarized context from previous conversations
    is_followup_question: Optional[bool]  # Whether this refers to previous context
    conversation_turn_number: Optional[int]  # Which turn in the conversation this is
    
    # LANGUAGE SUPPORT - NEW FIELDS
    detected_language: Optional[str]  # "en", "es", "fr", "pt" - detected language code
    language_name: Optional[str]  # "English", "Spanish", "French", "Portuguese"
    language_confidence: Optional[float]  # Detection confidence score (0.0-1.0)
    response_language: Optional[str]  # Language to respond in
    language_supported: Optional[bool]  # Whether detected language is supported
    detection_method: Optional[str]  # "langdetect", "pattern", "fallback"
    language_info: Optional[Dict[str, Any]] 
    # Manager's strategic analysis
    manager_decision: Optional[str]  # Manager's full strategic analysis
    structured_analysis: Optional[Dict[str, Any]]  # Parsed strategic parameters
    workflow_parameters: Optional[Dict[str, Any]]  # Processing parameters for downstream agents
    
    # Agent outputs
    synthesis: Optional[str]  # Final user-facing response
    rag_response: Optional[str]  # RAG retrieval results
    
    # Tool coordination
    tool_results: Optional[Dict[str, Any]]  # All tool execution results
    tools_used: Optional[List[str]]  # List of tools actually used
    
    # Workflow metadata
    question_type: Optional[str]  # Type of immigration question
    complexity: Optional[str]  # Question complexity level
    primary_focus: Optional[str]  # Main topic focus
    visa_type: Optional[str]  # Identified visa types
    country: Optional[str]  # Country context if relevant
    
    # Quality control and review
    revision_round: Optional[int]
    needs_revision: Optional[bool]
    
    # Component approvals
    synthesis_approved: Optional[bool]
    rag_retriever_approved: Optional[bool]
    references_approved: Optional[bool]
    
    # Component feedback
    synthesis_feedback: Optional[str]
    rag_retriever_feedback: Optional[str]
    references_feedback: Optional[str]
    
    # Immigration-specific data
    visa_fee: Optional[float]
    references: Optional[List[str]]
    
    # System metadata
    analysis_timestamp: Optional[str]
    strategy_applied: Optional[Dict[str, Any]]  # Which strategy was used
    synthesis_metadata: Optional[Dict[str, Any]]  # Synthesis execution details

# Keep existing Pydantic models
class SearchQueries(BaseModel):
    queries: List[str] = Field(description="The search queries to find relevant references")

class Reference(BaseModel):
    url: str = Field(description="The URL of the reference")
    title: str = Field(description="The title of the reference")

class References(BaseModel):
    references: List[Reference] = Field(description="List of references.")

class ReviewOutput(BaseModel):
    rag_retriever_approved: bool = Field(description="Whether the RAG summary is approved")
    rag_retriever_feedback: str = Field(description="Specific feedback for the RAG summary")
    synthesis_approved: bool = Field(description="Whether the synthesis is approved")
    synthesis_feedback: str = Field(description="Specific feedback for the synthesis")
    references_approved: bool = Field(description="Whether the references are approved")
    references_feedback: str = Field(description="Specific feedback for the references")