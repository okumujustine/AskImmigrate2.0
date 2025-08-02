#!/usr/bin/env python3
"""
Test for web search tool to verify it's working properly with real Tavily API
"""

import os
import sys
import pytest
from unittest.mock import patch
from dotenv import load_dotenv

# Add the backend code directory to Python path
backend_code_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_code_dir not in sys.path:
    sys.path.insert(0, backend_code_dir)

load_dotenv()

# Import the web search tool
from tools.web_search_tool import web_search_tool

@pytest.mark.tools
def test_web_search():
    """Test the web search tool directly"""
    print("🔍 Testing Web Search Tool...")
    print("=" * 50)
    
    # Test query about current immigration information
    test_query = "H1B visa fees 2025"
    
    # Check if TAVILY_API_KEY is available in environment (not from .env)  
    api_key = os.environ.get('TAVILY_API_KEY')
    if not api_key:
        pytest.skip("TAVILY_API_KEY not found in environment - skipping real API test")
    
    print(f"🔍 Searching for: '{test_query}' (real API)")
    print("⏳ Please wait...")
    
    results = web_search_tool.invoke({"query": test_query, "num_results": 3})
    
    print(f"✅ Search completed! Found {len(results)} results:")
    print("=" * 50)
    
    for i, result in enumerate(results, 1):
        print(f"\n📄 Result {i}:")
        print(f"   Title: {result.get('title', 'N/A')}")
        print(f"   Source: {result.get('source', 'N/A')}")
        print(f"   URL: {result.get('url', 'N/A')}")
        print(f"   Snippet: {result.get('snippet', 'N/A')[:100]}...")
    
    print("\n" + "=" * 50)
    print("🎉 Web search tool is working correctly!")
    
    # Test assertions for real results
    assert results and len(results) > 0, "No search results returned"
    
    first_result = results[0]
    mock_indicators = "mock" in first_result.get('title', '').lower() or "mock" in first_result.get('snippet', '').lower()
    assert not mock_indicators, "Results appear to be mock data"
    
    print("✅ Results appear to be real web search data")


@pytest.mark.tools
def test_web_search_mocked():
    """Test the web search tool with mocked results for CI/CD environments"""
    print("🔍 Testing Web Search Tool (Mocked)...")
    print("=" * 50)
    
    # Test query about current immigration information
    test_query = "H1B visa fees 2025"
    
    # Mock the web search tool for testing without API key
    mock_results = [
        {
            'title': 'H1B Visa Fees 2025 - USCIS Official Guide',
            'source': 'uscis.gov',
            'url': 'https://www.uscis.gov/h1b-fees-2025',
            'snippet': 'The H-1B petition filing fee for fiscal year 2025 is $780...'
        },
        {
            'title': 'H1B Filing Fees Complete Guide 2025',
            'source': 'immi-usa.com', 
            'url': 'https://www.immi-usa.com/h1b-fees-2025',
            'snippet': 'Complete breakdown of H1B visa fees for 2025 including premium processing...'
        },
        {
            'title': 'H1B Visa Costs and Fee Structure 2025',
            'source': 'nolo.com',
            'url': 'https://www.nolo.com/h1b-visa-fees-2025',
            'snippet': 'Understanding all the costs associated with H1B visa applications in 2025...'
        }
    ]
    
    # Import and patch the internal function that does the actual search
    from tools.web_search_tool import tavidy_run_search
    
    with patch('tools.web_search_tool.tavidy_run_search', return_value=mock_results):
        print(f"🔍 Searching for: '{test_query}' (mocked)")
        print("⏳ Please wait...")
        
        results = web_search_tool.invoke({"query": test_query, "num_results": 3})
        
        print(f"✅ Search completed! Found {len(results)} results:")
        print("=" * 50)
        
        for i, result in enumerate(results, 1):
            print(f"\n📄 Result {i}:")
            print(f"   Title: {result.get('title', 'N/A')}")
            print(f"   Source: {result.get('source', 'N/A')}")
            print(f"   URL: {result.get('url', 'N/A')}")
            print(f"   Snippet: {result.get('snippet', 'N/A')[:100]}...")
        
        print("\n" + "=" * 50)
        print("🎉 Web search tool test completed (mocked)!")
        
        # Test assertions for mocked results
        assert results and len(results) > 0, "No search results returned"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        
        # Verify structure of results
        for result in results:
            assert 'title' in result, "Result missing title"
            assert 'source' in result, "Result missing source"  
            assert 'url' in result, "Result missing URL"
            assert 'snippet' in result, "Result missing snippet"
        
        print("✅ Mocked results have correct structure")

if __name__ == "__main__":
    # Check if API key is available and run appropriate test
    api_key = os.environ.get('TAVILY_API_KEY') 
    if api_key:
        try:
            test_web_search()
            print("\n🚀 Web search tool test PASSED!")
        except Exception as e:
            print(f"\n💥 Web search tool test FAILED: {e}")
            sys.exit(1)
    else:
        try:
            test_web_search_mocked()
            print("\n🚀 Web search tool test PASSED (mocked)!")
        except Exception as e:
            print(f"\n💥 Web search tool test FAILED: {e}")
            sys.exit(1)
