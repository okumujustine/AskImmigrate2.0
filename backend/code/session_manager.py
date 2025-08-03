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
    Enhanced session manager for agentic workflow with comprehensive debugging.
    
    CHANGES:
    - Added session ID sanitization to handle whitespace issues
    - Enhanced error handling and debugging throughout
    - Better database connection management
    - Improved session context loading and validation
    - Added comprehensive logging for debugging
    """
    
    def __init__(self, db_path: str = SESSIONS_DB_PATH):
        self.db_path = db_path
        self._init_database()
        session_logger.info("session_manager_initialized", db_path=db_path)
    
    def _sanitize_session_id(self, session_id: str) -> str:
        """
        Sanitize session ID to handle whitespace and other issues.
        
        CHANGES: New method to fix session ID handling issues
        """
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
        """
        Initialize the sessions database with enhanced error handling.
        
        CHANGES:
        - Better error handling for database creation
        - Validation that tables were created successfully
        - Enhanced logging
        """
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
        """
        Get existing session or create new one with enhanced debugging.
        
        CHANGES:
        - Added session ID sanitization
        - Enhanced debugging and logging
        - Better error handling for database operations
        - Validation of session data retrieval
        """
        
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
        """
        Load conversation history with enhanced debugging.
        
        CHANGES:
        - Added session ID sanitization
        - Enhanced debugging and error handling
        - Better validation of returned data
        - Detailed logging of what's retrieved
        """
        
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
    
    def save_conversation_turn(self, session_id: str, turn: ConversationTurn, 
                         final_state: ImmigrationState, language_info: Dict[str, Any] = None):
        """
        Save conversation turn with enhanced debugging and validation.
        
        CHANGES:
        - Added session ID sanitization
        - Enhanced validation of input data
        - Better error handling and debugging
        - Transaction rollback on failure
        - Maintains backward compatibility
        - Centralizes conversation saving logic
        - Adds multilingual features incrementally
        """
        
        correlation_id = start_request_tracking()
        session_id = self._sanitize_session_id(session_id)
        
        # Extract language context with intelligent defaults
        language_context = self._extract_unified_language_context(language_info, final_state)
        
        session_logger.info(
            "unified_conversation_turn_save_started",
            session_id=session_id,
            user_language=language_context["language"],
            is_multilingual=language_context["is_multilingual"],
            has_translation=language_context["has_translation"],
            correlation_id=correlation_id
        )
        
        # Validation
        if not self._validate_turn_data(turn, session_id):
            return
        
        try:
            with PerformanceTimer(session_logger, "unified_conversation_save", session_id=session_id):
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("BEGIN")
                    
                    try:
                        # Get or create session with unified language support
                        session_data = self._get_or_create_session_unified(
                            conn, session_id, language_context
                        )
                        new_turn_number = session_data["turn_count"] + 1
                        
                        # Build comprehensive metadata for ALL conversations
                        agent_metadata = self._build_unified_agent_metadata(
                            final_state, language_context, turn
                        )
                        
                        # Single insert for all conversation types
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
                            turn.question_type or ("multilingual" if language_context["is_multilingual"] else "standard"),
                            json.dumps(turn.visa_focus) if turn.visa_focus else None,
                            json.dumps(turn.tools_used) if turn.tools_used else None,
                            json.dumps(agent_metadata)
                        ))
                        
                        # Update session with unified analytics
                        self._update_unified_session_analytics(
                            conn, session_id, language_context, new_turn_number, final_state
                        )
                        
                        conn.execute("COMMIT")
                        
                        session_logger.info(
                            "unified_conversation_turn_saved_successfully",
                            session_id=session_id,
                            turn_number=new_turn_number,
                            user_language=language_context["language"],
                            processing_method=language_context["processing_method"],
                            correlation_id=correlation_id
                        )
                        
                    except Exception as e:
                        conn.execute("ROLLBACK")
                        raise e
                        
        except Exception as e:
            session_logger.error(
                "unified_conversation_save_failed",
                session_id=session_id,
                user_language=language_context["language"],
                error_type=type(e).__name__,
                error_message=str(e),
                correlation_id=correlation_id
            )

    # =============================================================================
    # HELPER METHODS - ADD THESE TO YOUR SessionManager CLASS
    # =============================================================================

    def _validate_turn_data(self, turn: ConversationTurn, session_id: str) -> bool:
        """Validate conversation turn data"""
        
        if not turn.question or not turn.answer:
            session_logger.error(
                "invalid_turn_data", 
                session_id=session_id,
                has_question=bool(turn.question),
                has_answer=bool(turn.answer)
            )
            return False
        
        if len(turn.answer.strip()) < 10:
            session_logger.error(
                "answer_too_short", 
                session_id=session_id,
                answer_length=len(turn.answer.strip()),
                answer_preview=turn.answer[:50]
            )
            return False
        
        return True

    def _extract_unified_language_context(self, language_info: Dict[str, Any], 
                                        final_state: ImmigrationState) -> Dict[str, Any]:
        """Extract comprehensive language context from all available sources."""
        
        context = {
            "language": "en",
            "is_multilingual": False,
            "has_translation": False,
            "processing_method": "standard",
            "confidence": 1.0,
            "detection_metadata": None,
            "translation_metadata": None
        }
        
        # Extract from language_info parameter (highest priority)
        if language_info:
            context["language"] = language_info.get("language", "en")
            context["confidence"] = language_info.get("confidence", 1.0)
            context["detection_metadata"] = {
                "method": language_info.get("detection_method", "manual"),
                "confidence": context["confidence"],
                "source": "parameter"
            }
        
        # Extract from final_state (second priority)
        elif final_state.get("language_info"):
            state_lang_info = final_state["language_info"]
            context["language"] = state_lang_info.get("language", "en")
            context["confidence"] = state_lang_info.get("confidence", 1.0)
            context["detection_metadata"] = {
                "method": state_lang_info.get("detection_method", "auto"),
                "confidence": context["confidence"],
                "source": "state"
            }
        
        # Extract translation metadata from synthesis
        synthesis_meta = final_state.get("synthesis_metadata", {})
        if synthesis_meta.get("translation_info"):
            context["has_translation"] = True
            context["translation_metadata"] = synthesis_meta["translation_info"]
            context["processing_method"] = synthesis_meta["translation_info"].get("method", "unknown")
        
        # Set derived flags
        context["is_multilingual"] = context["language"] != "en"
        
        # Determine processing method if not set
        if context["processing_method"] == "standard":
            if context["is_multilingual"]:
                context["processing_method"] = "native_llm" if context["language"] == "es" else "translation"
            else:
                context["processing_method"] = "english_native"
        
        return context

    def _get_or_create_session_unified(self, conn, session_id: str, 
                                    language_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get existing session or create new one with language support."""
        
        current_session = conn.execute(
            "SELECT turn_count, session_context FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        
        if not current_session:
            # Create new session with language context
            session_context = {
                "preferred_language": language_context["language"],
                "language_detection_data": language_context.get("detection_metadata"),
                "created_at": datetime.now().isoformat(),
                "multilingual_session": language_context["is_multilingual"],
                "processing_method": language_context["processing_method"]
            }
            
            conn.execute(
                """INSERT INTO sessions (session_id, session_context, turn_count) 
                VALUES (?, ?, ?)""",
                (session_id, json.dumps(session_context), 0)
            )
            
            return {"turn_count": 0, "session_context": session_context}
        
        else:
            # Update existing session with language preference
            try:
                existing_context = json.loads(current_session[1]) if current_session[1] else {}
            except json.JSONDecodeError:
                existing_context = {}
            
            # Smart language preference updating
            current_lang = existing_context.get("preferred_language", "en")
            if current_lang != language_context["language"]:
                existing_context.update({
                    "preferred_language": language_context["language"],
                    "previous_language": current_lang,
                    "language_switched_at": datetime.now().isoformat(),
                    "language_switch_count": existing_context.get("language_switch_count", 0) + 1
                })
            
            existing_context.update({
                "last_interaction_language": language_context["language"],
                "language_updated_at": datetime.now().isoformat(),
                "processing_method": language_context["processing_method"]
            })
            
            conn.execute(
                "UPDATE sessions SET session_context = ? WHERE session_id = ?",
                (json.dumps(existing_context), session_id)
            )
            
            return {"turn_count": current_session[0], "session_context": existing_context}

    def _build_unified_agent_metadata(self, final_state: ImmigrationState, 
                                    language_context: Dict[str, Any], turn: ConversationTurn) -> Dict[str, Any]:
        """Build comprehensive agent metadata for the conversation turn."""
        
        synthesis_meta = final_state.get("synthesis_metadata", {})
        
        # Core metadata
        agent_metadata = {
            "language": language_context["language"],
            "is_multilingual": language_context["is_multilingual"],
            "processing_method": language_context["processing_method"],
            "turn_timestamp": datetime.now().isoformat(),
            "language_confidence": language_context["confidence"]
        }
        
        # Language detection information
        if language_context["detection_metadata"]:
            agent_metadata["language_detection"] = language_context["detection_metadata"]
        
        # Translation information
        if language_context["translation_metadata"]:
            agent_metadata["translation_info"] = language_context["translation_metadata"]
        
        # Synthesis information
        if synthesis_meta:
            agent_metadata["synthesis_info"] = {
                "response_type": synthesis_meta.get("response_type"),
                "tools_executed": synthesis_meta.get("tools_executed", 0),
                "processing_successful": synthesis_meta.get("processing_successful", True),
                "multilingual_enabled": synthesis_meta.get("multilingual_enabled", False),
                "quality_indicators": {
                    "response_length": len(turn.answer),
                    "tools_used_count": len(turn.tools_used) if turn.tools_used else 0,
                    "session_aware": synthesis_meta.get("session_aware_response", False)
                }
            }
        
        # Tool usage summary
        if turn.tools_used:
            agent_metadata["tools_summary"] = {
                "count": len(turn.tools_used),
                "tools": turn.tools_used,
                "multilingual_tools": [t for t in turn.tools_used if "multilingual" in t.lower() or "translation" in t.lower()]
            }
        
        return agent_metadata

    def _update_unified_session_analytics(self, conn, session_id: str, 
                                        language_context: Dict[str, Any], turn_number: int, 
                                        final_state: ImmigrationState):
        """Update session with language analytics and metrics."""
        
        # Get current session context
        session_data = conn.execute(
            "SELECT session_context FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        
        if session_data and session_data[0]:
            try:
                context = json.loads(session_data[0])
            except:
                context = {}
        else:
            context = {}
        
        # Update language analytics
        analytics = context.get("language_analytics", {})
        
        # Track language usage
        lang_usage = analytics.get("language_usage", {})
        lang_usage[language_context["language"]] = lang_usage.get(language_context["language"], 0) + 1
        
        # Track processing methods
        method_usage = analytics.get("processing_methods", {})
        method = language_context["processing_method"]
        method_usage[method] = method_usage.get(method, 0) + 1
        
        # Track translation quality if available
        if language_context["translation_metadata"]:
            trans_info = language_context["translation_metadata"]
            quality_data = analytics.get("translation_quality", [])
            quality_data.append({
                "turn": turn_number,
                "method": trans_info.get("method"),
                "confidence": trans_info.get("confidence"),
                "processing_time": trans_info.get("processing_time"),
                "timestamp": datetime.now().isoformat()
            })
            analytics["translation_quality"] = quality_data[-10:]  # Keep last 10
        
        # Track language detection accuracy
        if language_context["detection_metadata"]:
            detection_data = analytics.get("language_detection", [])
            detection_data.append({
                "turn": turn_number,
                "detected_language": language_context["language"],
                "confidence": language_context["confidence"],
                "method": language_context["detection_metadata"].get("method"),
                "timestamp": datetime.now().isoformat()
            })
            analytics["language_detection"] = detection_data[-10:]  # Keep last 10
        
        # Update context
        analytics.update({
            "language_usage": lang_usage,
            "processing_methods": method_usage,
            "total_turns": turn_number,
            "multilingual_turns": sum(count for lang, count in lang_usage.items() if lang != "en"),
            "last_updated": datetime.now().isoformat()
        })
        
        context["language_analytics"] = analytics
        
        # Save updated context
        conn.execute(
            "UPDATE sessions SET session_context = ?, updated_at = ? WHERE session_id = ?",
            (json.dumps(context), datetime.now().isoformat(), session_id)
        )

    # =============================================================================
    # ADDITIONAL UTILITY METHODS FOR LANGUAGE ANALYTICS
    # =============================================================================

    def get_session_language_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive language analytics for a session."""
        
        session_id = self._sanitize_session_id(session_id)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get session context
                session_data = conn.execute(
                    "SELECT session_context FROM sessions WHERE session_id = ?",
                    (session_id,)
                ).fetchone()
                
                if not session_data or not session_data[0]:
                    return {"error": "Session not found"}
                
                context = json.loads(session_data[0])
                
                # Get conversation turns with language data
                turns = conn.execute("""
                    SELECT agent_metadata, timestamp FROM conversation_turns 
                    WHERE session_id = ? ORDER BY turn_number
                """, (session_id,)).fetchall()
                
                # Analyze language patterns
                language_timeline = []
                translation_methods = {}
                
                for turn in turns:
                    if turn[0]:  # agent_metadata exists
                        try:
                            metadata = json.loads(turn[0])
                            lang = metadata.get("language", "en")
                            
                            language_timeline.append({
                                "timestamp": turn[1],
                                "language": lang,
                                "processing_method": metadata.get("processing_method", "unknown")
                            })
                            
                            # Track translation methods
                            if metadata.get("translation_info", {}).get("method"):
                                method = metadata["translation_info"]["method"]
                                translation_methods[method] = translation_methods.get(method, 0) + 1
                        except:
                            continue
                
                return {
                    "session_id": session_id,
                    "analytics": context.get("language_analytics", {}),
                    "language_timeline": language_timeline,
                    "translation_methods": translation_methods,
                    "total_turns": len(turns),
                    "multilingual_turns": len([t for t in language_timeline if t["language"] != "en"])
                }
                
        except Exception as e:
            session_logger.error("get_session_language_analytics_failed", 
                            session_id=session_id, error=str(e))
            return {"error": str(e)}

    def get_global_language_statistics(self) -> Dict[str, Any]:
        """Get system-wide language usage statistics."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Language distribution across all sessions
                language_dist = conn.execute("""
                    SELECT 
                        json_extract(agent_metadata, '$.language') as language,
                        COUNT(*) as turn_count,
                        json_extract(agent_metadata, '$.processing_method') as method
                    FROM conversation_turns 
                    WHERE json_extract(agent_metadata, '$.language') IS NOT NULL
                    GROUP BY language, method
                    ORDER BY turn_count DESC
                """).fetchall()
                
                # Translation quality metrics
                translation_quality = conn.execute("""
                    SELECT 
                        json_extract(agent_metadata, '$.translation_info.method') as method,
                        AVG(CAST(json_extract(agent_metadata, '$.translation_info.confidence') AS FLOAT)) as avg_confidence,
                        COUNT(*) as usage_count
                    FROM conversation_turns 
                    WHERE json_extract(agent_metadata, '$.translation_info.method') IS NOT NULL
                    GROUP BY method
                    ORDER BY usage_count DESC
                """).fetchall()
                
                # Recent activity (last 7 days)
                recent_activity = conn.execute("""
                    SELECT 
                        json_extract(agent_metadata, '$.language') as language,
                        COUNT(*) as recent_turns
                    FROM conversation_turns 
                    WHERE json_extract(agent_metadata, '$.language') IS NOT NULL
                    AND timestamp > datetime('now', '-7 days')
                    GROUP BY language
                    ORDER BY recent_turns DESC
                """).fetchall()
                
                return {
                    "language_distribution": [
                        {"language": row[0], "turns": row[1], "method": row[2]} 
                        for row in language_dist
                    ],
                    "translation_quality": [
                        {"method": row[0], "avg_confidence": row[1], "usage": row[2]} 
                        for row in translation_quality
                    ],
                    "recent_activity": [
                        {"language": row[0], "turns": row[1]} 
                        for row in recent_activity
                    ],
                    "total_multilingual_turns": sum(
                        row[1] for row in language_dist if row[0] != "en"
                    ),
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            session_logger.error("get_global_language_statistics_failed", error=str(e))
            return {"error": str(e)}

    def _get_or_create_session_with_language(self, conn, session_id: str, 
                                        user_language: str, language_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get existing session or create new one with language support."""
        
        current_session = conn.execute(
            "SELECT turn_count, session_context FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        
        if not current_session:
            # Create new session with language context
            session_context = {
                "preferred_language": user_language,
                "language_detection_data": language_info,
                "created_at": datetime.now().isoformat(),
                "multilingual_session": user_language != "en"
            }
            
            conn.execute(
                """INSERT INTO sessions (session_id, session_context, turn_count) 
                VALUES (?, ?, ?)""",
                (session_id, json.dumps(session_context), 0)
            )
            
            return {"turn_count": 0, "session_context": session_context}
        
        else:
            # Update existing session with language preference
            try:
                existing_context = json.loads(current_session[1]) if current_session[1] else {}
            except json.JSONDecodeError:
                existing_context = {}
            
            # Smart language preference updating
            current_lang = existing_context.get("preferred_language", "en")
            if current_lang != user_language:
                existing_context.update({
                    "preferred_language": user_language,
                    "previous_language": current_lang,
                    "language_switched_at": datetime.now().isoformat(),
                    "language_switch_count": existing_context.get("language_switch_count", 0) + 1
                })
            
            existing_context.update({
                "last_interaction_language": user_language,
                "language_updated_at": datetime.now().isoformat()
            })
            
            conn.execute(
                "UPDATE sessions SET session_context = ? WHERE session_id = ?",
                (json.dumps(existing_context), session_id)
            )
            
            return {"turn_count": current_session[0], "session_context": existing_context}

    def _build_agent_metadata(self, final_state: ImmigrationState, user_language: str,
                            translation_metadata: Dict[str, Any], turn: ConversationTurn) -> Dict[str, Any]:
        """Build comprehensive agent metadata for the conversation turn."""
        
        synthesis_meta = final_state.get("synthesis_metadata", {})
        
        # Core metadata
        agent_metadata = {
            "language": user_language,
            "is_multilingual": user_language != "en",
            "turn_timestamp": datetime.now().isoformat()
        }
        
        # Translation information
        if translation_metadata:
            agent_metadata["translation_info"] = translation_metadata
        
        # Synthesis information
        if synthesis_meta:
            agent_metadata["synthesis_metadata"] = {
                "response_type": synthesis_meta.get("response_type"),
                "tools_executed": synthesis_meta.get("tools_executed", 0),
                "processing_successful": synthesis_meta.get("processing_successful", True),
                "multilingual_enabled": synthesis_meta.get("multilingual_enabled", False)
            }
        
        # Tool usage summary
        if turn.tools_used:
            agent_metadata["tools_summary"] = {
                "count": len(turn.tools_used),
                "tools": turn.tools_used,
                "multilingual_tools": [t for t in turn.tools_used if "multilingual" in t.lower()]
            }
        
        return agent_metadata

    def _update_session_context(self, session_id: str, final_state: ImmigrationState, 
                               conn: sqlite3.Connection = None) -> Dict[str, Any]:
        """
        Update session context with enhanced error handling.
        
        CHANGES:
        - Better handling of missing data
        - Enhanced logging of context updates
        - More robust context building
        """
        
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
            
            updated_context = {
                "ongoing_topics": ongoing_topics,
                "visa_types_mentioned": visa_types_mentioned,
                "user_situation": context_data.get("user_situation"),
                "last_question_type": final_state.get("question_type"),
                "last_complexity": final_state.get("complexity")
            }
            
            session_logger.info("Session context updated successfully", extra={
                "event": "session_context_updated",
                "session_id": session_id,
                "ongoing_topics": ongoing_topics,
                "visa_types_mentioned": visa_types_mentioned,
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
    
    def build_session_context_string(self, session_id: str) -> str:
        """Build context string with enhanced error handling."""
        
        session_id = self._sanitize_session_id(session_id)
        
        try:
            session_info = self.get_or_create_session(session_id)
            conversation_history = self.load_conversation_history(session_id, limit=3)
            
            if not conversation_history:
                return ""
            
            context_parts = []
            context_parts.append("CONVERSATION CONTEXT:")
            context_parts.append(f"• Session: {session_id}")
            context_parts.append(f"• Total turns: {session_info['turn_count']}")
            
            # Add recent topics
            context_data = session_info.get("session_context", {})
            if context_data.get("ongoing_topics"):
                context_parts.append(f"• Topics discussed: {', '.join(context_data['ongoing_topics'])}")
            
            if context_data.get("visa_types_mentioned"):
                context_parts.append(f"• Visa types mentioned: {', '.join(context_data['visa_types_mentioned'])}")
            
            # Add recent conversation
            if conversation_history:
                context_parts.append("\nRECENT CONVERSATION:")
                for i, turn in enumerate(conversation_history[-2:], 1):
                    context_parts.append(f"Q{i}: {turn.question}")
                    context_parts.append(f"A{i}: {turn.answer[:200]}...")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            correlation_id = start_request_tracking()
            session_logger.error("Error building context string", extra={
                "event": "context_string_build_error",
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "correlation_id": correlation_id
            })
            return ""
    
    def detect_followup_question(self, current_question: str, session_context: Dict[str, Any]) -> bool:
        """Enhanced follow-up question detection with better precision."""
        
        # Strong follow-up indicators
        # Expanded strong follow-up indicators for better detection
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
        # Expanded session reference indicators for better follow-up detection
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
        is_short_question = len(current_question.split()) < 6  # More restrictive
        # Expanded immigration-related terms for better detection
        immigration_terms = [
            "visa", "green card", "citizenship", "naturalization", "h1b", "f1", "opt", "uscis", "immigration",
            "permanent resident", "work permit", "asylum", "refugee", "i-140", "i-485", "i-20", "ds-160",
            "eb-1", "eb-2", "eb-3", "l1", "j1", "b2", "e2", "o1", "tn", "daca", "advance parole", "us consulate",
            "petition", "sponsor", "interview", "status", "application", "case number", "priority date"
        ]
        has_immigration_terms = any(term in question_lower for term in immigration_terms)
        
        # IMPROVED LOGIC: More precise detection
        # 1. Explicit session references = definitely follow-up
        if has_session_references:
            is_followup = True
            reason = "explicit session reference"
        # 2. Strong follow-up words = likely follow-up
        elif has_strong_followup_words:
            is_followup = True
            reason = "strong follow-up indicators"
        # 3. Very short questions without immigration terms = might be follow-up
        elif is_short_question and not has_immigration_terms and len(current_question.split()) <= 3:
            is_followup = True
            reason = "very short non-immigration question"
        # 4. Everything else = not follow-up
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
        """
        Returns a list of all unique session IDs in the sessions table.
        """
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

    from typing import List, Dict, Any
    import sqlite3

    def get_answers_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Return *all* (question, answer) rows for the given session_id.

        Example result:
            [
                {"question": "Hi?", "answer": "Hello!"},
                {"question": "How are you?", "answer": "Great."},
                ...
            ]

        Empty list ⇢ no rows found.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # map-like rows
                cursor = conn.execute(
                    "SELECT question, answer FROM conversation_turns WHERE session_id = ?",
                    (session_id,)
                )
                rows = cursor.fetchall()  # all rows
                return [dict(r) for r in rows]  # list[dict]
        except sqlite3.Error as e:  # narrow the catch
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
        """
        Retrieves the last answer for a specific session_id.
        """
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