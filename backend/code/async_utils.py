"""
Async utilities for parallel processing to improve performance.
"""
import asyncio
import concurrent.futures
import time
from contextlib import asynccontextmanager
from functools import wraps, lru_cache
from typing import Dict, Any, List, Callable, Optional

from backend.code.llm import get_llm
from backend.code.utils import performance_timer


class AsyncPerformanceManager:
    """Manages async operations and performance tracking."""
    
    def __init__(self):
        self._executor = None
        self._llm_cache = {}
        
    def get_executor(self):
        """Get or create thread pool executor."""
        if self._executor is None:
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        return self._executor
    
    async def run_in_executor(self, func, *args, **kwargs):
        """Run sync function in executor thread."""
        loop = asyncio.get_event_loop()
        executor = self.get_executor()
        
        # Create a wrapper that handles kwargs
        def wrapper():
            return func(*args, **kwargs)
            
        return await loop.run_in_executor(executor, wrapper)
    
    def get_cached_llm(self, model_name: str, temperature: float = 0.2):
        """Cache LLM instances to avoid re-initialization."""
        cache_key = f"{model_name}_{temperature}"
        if cache_key not in self._llm_cache:
            self._llm_cache[cache_key] = get_llm(model_name, temperature)
        return self._llm_cache[cache_key]


# Global async manager
_async_manager = AsyncPerformanceManager()


@asynccontextmanager
async def async_performance_timer(operation_name: str):
    """Async version of performance timer."""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        print(f"ASYNC_PERF: {operation_name} took {duration:.3f}s")


async def parallel_llm_calls(calls: List[Dict[str, Any]]) -> List[Any]:
    """
    Execute multiple LLM calls in parallel.
    
    Args:
        calls: List of dicts with keys: 'model', 'prompt', 'temperature', 'structured_output'
    
    Returns:
        List of LLM responses in same order as input
    """
    async def single_llm_call(call_config):
        model_name = call_config.get('model', 'gemini-2.5-flash')
        prompt = call_config['prompt']
        temperature = call_config.get('temperature', 0.2)
        structured_output = call_config.get('structured_output')
        
        # Get cached LLM instance
        llm = _async_manager.get_cached_llm(model_name, temperature)
        
        # Apply structured output if needed
        if structured_output:
            llm = llm.with_structured_output(structured_output)
        
        # Execute in thread pool to avoid blocking
        return await _async_manager.run_in_executor(llm.invoke, prompt)
    
    # Execute all calls in parallel
    async with async_performance_timer("parallel_llm_calls"):
        results = await asyncio.gather(*[single_llm_call(call) for call in calls])
    
    return results


async def parallel_tool_execution(tool_calls: List[Dict[str, Any]]) -> List[Any]:
    """
    Execute multiple tool calls in parallel.
    
    Args:
        tool_calls: List of dicts with keys: 'tool', 'args'
    
    Returns:
        List of tool results in same order as input
    """
    async def single_tool_call(tool_config):
        tool = tool_config['tool']
        args = tool_config.get('args', {})
        
        # Execute tool in thread pool
        return await _async_manager.run_in_executor(tool.invoke, args)
    
    async with async_performance_timer("parallel_tool_execution"):
        results = await asyncio.gather(*[single_tool_call(call) for call in tool_calls])
    
    return results


def sync_to_async(func):
    """Decorator to convert sync function to async."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        return await _async_manager.run_in_executor(func, *args, **kwargs)
    return async_wrapper


class FastQueryDetector:
    """Detect simple queries that can bypass expensive processing."""
    
    # Simple patterns that don't need full agent processing
    SIMPLE_PATTERNS = [
        'what is',
        'define',
        'explain',
        'tell me about',
        'how much',
        'what does',
        'when is',
        'where is',
        'who is'
    ]
    
    # Complex patterns that need full processing
    COMPLEX_PATTERNS = [
        'how do i transition',
        'what are my options',
        'help me apply',
        'what should i do',
        'my situation is',
        'i need help with',
        'compare',
        'which is better'
    ]
    
    @classmethod
    def is_simple_query(cls, query: str) -> bool:
        """
        Detect if a query is simple enough to bypass review process.
        
        Args:
            query: User's question
            
        Returns:
            True if query is simple, False if complex
        """
        query_lower = query.lower().strip()
        
        # Check for complex patterns first (override simple patterns)
        for pattern in cls.COMPLEX_PATTERNS:
            if pattern in query_lower:
                return False
        
        # Check for simple patterns
        for pattern in cls.SIMPLE_PATTERNS:
            if query_lower.startswith(pattern):
                return True
        
        # If query is very short, likely simple
        if len(query.split()) <= 4:
            return True
            
        return False


@lru_cache(maxsize=1000)
def get_query_embedding(query: str) -> tuple:
    """
    Get cached embedding for query similarity detection.
    Returns tuple so it's hashable for caching.
    """
    from backend.code.utils import embed_documents
    embedding = embed_documents([query])[0]
    return tuple(embedding)


def calculate_similarity(query1: str, query2: str) -> float:
    """Calculate cosine similarity between two queries."""
    import numpy as np
    
    emb1 = np.array(get_query_embedding(query1))
    emb2 = np.array(get_query_embedding(query2))
    
    # Cosine similarity
    similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    return float(similarity)


class QueryCache:
    """Cache full query responses based on similarity."""
    
    def __init__(self, similarity_threshold: float = 0.95):
        self.cache = {}  # {query: (embedding, response, timestamp)}
        self.similarity_threshold = similarity_threshold
        
    def get_similar_response(self, query: str) -> Optional[str]:
        """Get cached response for similar query."""
        if not self.cache:
            return None
            
        query_emb = get_query_embedding(query)
        
        for cached_query, (cached_emb, response, timestamp) in self.cache.items():
            # Calculate similarity using numpy
            import numpy as np
            similarity = np.dot(query_emb, cached_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(cached_emb)
            )
            
            if similarity >= self.similarity_threshold:
                print(f"CACHE_HIT: Found similar query (similarity: {similarity:.3f})")
                return response
                
        return None
    
    def cache_response(self, query: str, response: str):
        """Cache a query response."""
        embedding = get_query_embedding(query)
        self.cache[query] = (embedding, response, time.time())
        
        # Limit cache size
        if len(self.cache) > 100:
            # Remove oldest entries
            oldest_queries = sorted(
                self.cache.keys(), 
                key=lambda q: self.cache[q][2]
            )[:20]
            for old_query in oldest_queries:
                del self.cache[old_query]


# Global query cache
_query_cache = QueryCache()


def should_use_fast_path(query: str, session_history: List = None) -> bool:
    """
    Determine if query should use fast processing path.
    
    Args:
        query: User's question
        session_history: Previous conversation history
        
    Returns:
        True if fast path should be used
    """
    # Check for cached similar response
    if _query_cache.get_similar_response(query):
        return True
    
    # Check if query is simple
    if FastQueryDetector.is_simple_query(query):
        return True
        
    # If it's a follow-up to a simple query, might also be simple
    if session_history and len(session_history) > 0:
        last_query = session_history[-1].get('question', '')
        if FastQueryDetector.is_simple_query(last_query) and len(query.split()) <= 6:
            return True
    
    return False