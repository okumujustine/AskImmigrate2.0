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
    
class MultilingualQueryRequest(BaseModel):
    question: str
    language: str = "auto"  # "auto", "en", "es", "fr", "pt"
    session_id: Optional[str] = None
    client_fingerprint: Optional[str] = None

class LanguageDetectionRequest(BaseModel):
    text: str

class MultilingualResponse(BaseModel):
    answer: str
    session_id: str
    language: str
    metadata: Dict[str, Any]

def get_language_capabilities():
    """Get supported languages with their capabilities"""
    return [
        {
            "code": "en",
            "name": "English", 
            "native_name": "English",
            "native_llm": True,
            "translation_available": True
        },
        {
            "code": "es",
            "name": "Spanish",
            "native_name": "Español", 
            "native_llm": True,
            "translation_available": True
        },
        {
            "code": "fr",
            "name": "French",
            "native_name": "Français",
            "native_llm": False,
            "translation_available": True
        },
        {
            "code": "pt", 
            "name": "Portuguese",
            "native_name": "Português",
            "native_llm": False,
            "translation_available": True
        }
    ]

supported_languages = ["en", "es", "fr", "pt"]

@app.post("/api/chat/multilingual", response_model=MultilingualResponse)
async def multilingual_chat(request: MultilingualQueryRequest):
    """Enhanced chat endpoint with comprehensive multilingual support and error handling"""
    logger.info(f"Multilingual chat request: language={request.language}, question_length={len(request.question)}")
    
    try:
        # Import translation service with error handling
        translation_service, is_available = get_translation_service()
        
        if not is_available:
            logger.warning("Translation service not available, falling back to English")
            # Fall back to regular English processing
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
                    "translation_method": "multilingual_service_unavailable",
                    "fallback_used": True,
                    "error": "Translation service not available"
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
                logger.info(f"Language auto-detected: {detected_language} (confidence: {detection_result.confidence})")
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
        
        # Process the question through the main workflow with language context
        from backend.code.graph_workflow import run_agentic_askimmigrate
        
        # Add language information to the state for proper processing
        result = run_agentic_askimmigrate(
            text=request.question, 
            session_id=session_id
        )
        
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
                    # Try native Spanish response first (best quality)
                    try:
                        logger.info("Attempting native Spanish response generation")
                        native_result = await translation_service.get_native_response(
                            request.question, "es"
                        )
                        final_answer = native_result.translated_text
                        translation_metadata = {
                            "method": native_result.translation_method,
                            "confidence": native_result.confidence,
                            "processing_time": native_result.processing_time,
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
                            "processing_time": translation_result.processing_time,
                            "translated_from": "en",
                            "fallback_from_native": True
                        }
                        logger.info("Fallback translation to Spanish completed")
                
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
                        "processing_time": translation_result.processing_time,
                        "translated_from": "en"
                    }
                    logger.info(f"Translation to {detected_language} completed")
                
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
            "multilingual_processing": detected_language != "en",
            "service_health": translation_service.get_stats().get("service_health", "unknown") if translation_service else "unavailable"
        }
        
        logger.info(f"Multilingual chat completed successfully: {detected_language}, method: {translation_metadata.get('method')}")
        
        return MultilingualResponse(
            answer=final_answer,
            session_id=session_id,
            language=detected_language,
            metadata=response_metadata
        )
        
    except Exception as e:
        logger.error(f"Multilingual chat error: {e}", exc_info=True)
        
        # Create error response in requested language if possible
        error_message = str(e)
        if hasattr(request, 'language') and request.language == "es":
            error_message = f"Error procesando su consulta: {error_message}"
        
        return MultilingualResponse(
            answer=f"I apologize, but I encountered an error processing your multilingual request: {error_message}",
            session_id=request.session_id or "error-session",
            language="en",
            metadata={
                "error": True,
                "error_message": str(e),
                "requested_language": getattr(request, 'language', 'unknown'),
                "fallback_language": "en"
            }
        )

