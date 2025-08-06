import logging
from datetime import datetime
from typing import List, Optional
import time
from typing import Dict, Any, Optional
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
    SECURITY: Only returns sessions belonging to the requesting client.
    """
    logger.info(f"GET /session-qa - Client fingerprint: {'provided' if client_fingerprint else 'not provided'}")
    
    try:
        from backend.code.utils import extract_client_from_session_id, create_client_fingerprint_hash
        
        sessions = session_manager.list_all_sessions()
        logger.info(f"Retrieved {len(sessions)} total sessions from session manager")
        
        # SECURITY FIX: Don't return sessions if no fingerprint provided
        if not client_fingerprint:
            logger.warning("No client fingerprint provided - returning empty list for security")
            return []
        
        # Filter sessions by client fingerprint
        client_hash = create_client_fingerprint_hash(client_fingerprint)
        filtered_sessions = []
        
        for session in sessions:
            session_id = session["session_id"]
            session_client_hash = extract_client_from_session_id(session_id)
            # Only include sessions that match this specific client
            if session_client_hash == client_hash:
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
    SECURITY: Only returns sessions belonging to the requesting client.
    """
    logger.info(f"GET /session-ids - Client fingerprint: {'provided' if client_fingerprint else 'not provided'}")
    
    try:
        from backend.code.utils import extract_client_from_session_id, create_client_fingerprint_hash
        
        sessions = session_manager.list_all_sessions()
        session_ids = [session["session_id"] for session in sessions]
        logger.info(f"Retrieved {len(session_ids)} total session IDs")
        
        # SECURITY FIX: Don't return sessions if no fingerprint provided
        if not client_fingerprint:
            logger.warning("No client fingerprint provided - returning empty list for security")
            return []
        
        # Filter sessions by client fingerprint
        client_hash = create_client_fingerprint_hash(client_fingerprint)
        filtered_sessions = []
        
        for session_id in session_ids:
            session_client_hash = extract_client_from_session_id(session_id)
            # Only include sessions that match this specific client
            if session_client_hash == client_hash:
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


# MULTILINGUAL SUPPORT - Essential endpoints only
def get_translation_service():
    """Helper function to get translation service with proper error handling"""
    try:
        from backend.code.multilingual.translation_service import translation_service
        return translation_service, True
    except ImportError:
        logger.warning("Translation service not available")
        return None, False
    except Exception as e:
        logger.error(f"Error importing translation service: {e}")
        return None, False


class MultilingualQueryRequest(BaseModel):
    question: str
    language: str = "auto"  # "auto", "en", "es", "fr", "pt"
    session_id: Optional[str] = None
    client_fingerprint: Optional[str] = None


class MultilingualResponse(BaseModel):
    answer: str
    session_id: str
    language: str
    metadata: Dict[str, Any]


supported_languages = ["en", "es", "fr", "pt"]


@app.post("/api/chat/multilingual", response_model=MultilingualResponse)
async def multilingual_chat(request: MultilingualQueryRequest):
    """Chat endpoint with multilingual support"""
    logger.info(f"Multilingual chat request: language={request.language}, question_length={len(request.question)}")
    
    try:
        translation_service, is_available = get_translation_service()
        
        if not is_available:
            logger.warning("Translation service not available, falling back to English")
            from backend.code.graph_workflow import run_agentic_askimmigrate
            from backend.code.utils import create_anonymous_session_id
            
            session_id = request.session_id or create_anonymous_session_id(
                request.client_fingerprint, request.question
            )
            
            result = run_agentic_askimmigrate(text=request.question, session_id=session_id)
            
            return MultilingualResponse(
                answer=result.get("synthesis", "I apologize, but I'm currently only available in English."),
                session_id=session_id,
                language="en",
                metadata={
                    "translation_method": "service_unavailable",
                    "fallback_used": True
                }
            )
        
        # Detect language if set to auto
        detected_language = request.language
        detection_metadata = {}
        
        if request.language == "auto":
            try:
                detection_result = await translation_service.detect_language(request.question)
                detected_language = detection_result.language
                detection_metadata = {
                    "confidence": detection_result.confidence,
                    "method": detection_result.detection_method
                }
                logger.info(f"Language auto-detected: {detected_language}")
            except Exception as e:
                logger.warning(f"Language detection failed: {e}, defaulting to English")
                detected_language = "en"
                detection_metadata = {"error": str(e), "fallback": "en"}
        
        # Validate language support
        if detected_language not in supported_languages:
            logger.warning(f"Unsupported language: {detected_language}, defaulting to English")
            detected_language = "en"
            detection_metadata["unsupported_fallback"] = True
        
        # Create session ID if not provided
        from backend.code.utils import create_anonymous_session_id
        session_id = request.session_id or create_anonymous_session_id(
            request.client_fingerprint, request.question
        )
        
        # Process the question through the main workflow
        from backend.code.graph_workflow import run_agentic_askimmigrate
        result = run_agentic_askimmigrate(text=request.question, session_id=session_id)
        
        # Get the final answer
        answer = result.get("synthesis", "")
        
        if not answer:
            raise Exception("No response generated from workflow")
        
        # Handle multilingual response processing
        final_answer = answer
        translation_metadata = {"method": "english_native"}
        
        # Only translate if we have a non-English target and the answer is in English
        if detected_language != "en" and answer:
            try:
                logger.info(f"Processing multilingual response for language: {detected_language}")
                
                if detected_language == "es":
                    # Try native Spanish response first
                    try:
                        native_result = await translation_service.get_native_response(
                            request.question, "es"
                        )
                        final_answer = native_result.translated_text
                        translation_metadata = {
                            "method": native_result.translation_method,
                            "confidence": native_result.confidence,
                            "native_response": True
                        }
                        logger.info("Native Spanish response generated successfully")
                        
                    except Exception as native_error:
                        logger.warning(f"Native Spanish generation failed: {native_error}, falling back to translation")
                        
                        # Fallback to translating the English response
                        translation_result = await translation_service.translate_text(
                            text=answer,
                            target_lang="es",
                            source_lang="en",
                            use_immigration_context=True
                        )
                        final_answer = translation_result.translated_text
                        translation_metadata = {
                            "method": translation_result.translation_method,
                            "confidence": translation_result.confidence,
                            "translated_from": "en",
                            "fallback_from_native": True
                        }
                
                else:
                    # For other languages, translate the English response
                    logger.info(f"Translating English response to {detected_language}")
                    translation_result = await translation_service.translate_text(
                        text=answer,
                        target_lang=detected_language,
                        source_lang="en",
                        use_immigration_context=True
                    )
                    final_answer = translation_result.translated_text
                    translation_metadata = {
                        "method": translation_result.translation_method,
                        "confidence": translation_result.confidence,
                        "translated_from": "en"
                    }
                
            except Exception as translation_error:
                logger.error(f"Multilingual processing failed: {translation_error}, using English response")
                final_answer = answer
                translation_metadata = {
                    "method": "english_fallback_due_to_error",
                    "error": str(translation_error),
                    "target_language": detected_language,
                    "fallback_used": True
                }
        
        # Combine all metadata
        response_metadata = {
            **translation_metadata,
            **detection_metadata,
            "target_language": detected_language,
            "original_language_request": request.language,
            "session_id": session_id,
            "multilingual_processing": detected_language != "en"
        }
        
        logger.info(f"Multilingual chat completed successfully: {detected_language}")
        
        return MultilingualResponse(
            answer=final_answer,
            session_id=session_id,
            language=detected_language,
            metadata=response_metadata
        )
        
    except Exception as e:
        logger.error(f"Multilingual chat error: {e}", exc_info=True)
        
        return MultilingualResponse(
            answer=f"I apologize, but I encountered an error processing your request: {str(e)}",
            session_id=request.session_id or "error-session",
            language="en",
            metadata={
                "error": True,
                "error_message": str(e),
                "requested_language": getattr(request, 'language', 'unknown'),
                "fallback_language": "en"
            }
        )


