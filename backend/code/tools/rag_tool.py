from typing import Dict, Any
from functools import lru_cache
from langchain_core.tools import tool
from backend.code.utils import (
    get_collection, 
    get_relevant_documents, 
    initialize_chroma_db, 
    slugify_chat_session,
    performance_timer,
    _chroma_manager
)
from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat

@lru_cache(maxsize=100)
def cached_rag_retrieval(query: str) -> Dict[str, Any]:
    """Cache RAG retrieval results to avoid redundant processing."""
    with performance_timer(f"RAG_retrieval_for_query"):
        # Create a session ID for this interaction
        session_id = slugify_chat_session(query)
        
        # Use the existing chat logic to get a response
        rag_response = chat(session_id=session_id, question=query)
        
        # Use singleton ChromaDB manager
        collection = _chroma_manager.get_collection("publications")
        
        # Get relevant documents using cached collection
        documents = get_relevant_documents(
            query=query,
            collection=collection,
            n_results=3,
            threshold=0.6
        )
        
        # Create references from documents
        references = [f"Immigration Document {i+1}" for i in range(len(documents))]
        
        return {
            "response": rag_response,
            "references": references[:3],
            "documents": documents
        }


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
        # Use cached RAG retrieval for performance
        return cached_rag_retrieval(query)
        
    except Exception as e:
        return {
            "response": f"Error during RAG processing: {str(e)}",
            "references": [],
            "documents": []
        }