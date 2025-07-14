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
def get_session_qa():
    """
    Returns a list of sessions, each with all questions and answers grouped by session_id.
    """
    sessions = session_manager.list_all_sessions()
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


@app.post("/query")
def query_agentic_system(request: QueryRequest):
    # Replace this with your actual agentic system logic
    # For now, just echo the question and session_id
    # You can call your agentic system here and return the result
    from backend.code.graph_workflow import run_agentic_askimmigrate
    from backend.code.utils import slugify_chat_session

    session_id = request.session_id or slugify_chat_session(request.question)
    run_agentic_askimmigrate(text=request.question, session_id=session_id)
    return {
        "answer": session_manager.get_last_answer_by_session(session_id),
        "session_id": session_id,
    }


@app.get("/session-ids", response_model=List[str])
def get_session_ids():
    """
    Returns a list of all unique session IDs.
    """
    sessions = session_manager.list_all_sessions()
    return [session["session_id"] for session in sessions]


@app.get("/answers/{session_id}")
def get_answer_by_session_id(session_id: str):
    """
    Returns the last answer for a given session ID.
    """
    return session_manager.get_answers_by_session(session_id)
