from typing import Dict, Any
from langchain_core.tools import tool
from backend.code.utils import (
    get_collection, 
    get_relevant_documents, 
    initialize_chroma_db, 
    slugify_chat_session,
    load_config
)
from backend.code.llm import get_llm
from backend.code.tools import rag_prompt_utils

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
        # Use cached ChromaDB instance for optimal performance
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
        
        # Generate AI response using direct LLM call with retrieved context
        config = load_config()
        llm = get_llm(config.get("llm", "gemini-2.5-flash"))
        
        # Build context from retrieved documents
        context = "\n\n".join(documents) if documents else ""
        
        # Use the standard RAG prompt
        system_message = rag_prompt_utils.build_rag_prompt(context, query)
        
        # Get LLM response
        rag_response = llm.invoke(system_message)
        
        # Create references from documents
        references = [f"Immigration Document {i+1}" for i in range(len(documents))]
        
        return {
            "response": rag_response.content if hasattr(rag_response, 'content') else str(rag_response),
            "references": references[:3],  # Match n_results
            "documents": documents
        }
        
    except Exception as e:
        return {
            "response": f"Error during RAG processing: {str(e)}",
            "references": [],
            "documents": []
        }