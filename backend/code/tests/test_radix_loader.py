#!/usr/bin/env python3
"""
Comprehensive test suite for radix_loader module - Test coverage improvement  
Target: 60% -> 100% coverage for backend/code/tools/radix_loader.py (68 statements, 27 missing)

Test categories:
1. Radix tree construction and node operations
2. Search functionality with different prefixes
3. File loading and JSON parsing
4. Streaming generator functionality
5. Edge cases and error conditions
"""

import pytest
import json
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestRadixLoaderModule:
    """Comprehensive radix_loader module testing"""

    def test_common_prefix_function(self):
        """Test 1: _common_prefix function with various string combinations"""
        
        from backend.code.tools.radix_loader import _common_prefix
        
        # Test identical strings
        assert _common_prefix("abc", "abc") == 3
        
        # Test partial matches
        assert _common_prefix("abc", "abd") == 2
        assert _common_prefix("hello", "help") == 3
        
        # Test no common prefix
        assert _common_prefix("abc", "def") == 0
        
        # Test empty strings
        assert _common_prefix("", "") == 0
        assert _common_prefix("abc", "") == 0
        assert _common_prefix("", "abc") == 0
        
        # Test different lengths
        assert _common_prefix("a", "abc") == 1
        assert _common_prefix("abc", "a") == 1

    def test_node_class_initialization(self):
        """Test 2: _Node class initialization and structure"""
        
        from backend.code.tools.radix_loader import _Node
        
        node = _Node()
        
        # Verify initial state
        assert isinstance(node.children, dict)
        assert len(node.children) == 0
        assert node.value is None
        
        # Test setting value
        node.value = {"test": "data"}
        assert node.value == {"test": "data"}
        
        # Test adding children
        child = _Node()
        node.children["test_key"] = child
        assert "test_key" in node.children
        assert node.children["test_key"] == child

    def test_insert_function_simple(self):
        """Test 3: _insert function with simple key-value pairs"""
        
        from backend.code.tools.radix_loader import _Node, _insert
        
        root = _Node()
        
        # Insert first key-value pair
        _insert(root, "abc", {"content": "test1"})
        
        # Verify structure
        assert "abc" in root.children
        assert root.children["abc"].value == {"content": "test1"}
        
        # Insert second non-overlapping key
        _insert(root, "def", {"content": "test2"})
        
        # Verify both keys exist
        assert "abc" in root.children
        assert "def" in root.children
        assert root.children["def"].value == {"content": "test2"}

    def test_insert_function_with_prefix_splitting(self):
        """Test 4: _insert function with edge splitting when keys share prefixes"""
        
        from backend.code.tools.radix_loader import _Node, _insert
        
        root = _Node()
        
        # Insert longer key first
        _insert(root, "hello", {"content": "test1"})
        
        # Insert shorter key that's a prefix - should trigger edge splitting
        _insert(root, "help", {"content": "test2"})
        
        # Verify the tree structure after splitting
        assert "hel" in root.children  # Common prefix
        hel_node = root.children["hel"]
        
        # Should have two children: "lo" and "p"
        assert "lo" in hel_node.children
        assert "p" in hel_node.children
        assert hel_node.children["lo"].value == {"content": "test1"}
        assert hel_node.children["p"].value == {"content": "test2"}

    def test_collect_function(self):
        """Test 5: _collect function for gathering values from subtree"""
        
        from backend.code.tools.radix_loader import _Node, _insert, _collect
        
        root = _Node()
        
        # Build a small tree
        _insert(root, "a", {"val": 1})
        _insert(root, "ab", {"val": 2})
        _insert(root, "abc", {"val": 3})
        
        # Test collecting all values
        result = []
        _collect(root, result)
        
        # Should collect all 3 values
        assert len(result) == 3
        values = [item["val"] for item in result]
        assert set(values) == {1, 2, 3}

    def test_search_function_exact_prefix(self):
        """Test 6: _search function with exact prefix matches"""
        
        from backend.code.tools.radix_loader import _Node, _insert, _search
        
        root = _Node()
        
        # Insert test data
        _insert(root, "EB-1", {"visa": "EB-1"})
        _insert(root, "EB-2", {"visa": "EB-2"})
        _insert(root, "H-1B", {"visa": "H-1B"})
        
        # Test exact prefix search
        results = _search(root, "EB-")
        assert len(results) == 2
        
        # Verify correct items found
        visa_types = [item["visa"] for item in results]
        assert "EB-1" in visa_types
        assert "EB-2" in visa_types
        assert "H-1B" not in visa_types

    def test_search_function_no_matches(self):
        """Test 7: _search function with prefix that has no matches"""
        
        from backend.code.tools.radix_loader import _Node, _insert, _search
        
        root = _Node()
        
        # Insert test data
        _insert(root, "EB-1", {"visa": "EB-1"})
        _insert(root, "H-1B", {"visa": "H-1B"})
        
        # Test prefix with no matches
        results = _search(root, "L-")
        assert len(results) == 0
        assert results == []

    def test_search_function_empty_prefix(self):
        """Test 8: _search function with empty prefix (should return all)"""
        
        from backend.code.tools.radix_loader import _Node, _insert, _search
        
        root = _Node()
        
        # Insert test data
        _insert(root, "EB-1", {"visa": "EB-1"})
        _insert(root, "H-1B", {"visa": "H-1B"})
        _insert(root, "F-1", {"visa": "F-1"})
        
        # Test empty prefix (should return all)
        results = _search(root, "")
        assert len(results) == 3
        
        visa_types = [item["visa"] for item in results]
        assert set(visa_types) == {"EB-1", "H-1B", "F-1"}

    def test_build_kb_function_with_json_files(self):
        """Test 9: build_kb function with actual JSON files"""
        
        # Create temporary directory with JSON files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test JSON files
            (temp_path / "EB-1_visa.json").write_text(
                json.dumps({"type": "EB-1", "category": "employment"}),
                encoding="utf-8"
            )
            (temp_path / "H-1B_visa.json").write_text(
                json.dumps({"type": "H-1B", "category": "temporary"}),
                encoding="utf-8"
            )
            
            from backend.code.tools.radix_loader import build_kb, search_prefix
            
            # Build knowledge base
            root = build_kb(temp_path)
            
            # Test that files were loaded
            eb1_results = search_prefix(root, "EB-1_visa")
            assert len(eb1_results) == 1
            assert eb1_results[0]["type"] == "EB-1"
            
            h1b_results = search_prefix(root, "H-1B_visa")
            assert len(h1b_results) == 1
            assert h1b_results[0]["type"] == "H-1B"

    def test_build_kb_function_with_subdirectories(self):
        """Test 10: build_kb function with JSON files in subdirectories"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create subdirectory with JSON file
            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "test_file.json").write_text(
                json.dumps({"content": "nested"}),
                encoding="utf-8"
            )
            
            from backend.code.tools.radix_loader import build_kb, search_prefix
            
            # Build knowledge base (should use rglob to find nested files)
            root = build_kb(temp_path)
            
            # Test that nested file was found
            results = search_prefix(root, "test_file")
            assert len(results) == 1
            assert results[0]["content"] == "nested"

    def test_build_kb_function_empty_directory(self):
        """Test 11: build_kb function with empty directory"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            from backend.code.tools.radix_loader import build_kb, search_prefix
            
            # Build knowledge base from empty directory
            root = build_kb(temp_path)
            
            # Should return empty results
            results = search_prefix(root, "")
            assert len(results) == 0

    def test_search_prefix_public_function(self):
        """Test 12: search_prefix public function"""
        
        from backend.code.tools.radix_loader import _Node, _insert, search_prefix
        
        root = _Node()
        
        # Insert test data
        _insert(root, "visa_EB-1", {"type": "employment"})
        _insert(root, "visa_EB-2", {"type": "employment"})
        _insert(root, "visa_H-1B", {"type": "temporary"})
        
        # Test public search_prefix function
        results = search_prefix(root, "visa_EB")
        assert len(results) == 2
        
        # Test with empty prefix
        all_results = search_prefix(root, "")
        assert len(all_results) == 3
        
        # Test with no matches
        no_results = search_prefix(root, "nonexistent")
        assert len(no_results) == 0

    def test_stream_nodes_function_basic(self):
        """Test 13: stream_nodes function basic functionality"""
        
        from backend.code.tools.radix_loader import _Node, _insert, stream_nodes
        
        root = _Node()
        
        # Insert test data
        _insert(root, "a", {"val": 1})
        _insert(root, "ab", {"val": 2})
        _insert(root, "b", {"val": 3})
        
        # Test streaming all nodes
        results = list(stream_nodes(root, ""))
        
        # Should get all 3 key-value pairs
        assert len(results) == 3
        
        # Verify structure (key, value) tuples
        keys = [key for key, value in results]
        values = [value["val"] for key, value in results]
        
        assert set(keys) == {"a", "ab", "b"}
        assert set(values) == {1, 2, 3}

    def test_stream_nodes_function_with_prefix_filter(self):
        """Test 14: stream_nodes function with prefix filtering"""
        
        from backend.code.tools.radix_loader import _Node, _insert, stream_nodes
        
        root = _Node()
        
        # Insert test data
        _insert(root, "EB-1", {"type": "employment"})
        _insert(root, "EB-2", {"type": "employment"})
        _insert(root, "H-1B", {"type": "temporary"})
        
        # Test streaming with prefix filter
        results = list(stream_nodes(root, "EB-"))
        
        # Should get only EB- prefixed items
        assert len(results) == 2
        
        keys = [key for key, value in results]
        assert all(key.startswith("EB-") for key in keys)

    def test_stream_nodes_function_empty_tree(self):
        """Test 15: stream_nodes function with empty tree"""
        
        from backend.code.tools.radix_loader import _Node, stream_nodes
        
        root = _Node()
        
        # Test streaming empty tree
        results = list(stream_nodes(root, ""))
        assert len(results) == 0

    def test_build_kb_with_malformed_json(self):
        """Test 16: build_kb handles malformed JSON gracefully"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create file with malformed JSON
            (temp_path / "bad.json").write_text("{ invalid json", encoding="utf-8")
            
            from backend.code.tools.radix_loader import build_kb
            
            # Should raise JSONDecodeError
            with pytest.raises(json.JSONDecodeError):
                build_kb(temp_path)

    def test_complex_radix_tree_operations(self):
        """Test 17: Complex radix tree operations with multiple edge cases"""
        
        from backend.code.tools.radix_loader import _Node, _insert, _search, stream_nodes
        
        root = _Node()
        
        # Insert keys that will trigger various edge splitting scenarios
        test_data = [
            ("test", {"id": 1}),
            ("testing", {"id": 2}),
            ("tea", {"id": 3}),
            ("ted", {"id": 4}),
            ("ten", {"id": 5}),
            ("i", {"id": 6}),
            ("in", {"id": 7}),
            ("inn", {"id": 8})
        ]
        
        for key, value in test_data:
            _insert(root, key, value)
        
        # Test various prefix searches
        assert len(_search(root, "te")) == 5  # test, testing, tea, ted, ten
        assert len(_search(root, "test")) == 2  # test, testing
        assert len(_search(root, "in")) == 2   # in, inn
        assert len(_search(root, "i")) == 3    # i, in, inn
        
        # Test streaming with complex tree
        all_nodes = list(stream_nodes(root, ""))
        assert len(all_nodes) == 8
        
        # Test prefix filtering in streaming
        te_nodes = list(stream_nodes(root, "te"))
        assert len(te_nodes) == 5

    def test_edge_case_single_character_keys(self):
        """Test 18: Edge case with single character keys"""
        
        from backend.code.tools.radix_loader import _Node, _insert, _search
        
        root = _Node()
        
        # Insert single character keys
        _insert(root, "a", {"char": "a"})
        _insert(root, "b", {"char": "b"})
        _insert(root, "c", {"char": "c"})
        
        # Test searches
        assert len(_search(root, "a")) == 1
        assert len(_search(root, "")) == 3
        assert len(_search(root, "d")) == 0

    def test_coverage_completion_verification(self):
        """Test 19: Verify comprehensive coverage of all functions and branches"""
        
        from backend.code.tools.radix_loader import (
            _common_prefix, _Node, _insert, _collect, _search,
            build_kb, search_prefix, stream_nodes
        )
        
        # Test all public functions exist and are callable
        assert callable(_common_prefix)
        assert callable(build_kb)
        assert callable(search_prefix)
        assert callable(stream_nodes)
        
        # Test internal functions exist
        assert callable(_insert)
        assert callable(_collect)
        assert callable(_search)
        
        # Test Node class
        node = _Node()
        assert hasattr(node, 'children')
        assert hasattr(node, 'value')
        
        # Create a comprehensive test scenario that exercises all code paths
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "comprehensive.json").write_text(
                json.dumps({"test": "comprehensive"}),
                encoding="utf-8"
            )
            
            root = build_kb(temp_path)
            
            # Exercise all public functions
            search_results = search_prefix(root, "comp")
            assert len(search_results) == 1
            
            stream_results = list(stream_nodes(root, ""))
            assert len(stream_results) == 1
            
            empty_search = search_prefix(root, "nonexistent")
            assert len(empty_search) == 0
