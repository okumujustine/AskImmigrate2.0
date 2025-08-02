#!/usr/bin/env python3
"""
Test for web search tool to verify it's working properly with real Tavily API
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend code directory to Python path
backend_code_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_code_dir not in sys.path:
    sys.path.insert(0, backend_code_dir)

load_dotenv()

# Import the web search tool
from tools.web_search_tool import web_search_tool

def test_web_search():
    """Test the web search tool directly"""
    print("🔍 Testing Web Search Tool...")
    print("=" * 50)
    
    # Test query about current immigration information
    test_query = "H1B visa fees 2025"
    
    try:
        print(f"🔍 Searching for: '{test_query}'")
        print("⏳ Please wait...")
        
        # Use invoke method for LangChain tools
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
        
        # Test if it's returning real data or mocks
        assert results and len(results) > 0, "No search results returned"
        
        first_result = results[0]
        mock_indicators = "mock" in first_result.get('title', '').lower() or "mock" in first_result.get('snippet', '').lower()
        assert not mock_indicators, "Results appear to be mock data"
        
        print("✅ Results appear to be real web search data")
        
    except Exception as e:
        print(f"❌ Error testing web search tool: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        test_web_search()
        print("\n🚀 Web search tool test PASSED!")
    except Exception as e:
        print(f"\n💥 Web search tool test FAILED: {e}")
        sys.exit(1)
