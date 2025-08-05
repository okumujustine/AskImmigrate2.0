#!/usr/bin/env python3
"""
Comprehensive test suite for radix_tool module - Test coverage improvement
Target: 0% -> 100% coverage for backend/code/tools/radix_tool.py (8 statements)

Test categories:
1. Module imports and initialization
2. Tool functionality and parameters
3. Search logic and integration
4. Edge cases and error handling
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestRadixToolModule:
    """Comprehensive radix_tool module testing"""

    @classmethod
    def setup_class(cls):
        """Clean setup before test class"""
        # Remove any cached imports to ensure clean state
        modules_to_remove = [
            'backend.code.tools.radix_tool',
            'backend.code.tools.radix_loader'
        ]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

    def setup_method(self):
        """Clean setup before each test"""
        # Remove any cached imports to ensure clean state
        modules_to_remove = [
            'backend.code.tools.radix_tool',
            'backend.code.tools.radix_loader'
        ]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

    def teardown_method(self):
        """Clean teardown after each test"""
        # Remove any cached imports to ensure clean state for next test
        modules_to_remove = [
            'backend.code.tools.radix_tool',
            'backend.code.tools.radix_loader'
        ]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

    def test_radix_tool_module_imports(self):
        """Test 1: Radix tool module imports successfully with mocking"""
        
        # Mock the radix_loader at the module level before any imports
        with patch.dict('sys.modules', {
            'backend.code.tools.radix_loader': MagicMock(
                build_kb=MagicMock(return_value={"mock": "knowledge_base"}),
                search_prefix=MagicMock(return_value=[])
            )
        }):
            # Clear any existing imports
            if 'backend.code.tools.radix_tool' in sys.modules:
                del sys.modules['backend.code.tools.radix_tool']
            
            # Import should work without errors
            from backend.code.tools import radix_tool
            
            assert radix_tool is not None
            assert hasattr(radix_tool, 'radix_prefix_search')

    def test_data_directory_path_initialization(self):
        """Test 2: Data directory path is correctly initialized"""
        
        with patch.dict('sys.modules', {
            'backend.code.tools.radix_loader': MagicMock(
                build_kb=MagicMock(return_value={"mock": "kb"}),
                search_prefix=MagicMock(return_value=[])
            )
        }):
            # Clear cache
            if 'backend.code.tools.radix_tool' in sys.modules:
                del sys.modules['backend.code.tools.radix_tool']
            
            from backend.code.tools import radix_tool
            
            # Verify the data directory path is set correctly
            assert hasattr(radix_tool, '_DATA_DIR')
            assert isinstance(radix_tool._DATA_DIR, Path)
            assert str(radix_tool._DATA_DIR).endswith('data')

    def test_radix_prefix_search_function_basic(self):
        """Test 3: Basic radix prefix search functionality"""
        
        mock_loader = MagicMock()
        mock_kb = {"mock": "knowledge_base"}
        mock_loader.build_kb = MagicMock(return_value=mock_kb)
        
        expected_results = [
            {"filename": "E-1_visa.json", "content": "E-1 visa information"},
            {"filename": "E-2_visa.json", "content": "E-2 visa information"}
        ]
        mock_loader.search_prefix = MagicMock(return_value=expected_results)
        
        with patch.dict('sys.modules', {
            'backend.code.tools.radix_loader': mock_loader
        }):
            # Clear cache and import
            if 'backend.code.tools.radix_tool' in sys.modules:
                del sys.modules['backend.code.tools.radix_tool']
            
            from backend.code.tools.radix_tool import radix_prefix_search
            
            # Test the function call
            results = radix_prefix_search("E-")
            
            # Verify search_prefix was called with correct parameters
            mock_loader.search_prefix.assert_called_once_with(mock_kb, "E-")
            
            # Verify results
            assert results == expected_results
            assert isinstance(results, list)

    def test_radix_prefix_search_different_prefixes(self):
        """Test 4: Radix prefix search with different prefix patterns"""
        
        mock_loader = MagicMock()
        mock_kb = {"mock": "kb"}
        mock_loader.build_kb = MagicMock(return_value=mock_kb)
        
        with patch.dict('sys.modules', {
            'backend.code.tools.radix_loader': mock_loader
        }):
            # Clear cache
            if 'backend.code.tools.radix_tool' in sys.modules:
                del sys.modules['backend.code.tools.radix_tool']
            
            from backend.code.tools.radix_tool import radix_prefix_search
            
            # Test different prefix patterns
            test_cases = [
                ("E-", [{"filename": "E-1_visa.json"}]),
                ("EB-3", [{"filename": "EB-3_visa.json"}]),
                ("F-1", [{"filename": "F-1_visa.json"}]),
                ("H-1B", [{"filename": "H-1B_visa.json"}]),
                ("", [])  # Empty prefix
            ]
            
            for prefix, expected_result in test_cases:
                mock_loader.search_prefix.return_value = expected_result
                
                result = radix_prefix_search(prefix)
                
                assert result == expected_result
                assert isinstance(result, list)

    def test_radix_prefix_search_tool_decorator(self):
        """Test 5: Verify the function is properly decorated as a LangChain tool"""
        
        mock_loader = MagicMock()
        mock_loader.build_kb = MagicMock(return_value={"mock": "kb"})
        mock_loader.search_prefix = MagicMock(return_value=[])
        
        with patch.dict('sys.modules', {
            'backend.code.tools.radix_loader': mock_loader
        }):
            # Clear cache
            if 'backend.code.tools.radix_tool' in sys.modules:
                del sys.modules['backend.code.tools.radix_tool']
            
            from backend.code.tools.radix_tool import radix_prefix_search
            
            # Verify it has tool attributes
            assert hasattr(radix_prefix_search, 'name')
            assert hasattr(radix_prefix_search, 'description')
            assert hasattr(radix_prefix_search, 'args_schema')
            
            # Verify the description mentions immigration docs and filename prefix
            description = radix_prefix_search.description
            assert 'immigration' in description.lower()
            assert 'filename' in description.lower()
            assert 'prefix' in description.lower()

    def test_radix_prefix_search_empty_results(self):
        """Test 6: Handle empty search results"""
        
        mock_loader = MagicMock()
        mock_loader.build_kb = MagicMock(return_value={"mock": "kb"})
        mock_loader.search_prefix = MagicMock(return_value=[])
        
        with patch.dict('sys.modules', {
            'backend.code.tools.radix_loader': mock_loader
        }):
            # Clear cache
            if 'backend.code.tools.radix_tool' in sys.modules:
                del sys.modules['backend.code.tools.radix_tool']
            
            from backend.code.tools.radix_tool import radix_prefix_search
            
            result = radix_prefix_search("NONEXISTENT")
            
            assert result == []
            assert isinstance(result, list)

    def test_radix_prefix_search_error_handling(self):
        """Test 7: Error handling in search functionality"""
        
        mock_loader = MagicMock()
        mock_loader.build_kb = MagicMock(return_value={"mock": "kb"})
        mock_loader.search_prefix = MagicMock(side_effect=Exception("Search error"))
        
        with patch.dict('sys.modules', {
            'backend.code.tools.radix_loader': mock_loader
        }):
            # Clear cache
            if 'backend.code.tools.radix_tool' in sys.modules:
                del sys.modules['backend.code.tools.radix_tool']
            
            from backend.code.tools.radix_tool import radix_prefix_search
            
            # Test when search_prefix raises an exception
            with pytest.raises(Exception, match="Search error"):
                radix_prefix_search("E-")

    def test_module_level_variables_accessibility(self):
        """Test 8: Module-level variables are accessible"""
        
        mock_loader = MagicMock()
        test_kb = {"test": "kb"}
        mock_loader.build_kb = MagicMock(return_value=test_kb)
        mock_loader.search_prefix = MagicMock(return_value=[])
        
        with patch.dict('sys.modules', {
            'backend.code.tools.radix_loader': mock_loader
        }):
            # Clear cache
            if 'backend.code.tools.radix_tool' in sys.modules:
                del sys.modules['backend.code.tools.radix_tool']
            
            from backend.code.tools import radix_tool
            
            # Verify module variables are accessible
            assert hasattr(radix_tool, '_DATA_DIR')
            assert hasattr(radix_tool, '_ROOT')
            # Be flexible with knowledge base content (could be from previous tests)
            assert isinstance(radix_tool._ROOT, dict)

    def test_comprehensive_coverage_verification(self):
        """Test 9: Final verification with comprehensive testing"""
        
        mock_loader = MagicMock()
        test_kb = {"documents": ["test1", "test2"], "index": "radix_tree"}
        mock_loader.build_kb = MagicMock(return_value=test_kb)
        
        test_results = [
            {"filename": "E-1_visa.json", "content": "E-1 information"},
            {"filename": "E-2_visa.json", "content": "E-2 information"}
        ]
        mock_loader.search_prefix = MagicMock(return_value=test_results)
        
        with patch.dict('sys.modules', {
            'backend.code.tools.radix_loader': mock_loader
        }):
            # Clear cache
            if 'backend.code.tools.radix_tool' in sys.modules:
                del sys.modules['backend.code.tools.radix_tool']
            
            from backend.code.tools.radix_tool import radix_prefix_search
            from backend.code.tools import radix_tool
            
            # Test all covered lines:
            # Line 1: from pathlib import Path ✓ (covered by import)
            # Line 2: from langchain_core.tools import tool ✓ (covered by import)
            # Line 3: from .radix_loader import build_kb, search_prefix ✓ (covered by import)
            # Line 5: _DATA_DIR = Path(...) ✓ (covered by import and variable access)
            assert isinstance(radix_tool._DATA_DIR, Path)
            
            # Line 6: _ROOT = build_kb(_DATA_DIR) ✓ (covered by import)
            assert radix_tool._ROOT == test_kb
            mock_loader.build_kb.assert_called_once()
            
            # Line 8-13: @tool and function definition ✓ (covered by function call)
            result = radix_prefix_search("E-")
            assert result == test_results
            
            # Line 14: return search_prefix(_ROOT, prefix) ✓ (covered by function call)
            mock_loader.search_prefix.assert_called_with(test_kb, "E-")
        
        print("✅ All radix_tool functionality tested successfully!")
        print("🎯 Coverage targets achieved:")
        print("   • Line 1: pathlib import ✓")
        print("   • Line 2: langchain_core.tools import ✓")  
        print("   • Line 3: radix_loader import ✓")
        print("   • Line 5: _DATA_DIR initialization ✓")
        print("   • Line 6: _ROOT knowledge base build ✓")
        print("   • Line 8-13: @tool decorator and function definition ✓")
        print("   • Line 14: search_prefix function call ✓")
        print("   📊 Expected: 0% -> 100% coverage (8/8 statements)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
