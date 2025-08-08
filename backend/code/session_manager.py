import json
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from backend.code.agentic_state import ConversationTurn, SessionContext, ImmigrationState
from backend.code.paths import OUTPUTS_DIR
from backend.code.structured_logging import get_logger, PerformanceTimer, start_request_tracking

# Create session manager specific logger
session_logger = get_logger("session_manager")

SESSIONS_DB_PATH = os.path.join(OUTPUTS_DIR, "agentic_sessions.db")

class SessionManager:
    """
    Enhanced session manager for agentic workflow with comprehensive debugging and language support.
    """
    
    def __init__(self, db_path: str = SESSIONS_DB_PATH):
        self.db_path = db_path
        self._init_database()
        session_logger.info("session_manager_initialized", db_path=db_path)
    
    def _sanitize_session_id(self, session_id: str) -> str:
        """Sanitize session ID to handle whitespace and other issues."""
        if not session_id:
            return session_id
        
        # Remove leading/trailing whitespace
        cleaned = session_id.strip()
        
        # Log if we had to clean it
        if cleaned != session_id:
            session_logger.info(
                "session_id_sanitized",
                original_session_id=session_id,
                cleaned_session_id=cleaned
            )
        
        return cleaned
    
    def _init_database(self):
        """Initialize the sessions database with enhanced error handling."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            session_logger.info("database_directory_ensured", db_dir=os.path.dirname(self.db_path))
            
            with PerformanceTimer(session_logger, "database_initialization"):
                with sqlite3.connect(self.db_path) as conn:
                    # Create sessions table
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS sessions (
                            session_id TEXT PRIMARY KEY,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            turn_count INTEGER DEFAULT 0,
                            session_context TEXT  -- JSON serialized SessionContext
                        )
                    """)
                
                    # Create conversation_turns table
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS conversation_turns (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            session_id TEXT,
                            turn_number INTEGER,
                            question TEXT,
                            answer TEXT,
                            timestamp TIMESTAMP,
                            question_type TEXT,
                            visa_focus TEXT,  -- JSON serialized list
                            tools_used TEXT,  -- JSON serialized list
                            agent_metadata TEXT,  -- JSON serialized dict
                            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                        )
                    """)
                
                    # Create indexes
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_session_turns 
                        ON conversation_turns (session_id, turn_number)
                    """)
                
                    # Validate tables exist
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                
                    expected_tables = ['sessions', 'conversation_turns']
                    missing_tables = [t for t in expected_tables if t not in tables]
                
                    if missing_tables:
                        raise Exception(f"Failed to create tables: {missing_tables}")
                
                    session_logger.info("database_initialized_successfully", tables=tables)
                
        except Exception as e:
            session_logger.error(
                "database_initialization_failed",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
    
    def get_or_create_session(self, session_id: str = None) -> Dict[str, Any]:
        """Get existing session or create new one with enhanced debugging."""
        
        # Sanitize session ID
        if session_id:
            session_id = self._sanitize_session_id(session_id)
        
        if not session_id:
            from backend.code.utils import slugify_chat_session
            import uuid
            session_id = f"session-{uuid.uuid4().hex[:8]}"
            session_logger.info("new_session_id_generated", session_id=session_id)
        
        session_logger.info("getting_or_creating_session", session_id=session_id)
        
        try:
            with PerformanceTimer(session_logger, "session_retrieval", session_id=session_id):
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    # Check if session exists with debugging
                    session_logger.info("querying_for_session", session_id=session_id)
                    session = conn.execute(
                        "SELECT * FROM sessions WHERE session_id = ?", 
                        (session_id,)
                    ).fetchone()
                    
                    if session:
                        session_logger.info("existing_session_found", session_id=session_id)
                        session_data = {
                            "session_id": session["session_id"],
                            "created_at": session["created_at"],
                            "updated_at": session["updated_at"],
                            "turn_count": session["turn_count"],
                            "session_context": json.loads(session["session_context"]) if session["session_context"] else {}
                        }
                        session_logger.info("session_data_retrieved", 
                                          session_id=session_id, 
                                          turn_count=session_data['turn_count'])
                        return session_data
                    else:
                        session_logger.info("session_not_found_creating_new", session_id=session_id)
                        
                        # Create new session
                        conn.execute(
                            """INSERT INTO sessions (session_id, session_context) 
                               VALUES (?, ?)""",
                            (session_id, json.dumps({}))
                        )
                        
                        # Verify creation
                        created_session = conn.execute(
                            "SELECT * FROM sessions WHERE session_id = ?", 
                            (session_id,)
                        ).fetchone()
                        
                        if not created_session:
                            raise Exception(f"Failed to create session: {session_id}")
                        
                        session_logger.info("new_session_created", session_id=session_id)
                        return {
                            "session_id": session_id,
                            "created_at": datetime.now().isoformat(),
                            "updated_at": datetime.now().isoformat(),
                            "turn_count": 0,
                            "session_context": {}
                        }
                    
        except Exception as e:
            session_logger.error(
                "session_get_create_failed",
                session_id=session_id,
                error_type=type(e).__name__,
                error_message=str(e),
                db_path=self.db_path
            )
            raise
    
    def load_conversation_history(self, session_id: str, limit: int = 10) -> List[ConversationTurn]:
        """Load conversation history with enhanced debugging."""
        
        session_id = self._sanitize_session_id(session_id)
        session_logger.info("loading_conversation_history", 
                          session_id=session_id, 
                          limit=limit)
        
        try:
            with PerformanceTimer(session_logger, "conversation_history_load", session_id=session_id):
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    # Query with debugging
                    rows = conn.execute("""
                        SELECT * FROM conversation_turns 
                        WHERE session_id = ? 
                        ORDER BY turn_number ASC 
                        LIMIT ?
                    """, (session_id, limit)).fetchall()
                    
                    session_logger.info("conversation_turns_found", 
                                      session_id=session_id, 
                                      turn_count=len(rows))
                    
                    if len(rows) == 0:
                        session_logger.info("no_conversation_history_found", session_id=session_id)
                        return []
                    
                    turns = []
                    for i, row in enumerate(rows):
                        try:
                            turn = ConversationTurn(
                                question=row["question"],
                                answer=row["answer"],
                                timestamp=row["timestamp"],
                                question_type=row["question_type"],
                                visa_focus=json.loads(row["visa_focus"]) if row["visa_focus"] else None,
                                tools_used=json.loads(row["tools_used"]) if row["tools_used"] else None
                            )
                            turns.append(turn)
                            session_logger.debug("conversation_turn_loaded", 
                                               session_id=session_id,
                                               turn_number=i+1,
                                               question_preview=turn.question[:50])
                        except Exception as e:
                            session_logger.error("conversation_turn_load_failed",
                                                session_id=session_id,
                                                turn_number=i+1,
                                                error_message=str(e))
                            continue
                    
                    session_logger.info("conversation_history_loaded_successfully", 
                                       session_id=session_id, 
                                       turns_loaded=len(turns))
                    return turns
                
        except Exception as e:
            session_logger.error("conversation_history_load_failed",
                                session_id=session_id,
                                error_type=type(e).__name__,
                                error_message=str(e))
            return []

    def get_session_language_preference(self, session_id: str) -> Optional[str]:
        """Get the preferred language for a session with enhanced debugging."""
        session_id = self._sanitize_session_id(session_id)
        
        session_logger.info("get_session_language_preference_started", session_id=session_id)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Check if session exists first
                session_check = conn.execute(
                    "SELECT session_id, session_context FROM sessions WHERE session_id = ?",
                    (session_id,)
                ).fetchone()
                
                if not session_check:
                    session_logger.warning("Session not found in database", session_id=session_id)
                    return None
                
                session_context_raw = session_check["session_context"]
                session_logger.debug("Session context raw data", 
                                    session_id=session_id, 
                                    context_preview=str(session_context_raw)[:100])
                
                if session_context_raw:
                    try:
                        context_data = json.loads(session_context_raw)
                        session_logger.debug("Session context parsed successfully", 
                                            session_id=session_id,
                                            context_keys=list(context_data.keys()))
                        
                        preferred_language = context_data.get("preferred_language")
                        
                        if preferred_language:
                            session_logger.info(
                                "session_language_preference_found_from_context",
                                session_id=session_id,
                                preferred_language=preferred_language,
                                source="session_context"
                            )
                            return preferred_language
                        else:
                            session_logger.debug("No preferred_language key in context", 
                                                session_id=session_id,
                                                available_keys=list(context_data.keys()))
                            
                    except json.JSONDecodeError as e:
                        session_logger.warning(
                            "invalid_session_context_json_detailed",
                            session_id=session_id,
                            json_error=str(e),
                            raw_context=str(session_context_raw)[:200]
                        )
                else:
                    session_logger.debug("Session context is empty or null", session_id=session_id)
                
                # Fallback: analyze recent conversation turns for language patterns
                session_logger.debug("Trying fallback language detection from conversation history", 
                                    session_id=session_id)
                
                recent_turns = conn.execute("""
                    SELECT answer FROM conversation_turns 
                    WHERE session_id = ? 
                    ORDER BY turn_number DESC 
                    LIMIT 3
                """, (session_id,)).fetchall()
                
                session_logger.debug("Found conversation turns for fallback", 
                                    session_id=session_id, 
                                    turn_count=len(recent_turns))
                
                if recent_turns:
                    for i, turn in enumerate(recent_turns):
                        answer = turn[0]
                        
                        # Look for language-specific verification phrases
                        if "Vérifiez les informations actuelles sur uscis.gov" in answer:
                            session_logger.info(
                                "session_language_detected_from_history_french",
                                session_id=session_id,
                                detected_language="fr",
                                source="conversation_analysis"
                            )
                            return "fr"
                        elif "Verifica la información actual en uscis.gov" in answer:
                            session_logger.info(
                                "session_language_detected_from_history_spanish",
                                session_id=session_id,
                                detected_language="es",
                                source="conversation_analysis"
                            )
                            return "es"
                        elif "Verifique as informações atuais em uscis.gov" in answer:
                            session_logger.info(
                                "session_language_detected_from_history_portuguese",
                                session_id=session_id,
                                detected_language="pt",
                                source="conversation_analysis"
                            )
                            return "pt"
                
                session_logger.info(
                    "no_session_language_preference_found_final",
                    session_id=session_id
                )
                return None
                
        except Exception as e:
            session_logger.error(
                "error_getting_session_language_preference_detailed",
                session_id=session_id,
                error_message=str(e),
                error_type=type(e).__name__
            )
            return None

    def set_session_language_preference(self, session_id: str, language_code: str, confidence: float = 1.0) -> None:
        """Set or update the language preference for a session."""
        session_id = self._sanitize_session_id(session_id)
        
        session_logger.info("set_session_language_preference_started", 
                          session_id=session_id,
                          language_code=language_code,
                          confidence=confidence)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Ensure session exists first
                self.get_or_create_session(session_id)
                
                # Get current context
                current_context = conn.execute(
                    "SELECT session_context FROM sessions WHERE session_id = ?",
                    (session_id,)
                ).fetchone()
                
                context_data = {}
                if current_context and current_context[0]:
                    try:
                        context_data = json.loads(current_context[0])
                        session_logger.debug("Existing context loaded", 
                                           session_id=session_id,
                                           existing_keys=list(context_data.keys()))
                    except json.JSONDecodeError:
                        session_logger.warning("Invalid JSON in existing session context", session_id=session_id)
                        context_data = {}
                
                # Update language preference
                context_data["preferred_language"] = language_code
                context_data["language_confidence"] = confidence
                context_data["language_last_updated"] = datetime.now().isoformat()
                
                session_logger.debug("Updated context data", 
                                    session_id=session_id,
                                    context_keys=list(context_data.keys()),
                                    preferred_language=context_data.get("preferred_language"))
                
                # Update database
                rows_updated = conn.execute(
                    "UPDATE sessions SET session_context = ?, updated_at = ? WHERE session_id = ?",
                    (json.dumps(context_data), datetime.now().isoformat(), session_id)
                ).rowcount
                
                if rows_updated == 0:
                    session_logger.error("Failed to update session context - no rows affected", 
                                       session_id=session_id)
                    return
                
                # Verification: Check if the update worked
                verify_context = conn.execute(
                    "SELECT session_context FROM sessions WHERE session_id = ?",
                    (session_id,)
                ).fetchone()
                
                if verify_context and verify_context[0]:
                    try:
                        verify_data = json.loads(verify_context[0])
                        stored_language = verify_data.get("preferred_language")
                        if stored_language == language_code:
                            session_logger.info(
                                "session_language_preference_updated_verified",
                                session_id=session_id,
                                language_code=language_code,
                                confidence=confidence
                            )
                        else:
                            session_logger.error(
                                "session_language_preference_verification_failed",
                                session_id=session_id,
                                expected=language_code,
                                actual=stored_language
                            )
                    except json.JSONDecodeError:
                        session_logger.error("Verification failed - invalid JSON after update", 
                                           session_id=session_id)
                
        except Exception as e:
            session_logger.error(
                "error_setting_session_language_preference",
                session_id=session_id,
                language_code=language_code,
                error_message=str(e)
            )

    def should_maintain_session_language(self, session_id: str, new_detected_language: str, 
                                       new_confidence: float) -> tuple:
        """Determine if we should maintain session language or switch to newly detected language."""
        session_id = self._sanitize_session_id(session_id)
        
        session_logger.info("should_maintain_session_language_started",
                          session_id=session_id,
                          new_detected_language=new_detected_language,
                          new_confidence=new_confidence)
        
        # Get current session language preference
        session_language = self.get_session_language_preference(session_id)
        
        if not session_language:
            # No session preference - use new detection
            session_logger.info(
                "no_session_language_using_new_detection",
                session_id=session_id,
                new_language=new_detected_language,
                confidence=new_confidence
            )
            return False, new_detected_language
        
        # We have a session language preference
        if session_language == new_detected_language:
            # Same language - maintain
            session_logger.info(
                "same_language_maintaining_session",
                session_id=session_id,
                session_language=session_language
            )
            return True, session_language
        
        # Different language detected
        if new_confidence > 0.85:  # High confidence threshold for language switching
            session_logger.info(
                "high_confidence_language_switch",
                session_id=session_id,
                from_language=session_language,
                to_language=new_detected_language,
                confidence=new_confidence
            )
            return False, new_detected_language
        else:
            # Low confidence - maintain session language
            session_logger.info(
                "low_confidence_maintaining_session_language",
                session_id=session_id,
                session_language=session_language,
                new_detected=new_detected_language,
                confidence=new_confidence
            )
            return True, session_language
    
    def save_conversation_turn(self, session_id: str, turn: ConversationTurn, 
                             final_state: ImmigrationState) -> None:
        """Save conversation turn with enhanced debugging and validation."""
        
        correlation_id = start_request_tracking()
        session_id = self._sanitize_session_id(session_id)
        session_logger.info("saving_conversation_turn", session_id=session_id, 
                          correlation_id=correlation_id)
        
        # Validate input data
        if not turn.question or not turn.answer:
            session_logger.error("invalid_turn_data", 
                               session_id=session_id,
                               has_question=bool(turn.question),
                               has_answer=bool(turn.answer))
            return
        
        if len(turn.answer.strip()) < 10:
            session_logger.error("answer_too_short", 
                               session_id=session_id,
                               answer_length=len(turn.answer.strip()),
                               answer_preview=turn.answer[:50])
            return
        
        try:
            with PerformanceTimer(session_logger, "conversation_turn_save", session_id=session_id):
                with sqlite3.connect(self.db_path) as conn:
                    # Start transaction
                    conn.execute("BEGIN")
                
                    try:
                        # Get current turn count with validation
                        current_session = conn.execute(
                            "SELECT turn_count FROM sessions WHERE session_id = ?",
                            (session_id,)
                        ).fetchone()
                        
                        if not current_session:
                            session_logger.error("session_not_found_during_save", session_id=session_id)
                            # Try to create the session
                            conn.execute(
                                """INSERT INTO sessions (session_id, session_context, turn_count) 
                                   VALUES (?, ?, ?)""",
                                (session_id, json.dumps({}), 0)
                            )
                            new_turn_number = 1
                        else:
                            new_turn_number = current_session[0] + 1
                        
                        session_logger.info("saving_turn", session_id=session_id, turn_number=new_turn_number)
                        
                        # Insert conversation turn
                        conn.execute("""
                            INSERT INTO conversation_turns 
                            (session_id, turn_number, question, answer, timestamp, 
                             question_type, visa_focus, tools_used, agent_metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            session_id,
                            new_turn_number,
                            turn.question,
                            turn.answer,
                            turn.timestamp,
                            turn.question_type,
                            json.dumps(turn.visa_focus) if turn.visa_focus else None,
                            json.dumps(turn.tools_used) if turn.tools_used else None,
                            json.dumps(final_state.get("synthesis_metadata", {}))
                        ))
                        
                        # Update session context
                        updated_context = self._update_session_context(session_id, final_state, conn)
                        
                        # Update session
                        conn.execute("""
                            UPDATE sessions 
                            SET turn_count = ?, updated_at = ?, session_context = ?
                            WHERE session_id = ?
                        """, (
                            new_turn_number,
                            datetime.now().isoformat(),
                            json.dumps(updated_context),
                            session_id
                        ))
                        
                        # Commit transaction
                        conn.execute("COMMIT")
                        
                        session_logger.info("conversation_turn_saved_successfully", 
                                           session_id=session_id, 
                                           turn_number=new_turn_number)
                        
                    except Exception as e:
                        conn.execute("ROLLBACK")
                        raise e
                        
        except Exception as e:
            session_logger.error("conversation_turn_save_failed",
                                session_id=session_id,
                                error_type=type(e).__name__,
                                error_message=str(e),
                                question_preview=turn.question[:50],
                                answer_length=len(turn.answer),
                                correlation_id=correlation_id)

    def _update_session_context(self, session_id: str, final_state: ImmigrationState, 
                               conn: sqlite3.Connection = None) -> Dict[str, Any]:
        """Update session context with language tracking and enhanced error handling."""
        
        correlation_id = start_request_tracking()
        session_logger.info("Session context update started", extra={
            "event": "session_context_update_started",
            "session_id": session_id,
            "correlation_id": correlation_id
        })
        
        try:
            # Load current context
            if conn:
                current_context = conn.execute(
                    "SELECT session_context FROM sessions WHERE session_id = ?",
                    (session_id,)
                ).fetchone()
            else:
                with sqlite3.connect(self.db_path) as temp_conn:
                    current_context = temp_conn.execute(
                        "SELECT session_context FROM sessions WHERE session_id = ?",
                        (session_id,)
                    ).fetchone()
            
            context_data = {}
            if current_context and current_context[0]:
                try:
                    context_data = json.loads(current_context[0])
                except json.JSONDecodeError:
                    session_logger.warning("Invalid JSON in session context", extra={
                        "event": "invalid_session_context_json",
                        "session_id": session_id,
                        "correlation_id": correlation_id
                    })
                    context_data = {}
            
            # Update context with new information
            ongoing_topics = context_data.get("ongoing_topics", [])
            visa_types_mentioned = context_data.get("visa_types_mentioned", [])
            
            # Add new topics and visa types
            structured_analysis = final_state.get("structured_analysis", {})
            if structured_analysis.get("primary_focus"):
                topic = structured_analysis["primary_focus"]
                if topic not in ongoing_topics:
                    ongoing_topics.append(topic)
            
            if structured_analysis.get("visa_focus"):
                for visa in structured_analysis["visa_focus"]:
                    if visa not in visa_types_mentioned and visa.lower() != "none":
                        visa_types_mentioned.append(visa)
            
            # Keep only recent items to avoid clutter
            ongoing_topics = ongoing_topics[-5:]
            visa_types_mentioned = visa_types_mentioned[-10:]
            
            # ENHANCED: Update language tracking from final_state
            detected_language = final_state.get("detected_language")
            language_confidence = final_state.get("language_confidence", 0.0)
            
            session_logger.info("Language tracking info from final_state", extra={
                "event": "language_tracking_from_final_state",
                "session_id": session_id,
                "detected_language": detected_language,
                "language_confidence": language_confidence,
                "correlation_id": correlation_id
            })
            
            if detected_language and language_confidence > 0.7:
                context_data["preferred_language"] = detected_language
                context_data["language_confidence"] = language_confidence
                context_data["language_last_updated"] = datetime.now().isoformat()
                
                session_logger.info("Language preference updated in context", extra={
                    "event": "language_preference_updated_in_context",
                    "session_id": session_id,
                    "language": detected_language,
                    "confidence": language_confidence,
                    "correlation_id": correlation_id
                })
            
            updated_context = {
                "ongoing_topics": ongoing_topics,
                "visa_types_mentioned": visa_types_mentioned,
                "user_situation": context_data.get("user_situation"),
                "last_question_type": final_state.get("question_type"),
                "last_complexity": final_state.get("complexity"),
                # Language tracking fields
                "preferred_language": context_data.get("preferred_language"),
                "language_confidence": context_data.get("language_confidence"),
                "language_last_updated": context_data.get("language_last_updated")
            }
            
            session_logger.info("Session context updated successfully", extra={
                "event": "session_context_updated",
                "session_id": session_id,
                "ongoing_topics": ongoing_topics,
                "visa_types_mentioned": visa_types_mentioned,
                "preferred_language": updated_context.get("preferred_language"),
                "correlation_id": correlation_id
            })
            return updated_context
            
        except Exception as e:
            session_logger.error("Session context update failed", extra={
                "event": "session_context_update_error",
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "correlation_id": correlation_id
            })
            return {"ongoing_topics": [], "visa_types_mentioned": []}
    
    def detect_followup_question(self, current_question: str, session_context: Dict[str, Any]) -> bool:
        """Enhanced follow-up question detection with better precision."""
        
        # Strong follow-up indicators
        strong_followup_indicators = [
            "it", "that", "this", "what about", "can i also", "and what", "follow up",
            "additionally", "furthermore", "next step", "after that", "my first", "previous",
            "earlier", "before", "what did i", "what was", "tell me more", "more details",
            "can you elaborate", "could you clarify", "expand on", "continue", "go on",
            "what happened next", "what else", "also", "besides", "in addition", "related to",
            "regarding that", "regarding this", "about that", "about this", "as mentioned",
            "as discussed", "as you said", "as you mentioned", "as stated", "as explained"
        ]
        
        # Session reference indicators (very strong)
        session_references = [
            "first", "previous", "earlier", "what did i", "what was", "before", "last",
            "my last question", "my previous question", "the last answer", "the previous answer",
            "the last one", "the previous one", "the earlier one", "the earlier question",
            "the earlier answer", "the answer you gave", "the question before", "the answer before",
            "the one before", "the one you just answered", "the one you just gave", "the last response",
            "the previous response", "the earlier response"
        ]
        
        question_lower = current_question.lower()
        
        # Check for explicit session references (highest priority)
        has_session_references = any(word in question_lower for word in session_references)
        
        # Check for strong follow-up words
        has_strong_followup_words = any(indicator in question_lower for indicator in strong_followup_indicators)
        
        # Check question length and immigration terms
        is_short_question = len(current_question.split()) < 6
        immigration_terms = [
            "visa", "green card", "citizenship", "naturalization", "h1b", "f1", "opt", "uscis", "immigration",
            "permanent resident", "work permit", "asylum", "refugee", "i-140", "i-485", "i-20", "ds-160",
            "eb-1", "eb-2", "eb-3", "l1", "j1", "b2", "e2", "o1", "tn", "daca", "advance parole", "us consulate",
            "petition", "sponsor", "interview", "status", "application", "case number", "priority date"
        ]
        has_immigration_terms = any(term in question_lower for term in immigration_terms)
        
        # IMPROVED LOGIC: More precise detection
        if has_session_references:
            is_followup = True
            reason = "explicit session reference"
        elif has_strong_followup_words:
            is_followup = True
            reason = "strong follow-up indicators"
        elif session_context.get("ongoing_topics"):
            # Extract topics and terms from previous context
            prev_topics = set(session_context.get("ongoing_topics", []))
            prev_terms = {term.lower() for topic in prev_topics for term in topic.split()}
            
            # Check if current question contains previously discussed terms
            question_terms = set(question_lower.split())
            common_terms = prev_terms.intersection(question_terms)
            
            if common_terms:
                is_followup = True
                reason = f"contains previously discussed terms: {common_terms}"
            else:
                is_followup = False
                reason = "no related terms found in context"
            
        # Very short questions without immigration terms = might be follow-up
        elif is_short_question and not has_immigration_terms and len(current_question.split()) <= 3:
            is_followup = True
            reason = "very short non-immigration question"
            
        # Everything else = not follow-up
        else:
            is_followup = False
            reason = "appears to be new question"
        
        correlation_id = start_request_tracking()
        session_logger.info("Follow-up question detection completed", extra={
            "event": "followup_detection_completed",
            "question_preview": current_question[:30],
            "is_followup": is_followup,
            "has_session_references": has_session_references,
            "has_strong_followup_words": has_strong_followup_words,
            "is_short_question": is_short_question and len(current_question.split()) <= 3,
            "has_immigration_terms": has_immigration_terms,
            "detection_reason": reason,
            "correlation_id": correlation_id
        })
        
        return is_followup
    
    def list_all_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with error handling."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                sessions = conn.execute("""
                    SELECT session_id, created_at, updated_at, turn_count
                    FROM sessions
                    ORDER BY updated_at DESC
                """).fetchall()
                
                return [dict(session) for session in sessions]
        except Exception as e:
            correlation_id = start_request_tracking()
            session_logger.error("Error listing sessions", extra={
                "event": "session_listing_error",
                "error": str(e),
                "error_type": type(e).__name__,
                "correlation_id": correlation_id
            })
            return []

    def get_unique_session_ids(self) -> List[str]:
        """Returns a list of all unique session IDs in the sessions table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT DISTINCT session_id FROM sessions")
                session_ids = [row[0] for row in cursor.fetchall()]
                return session_ids
        except Exception as e:
            correlation_id = start_request_tracking()
            session_logger.error("Error retrieving unique session IDs", extra={
                "event": "unique_session_ids_error",
                "error": str(e),
                "error_type": type(e).__name__,
                "correlation_id": correlation_id
            })
            return []

    def get_answers_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Return *all* (question, answer) rows for the given session_id."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT question, answer FROM conversation_turns WHERE session_id = ?",
                    (session_id,)
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except sqlite3.Error as e:
            correlation_id = start_request_tracking()
            session_logger.error("Database error getting answers by session", extra={
                "event": "get_answers_db_error",
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "correlation_id": correlation_id
            })
            return []

    def get_last_answer_by_session(self, session_id: str) -> Optional[str]:
        """Retrieves the last answer for a specific session_id."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT answer FROM conversation_turns WHERE session_id = ? ORDER BY turn_number DESC LIMIT 1",
                    (session_id,)
                ).fetchone()
                return row['answer'] if row else None
        except Exception as e:
            correlation_id = start_request_tracking()
            session_logger.error("Error retrieving last answer", extra={
                "event": "get_last_answer_error",
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "correlation_id": correlation_id
            })
            return None

# Global session manager instance
session_manager = SessionManager()

# ENHANCED TEST with detailed debugging
if __name__ == "__main__":
    print("🧪 ENHANCED Testing Session Manager Language Methods...")
    
    # Create test session manager
    test_manager = SessionManager()
    test_session_id = "test-lang-session-debug"
    
    print(f"\n📝 Using test session ID: {test_session_id}")
    
    # Test 1: Create session first
    print("\n1️⃣ Creating/getting session...")
    session_info = test_manager.get_or_create_session(test_session_id)
    print(f"   Session created: {session_info['session_id']}")
    
    # Test 2: Set language preference
    print("\n2️⃣ Setting French language preference...")
    test_manager.set_session_language_preference(test_session_id, "fr", 0.9)
    
    # Test 3: Get language preference immediately
    print("\n3️⃣ Getting language preference...")
    lang = test_manager.get_session_language_preference(test_session_id)
    print(f"   Retrieved language: {lang}")
    
    # Test 4: Should maintain language
    print("\n4️⃣ Testing should maintain language...")
    should_maintain, final_lang = test_manager.should_maintain_session_language(test_session_id, "en", 0.7)
    print(f"   Should maintain: {should_maintain}, Final language: {final_lang}")
    
    # Test 5: Direct database check
    print("\n5️⃣ Direct database verification...")
    import sqlite3
    with sqlite3.connect(test_manager.db_path) as conn:
        result = conn.execute(
            "SELECT session_context FROM sessions WHERE session_id = ?", 
            (test_session_id,)
        ).fetchone()
        if result:
            print(f"   Raw session context: {result[0]}")
            if result[0]:
                try:
                    import json
                    context = json.loads(result[0])
                    print(f"   Parsed context: {context}")
                    print(f"   Preferred language: {context.get('preferred_language', 'NOT FOUND')}")
                except:
                    print("   Error parsing JSON")
        else:
            print("   No session found in database!")
    
    print(f"\n🎯 RESULT:")
    if lang == "fr" and should_maintain and final_lang == "fr":
        print("   ✅ SUCCESS: Language methods working correctly!")
    else:
        print("   ❌ FAILED: Language methods need fixing")
        print(f"   Expected: lang='fr', should_maintain=True, final_lang='fr'")
        print(f"   Actual: lang='{lang}', should_maintain={should_maintain}, final_lang='{final_lang}'")