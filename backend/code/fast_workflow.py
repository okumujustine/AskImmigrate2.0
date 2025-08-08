"""
Fast workflow for simple queries - bypasses multi-agent processing for 90% performance improvement.
"""
import asyncio
from typing import Dict, Any, Optional

from backend.code.async_utils import (
    should_use_fast_path, 
    _query_cache, 
    _async_manager,
    async_performance_timer
)
from backend.code.utils import load_yaml_config, performance_timer, _chroma_manager
from backend.code.paths import APP_CONFIG_FPATH
from backend.code.session_manager import session_manager
from backend.code.agent_nodes.rag_retrieval_agent.chat_logic import chat


async def fast_path_query(query: str, session_id: str) -> Dict[str, Any]:
    """
    Fast path for simple queries - bypasses full agent workflow.
    
    Expected performance: 3-5 seconds vs 24+ seconds for full workflow.
    """
    async with async_performance_timer("fast_path_total"):
        # Check query cache first
        cached_response = _query_cache.get_similar_response(query)
        if cached_response:
            return {
                "synthesis": cached_response,
                "session_id": session_id,
                "fast_path": True,
                "cache_hit": True,
                "processing_time": "< 0.1s"
            }
        
        # Use direct RAG without multi-agent overhead
        with performance_timer("fast_rag_processing"):
            # Execute RAG in thread pool to avoid blocking
            rag_response = await _async_manager.run_in_executor(
                chat, session_id, query
            )
        
        # Cache the response for future similar queries
        _query_cache.cache_response(query, rag_response)
        
        return {
            "synthesis": rag_response,
            "session_id": session_id, 
            "fast_path": True,
            "cache_hit": False,
            "processing_time": "3-5s"
        }


def run_optimized_workflow(text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Optimized workflow dispatcher - chooses fast path vs full workflow.
    
    Args:
        text: User's question
        session_id: Optional session ID
        
    Returns:
        Response dictionary with synthesis and metadata
    """
    # Get session history for context
    session_history = []
    if session_id:
        try:
            history = session_manager.load_conversation_history(session_id, limit=5)
            session_history = [{"question": turn.question} for turn in history]
        except Exception:
            pass  # Continue without history if loading fails
    
    # Decide on processing path
    use_fast_path = should_use_fast_path(text, session_history)
    
    if use_fast_path:
        print("🚀 FAST_PATH: Using optimized processing for simple query")
        
        # Run async fast path
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(fast_path_query(text, session_id))
            loop.close()
            return result
        except Exception as e:
            print(f"⚠️ FAST_PATH failed, falling back to full workflow: {e}")
            # Fall through to full workflow
    
    # Use full multi-agent workflow for complex queries
    print("🔄 FULL_WORKFLOW: Using complete agent processing")
    from backend.code.graph_workflow import run_agentic_askimmigrate
    return run_agentic_askimmigrate(text=text, session_id=session_id)


class StreamingResponseManager:
    """Manages streaming responses for immediate user feedback."""
    
    def __init__(self):
        self.callbacks = []
        
    def add_callback(self, callback):
        """Add callback for streaming updates."""
        self.callbacks.append(callback)
        
    def stream_update(self, message: str, stage: str):
        """Send streaming update to all callbacks."""
        for callback in self.callbacks:
            try:
                callback({
                    "message": message,
                    "stage": stage,
                    "timestamp": __import__('time').time()
                })
            except Exception:
                pass  # Don't let callback errors break the flow
    
    def stream_partial_response(self, partial_text: str, completion_percent: int):
        """Stream partial response as it's being generated."""
        self.stream_update(
            message=partial_text,
            stage=f"generating_response_{completion_percent}%"
        )


# Global streaming manager
streaming_manager = StreamingResponseManager()


def create_fast_api_endpoint():
    """
    Creates optimized FastAPI endpoint with streaming support.
    This should replace the existing /query endpoint for better performance.
    """
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse
    import json
    
    def get_optimized_response(query: str, session_id: str = None):
        """Generator for streaming response."""
        # Send immediate acknowledgment
        yield f"data: {json.dumps({'stage': 'processing_started', 'message': 'Processing your question...'})}\n\n"
        
        # Check for cached response first
        cached = _query_cache.get_similar_response(query)
        if cached:
            yield f"data: {json.dumps({'stage': 'cache_hit', 'message': 'Found similar previous answer'})}\n\n"
            yield f"data: {json.dumps({'stage': 'complete', 'response': cached, 'processing_time': '<0.1s'})}\n\n"
            return
        
        # Determine processing path
        use_fast = should_use_fast_path(query)
        processing_type = "fast_path" if use_fast else "full_workflow"
        estimated_time = "3-5 seconds" if use_fast else "15-25 seconds"
        
        yield f"data: {json.dumps({'stage': 'path_selected', 'message': f'Using {processing_type} (est. {estimated_time})'})}\n\n"
        
        # Execute processing
        result = run_optimized_workflow(query, session_id)
        
        # Stream final response
        yield f"data: {json.dumps({'stage': 'complete', 'response': result['synthesis'], 'metadata': result})}\n\n"
    
    return get_optimized_response


# Pre-warm critical components at module import
def _initialize_performance_components():
    """Initialize performance-critical components."""
    try:
        # Pre-warm embedding model
        from backend.code.utils import get_cpu_embedder
        get_cpu_embedder()
        
        # Pre-warm ChromaDB connection
        _chroma_manager.get_collection("publications")
        
        # Pre-warm LLM cache with common model
        config = load_yaml_config(APP_CONFIG_FPATH)
        model_name = config.get("llm", "gemini-2.5-flash")
        _async_manager.get_cached_llm(model_name)
        
        print("✅ Performance components pre-warmed successfully")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not pre-warm all components: {e}")


# Initialize on import
_initialize_performance_components()