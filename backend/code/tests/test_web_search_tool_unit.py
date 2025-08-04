#!/usr/bin/env python3
"""
Comprehensive test suite for web_search_tool module - Test coverage improvement
Target: 48% -> 100% coverage for backend/code/tools/web_search_tool.py (23 statements, 12 missing)

Test categories:
1. URL parsing and source extraction functions
2. Result formatting and transformation
3. Search functionality with mocking
4. Tool decorator integration
5. Edge cases and error handling
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestWebSearchToolUnit:
    """Unit tests for web_search_tool module components"""

    def test_extract_source_function_basic_domain(self):
        """Test 1: extract_source function with basic domain"""
        
        from backend.code.tools.web_search_tool import extract_source
        
        # Test basic domain extraction
        url = "https://example.com/page"
        result = extract_source(url)
        assert result == "Example.com"

    def test_extract_source_function_with_www(self):
        """Test 2: extract_source function removes www prefix"""
        
        from backend.code.tools.web_search_tool import extract_source
        
        # Test www removal
        url = "https://www.immigration.gov/visa-info"
        result = extract_source(url)
        assert result == "Immigration.gov"

    def test_extract_source_function_complex_urls(self):
        """Test 3: extract_source function with complex URLs"""
        
        from backend.code.tools.web_search_tool import extract_source
        
        # Test various URL formats
        test_cases = [
            ("https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations", "Uscis.gov"),
            ("http://travel.state.gov/content/travel/en/us-visas.html", "Travel.state.gov"),
            ("https://cis.org/immigration-data", "Cis.org"),
            ("https://subdomain.example.org/path/to/page", "Subdomain.example.org")
        ]
        
        for url, expected in test_cases:
            result = extract_source(url)
            assert result == expected

    def test_extract_source_function_edge_cases(self):
        """Test 4: extract_source function edge cases"""
        
        from backend.code.tools.web_search_tool import extract_source
        
        # Test edge cases
        assert extract_source("") == ""
        assert extract_source("invalid-url") == ""
        assert extract_source("https://") == ""

    def test_format_tavidy_results_function_basic(self):
        """Test 5: format_tavidy_results function with basic input"""
        
        from backend.code.tools.web_search_tool import format_tavidy_results
        
        # Mock raw results from Tavily
        raw_results = [
            {
                "url": "https://www.uscis.gov/h1b",
                "content": "Information about H1B visas and application process",
                "title": "H1B Visa Information"
            }
        ]
        
        query = "H1B visa information"
        results = format_tavidy_results(raw_results, query)
        
        assert len(results) == 1
        result = results[0]
        assert result["title"] == "Uscis.gov Guide: H1B visa information"
        assert result["url"] == "https://www.uscis.gov/h1b"
        assert result["snippet"] == "Information about H1B visas and application process"
        assert result["source"] == "Uscis.gov"

    def test_format_tavidy_results_function_multiple_results(self):
        """Test 6: format_tavidy_results function with multiple results"""
        
        from backend.code.tools.web_search_tool import format_tavidy_results
        
        # Mock multiple raw results
        raw_results = [
            {
                "url": "https://www.uscis.gov/h1b",
                "content": "USCIS H1B information",
                "title": "H1B Visa"
            },
            {
                "url": "https://www.immihelp.com/h1b-visa",
                "content": "Complete guide to H1B visa process",
                "title": "H1B Guide"
            }
        ]
        
        query = "H1B visa"
        results = format_tavidy_results(raw_results, query)
        
        assert len(results) == 2
        
        # Verify first result
        assert results[0]["title"] == "Uscis.gov Guide: H1B visa"
        assert results[0]["source"] == "Uscis.gov"
        
        # Verify second result
        assert results[1]["title"] == "Immihelp.com Guide: H1B visa"
        assert results[1]["source"] == "Immihelp.com"

    def test_format_tavidy_results_function_long_content(self):
        """Test 7: format_tavidy_results function truncates long content"""
        
        from backend.code.tools.web_search_tool import format_tavidy_results
        
        # Mock result with long content (should be truncated to 200 chars)
        long_content = "A" * 300  # 300 character string
        raw_results = [
            {
                "url": "https://example.com",
                "content": long_content,
                "title": "Test Title"
            }
        ]
        
        query = "test query"
        results = format_tavidy_results(raw_results, query)
        
        assert len(results) == 1
        # Content should be truncated to 200 characters
        assert len(results[0]["snippet"]) == 200
        assert results[0]["snippet"] == "A" * 200

    def test_format_tavidy_results_function_missing_fields(self):
        """Test 8: format_tavidy_results function handles missing fields"""
        
        from backend.code.tools.web_search_tool import format_tavidy_results
        
        # Mock result with missing fields
        raw_results = [
            {
                "title": "Only Title Available"
                # Missing url and content
            },
            {
                "url": "https://example.com"
                # Missing content and title
            }
        ]
        
        query = "test query"
        results = format_tavidy_results(raw_results, query)
        
        assert len(results) == 2
        
        # First result - missing url and content
        assert results[0]["title"] == " Guide: test query"  # Empty source
        assert results[0]["url"] == ""
        assert results[0]["snippet"] == "Only Title Available"  # Falls back to title
        assert results[0]["source"] == ""
        
        # Second result - missing content and title
        assert results[1]["title"] == "Example.com Guide: test query"
        assert results[1]["url"] == "https://example.com"
        assert results[1]["snippet"] == ""  # Empty content and title
        assert results[1]["source"] == "Example.com"

    def test_tavidy_run_search_function_integration(self):
        """Test 9: tavidy_run_search function with mocked TavilySearchResults"""
        
        with patch('backend.code.tools.web_search_tool.TavilySearchResults') as mock_tavily:
            mock_search_instance = MagicMock()
            mock_tavily.return_value = mock_search_instance
            
            # Mock the search results
            mock_raw_results = [
                {
                    "url": "https://www.uscis.gov/test",
                    "content": "Test content from USCIS",
                    "title": "Test Title"
                }
            ]
            mock_search_instance.invoke.return_value = mock_raw_results
            
            from backend.code.tools.web_search_tool import tavidy_run_search
            
            result = tavidy_run_search("test query", k=1)
            
            # Verify TavilySearchResults was instantiated
            mock_tavily.assert_called_once()
            
            # Verify search was invoked with correct parameters
            mock_search_instance.invoke.assert_called_once_with(input="test query", k=1)
            
            # Verify result formatting
            assert len(result) == 1
            assert result[0]["title"] == "Uscis.gov Guide: test query"
            assert result[0]["source"] == "Uscis.gov"

    def test_tavidy_run_search_function_default_k_parameter(self):
        """Test 10: tavidy_run_search function uses default k=3"""
        
        with patch('backend.code.tools.web_search_tool.TavilySearchResults') as mock_tavily:
            mock_search_instance = MagicMock()
            mock_tavily.return_value = mock_search_instance
            mock_search_instance.invoke.return_value = []
            
            from backend.code.tools.web_search_tool import tavidy_run_search
            
            # Call without k parameter (should default to 3)
            tavidy_run_search("test query")
            
            # Verify default k=3 was used
            mock_search_instance.invoke.assert_called_once_with(input="test query", k=3)

    def test_web_search_tool_decorator_and_function(self):
        """Test 11: web_search_tool function with tool decorator"""
        
        with patch('backend.code.tools.web_search_tool.tavidy_run_search') as mock_tavidy:
            mock_results = [{"title": "Test", "url": "test.com", "snippet": "test", "source": "Test"}]
            mock_tavidy.return_value = mock_results
            
            from backend.code.tools.web_search_tool import web_search_tool
            
            # Test the tool function
            result = web_search_tool.invoke({"query": "test immigration", "num_results": 2})
            
            # Verify tavidy_run_search was called with correct parameters
            mock_tavidy.assert_called_once_with("test immigration", k=2)
            
            # Verify result
            assert result == mock_results

    def test_web_search_tool_default_num_results(self):
        """Test 12: web_search_tool function uses default num_results=3"""
        
        with patch('backend.code.tools.web_search_tool.tavidy_run_search') as mock_tavidy:
            mock_tavidy.return_value = []
            
            from backend.code.tools.web_search_tool import web_search_tool
            
            # Call without num_results parameter
            web_search_tool.invoke({"query": "test"})
            
            # Verify default num_results=3 was used (k=3)
            mock_tavidy.assert_called_once_with("test", k=3)

    def test_web_search_tool_langchain_tool_properties(self):
        """Test 13: web_search_tool has correct LangChain tool properties"""
        
        from backend.code.tools.web_search_tool import web_search_tool
        from langchain_core.tools import BaseTool
        
        # Verify it's a LangChain tool
        assert isinstance(web_search_tool, BaseTool)
        
        # Verify tool properties
        assert hasattr(web_search_tool, 'name')
        assert hasattr(web_search_tool, 'description')
        assert hasattr(web_search_tool, 'invoke')
        
        # Verify tool name and description are set
        assert web_search_tool.name == "web_search_tool"
        assert "web search" in web_search_tool.description.lower()

    def test_format_tavidy_results_empty_input(self):
        """Test 14: format_tavidy_results function handles empty input"""
        
        from backend.code.tools.web_search_tool import format_tavidy_results
        
        # Test with empty list
        results = format_tavidy_results([], "test query")
        assert results == []
        
        # Test with None-like values
        raw_results = [{}]  # Empty dict
        results = format_tavidy_results(raw_results, "test query")
        assert len(results) == 1
        assert results[0]["title"] == " Guide: test query"
        assert results[0]["url"] == ""
        assert results[0]["snippet"] == ""
        assert results[0]["source"] == ""

    def test_comprehensive_integration_with_all_functions(self):
        """Test 15: Comprehensive integration test covering all functions"""
        
        with patch('backend.code.tools.web_search_tool.TavilySearchResults') as mock_tavily:
            # Setup comprehensive mock data
            mock_search_instance = MagicMock()
            mock_tavily.return_value = mock_search_instance
            
            mock_raw_results = [
                {
                    "url": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
                    "content": "The H-1B program allows companies to employ foreign workers in specialty occupations that require theoretical or technical expertise." * 3,  # Long content
                    "title": "H-1B Specialty Occupations"
                },
                {
                    "url": "https://www.immihelp.com/h1b/",
                    "content": "Complete guide to H1B visa process",
                    "title": "H1B Visa Guide"
                }
            ]
            mock_search_instance.invoke.return_value = mock_raw_results
            
            from backend.code.tools.web_search_tool import web_search_tool
            
            # Execute full flow
            result = web_search_tool.invoke({"query": "H1B visa requirements", "num_results": 2})
            
            # Verify complete integration
            assert len(result) == 2
            
            # Verify first result processing
            assert result[0]["title"] == "Uscis.gov Guide: H1B visa requirements"
            assert result[0]["source"] == "Uscis.gov"
            assert result[0]["url"] == "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations"
            assert len(result[0]["snippet"]) == 200  # Content truncated
            
            # Verify second result processing
            assert result[1]["title"] == "Immihelp.com Guide: H1B visa requirements"
            assert result[1]["source"] == "Immihelp.com"
            assert result[1]["snippet"] == "Complete guide to H1B visa process"
            
            # Verify the complete call chain
            mock_tavily.assert_called_once()
            mock_search_instance.invoke.assert_called_once_with(input="H1B visa requirements", k=2)
