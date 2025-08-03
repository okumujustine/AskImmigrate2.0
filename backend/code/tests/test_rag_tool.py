#!/usr/bin/env python3
"""
Comprehensive test suite for the RAG Retrieval Tool
Tests cover functionality, error handling, integration points, and edge cases.

Place this file as: backend/code/tests/test_rag_tool.py
Run directly with: python backend/code/tests/test_rag_tool.py
Or with pytest: python -m pytest backend/code/tests/test_rag_tool.py -v
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path (tests are in backend/code/tests/)
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock, Mock

try:
    from backend.code.tools.rag_tool import rag_retrieval_tool
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"📁 Test file location: {__file__}")
    print(f"📁 Project root: {project_root}")
    print(f"📁 Current working directory: {os.getcwd()}")
    raise


class TestRagRetrievalTool:
    """Test suite for the RAG retrieval tool"""

    def test_rag_tool_basic_functionality(self):
        """Test basic RAG tool functionality with mocked dependencies"""
        
        # Mock all the dependencies
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            # Setup mock returns
            mock_slugify.return_value = "test-session-123"
            mock_chat.return_value = "This is a test immigration response about F-1 visas."
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = [
                "Document 1: F-1 visa requirements...",
                "Document 2: Student visa guidelines...",
                "Document 3: Immigration procedures..."
            ]
            
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
            
            # Verify function calls
            mock_slugify.assert_called_once_with("What is an F-1 visa?")
            mock_chat.assert_called_once_with(session_id="test-session-123", question="What is an F-1 visa?")
            mock_init_db.assert_called_once()
            mock_get_collection.assert_called_once_with(mock_db_instance, collection_name="publications")
            mock_get_docs.assert_called_once_with(
                query="What is an F-1 visa?",
                collection=mock_collection,
                n_results=5,
                threshold=0.5
            )

    def test_rag_tool_empty_query(self):
        """Test RAG tool with empty query"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_slugify.return_value = "empty-query-123"
            mock_chat.return_value = "I need more specific information to help you."
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = []
            
            result = rag_retrieval_tool("")
            
            assert result["response"] == "I need more specific information to help you."
            assert result["references"] == []
            assert result["documents"] == []

    def test_rag_tool_no_documents_found(self):
        """Test RAG tool when no relevant documents are found"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_slugify.return_value = "no-docs-session-123"
            mock_chat.return_value = "I couldn't find specific information about that topic."
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = []  # No documents found
            
            result = rag_retrieval_tool("What is a very rare visa type?")
            
            assert result["response"] == "I couldn't find specific information about that topic."
            assert result["references"] == []
            assert result["documents"] == []

    def test_rag_tool_maximum_documents(self):
        """Test RAG tool with maximum number of documents"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_slugify.return_value = "max-docs-session-123"
            mock_chat.return_value = "Comprehensive response about immigration."
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            # Return more than 5 documents to test limiting
            mock_get_docs.return_value = [f"Document {i}: Content..." for i in range(1, 8)]
            
            result = rag_retrieval_tool("Comprehensive immigration question")
            
            # Should limit references to 5 even if more documents returned
            assert len(result["references"]) == 5
            assert len(result["documents"]) == 7  # Original documents not limited
            assert result["references"] == [f"Immigration Document {i}" for i in range(1, 6)]

    def test_rag_tool_chat_logic_error(self):
        """Test RAG tool when chat logic throws an exception"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_slugify.return_value = "error-session-123"
            mock_chat.side_effect = Exception("Chat service unavailable")
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = ["Document 1"]
            
            result = rag_retrieval_tool("Test query")
            
            assert "Error during RAG processing" in result["response"]
            assert "Chat service unavailable" in result["response"]
            assert result["references"] == []
            assert result["documents"] == []

    def test_rag_tool_database_initialization_error(self):
        """Test RAG tool when database initialization fails"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db:
            
            mock_slugify.return_value = "db-error-session-123"
            mock_chat.return_value = "Chat response"
            mock_init_db.side_effect = Exception("Database connection failed")
            
            result = rag_retrieval_tool("Test query")
            
            assert "Error during RAG processing" in result["response"]
            assert "Database connection failed" in result["response"]
            assert result["references"] == []
            assert result["documents"] == []

    def test_rag_tool_document_retrieval_error(self):
        """Test RAG tool when document retrieval fails"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_slugify.return_value = "doc-error-session-123"
            mock_chat.return_value = "Chat response"
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.side_effect = Exception("Document retrieval failed")
            
            result = rag_retrieval_tool("Test query")
            
            assert "Error during RAG processing" in result["response"]
            assert "Document retrieval failed" in result["response"]
            assert result["references"] == []
            assert result["documents"] == []

    def test_rag_tool_special_characters_in_query(self):
        """Test RAG tool with special characters in query"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            special_query = "What is an H-1B visa? (Including fees & requirements)"
            
            mock_slugify.return_value = "special-chars-session-123"
            mock_chat.return_value = "Response about H-1B visa with fees and requirements."
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = ["H-1B document"]
            
            result = rag_retrieval_tool(special_query)
            
            assert result["response"] == "Response about H-1B visa with fees and requirements."
            mock_chat.assert_called_once_with(session_id="special-chars-session-123", question=special_query)

    def test_rag_tool_long_query(self):
        """Test RAG tool with very long query"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            long_query = "I am currently on an F-1 student visa and I want to know about all the options available for transitioning to a work visa like H-1B, including the timeline, requirements, fees, and whether I can apply for Optional Practical Training (OPT) first before applying for H-1B, and what happens if my H-1B application is denied while I'm on OPT status?"
            
            mock_slugify.return_value = "long-query-session-123"
            mock_chat.return_value = "Detailed response about F-1 to H-1B transition."
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = ["F-1 transition document", "H-1B requirements", "OPT guidelines"]
            
            result = rag_retrieval_tool(long_query)
            
            assert result["response"] == "Detailed response about F-1 to H-1B transition."
            assert len(result["documents"]) == 3
            mock_chat.assert_called_once_with(session_id="long-query-session-123", question=long_query)

    def test_rag_tool_unicode_query(self):
        """Test RAG tool with unicode characters in query"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            unicode_query = "¿Qué es una visa de estudiante? 学生签证是什么？"
            
            mock_slugify.return_value = "unicode-session-123"
            mock_chat.return_value = "Response about student visas."
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = ["Student visa document"]
            
            result = rag_retrieval_tool(unicode_query)
            
            assert result["response"] == "Response about student visas."
            mock_chat.assert_called_once_with(session_id="unicode-session-123", question=unicode_query)

    def test_rag_tool_parameter_passing(self):
        """Test that RAG tool passes correct parameters to underlying functions"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            test_query = "Test immigration query"
            
            mock_slugify.return_value = "param-test-session-123"
            mock_chat.return_value = "Test response"
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = ["Test document"]
            
            result = rag_retrieval_tool(test_query)
            
            # Verify exact parameters passed to get_relevant_documents
            mock_get_docs.assert_called_once_with(
                query=test_query,
                collection=mock_collection,
                n_results=5,
                threshold=0.5
            )
            
            # Verify exact parameters passed to get_collection
            mock_get_collection.assert_called_once_with(
                mock_db_instance, 
                collection_name="publications"
            )

    def test_rag_tool_return_type_validation(self):
        """Test that RAG tool returns the correct data types"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_slugify.return_value = "type-test-session-123"
            mock_chat.return_value = "Test response"
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = ["Doc1", "Doc2"]
            
            result = rag_retrieval_tool("Test query")
            
            # Type validation
            assert isinstance(result, dict)
            assert isinstance(result["response"], str)
            assert isinstance(result["references"], list)
            assert isinstance(result["documents"], list)
            
            # Content validation
            for ref in result["references"]:
                assert isinstance(ref, str)
                assert ref.startswith("Immigration Document")
            
            for doc in result["documents"]:
                assert isinstance(doc, str)


