import json
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from backend.code.agentic_state import ConversationTurn, SessionContext, ImmigrationState
from backend.code.paths import OUTPUTS_DIR

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
        print(f"📱 SessionManager initialized with database: {db_path}")
    
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
            print(f"🔧 SessionManager: Cleaned session ID '{session_id}' -> '{cleaned}'")
        
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
            print(f"📁 SessionManager: Database directory ensured: {os.path.dirname(self.db_path)}")
            
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
                
                print(f"✅ SessionManager: Database initialized with tables: {tables}")
                
        except Exception as e:
            print(f"❌ SessionManager: Database initialization failed: {e}")
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
            print(f"📱 SessionManager: Generated new session ID: {session_id}")
        
        print(f"📱 SessionManager: Getting or creating session: '{session_id}'")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Check if session exists with debugging
                print(f"🔍 SessionManager: Querying for session: '{session_id}'")
                session = conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?", 
                    (session_id,)
                ).fetchone()
                
                if session:
                    print(f"✅ SessionManager: Found existing session: {session_id}")
                    session_data = {
                        "session_id": session["session_id"],
                        "created_at": session["created_at"],
                        "updated_at": session["updated_at"],
                        "turn_count": session["turn_count"],
                        "session_context": json.loads(session["session_context"]) if session["session_context"] else {}
                    }
                    print(f"📊 SessionManager: Session has {session_data['turn_count']} turns")
                    return session_data
                else:
                    print(f"📱 SessionManager: Session not found, creating new: {session_id}")
                    
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
                    
                    print(f"✅ SessionManager: Created new session: {session_id}")
                    return {
                        "session_id": session_id,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "turn_count": 0,
                        "session_context": {}
                    }
                    
        except Exception as e:
            print(f"❌ SessionManager: Error in get_or_create_session: {e}")
            print(f"   Session ID: '{session_id}'")
            print(f"   Database path: {self.db_path}")
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
        print(f"📚 SessionManager: Loading conversation history for: '{session_id}' (limit: {limit})")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Query with debugging
                rows = conn.execute("""
                    SELECT * FROM conversation_turns 
                    WHERE session_id = ? 
                    ORDER BY turn_number ASC 
                    LIMIT ?
                """, (session_id, limit)).fetchall()
                
                print(f"📊 SessionManager: Found {len(rows)} conversation turns")
                
                if len(rows) == 0:
                    print(f"📭 SessionManager: No conversation history found for session: {session_id}")
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
                        print(f"✅ SessionManager: Loaded turn {i+1}: {turn.question[:50]}...")
                    except Exception as e:
                        print(f"❌ SessionManager: Error loading turn {i+1}: {e}")
                        continue
                
                print(f"📚 SessionManager: Successfully loaded {len(turns)} turns")
                return turns
                
        except Exception as e:
            print(f"❌ SessionManager: Error loading conversation history: {e}")
            print(f"   Session ID: '{session_id}'")
            return []
    
    def save_conversation_turn(self, session_id: str, turn: ConversationTurn, 
                             final_state: ImmigrationState) -> None:
        """
        Save conversation turn with enhanced debugging and validation.
        
        CHANGES:
        - Added session ID sanitization
        - Enhanced validation of input data
        - Better error handling and debugging
        - Transaction rollback on failure
        """
        
        session_id = self._sanitize_session_id(session_id)
        print(f"💾 SessionManager: Saving conversation turn to session: '{session_id}'")
        
        # Validate input data
        if not turn.question or not turn.answer:
            print(f"❌ SessionManager: Invalid turn data - Question: {bool(turn.question)}, Answer: {bool(turn.answer)}")
            return
        
        if len(turn.answer.strip()) < 10:
            print(f"❌ SessionManager: Answer too short: '{turn.answer[:50]}...'")
            return
        
        try:
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
                        print(f"❌ SessionManager: Session not found: {session_id}")
                        # Try to create the session
                        conn.execute(
                            """INSERT INTO sessions (session_id, session_context, turn_count) 
                               VALUES (?, ?, ?)""",
                            (session_id, json.dumps({}), 0)
                        )
                        new_turn_number = 1
                    else:
                        new_turn_number = current_session[0] + 1
                    
                    print(f"💾 SessionManager: Saving as turn #{new_turn_number}")
                    
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
                    
                    print(f"✅ SessionManager: Successfully saved turn #{new_turn_number} to session {session_id}")
                    
                    # Verify the save
                    verify = conn.execute(
                        "SELECT turn_count FROM sessions WHERE session_id = ?",
                        (session_id,)
                    ).fetchone()
                    
                    if verify and verify[0] == new_turn_number:
                        print(f"✅ SessionManager: Verified session now has {verify[0]} turns")
                    else:
                        print(f"⚠️ SessionManager: Turn count verification failed")
                        
                except Exception as e:
                    conn.execute("ROLLBACK")
                    raise e
                    
        except Exception as e:
            print(f"❌ SessionManager: Failed to save conversation turn: {e}")
            print(f"   Session ID: '{session_id}'")
            print(f"   Question: '{turn.question[:50]}...'")
            print(f"   Answer length: {len(turn.answer)}")
            import traceback
            traceback.print_exc()
    
    def _update_session_context(self, session_id: str, final_state: ImmigrationState, 
                               conn: sqlite3.Connection = None) -> Dict[str, Any]:
        """
        Update session context with enhanced error handling.
        
        CHANGES:
        - Better handling of missing data
        - Enhanced logging of context updates
        - More robust context building
        """
        
        print(f"🔄 SessionManager: Updating session context for: {session_id}")
        
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
                    print(f"⚠️ SessionManager: Invalid JSON in session context, resetting")
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
            
            print(f"🔄 SessionManager: Context updated - Topics: {ongoing_topics}, Visas: {visa_types_mentioned}")
            return updated_context
            
        except Exception as e:
            print(f"❌ SessionManager: Error updating session context: {e}")
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
            print(f"❌ SessionManager: Error building context string: {e}")
            return ""
    
    def detect_followup_question(self, current_question: str, session_context: Dict[str, Any]) -> bool:
        """Enhanced follow-up question detection with better precision."""
        
        # Strong follow-up indicators
        strong_followup_indicators = [
            "it", "that", "this", "what about", "can i also",
            "and what", "follow up", "additionally", "furthermore", 
            "next step", "after that", "my first", "previous", "earlier", 
            "before", "what did i", "what was", "tell me more"
        ]
        
        # Session reference indicators (very strong)
        session_references = ["first", "previous", "earlier", "what did i", "what was", "before", "last"]
        
        question_lower = current_question.lower()
        
        # Check for explicit session references (highest priority)
        has_session_references = any(word in question_lower for word in session_references)
        
        # Check for strong follow-up words
        has_strong_followup_words = any(indicator in question_lower for indicator in strong_followup_indicators)
        
        # Check question length and immigration terms
        is_short_question = len(current_question.split()) < 6  # More restrictive
        immigration_terms = ["visa", "green card", "citizenship", "naturalization", "h1b", "f1", "opt", "uscis", "immigration"]
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
        
        print(f"🔗 SessionManager: Follow-up detection for '{current_question[:30]}...': {is_followup}")
        print(f"   • Has session references: {has_session_references}")
        print(f"   • Has strong follow-up words: {has_strong_followup_words}")
        print(f"   • Is very short question: {is_short_question and len(current_question.split()) <= 3}")
        print(f"   • Has immigration terms: {has_immigration_terms}")
        print(f"   • Reason: {reason}")
        
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
            print(f"❌ SessionManager: Error listing sessions: {e}")
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
            print(f"❌ SessionManager: Error retrieving unique session IDs: {e}")
            return []
        
    def get_answer_by_session(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieves session metadata for a specific session_id from the sessions table.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (session_id,)
                ).fetchall()
                return dict(row) if row else {}
        except Exception as e:
            print(f"❌ SessionManager: Error retrieving session metadata for {session_id}: {e}")
            return {}
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
            print(f"❌ SessionManager: Error retrieving last answer for {session_id}: {e}")
            return None
    
# Global session manager instance
session_manager = SessionManager()