class LanguageDetectionRequest(BaseModel):
    text: str


@app.post("/api/detect-language")
async def detect_language(request: LanguageDetectionRequest):
    """Language detection endpoint"""
    logger.info(f"Language detection request: text_length={len(request.text)}")
    
    try:
        translation_service, is_available = get_translation_service()
        
        if is_available:
            try:
                result = await translation_service.detect_language(request.text)
                return {
                    "language": result.language,
                    "confidence": result.confidence,
                    "supported": result.language in supported_languages,
                    "detection_method": result.detection_method,
                    "service_available": True
                }
            except Exception as service_error:
                logger.warning(f"Translation service detection failed: {service_error}, using fallback")
        
        # Fallback pattern detection
        logger.info("Using pattern-based language detection fallback")
        
        text_lower = request.text.lower()
        
        # Spanish detection
        spanish_patterns = ['ñ', '¿', '¡', 'inmigración', 'visa', 'español', 'cómo', 'qué', 'necesito', 'quiero']
        spanish_score = sum(1 for pattern in spanish_patterns if pattern in text_lower)
        
        if spanish_score > 0:
            detected_lang = "es"
            confidence = min(0.3 + (spanish_score * 0.1), 0.8)
        elif any(pattern in text_lower for pattern in ['ç', 'où', 'français', 'immigration']):
            detected_lang = "fr"
            confidence = 0.6
        elif any(pattern in text_lower for pattern in ['ção', 'português', 'imigração']):
            detected_lang = "pt"
            confidence = 0.6
        else:
            detected_lang = "en"
            confidence = 0.7
            
        return {
            "language": detected_lang,
            "confidence": confidence,
            "supported": detected_lang in supported_languages,
            "detection_method": "pattern_fallback",
            "service_available": False
        }
        
    except Exception as e:
        logger.error(f"Language detection failed completely: {e}")
        return {
            "language": "en",
            "confidence": 0.1,
            "supported": True,
            "detection_method": "error_fallback",
            "service_available": False,
            "error": str(e)
        }


@app.get("/api/languages/supported")
async def get_supported_languages():
    """Get supported languages endpoint"""
    logger.info("Supported languages request")
    
    try:
        translation_service, is_available = get_translation_service()
        
        capabilities = [
            {
                "code": "en",
                "name": "English", 
                "native_name": "English",
                "native_llm": True,
                "translation_available": is_available,
                "quality": "native"
            },
            {
                "code": "es",
                "name": "Spanish",
                "native_name": "Español", 
                "native_llm": is_available,
                "translation_available": is_available,
                "quality": "native" if is_available else "unavailable"
            },
            {
                "code": "fr",
                "name": "French",
                "native_name": "Français",
                "native_llm": False,
                "translation_available": is_available,
                "quality": "translated" if is_available else "unavailable"
            },
            {
                "code": "pt", 
                "name": "Portuguese",
                "native_name": "Português",
                "native_llm": False,
                "translation_available": is_available,
                "quality": "translated" if is_available else "unavailable"
            }
        ]
        
        return {
            "supported_languages": capabilities,
            "multilingual_enabled": is_available,
            "service_status": "available" if is_available else "unavailable"
        }
            
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        
        return {
            "supported_languages": [
                {
                    "code": "en",
                    "name": "English", 
                    "native_name": "English",
                    "native_llm": True,
                    "translation_available": False,
                    "quality": "native"
                }
            ],
            "multilingual_enabled": False,
            "service_status": "error",
            "error": str(e)
        }