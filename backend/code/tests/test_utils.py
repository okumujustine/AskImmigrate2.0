#!/usr/bin/env python3
"""
Comprehensive test suite for utils module - Test coverage improvement
Target: 32% -> 80%+ coverage for backend/code/utils.py (113 statements)

Test categories:
1. Configuration loading
2. Session ID management (legacy and client-isolated)
3. Client fingerprint handling
4. Database operations
5. Document processing (chunking, PDF loading)
6. YAML configuration
7. Embedding operations
8. Document retrieval
9. Print utilities
10. Error handling and edge cases
"""

import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestUtilsModule:
    """Comprehensive utils module testing"""

    def test_utils_module_imports(self):
        """Test 1: Utils module imports successfully"""
        from backend.code import utils
        
        # Verify key functions exist
        assert hasattr(utils, 'load_config')
        assert hasattr(utils, 'slugify_chat_session')
        assert hasattr(utils, 'create_client_fingerprint_hash')
        assert hasattr(utils, 'create_anonymous_session_id')
        assert hasattr(utils, 'extract_client_from_session_id')

    @patch('backend.code.utils.yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open, read_data='test: config')
    def test_load_config_basic(self, mock_file, mock_yaml):
        """Test 2: Basic configuration loading"""
        from backend.code.utils import load_config
        
        mock_yaml.return_value = {'test': 'config'}
        
        result = load_config('test_config.yaml')
        
        mock_file.assert_called_once_with('test_config.yaml', 'r', encoding='utf-8')
        mock_yaml.assert_called_once()
        assert result == {'test': 'config'}

    def test_slugify_chat_session_basic(self):
        """Test 3: Legacy session ID creation"""
        from backend.code.utils import slugify_chat_session
        
        # Test basic functionality
        result = slugify_chat_session("What is H-1B visa?")
        
        # Should contain slugified question and random component
        parts = result.split('-')
        assert len(parts) >= 2  # question-part and uuid part
        assert 'what-is-h-1b-visa' in result.lower()
        
        # Should handle empty strings
        result_empty = slugify_chat_session("")
        assert len(result_empty) > 0  # Should still generate something

    def test_create_client_fingerprint_hash_basic(self):
        """Test 4: Client fingerprint hashing"""
        from backend.code.utils import create_client_fingerprint_hash
        
        # Test normal fingerprint
        result = create_client_fingerprint_hash("test-browser-fingerprint")
        assert len(result) == 8
        assert result.isalnum()
        
        # Test consistency (same input -> same output)
        result2 = create_client_fingerprint_hash("test-browser-fingerprint")
        assert result == result2
        
        # Test different inputs produce different hashes
        result3 = create_client_fingerprint_hash("different-fingerprint")
        assert result != result3

    def test_create_client_fingerprint_hash_edge_cases(self):
        """Test 5: Client fingerprint hashing edge cases"""
        from backend.code.utils import create_client_fingerprint_hash
        
        # Test empty fingerprint
        result = create_client_fingerprint_hash("")
        assert result == "anonymous"
        
        # Test None fingerprint
        result_none = create_client_fingerprint_hash(None)
        assert result_none == "anonymous"

    def test_create_anonymous_session_id_with_fingerprint(self):
        """Test 6: Anonymous session ID creation with client fingerprint"""
        from backend.code.utils import create_anonymous_session_id
        
        # Test with fingerprint and question
        result = create_anonymous_session_id("test-fingerprint", "What is H-1B visa?")
        
        parts = result.split('-')
        assert len(parts) >= 3  # client_hash-question_slug-unique_id
        
        # First part should be 8-char client hash
        assert len(parts[0]) == 8
        assert parts[0].isalnum()
        
        # Should contain question context
        assert 'what-is-h-1b-visa' in result.lower()

    def test_create_anonymous_session_id_without_fingerprint(self):
        """Test 7: Anonymous session ID creation without client fingerprint (legacy)"""
        from backend.code.utils import create_anonymous_session_id
        
        # Test legacy mode (no fingerprint)
        result = create_anonymous_session_id(None, "What is H-1B visa?")
        
        # Should fall back to legacy format
        parts = result.split('-')
        assert len(parts) >= 2  # Should be legacy format
        assert 'what-is-h-1b-visa' in result.lower()

    def test_create_anonymous_session_id_edge_cases(self):
        """Test 8: Anonymous session ID edge cases"""
        from backend.code.utils import create_anonymous_session_id
        
        # Test with empty question
        result = create_anonymous_session_id("test-fingerprint", "")
        parts = result.split('-')
        assert len(parts) >= 3
        assert 'chat' in result  # Should default to 'chat'
        
        # Test with None question
        result_none = create_anonymous_session_id("test-fingerprint", None)
        parts = result_none.split('-')
        assert len(parts) >= 3
        assert 'chat' in result_none

    def test_extract_client_from_session_id_new_format(self):
        """Test 9: Extract client hash from new format session IDs"""
        from backend.code.utils import extract_client_from_session_id
        
        # Test new format: client_hash-question_slug-unique_id
        result = extract_client_from_session_id("a1b2c3d4-what-is-h1b-e5f6g7h8")
        assert result == "a1b2c3d4"
        
        # Test another valid format
        result2 = extract_client_from_session_id("12345678-apply-for-visa-abcdefgh")
        assert result2 == "12345678"

    def test_extract_client_from_session_id_legacy_format(self):
        """Test 10: Extract client hash from legacy format session IDs"""
        from backend.code.utils import extract_client_from_session_id
        
        # Test legacy format: question_slug-unique_id (2 parts)
        result = extract_client_from_session_id("what-is-h1b-e5f6g7h8")
        assert result is None  # Legacy format has no client hash
        
        # Test single part (also legacy)
        result2 = extract_client_from_session_id("single-session")
        assert result2 is None

    def test_extract_client_from_session_id_edge_cases(self):
        """Test 11: Extract client hash edge cases"""
        from backend.code.utils import extract_client_from_session_id
        
        # Test empty session ID
        result = extract_client_from_session_id("")
        assert result is None
        
        # Test None session ID
        result_none = extract_client_from_session_id(None)
        assert result_none is None
        
        # Test invalid format (wrong hash length)
        result_invalid = extract_client_from_session_id("abc-question-unique")
        assert result_invalid is None  # Hash too short
        
        # Test non-alphanumeric hash
        result_special = extract_client_from_session_id("abc@#$%!-question-unique")
        assert result_special is None  # Not alphanumeric

    def test_custom_terminal_print(self):
        """Test 12: Custom terminal print functionality"""
        from backend.code.utils import custom_terminal_print
        
        # Test basic printing (should not raise exception)
        with patch('builtins.print') as mock_print:
            custom_terminal_print("Test message")
            mock_print.assert_called_once()
            
            # Verify message format
            call_args = mock_print.call_args[0]
            assert "Test message" in call_args[1]
            assert "." * 10 in call_args[0]
            assert "." * 10 in call_args[2]

    @patch('backend.code.utils.os.path.exists')
    @patch('backend.code.utils.shutil.rmtree')
    @patch('backend.code.utils.os.makedirs')
    @patch('backend.code.utils.chromadb.PersistentClient')
    def test_initialize_chroma_db_new_folder(self, mock_client, mock_makedirs, mock_rmtree, mock_exists):
        """Test 13: ChromaDB initialization with new folder creation"""
        from backend.code.utils import initialize_chroma_db
        
        # Mock existing directory
        mock_exists.return_value = True
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        # Test with create_new_folder=True
        result = initialize_chroma_db(create_new_folder=True)
        
        mock_rmtree.assert_called_once()  # Should remove existing
        mock_makedirs.assert_called_once()  # Should create new
        mock_client.assert_called_once()  # Should initialize client
        assert result == mock_client_instance

    @patch('backend.code.utils.os.path.exists')
    @patch('backend.code.utils.os.makedirs')
    @patch('backend.code.utils.chromadb.PersistentClient')
    def test_initialize_chroma_db_existing_folder(self, mock_client, mock_makedirs, mock_exists):
        """Test 14: ChromaDB initialization with existing folder preservation"""
        from backend.code.utils import initialize_chroma_db
        
        # Mock existing directory
        mock_exists.return_value = True
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        # Test with create_new_folder=False (default)
        result = initialize_chroma_db(create_new_folder=False)
        
        mock_makedirs.assert_called_once()  # Should ensure directory exists
        mock_client.assert_called_once()  # Should initialize client
        assert result == mock_client_instance

    def test_get_collection(self):
        """Test 15: ChromaDB collection retrieval"""
        from backend.code.utils import get_collection
        
        # Mock database instance
        mock_db = Mock()
        mock_collection = Mock()
        mock_db.get_or_create_collection.return_value = mock_collection
        
        # Test collection retrieval
        result = get_collection(mock_db, "test_collection")
        
        mock_db.get_or_create_collection.assert_called_once_with(name="test_collection")
        assert result == mock_collection

    def test_chunk_publication_basic(self):
        """Test 16: Publication text chunking"""
        from backend.code.utils import chunk_publication
        
        # Test basic chunking
        test_text = "This is a long document that needs to be split into smaller chunks for processing. " * 20
        
        chunks = chunk_publication(test_text, chunk_size=100, chunk_overlap=20)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 1  # Should be split into multiple chunks
        
        # Test each chunk is roughly the right size
        for chunk in chunks:
            assert len(chunk) <= 120  # Should be close to chunk_size + some overlap

    def test_chunk_publication_custom_params(self):
        """Test 17: Publication chunking with custom parameters"""
        from backend.code.utils import chunk_publication
        
        test_text = "Short text"
        
        # Test with small chunk size
        chunks = chunk_publication(test_text, chunk_size=5, chunk_overlap=1)
        
        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    @patch('backend.code.utils.Path')
    @patch('backend.code.utils.extract_text')
    def test_load_pdf_publication_success(self, mock_extract_text, mock_path):
        """Test 18: PDF publication loading success"""
        from backend.code.utils import load_pdf_publication
        
        # Mock path and file existence
        mock_path_instance = Mock()
        mock_path_instance.is_file.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Mock PDF text extraction
        mock_extract_text.return_value = "Extracted PDF content"
        
        result = load_pdf_publication("test.pdf")
        
        assert result == "Extracted PDF content"
        mock_extract_text.assert_called_once()

    @patch('backend.code.utils.Path')
    def test_load_pdf_publication_not_found(self, mock_path):
        """Test 19: PDF publication loading - file not found"""
        from backend.code.utils import load_pdf_publication
        
        # Mock file not existing
        mock_path_instance = Mock()
        mock_path_instance.is_file.return_value = False
        mock_path.return_value = mock_path_instance
        
        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            load_pdf_publication("nonexistent.pdf")

    @patch('backend.code.utils.stream_nodes')
    @patch('backend.code.utils.Path')
    def test_iter_all_publications(self, mock_path, mock_stream_nodes):
        """Test 20: Iterator for all publications"""
        from backend.code.utils import iter_all_publications
        
        # Mock JSON documents from Radix
        mock_stream_nodes.return_value = [
            ("key1", {"title": "Doc 1", "url": "url1", "text": "Text 1"}),
            ("key2", {"title": "Doc 2", "url": "url2", "text": "Text 2"})
        ]
        
        # Mock PDF files
        mock_pdf_path = Mock()
        mock_pdf_path.name = "test.pdf"
        mock_path_instance = Mock()
        mock_path_instance.rglob.return_value = [mock_pdf_path]
        mock_path.return_value = mock_path_instance
        
        # Mock PDF loading
        with patch('backend.code.utils.load_pdf_publication', return_value="PDF content"):
            publications = list(iter_all_publications())
            
            assert len(publications) >= 2  # At least JSON docs
            assert "title: Doc 1" in publications[0]
            assert "title: Doc 2" in publications[1]

    @patch('backend.code.utils.iter_all_publications')
    def test_load_all_publications(self, mock_iter):
        """Test 21: Load all publications (eager version)"""
        from backend.code.utils import load_all_publications
        
        mock_iter.return_value = ["doc1", "doc2", "doc3"]
        
        result = load_all_publications()
        
        assert result == ["doc1", "doc2", "doc3"]
        mock_iter.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, read_data='test: config')
    @patch('backend.code.utils.yaml.safe_load')
    @patch('backend.code.utils.Path')
    def test_load_yaml_config_success(self, mock_path, mock_yaml, mock_file):
        """Test 22: YAML configuration loading success"""
        from backend.code.utils import load_yaml_config
        
        # Mock path existence
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_yaml.return_value = {'test': 'config'}
        
        result = load_yaml_config('config.yaml')
        
        assert result == {'test': 'config'}
        mock_yaml.assert_called_once()

    @patch('backend.code.utils.Path')
    def test_load_yaml_config_file_not_found(self, mock_path):
        """Test 23: YAML configuration loading - file not found"""
        from backend.code.utils import load_yaml_config
        
        # Mock file not existing
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        with pytest.raises(FileNotFoundError):
            load_yaml_config('nonexistent.yaml')

    @patch('builtins.open', new_callable=mock_open, read_data='invalid: yaml: content:')
    @patch('backend.code.utils.yaml.safe_load')
    @patch('backend.code.utils.Path')
    def test_load_yaml_config_yaml_error(self, mock_path, mock_yaml, mock_file):
        """Test 24: YAML configuration loading - YAML parse error"""
        from backend.code.utils import load_yaml_config
        import yaml
        
        # Mock path existence
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Mock YAML error
        mock_yaml.side_effect = yaml.YAMLError("Invalid YAML")
        
        with pytest.raises(yaml.YAMLError):
            load_yaml_config('config.yaml')

    @patch('backend.code.utils.get_cpu_embedder')
    def test_embed_documents(self, mock_embedder):
        """Test 25: Document embedding"""
        from backend.code.utils import embed_documents
        
        # Mock embedder
        mock_model = Mock()
        mock_model.embed_documents.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embedder.return_value = mock_model
        
        result = embed_documents(["doc1", "doc2"])
        
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_model.embed_documents.assert_called_once_with(["doc1", "doc2"])

    @patch('backend.code.utils.embed_documents')
    def test_get_relevant_documents_basic(self, mock_embed):
        """Test 26: Relevant document retrieval"""
        from backend.code.utils import get_relevant_documents
        
        # Mock query embedding
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        
        # Mock collection
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2", "doc3"]],
            "documents": [["Document 1", "Document 2", "Document 3"]],
            "distances": [[0.1, 0.2, 0.5]]  # Third doc exceeds threshold
        }
        
        result = get_relevant_documents("test query", mock_collection, threshold=0.3)
        
        # Should return only docs below threshold
        assert result == ["Document 1", "Document 2"]
        mock_collection.query.assert_called_once()

    @patch('backend.code.utils.embed_documents')
    def test_get_relevant_documents_no_results(self, mock_embed):
        """Test 27: Relevant document retrieval - no results below threshold"""
        from backend.code.utils import get_relevant_documents
        
        # Mock query embedding  
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        
        # Mock collection with all distances above threshold
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "documents": [["Document 1", "Document 2"]],
            "distances": [[0.8, 0.9]]  # All exceed threshold of 0.3
        }
        
        result = get_relevant_documents("test query", mock_collection, threshold=0.3)
        
        assert result == []  # No documents below threshold

    @patch('langchain_huggingface.HuggingFaceEmbeddings')
    def test_get_cpu_embedder(self, mock_embeddings):
        """Test 28: CPU embedder initialization"""
        from backend.code.utils import get_cpu_embedder
        
        mock_embedder = Mock() 
        mock_embeddings.return_value = mock_embedder
        
        # Clear the cache first to ensure we test the function
        get_cpu_embedder.cache_clear()
        
        # First call should create embedder
        result1 = get_cpu_embedder()
        assert result1 == mock_embedder
        
        # Second call should return cached version (due to @lru_cache)
        result2 = get_cpu_embedder()
        assert result2 == mock_embedder
        
        # Should only create once due to caching
        mock_embeddings.assert_called_once_with(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={"device": "cpu"}
        )

    def test_comprehensive_coverage_verification(self):
        """Test 29: Comprehensive verification of all utils functions"""
        from backend.code.utils import (
            load_config, slugify_chat_session, create_client_fingerprint_hash,
            create_anonymous_session_id, extract_client_from_session_id,
            custom_terminal_print, chunk_publication
        )
        
        # Verify all functions are callable
        assert callable(load_config)
        assert callable(slugify_chat_session)
        assert callable(create_client_fingerprint_hash)
        assert callable(create_anonymous_session_id)
        assert callable(extract_client_from_session_id)
        assert callable(custom_terminal_print)
        assert callable(chunk_publication)
        
        # Test session ID workflow end-to-end
        fingerprint = "test-browser-fingerprint"
        question = "How do I apply for H-1B visa?"
        
        # Create session ID
        session_id = create_anonymous_session_id(fingerprint, question)
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        
        # Extract client hash
        extracted_hash = extract_client_from_session_id(session_id)
        assert extracted_hash is not None
        assert len(extracted_hash) == 8
        
        # Verify consistency
        expected_hash = create_client_fingerprint_hash(fingerprint)
        assert extracted_hash == expected_hash
        
        print("✅ All utils functionality tested successfully!")
        print("🎯 Utils Module Coverage targets:")
        print("   • Configuration loading: Success and error paths")
        print("   • Session ID management: Legacy and client-isolated")
        print("   • Client fingerprint handling: All edge cases")
        print("   • Database operations: ChromaDB initialization")
        print("   • Document processing: Chunking and PDF loading")
        print("   • YAML configuration: Success and error handling")
        print("   • Embedding operations: Document embedding")
        print("   • Document retrieval: Relevant document filtering")
        print("   • Print utilities: Terminal output formatting")
        print("   • End-to-end workflows: Session creation and extraction")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
