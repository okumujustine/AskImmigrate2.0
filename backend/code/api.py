import logging
from datetime import datetime
from typing import List, Optional
import time

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.code.session_manager import session_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend/outputs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AskImmigrate API", version="2.0.0")

# Log application startup
logger.info("Starting AskImmigrate API v2.0.0 with anonymous user isolation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware configured for all origins")


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing information"""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    # Log request start
    logger.info(f"REQUEST START: {request.method} {request.url.path} - Client: {client_ip}")
    
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log successful response
        logger.info(f"REQUEST COMPLETE: {request.method} {request.url.path} - "
                   f"Status: {response.status_code} - Duration: {process_time:.3f}s")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"REQUEST ERROR: {request.method} {request.url.path} - "
                    f"Duration: {process_time:.3f}s - Error: {str(e)}")
        raise


@app.on_event("startup")
async def startup_event():
    """Log application startup"""
    logger.info("=== AskImmigrate API Starting Up ===")
    logger.info("Features enabled:")
    logger.info("- Anonymous user isolation via browser fingerprinting")
    logger.info("- Client-scoped session management")
    logger.info("- Comprehensive API logging")
    logger.info("- Multi-user Docker deployment ready")
    logger.info("=====================================")


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown"""
    logger.info("=== AskImmigrate API Shutting Down ===")
    logger.info("Application stopped gracefully")
    logger.info("=======================================")


class SessionQA(BaseModel):
    session_id: str
    questions: List[str]
    answers: List[str]


@app.get("/session-qa", response_model=List[SessionQA])
def get_session_qa(client_fingerprint: Optional[str] = Query(None)):
    """
    Returns a list of sessions with Q&A, filtered by client fingerprint for isolation.
    """
    logger.info(f"GET /session-qa - Client fingerprint: {'provided' if client_fingerprint else 'not provided'}")
    
    try:
        from backend.code.utils import extract_client_from_session_id, create_client_fingerprint_hash
        
        sessions = session_manager.list_all_sessions()
        logger.info(f"Retrieved {len(sessions)} total sessions from session manager")
        
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
            logger.info(f"Filtered to {len(sessions)} sessions for client fingerprint")
        
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
        
        logger.info(f"Successfully returned {len(grouped)} session Q&A records")
        return grouped
        
    except Exception as e:
        logger.error(f"Error retrieving session Q&A: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve session data")


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    client_fingerprint: Optional[str] = None  # New field for client isolation


@app.post("/query")
def query_agentic_system(request: QueryRequest):
    """
    Process a question through the agentic system with comprehensive logging.
    """
    logger.info(f"POST /query - Question length: {len(request.question)} chars, "
                f"Session ID: {'provided' if request.session_id else 'will generate'}, "
                f"Client fingerprint: {'provided' if request.client_fingerprint else 'not provided'}")
    
    try:
        # Use new client-aware session generation
        from backend.code.graph_workflow import run_agentic_askimmigrate
        from backend.code.utils import create_anonymous_session_id

        # Create client-isolated session ID if not provided
        original_session_id = request.session_id
        session_id = request.session_id or create_anonymous_session_id(
            request.client_fingerprint, request.question
        )
        
        if not original_session_id:
            logger.info(f"Generated new session ID: {session_id}")
        
        # Log the question (truncated for privacy)
        question_preview = request.question[:100] + "..." if len(request.question) > 100 else request.question
        logger.info(f"Processing question: '{question_preview}' for session {session_id}")
        
        # Run the agentic workflow
        run_agentic_askimmigrate(text=request.question, session_id=session_id)
        
        # Get the response
        answer = session_manager.get_last_answer_by_session(session_id)
        
        logger.info(f"Successfully processed question for session {session_id}, "
                   f"answer length: {len(answer) if answer else 0} chars")
        
        return {
            "answer": answer,
            "session_id": session_id,
        }
        
    except Exception as e:
        logger.error(f"Error processing query for session {session_id if 'session_id' in locals() else 'unknown'}: {str(e)}", 
                    exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process question")


@app.get("/session-ids", response_model=List[str])
def get_session_ids(client_fingerprint: Optional[str] = Query(None)):
    """
    Returns a list of session IDs filtered by client fingerprint for isolation.
    """
    logger.info(f"GET /session-ids - Client fingerprint: {'provided' if client_fingerprint else 'not provided'}")
    
    try:
        from backend.code.utils import extract_client_from_session_id, create_client_fingerprint_hash
        
        sessions = session_manager.list_all_sessions()
        session_ids = [session["session_id"] for session in sessions]
        logger.info(f"Retrieved {len(session_ids)} total session IDs")
        
        # If no client fingerprint provided, return all sessions (legacy support)
        if not client_fingerprint:
            logger.info("No client fingerprint provided, returning all sessions (legacy mode)")
            return session_ids
        
        # Filter sessions by client fingerprint
        client_hash = create_client_fingerprint_hash(client_fingerprint)
        filtered_sessions = []
        
        for session_id in session_ids:
            session_client_hash = extract_client_from_session_id(session_id)
            # Include sessions that match this client or legacy sessions (None)
            if session_client_hash == client_hash or session_client_hash is None:
                filtered_sessions.append(session_id)
        
        logger.info(f"Filtered to {len(filtered_sessions)} sessions for client")
        return filtered_sessions
        
    except Exception as e:
        logger.error(f"Error retrieving session IDs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve session IDs")


@app.get("/answers/{session_id}")
def get_answer_by_session_id(session_id: str):
    """
    Returns the last answer for a given session ID.
    """
    logger.info(f"GET /answers/{session_id}")
    
    try:
        answers = session_manager.get_answers_by_session(session_id)
        logger.info(f"Retrieved answers for session {session_id}: {len(answers) if answers else 0} answers")
        return answers
        
    except Exception as e:
        logger.error(f"Error retrieving answers for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve answers for session {session_id}")


@app.get("/health")
def health_check():
    """
    Health check endpoint with client isolation status and comprehensive logging.
    """
    logger.info("GET /health - Health check requested")
    
    try:
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
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "anonymous_isolation": "enabled",
            "session_stats": {
                "total_sessions": total_sessions,
                "client_isolated_sessions": client_sessions,
                "legacy_sessions": legacy_sessions
            }
        }
        
        logger.info(f"Health check successful - Total sessions: {total_sessions}, "
                   f"Client isolated: {client_sessions}, Legacy: {legacy_sessions}")
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
