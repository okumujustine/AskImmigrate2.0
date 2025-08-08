#!/usr/bin/env python3
"""
Test performance optimizations to ensure they work correctly.
"""
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_singleton_chroma_manager():
    """Test that ChromaDB manager is a proper singleton."""
    from backend.code.utils import _chroma_manager, ChromaDBManager
    
    # Create multiple instances
    manager1 = ChromaDBManager()
    manager2 = ChromaDBManager()
    
    # They should be the same object
    assert manager1 is manager2, "ChromaDB manager should be singleton"
    assert manager1 is _chroma_manager, "Global instance should be same as new instance"
    print("✓ ChromaDB singleton pattern works correctly")


def test_cached_config_loading():
    """Test that config loading is cached."""
    from backend.code.utils import load_yaml_config_cached
    from backend.code.paths import APP_CONFIG_FPATH
    import time
    
    # First call - will load from disk
    start = time.time()
    config1 = load_yaml_config_cached(str(APP_CONFIG_FPATH))
    first_time = time.time() - start
    
    # Second call - should be cached
    start = time.time()
    config2 = load_yaml_config_cached(str(APP_CONFIG_FPATH))
    cached_time = time.time() - start
    
    # Cached call should be much faster
    assert cached_time < first_time, f"Cached call ({cached_time:.4f}s) should be faster than first call ({first_time:.4f}s)"
    assert config1 == config2, "Cached config should be identical to original"
    print(f"✓ Config caching works: First call: {first_time:.4f}s, Cached call: {cached_time:.4f}s")


def test_performance_timer():
    """Test that performance timer works correctly."""
    from backend.code.utils import performance_timer
    import time
    import io
    import sys
    
    # Capture output
    captured_output = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_output
    
    try:
        with performance_timer("test_operation"):
            time.sleep(0.01)  # Sleep for 10ms
        
        # Restore stdout and get output
        sys.stdout = old_stdout
        output = captured_output.getvalue()
        
        # Should contain timing information
        assert "PERF: test_operation took" in output, f"Expected timing output, got: {output}"
        assert "0.01" in output or "0.02" in output or "0.00" in output, f"Expected timing around 0.01s, got: {output}"
        print("✓ Performance timer works correctly")
        
    finally:
        sys.stdout = old_stdout


def test_load_yaml_config_wrapper():
    """Test that the load_yaml_config wrapper uses caching."""
    from backend.code.utils import load_yaml_config
    from backend.code.paths import APP_CONFIG_FPATH
    import time
    
    # First call
    start = time.time()
    config1 = load_yaml_config(APP_CONFIG_FPATH)
    first_time = time.time() - start
    
    # Second call should use cache
    start = time.time()
    config2 = load_yaml_config(APP_CONFIG_FPATH)
    cached_time = time.time() - start
    
    # Results should be identical and cached call faster
    assert config1 == config2, "Configs should be identical"
    assert cached_time < first_time, f"Cached call should be faster"
    print(f"✓ load_yaml_config wrapper caching works")


if __name__ == "__main__":
    print("Running performance optimization tests...")
    
    try:
        test_singleton_chroma_manager()
        test_cached_config_loading()
        test_performance_timer()
        test_load_yaml_config_wrapper()
        
        print("\n🎉 All performance optimization tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)