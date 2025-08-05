"""
Tool result caching for improved performance across agent calls.
"""
import time
import hashlib
from typing import Dict, Any, Optional
from backend.code.utils import load_config
from backend.code.paths import APP_CONFIG_FPATH

# Global cache for tool results
_tool_cache = {}

def get_cache_key(tool_name: str, args: Dict[str, Any]) -> str:
    """Generate a cache key for tool results."""
    # Create a deterministic key from tool name and arguments
    args_str = str(sorted(args.items()))
    combined = f"{tool_name}:{args_str}"
    return hashlib.md5(combined.encode()).hexdigest()

def get_cached_tool_result(tool_name: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get cached tool result if available and not expired."""
    try:
        config = load_config(APP_CONFIG_FPATH)
        if not config.get("performance", {}).get("enable_tool_caching", False):
            return None
        
        cache_key = get_cache_key(tool_name, args)
        
        if cache_key in _tool_cache:
            cached_item = _tool_cache[cache_key]
            cache_ttl = config.get("performance", {}).get("cache_ttl_seconds", 300)
            
            # Check if cache is still valid
            if time.time() - cached_item["timestamp"] < cache_ttl:
                return cached_item["result"]
            else:
                # Remove expired cache entry
                del _tool_cache[cache_key]
        
        return None
    except Exception:
        # If caching fails, return None to proceed without cache
        return None

def cache_tool_result(tool_name: str, args: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Cache tool result for future use."""
    try:
        config = load_config(APP_CONFIG_FPATH)
        if not config.get("performance", {}).get("enable_tool_caching", False):
            return
        
        cache_key = get_cache_key(tool_name, args)
        _tool_cache[cache_key] = {
            "result": result,
            "timestamp": time.time()
        }
        
        # Basic cache cleanup - remove old entries if cache gets too large
        if len(_tool_cache) > 100:
            # Remove oldest 20 entries
            sorted_items = sorted(_tool_cache.items(), key=lambda x: x[1]["timestamp"])
            for key, _ in sorted_items[:20]:
                del _tool_cache[key]
                
    except Exception:
        # If caching fails, continue without caching
        pass

def clear_tool_cache() -> None:
    """Clear all cached tool results."""
    global _tool_cache
    _tool_cache = {}