@app.post("/api/detect-language")
async def detect_language(request: LanguageDetectionRequest):
    """Enhanced language detection endpoint with comprehensive error handling"""
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
        
        # Fallback pattern detection with enhanced patterns
        logger.info("Using pattern-based language detection fallback")
        
        text_lower = request.text.lower()
        confidence = 0.5  # Lower confidence for pattern detection
        
        # Enhanced Spanish detection
        spanish_patterns = [
            # Characters
            'ñ', '¿', '¡',
            # Common words
            'inmigración', 'visa', 'español', 'cómo', 'qué', 'cuándo', 'dónde',
            'necesito', 'quiero', 'puedo', 'solicitar', 'formulario',
            # Immigration specific
            'uscis', 'tarjeta verde', 'ciudadanía', 'residencia'
        ]
        
        spanish_score = sum(1 for pattern in spanish_patterns if pattern in text_lower)
        if spanish_score > 0:
            detected_lang = "es"
            confidence = min(0.3 + (spanish_score * 0.1), 0.8)
        
        # Enhanced French detection
        elif any(pattern in text_lower for pattern in ['ç', 'où', 'français', 'immigration', 'visa français']):
            detected_lang = "fr"
            confidence = 0.6
        
        # Enhanced Portuguese detection
        elif any(pattern in text_lower for pattern in ['ção', 'português', 'imigração']):
            detected_lang = "pt"
            confidence = 0.6
        
        # Default to English
        else:
            detected_lang = "en"
            confidence = 0.7
            
        return {
            "language": detected_lang,
            "confidence": confidence,
            "supported": detected_lang in supported_languages,
            "detection_method": "enhanced_pattern_fallback",
            "service_available": False,
            "patterns_matched": spanish_score if detected_lang == "es" else 0
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
    """Enhanced supported languages endpoint with real-time service status"""
    logger.info("Supported languages request")
    
    try:
        translation_service, is_available = get_translation_service()
        
        # Enhanced capabilities with real-time status
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
                "quality": "native" if is_available else "unavailable",
                "features": ["native_generation", "contextual_translation"] if is_available else []
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
        
        response_data = {
            "supported_languages": capabilities,
            "multilingual_enabled": is_available,
            "service_status": "available" if is_available else "unavailable"
        }
        
        # Add service statistics if available
        if is_available and translation_service:
            try:
                stats = translation_service.get_stats()
                response_data["service_stats"] = {
                    "total_operations": stats.get("total_operations", 0),
                    "cache_hit_rate": round(stats.get("cache_hit_rate", 0), 2),
                    "error_rate": round(stats.get("error_rate", 0), 2),
                    "service_health": stats.get("service_health", "unknown"),
                    "has_google_translate": stats.get("has_google", False),
                    "has_redis_cache": stats.get("has_redis", False),
                    "has_openai": stats.get("has_openai", False)
                }
            except Exception as stats_error:
                logger.warning(f"Could not get service stats: {stats_error}")
                response_data["service_stats"] = {"error": "stats_unavailable"}
        
        return response_data
            
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        
        # Return basic fallback response
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

# Add health check endpoint for multilingual services
@app.get("/api/multilingual/health")
async def multilingual_health_check():
    """Health check specifically for multilingual services"""
    logger.info("Multilingual health check requested")
    
    try:
        translation_service, is_available = get_translation_service()
        
        if not is_available:
            return {
                "status": "unavailable",
                "service_available": False,
                "timestamp": datetime.now().isoformat(),
                "error": "Translation service not available"
            }
        
        # Perform comprehensive health check
        health_results = await translation_service.health_check()
        stats = translation_service.get_stats()
        
        return {
            "status": health_results["overall_status"],
            "service_available": True,
            "timestamp": datetime.now().isoformat(),
            "health_details": health_results,
            "performance_stats": {
                "total_operations": stats.get("total_operations", 0),
                "cache_hit_rate": round(stats.get("cache_hit_rate", 0), 2),
                "error_rate": round(stats.get("error_rate", 0), 2),
                "service_health": stats.get("service_health", "unknown")
            },
            "capabilities": {
                "openai_available": health_results["openai"],
                "google_translate_available": health_results["google_translate"],
                "redis_cache_available": health_results["redis_cache"],
                "native_spanish": health_results["openai"],
                "translation_fallbacks": health_results["openai"] or health_results["google_translate"]
            }
        }
        
    except Exception as e:
        logger.error(f"Multilingual health check failed: {e}")
        return {
            "status": "error",
            "service_available": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# Also add this import at the top of your api.py file for better organization:
# (Add this after your existing imports)

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