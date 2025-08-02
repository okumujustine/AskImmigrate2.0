#!/usr/bin/env python3
"""
Clear All Sessions from Backend Database
This script will completely wipe all session data from the backend databases
"""

import sqlite3
import os
import shutil

def clear_all_sessions():
    """Clear all session data from backend databases"""
    
    # Database paths (relative to current directory)
    outputs_dir = "outputs"
    agentic_sessions_db = os.path.join(outputs_dir, "agentic_sessions.db")
    chat_history_db = os.path.join(outputs_dir, "chat_history.db")
    
    print("🧹 Clearing all backend session data...")
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"📁 Outputs directory: {outputs_dir}")
    
    # Clear agentic_sessions.db
    if os.path.exists(agentic_sessions_db):
        try:
            conn = sqlite3.connect(agentic_sessions_db)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            print(f"📊 Found {len(tables)} tables in agentic_sessions.db:")
            for table in tables:
                table_name = table[0]
                print(f"   - {table_name}")
                
                # Count rows before deletion
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"     └── {count} rows")
                
                # Clear the table
                cursor.execute(f"DELETE FROM {table_name}")
                print(f"     └── ✅ Cleared")
            
            conn.commit()
            conn.close()
            print("✅ agentic_sessions.db cleared successfully")
            
        except Exception as e:
            print(f"❌ Error clearing agentic_sessions.db: {e}")
    else:
        print("ℹ️  agentic_sessions.db not found")
    
    # Clear chat_history.db
    if os.path.exists(chat_history_db):
        try:
            conn = sqlite3.connect(chat_history_db)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            print(f"📊 Found {len(tables)} tables in chat_history.db:")
            for table in tables:
                table_name = table[0]
                print(f"   - {table_name}")
                
                # Count rows before deletion
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"     └── {count} rows")
                
                # Clear the table
                cursor.execute(f"DELETE FROM {table_name}")
                print(f"     └── ✅ Cleared")
            
            conn.commit()
            conn.close()
            print("✅ chat_history.db cleared successfully")
            
        except Exception as e:
            print(f"❌ Error clearing chat_history.db: {e}")
    else:
        print("ℹ️  chat_history.db not found")
    
    # Clear vector database if it exists
    vector_db_path = os.path.join(outputs_dir, "vector_db")
    if os.path.exists(vector_db_path):
        try:
            shutil.rmtree(vector_db_path)
            print("✅ Vector database cleared successfully")
        except Exception as e:
            print(f"❌ Error clearing vector database: {e}")
    
    print("\n🎉 All backend session data cleared!")
    print("💡 Don't forget to also clear frontend localStorage:")
    print("   - Open browser console (F12)")
    print("   - Run: localStorage.clear()")
    print("   - Refresh the page")

if __name__ == "__main__":
    clear_all_sessions()