class TestRagToolIntegration:
    """Integration tests for RAG tool with real dependencies (if available)"""
    
    @pytest.mark.integration
    def test_rag_tool_with_real_slugify(self):
        """Test RAG tool with real slugify function"""
        
        with patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_chat.return_value = "Test response"
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = ["Test document"]
            
            # Don't mock slugify_chat_session to test real implementation
            result = rag_retrieval_tool("What is an F-1 visa?")
            
            # Verify result structure is still correct
            assert isinstance(result, dict)
            assert "response" in result
            assert "references" in result
            assert "documents" in result
            
            # Verify chat was called with a real session ID
            chat_call_args = mock_chat.call_args
            assert chat_call_args[1]["question"] == "What is an F-1 visa?"
            assert isinstance(chat_call_args[1]["session_id"], str)
            assert len(chat_call_args[1]["session_id"]) > 0


class TestRagToolEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_rag_tool_none_query(self):
        """Test RAG tool with None as query"""
        
        # This should raise an exception or handle gracefully
        with pytest.raises(Exception):
            rag_retrieval_tool(None)
    
    def test_rag_tool_numeric_query(self):
        """Test RAG tool with numeric query"""
        
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_slugify.return_value = "numeric-session-123"
            mock_chat.return_value = "Response to numeric query"
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = []
            
            # Should handle numeric input by converting to string
            result = rag_retrieval_tool("12345")
            
            assert result["response"] == "Response to numeric query"
            mock_chat.assert_called_once_with(session_id="numeric-session-123", question="12345")


