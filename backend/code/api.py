from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.code.session_manager import session_manager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SessionQA(BaseModel):
    session_id: str
    questions: List[str]
    answers: List[str]


@app.get("/session-qa", response_model=List[SessionQA])
def get_session_qa(client_fingerprint: Optional[str] = Query(None)):
    """
    Returns a list of sessions with Q&A, filtered by client fingerprint for isolation.
    """
    from backend.code.utils import extract_client_from_session_id, create_client_fingerprint_hash
    
    sessions = session_manager.list_all_sessions()
    
    # Filter sessions by client if fingerprint provided
    if client_fingerprint:
        client_hash = create_client_fingerprint_hash(client_fingerprint)
        filtered_sessions = []
        
        for session in sessions:
            session_id = session["session_id"]
            session_client_hash = extract_client_from_session_id(session_id)
            # Include sessions that match this client or legacy sessions (None)
            if session_client_hash == client_hash or session_client_hash is None:
                filtered_sessions.append(session)
        
        sessions = filtered_sessions
    
    # Build response with Q&A data
    grouped = []
    for session in sessions:
        session_id = session["session_id"]
        turns = session_manager.load_conversation_history(session_id, limit=1000)
        questions = [turn.question for turn in turns]
        answers = [turn.answer for turn in turns]
        grouped.append(
            SessionQA(session_id=session_id, questions=questions, answers=answers)
        )
    return grouped


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    client_fingerprint: Optional[str] = None  # New field for client isolation


@app.post("/query")
def query_agentic_system(request: QueryRequest):
    # Use new client-aware session generation
    from backend.code.graph_workflow import run_agentic_askimmigrate
    from backend.code.utils import create_anonymous_session_id

    # Create client-isolated session ID if not provided
    session_id = request.session_id or create_anonymous_session_id(
        request.client_fingerprint, request.question
    )
    
    run_agentic_askimmigrate(text=request.question, session_id=session_id)
    return {
        "answer": session_manager.get_last_answer_by_session(session_id),
        "session_id": session_id,
    }


@app.get("/session-ids", response_model=List[str])
def get_session_ids(client_fingerprint: Optional[str] = Query(None)):
    """
    Returns a list of session IDs filtered by client fingerprint for isolation.
    """
    from backend.code.utils import extract_client_from_session_id, create_client_fingerprint_hash
    
    sessions = session_manager.list_all_sessions()
    session_ids = [session["session_id"] for session in sessions]
    
    # If no client fingerprint provided, return all sessions (legacy support)
    if not client_fingerprint:
        return session_ids
    
    # Filter sessions by client fingerprint
    client_hash = create_client_fingerprint_hash(client_fingerprint)
    filtered_sessions = []
    
    for session_id in session_ids:
        session_client_hash = extract_client_from_session_id(session_id)
        # Include sessions that match this client or legacy sessions (None)
        if session_client_hash == client_hash or session_client_hash is None:
            filtered_sessions.append(session_id)
    
    return filtered_sessions


@app.get("/answers/{session_id}")
def get_answer_by_session_id(session_id: str):
    """
    Returns the last answer for a given session ID.
    """
    return session_manager.get_answers_by_session(session_id)


@app.get("/health")
def health_check():
    """
    Health check endpoint with client isolation status.
    """
    from backend.code.utils import extract_client_from_session_id
    
    sessions = session_manager.list_all_sessions()
    total_sessions = len(sessions)
    
    # Count client-isolated vs legacy sessions
    client_sessions = 0
    legacy_sessions = 0
    
    for session in sessions:
        session_id = session["session_id"]
        if extract_client_from_session_id(session_id):
            client_sessions += 1
        else:
            legacy_sessions += 1
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "anonymous_isolation": "enabled",
        "session_stats": {
            "total_sessions": total_sessions,
            "client_isolated_sessions": client_sessions,
            "legacy_sessions": legacy_sessions
        }
    }
