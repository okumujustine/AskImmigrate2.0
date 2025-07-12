from typing import Dict, Any
from langchain_core.tools import tool
from backend.code.utils import (
    get_collection, 
    get_relevant_documents, 
    initialize_chroma_db, 
    slugify_chat_session
)
from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat


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
        
        # Get actual retrieved documents using existing utils functions
        db_instance = initialize_chroma_db()
        collection = get_collection(db_instance, collection_name="publications")
        documents = get_relevant_documents(
            query=query,
            collection=collection,
            n_results=5,
            threshold=0.5
        )
        
        # Create references from documents (documents are strings in the current utils)
        references = [f"Immigration Document {i+1}" for i in range(len(documents))]
        
        return {
            "response": rag_response,
            "references": references[:5],
            "documents": documents
        }
        
    except Exception as e:
        return {
            "response": f"Error during RAG processing: {str(e)}",
            "references": [],
            "documents": []
        }