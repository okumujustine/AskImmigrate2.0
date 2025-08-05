from typing import Dict, Any
from langchain_core.tools import tool
from backend.code.utils import (
    get_collection, 
    get_relevant_documents, 
    initialize_chroma_db, 
    slugify_chat_session
)
from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat

# Global cache for ChromaDB instance and collection
_chroma_cache = {
    "db_instance": None,
    "collection": None,
    "initialized": False
}

def get_cached_chroma_collection():
    """Get cached ChromaDB collection, initialize if needed."""
    if not _chroma_cache["initialized"]:
        try:
            _chroma_cache["db_instance"] = initialize_chroma_db()
            _chroma_cache["collection"] = get_collection(
                _chroma_cache["db_instance"], 
                collection_name="publications"
            )
            _chroma_cache["initialized"] = True
        except Exception as e:
            # If caching fails, fall back to non-cached approach
            return None, None
    
    return _chroma_cache["db_instance"], _chroma_cache["collection"]


@tool
def rag_retrieval_tool(query: str) -> Dict[str, Any]:
    """
    Retrieves relevant immigration documents and provides AI-generated responses 
    based on the query using RAG (Retrieval-Augmented Generation).
    
    Args:
        query: The immigration-related question to search for
        
    Returns:
        Dictionary containing the AI response, visa information, and references
    """
    try:
        # Create a session ID for this interaction
        session_id = slugify_chat_session(query)
        
        # Use the existing chat logic to get a response
        rag_response = chat(session_id=session_id, question=query)
        
        # Try to use cached ChromaDB instance first
        db_instance, collection = get_cached_chroma_collection()
        
        if db_instance is None or collection is None:
            # Fallback to non-cached approach if caching fails
            db_instance = initialize_chroma_db()
            collection = get_collection(db_instance, collection_name="publications")
        
        # Get relevant documents using cached collection
        documents = get_relevant_documents(
            query=query,
            collection=collection,
            n_results=3,  # Use optimized number from config
            threshold=0.6  # Use optimized threshold from config
        )
        
        # Create references from documents (documents are strings in the current utils)
        references = [f"Immigration Document {i+1}" for i in range(len(documents))]
        
        return {
            "response": rag_response,
            "references": references[:3],  # Match n_results
            "documents": documents
        }
        
    except Exception as e:
        return {
            "response": f"Error during RAG processing: {str(e)}",
            "references": [],
            "documents": []
        }