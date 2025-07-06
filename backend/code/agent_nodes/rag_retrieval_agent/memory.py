import sqlite3

from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories.sql import SQLChatMessageHistory

from backend.code.paths import CHAT_HISTORY_DB_FPATH


def make_memory(session_id: str) -> ConversationBufferMemory:
    sql_history = SQLChatMessageHistory(
        connection=f"sqlite:///{CHAT_HISTORY_DB_FPATH}",
        session_id=session_id,
    )
    return ConversationBufferMemory(
        memory_key="chat_history",
        input_key="question",
        output_key="answer",
        chat_memory=sql_history,
    )


def list_sessions():
    try:
        conn = sqlite3.connect(CHAT_HISTORY_DB_FPATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS message_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            "SELECT DISTINCT session_id FROM message_store ORDER BY session_id"
        )
        sessions = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sessions
    except Exception:
        return []
