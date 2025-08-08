#!/usr/bin/env python3
"""
Test suite for the optimized RAG Retrieval Tool
Tests the new single-path RAG implementation with cached ChromaDB.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock

try:
    from backend.code.tools.rag_tool import rag_retrieval_tool
except ImportError as e:
    print(f"❌ Import error: {e}")
    raise


class TestRagRetrievalTool:
    """Test suite for the optimized RAG retrieval tool"""

    def test_rag_tool_basic_functionality(self):
        """Test basic RAG tool functionality with mocked dependencies"""
        
        with patch('backend.code.tools.rag_tool.get_cached_chroma_collection') as mock_cached_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs, \
             patch('backend.code.tools.rag_tool.load_config') as mock_load_config, \
             patch('backend.code.tools.rag_tool.get_llm') as mock_get_llm, \
             patch('backend.code.tools.rag_tool.rag_prompt_utils') as mock_prompt_utils:
            
            # Setup mock returns
            mock_db_instance = MagicMock()
            mock_collection = MagicMock()
            mock_cached_collection.return_value = (mock_db_instance, mock_collection)
            mock_get_docs.return_value = [
                "Document 1: F-1 visa requirements...",
                "Document 2: Student visa guidelines...",
                "Document 3: Immigration procedures..."
            ]
            mock_load_config.return_value = {"llm": "gemini-2.5-flash"}
            
            # Mock LLM response
            mock_llm = MagicMock()
            mock_llm_response = MagicMock()
            mock_llm_response.content = "This is a test immigration response about F-1 visas."
            mock_llm.invoke.return_value = mock_llm_response
            mock_get_llm.return_value = mock_llm
            
            # Mock prompt building
            mock_prompt_utils.build_query_prompt.return_value = "Mocked RAG prompt"
            
            # Execute the tool
            result = rag_retrieval_tool("What is an F-1 visa?")
            
            # Verify the result structure
            assert isinstance(result, dict)
            assert "response" in result
            assert "references" in result
            assert "documents" in result
            
            # Verify the content
            assert result["response"] == "This is a test immigration response about F-1 visas."
            assert len(result["references"]) == 3
            assert len(result["documents"]) == 3
            assert result["references"][0] == "Immigration Document 1"

    def test_rag_tool_empty_query(self):
        """Test RAG tool with empty query"""
        
        with patch('backend.code.tools.rag_tool.get_cached_chroma_collection') as mock_cached_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs, \
             patch('backend.code.tools.rag_tool.load_config') as mock_load_config, \
             patch('backend.code.tools.rag_tool.get_llm') as mock_get_llm, \
             patch('backend.code.tools.rag_tool.rag_prompt_utils') as mock_prompt_utils:
            
            mock_db_instance = MagicMock()
            mock_collection = MagicMock()
            mock_cached_collection.return_value = (mock_db_instance, mock_collection)
            mock_get_docs.return_value = []
            mock_load_config.return_value = {"llm": "gemini-2.5-flash"}
            
            # Mock LLM response for empty query
            mock_llm = MagicMock()
            mock_llm_response = MagicMock()
            mock_llm_response.content = "I need more specific information to help you."
            mock_llm.invoke.return_value = mock_llm_response
            mock_get_llm.return_value = mock_llm
            
            mock_prompt_utils.build_query_prompt.return_value = "Mocked RAG prompt"
            
            result = rag_retrieval_tool("")
            
            assert result["response"] == "I need more specific information to help you."
            assert result["references"] == []
            assert result["documents"] == []

    def test_rag_tool_database_initialization_error(self):
        """Test RAG tool handling database initialization failure"""
        
        with patch('backend.code.tools.rag_tool.get_cached_chroma_collection') as mock_cached_collection, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection:
            
            # Make cached collection fail, triggering fallback
            mock_cached_collection.return_value = (None, None)
            mock_init_db.side_effect = Exception("Database connection failed")
            
            result = rag_retrieval_tool("What is an F-1 visa?")
            
            assert isinstance(result, dict)
            assert "Error during RAG processing" in result["response"]
            assert result["references"] == []
            assert result["documents"] == []

    def test_rag_tool_error_handling(self):
        """Test RAG tool general error handling"""
        
        with patch('backend.code.tools.rag_tool.get_cached_chroma_collection') as mock_cached_collection:
            mock_cached_collection.side_effect = Exception("Unexpected error")
            
            result = rag_retrieval_tool("What is an F-1 visa?")
            
            assert isinstance(result, dict)
            assert "Error during RAG processing" in result["response"]
            assert result["references"] == []
            assert result["documents"] == []

    def test_rag_tool_return_type_validation(self):
        """Test that RAG tool always returns correct response format"""
        
        with patch('backend.code.tools.rag_tool.get_cached_chroma_collection') as mock_cached_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs, \
             patch('backend.code.tools.rag_tool.load_config') as mock_load_config, \
             patch('backend.code.tools.rag_tool.get_llm') as mock_get_llm, \
             patch('backend.code.tools.rag_tool.rag_prompt_utils') as mock_prompt_utils:
            
            # Setup minimal working mocks
            mock_cached_collection.return_value = (MagicMock(), MagicMock())
            mock_get_docs.return_value = ["Test document"]
            mock_load_config.return_value = {"llm": "gemini-2.5-flash"}
            
            mock_llm = MagicMock()
            mock_llm_response = MagicMock()
            mock_llm_response.content = "Test response"
            mock_llm.invoke.return_value = mock_llm_response
            mock_get_llm.return_value = mock_llm
            mock_prompt_utils.build_query_prompt.return_value = "Test prompt"
            
            result = rag_retrieval_tool("Test query")
            
            # Validate response structure
            assert isinstance(result, dict)
            required_keys = ["response", "references", "documents"]
            for key in required_keys:
                assert key in result, f"Missing required key: {key}"
                
            assert isinstance(result["response"], str)
            assert isinstance(result["references"], list)
            assert isinstance(result["documents"], list)

    def test_rag_tool_empty_string_query(self):
        """Test RAG tool with empty string query input"""
        result = rag_retrieval_tool("")
        
        assert isinstance(result, dict)
        # Empty string should be handled gracefully
        assert "response" in result
        assert "references" in result  
        assert "documents" in result


class TestRagToolIntegration:
    """Integration tests for RAG tool"""

    def test_rag_tool_imports(self):
        """Test that RAG tool can be imported successfully"""
        from backend.code.tools.rag_tool import rag_retrieval_tool
        assert callable(rag_retrieval_tool)

    def test_rag_tool_is_langchain_tool(self):
        """Test that RAG tool has proper tool decoration"""
        from backend.code.tools.rag_tool import rag_retrieval_tool
        
        # Check if it has the tool attributes
        assert hasattr(rag_retrieval_tool, 'name')
        assert hasattr(rag_retrieval_tool, 'description')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