# Pytest fixtures for common test data
@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return [
        "Document about F-1 student visas and requirements",
        "Document about H-1B work visas and application process", 
        "Document about green card applications and procedures",
        "Document about OPT and STEM extension guidelines",
        "Document about immigration fees and payment methods"
    ]

@pytest.fixture
def sample_rag_response():
    """Sample RAG response for testing"""
    return """
    Based on the immigration documents, an F-1 visa is a non-immigrant student visa 
    for academic students. Key requirements include:
    
    1. Acceptance at a SEVP-approved school
    2. Proof of financial support
    3. Intent to return to home country
    4. English proficiency
    
    The F-1 visa allows for Optional Practical Training (OPT) after graduation.
    """


def run_simple_tests():
    """Run a subset of tests without pytest for direct execution"""
    print("\n" + "="*60)
    print("🧪 Running Simple RAG Tool Tests")
    print("="*60)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Basic functionality
    print("\n📋 Test 1: Basic RAG tool functionality")
    try:
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            # Setup mocks
            mock_slugify.return_value = "test-session-123"
            mock_chat.return_value = "This is a test immigration response about F-1 visas."
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = [
                "Document 1: F-1 visa requirements...",
                "Document 2: Student visa guidelines...",
                "Document 3: Immigration procedures..."
            ]
            
            # Execute the tool
            result = rag_retrieval_tool("What is an F-1 visa?")
            
            # Verify the result
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "response" in result, "Result should have 'response' key"
            assert "references" in result, "Result should have 'references' key"
            assert "documents" in result, "Result should have 'documents' key"
            assert result["response"] == "This is a test immigration response about F-1 visas."
            assert len(result["references"]) == 3
            assert len(result["documents"]) == 3
            
            print("   ✅ All assertions passed")
            tests_passed += 1
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        tests_failed += 1
    
    # Test 2: Error handling
    print("\n📋 Test 2: Error handling")
    try:
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat:
            
            mock_slugify.return_value = "error-session-123"
            mock_chat.side_effect = Exception("Chat service unavailable")
            
            result = rag_retrieval_tool("Test query")
            
            assert "Error during RAG processing" in result["response"]
            assert "Chat service unavailable" in result["response"]
            assert result["references"] == []
            assert result["documents"] == []
            
            print("   ✅ Error handling works correctly")
            tests_passed += 1
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        tests_failed += 1
    
    # Test 3: Empty query
    print("\n📋 Test 3: Empty query handling")
    try:
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_slugify.return_value = "empty-query-123"
            mock_chat.return_value = "I need more specific information to help you."
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = []
            
            result = rag_retrieval_tool("")
            
            assert result["response"] == "I need more specific information to help you."
            assert result["references"] == []
            assert result["documents"] == []
            
            print("   ✅ Empty query handled correctly")
            tests_passed += 1
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        tests_failed += 1
    
    # Test 4: Return type validation
    print("\n📋 Test 4: Return type validation")
    try:
        with patch('backend.code.tools.rag_tool.slugify_chat_session') as mock_slugify, \
             patch('backend.code.tools.rag_tool.chat') as mock_chat, \
             patch('backend.code.tools.rag_tool.initialize_chroma_db') as mock_init_db, \
             patch('backend.code.tools.rag_tool.get_collection') as mock_get_collection, \
             patch('backend.code.tools.rag_tool.get_relevant_documents') as mock_get_docs:
            
            mock_slugify.return_value = "type-test-session-123"
            mock_chat.return_value = "Test response"
            mock_db_instance = MagicMock()
            mock_init_db.return_value = mock_db_instance
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_get_docs.return_value = ["Doc1", "Doc2"]
            
            result = rag_retrieval_tool("Test query")
            
            # Type validation
            assert isinstance(result, dict)
            assert isinstance(result["response"], str)
            assert isinstance(result["references"], list)
            assert isinstance(result["documents"], list)
            
            # Content validation
            for ref in result["references"]:
                assert isinstance(ref, str)
                assert ref.startswith("Immigration Document")
            
            for doc in result["documents"]:
                assert isinstance(doc, str)
            
            print("   ✅ All return types are correct")
            tests_passed += 1
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "="*60)
    print(f"📊 Test Results:")
    print(f"   ✅ Passed: {tests_passed}")
    print(f"   ❌ Failed: {tests_failed}")
    print(f"   📈 Success Rate: {tests_passed}/{tests_passed + tests_failed}")
    
    if tests_failed == 0:
        print("\n🎉 Tests passed!")
        return True
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed!")
        return False


if __name__ == "__main__":
    print("🚀 RAG Tool Test Suite")
    print("="*60)
    
    # Check if we should run with pytest or simple tests
    if len(sys.argv) > 1 and sys.argv[1] == "pytest":
        print("Running with pytest...")
        pytest.main([__file__, "-v"])
    else:
        success = run_simple_tests()
        sys.exit(0 if success else 1)