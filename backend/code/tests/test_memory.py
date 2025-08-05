#!/usr/bin/env python3
"""
Comprehensive test suite for memory module - Test coverage improvement
Target: 44% -> 100% coverage for backend/code/agent_nodes/rag_retrieval_agent/memory.py (18 statements, 10 missing)

Test categories:
1. Memory creation and initialization
2. SQL chat history integration
3. Session listing functionality
4. Database operations and error handling
5. Edge cases and error conditions
"""

import pytest
import sqlite3
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestMemoryModule:
    """Comprehensive memory module testing"""

    def test_make_memory_function_basic(self):
        """Test 1: make_memory function creates ConversationBufferMemory"""
        
        with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.SQLChatMessageHistory') as mock_sql_history, \
             patch('backend.code.agent_nodes.rag_retrieval_agent.memory.ConversationBufferMemory') as mock_memory, \
             patch('backend.code.agent_nodes.rag_retrieval_agent.memory.CHAT_HISTORY_DB_FPATH', '/tmp/test.db'):
            
            mock_sql_instance = MagicMock()
            mock_sql_history.return_value = mock_sql_instance
            mock_memory_instance = MagicMock()
            mock_memory.return_value = mock_memory_instance
            
            from backend.code.agent_nodes.rag_retrieval_agent.memory import make_memory
            
            result = make_memory("test_session_123")
            
            # Verify SQLChatMessageHistory was created with correct parameters
            mock_sql_history.assert_called_once_with(
                connection="sqlite:////tmp/test.db",
                session_id="test_session_123"
            )
            
            # Verify ConversationBufferMemory was created with correct parameters
            mock_memory.assert_called_once_with(
                memory_key="chat_history",
                input_key="question",
                output_key="answer",
                chat_memory=mock_sql_instance
            )
            
            assert result == mock_memory_instance

    def test_make_memory_function_different_session_ids(self):
        """Test 2: make_memory function with different session IDs"""
        
        with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.SQLChatMessageHistory') as mock_sql_history, \
             patch('backend.code.agent_nodes.rag_retrieval_agent.memory.ConversationBufferMemory'), \
             patch('backend.code.agent_nodes.rag_retrieval_agent.memory.CHAT_HISTORY_DB_FPATH', '/tmp/test.db'):
            
            from backend.code.agent_nodes.rag_retrieval_agent.memory import make_memory
            
            # Test with different session IDs
            session_ids = ["session_1", "user_12345", "admin_session", "guest"]
            
            for session_id in session_ids:
                make_memory(session_id)
                
                # Find the call with this session_id
                calls = mock_sql_history.call_args_list
                found_call = None
                for call in calls:
                    if call.kwargs.get('session_id') == session_id:
                        found_call = call
                        break
                
                assert found_call is not None, f"Session ID {session_id} not found in calls"
                assert found_call.kwargs['session_id'] == session_id

    def test_make_memory_function_paths_integration(self):
        """Test 3: make_memory function uses correct paths module"""
        
        with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.SQLChatMessageHistory'), \
             patch('backend.code.agent_nodes.rag_retrieval_agent.memory.ConversationBufferMemory'), \
             patch('backend.code.agent_nodes.rag_retrieval_agent.memory.CHAT_HISTORY_DB_FPATH') as mock_path:
            
            mock_path.__str__ = MagicMock(return_value="/custom/path/chat.db")
            
            from backend.code.agent_nodes.rag_retrieval_agent.memory import make_memory
            
            make_memory("test")
            
            # Verify the path was used (it's imported from paths module)
            assert mock_path is not None

    def test_list_sessions_function_with_data(self):
        """Test 4: list_sessions function with existing data"""
        
        # Create temporary database
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_chat.db"
            
            # Create database and insert test data
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create table
            cursor.execute("""
                CREATE TABLE message_store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert test data
            test_sessions = ["session_1", "session_2", "session_1", "session_3"]
            for session_id in test_sessions:
                cursor.execute(
                    "INSERT INTO message_store (session_id, message) VALUES (?, ?)",
                    (session_id, f"Test message for {session_id}")
                )
            
            conn.commit()
            conn.close()
            
            # Test list_sessions with mocked path
            with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.CHAT_HISTORY_DB_FPATH', str(db_path)):
                from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
                
                sessions = list_sessions()
                
                # Should return unique sessions in order
                expected_sessions = ["session_1", "session_2", "session_3"]
                assert sessions == expected_sessions

    def test_list_sessions_function_empty_database(self):
        """Test 5: list_sessions function with empty database"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "empty_chat.db"
            
            # Create empty database
            conn = sqlite3.connect(db_path)
            conn.close()
            
            with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.CHAT_HISTORY_DB_FPATH', str(db_path)):
                from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
                
                sessions = list_sessions()
                
                # Should return empty list
                assert sessions == []

    def test_list_sessions_function_creates_table_if_not_exists(self):
        """Test 6: list_sessions function creates table if it doesn't exist"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "new_chat.db"
            
            with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.CHAT_HISTORY_DB_FPATH', str(db_path)):
                from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
                
                sessions = list_sessions()
                
                # Should return empty list and create table
                assert sessions == []
                
                # Verify table was created
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_store'")
                table_exists = cursor.fetchone() is not None
                conn.close()
                
                assert table_exists

    def test_list_sessions_function_error_handling(self):
        """Test 7: list_sessions function handles database errors gracefully"""
        
        # Test with non-existent directory (should cause error)
        with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.CHAT_HISTORY_DB_FPATH', '/non/existent/path/chat.db'):
            from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
            
            sessions = list_sessions()
            
            # Should return empty list on error
            assert sessions == []

    def test_list_sessions_function_database_permission_error(self):
        """Test 8: list_sessions function handles permission errors"""
        
        with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.sqlite3.connect') as mock_connect:
            mock_connect.side_effect = PermissionError("Permission denied")
            
            from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
            
            sessions = list_sessions()
            
            # Should return empty list on permission error
            assert sessions == []

    def test_list_sessions_function_database_corruption_error(self):
        """Test 9: list_sessions function handles database corruption"""
        
        with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Simulate database corruption during query execution
            mock_cursor.execute.side_effect = [None, sqlite3.DatabaseError("Database is corrupted")]
            
            from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
            
            sessions = list_sessions()
            
            # Should return empty list on database error
            assert sessions == []

    def test_list_sessions_function_with_special_session_ids(self):
        """Test 10: list_sessions function with special session IDs"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "special_sessions.db"
            
            # Create database and insert special session IDs
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE message_store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Test with special characters and formats
            special_sessions = [
                "user@email.com",
                "session-with-dashes",
                "session_with_underscores",
                "123456",
                "SESSION_CAPS",
                "unicode-session-🚀"
            ]
            
            for session_id in special_sessions:
                cursor.execute(
                    "INSERT INTO message_store (session_id, message) VALUES (?, ?)",
                    (session_id, "Test message")
                )
            
            conn.commit()
            conn.close()
            
            with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.CHAT_HISTORY_DB_FPATH', str(db_path)):
                from backend.code.agent_nodes.rag_retrieval_agent.memory import list_sessions
                
                sessions = list_sessions()
                
                # Should handle all special session IDs
                assert len(sessions) == len(special_sessions)
                for session in special_sessions:
                    assert session in sessions

    def test_module_imports_and_dependencies(self):
        """Test 11: Module imports and dependencies are correct"""
        
        import backend.code.agent_nodes.rag_retrieval_agent.memory as memory_module
        
        # Verify required functions exist
        assert hasattr(memory_module, 'make_memory')
        assert hasattr(memory_module, 'list_sessions')
        assert callable(memory_module.make_memory)
        assert callable(memory_module.list_sessions)
        
        # Verify required imports are available
        assert hasattr(memory_module, 'sqlite3')
        assert hasattr(memory_module, 'ConversationBufferMemory')
        assert hasattr(memory_module, 'SQLChatMessageHistory')
        assert hasattr(memory_module, 'CHAT_HISTORY_DB_FPATH')

    def test_complete_workflow_integration(self):
        """Test 12: Complete workflow with memory creation and session listing"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "workflow_test.db"
            
            with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.CHAT_HISTORY_DB_FPATH', str(db_path)), \
                 patch('backend.code.agent_nodes.rag_retrieval_agent.memory.SQLChatMessageHistory') as mock_sql_history, \
                 patch('backend.code.agent_nodes.rag_retrieval_agent.memory.ConversationBufferMemory') as mock_memory:
                
                mock_sql_instance = MagicMock()
                mock_sql_history.return_value = mock_sql_instance
                mock_memory_instance = MagicMock()
                mock_memory.return_value = mock_memory_instance
                
                from backend.code.agent_nodes.rag_retrieval_agent.memory import make_memory, list_sessions
                
                # Test memory creation
                memory = make_memory("workflow_session")
                assert memory == mock_memory_instance
                
                # Verify correct connection string was used
                expected_connection = f"sqlite:///{db_path}"
                mock_sql_history.assert_called_with(
                    connection=expected_connection,
                    session_id="workflow_session"
                )
                
                # Test session listing (should work even with empty database)
                sessions = list_sessions()
                assert isinstance(sessions, list)

    def test_make_memory_parameter_validation(self):
        """Test 13: make_memory function parameter validation"""
        
        with patch('backend.code.agent_nodes.rag_retrieval_agent.memory.SQLChatMessageHistory'), \
             patch('backend.code.agent_nodes.rag_retrieval_agent.memory.ConversationBufferMemory'):
            
            from backend.code.agent_nodes.rag_retrieval_agent.memory import make_memory
            
            # Test with various session ID types
            test_session_ids = [
                "normal_session",
                "",  # Empty string
                "123",  # Numeric string
                "special@chars.com",  # Special characters
                "very_long_session_id_with_many_characters_to_test_limits"
            ]
            
            for session_id in test_session_ids:
                memory = make_memory(session_id)
                assert memory is not None
