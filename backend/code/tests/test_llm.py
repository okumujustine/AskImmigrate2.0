#!/usr/bin/env python3
"""
Comprehensive test suite for llm module - Test coverage improvement
Target: 77% -> 100% coverage for backend/code/llm.py (13 statements, 3 missing)

Test categories:
1. LLM factory function testing with different models
2. Parameter validation and error handling 
3. Environment variable and configuration handling
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestLLMModule:
    """Comprehensive llm module testing"""

    def test_get_llm_gpt4o_mini(self):
        """Test 1: Get GPT-4o-mini model with default temperature"""
        
        with patch('backend.code.llm.ChatOpenAI') as mock_openai:
            mock_instance = MagicMock()
            mock_openai.return_value = mock_instance
            
            from backend.code.llm import get_llm
            
            result = get_llm("gpt-4o-mini")
            
            # Verify ChatOpenAI was called with correct parameters
            mock_openai.assert_called_once_with(model="gpt-4o-mini", temperature=0.2)
            assert result == mock_instance

    def test_get_llm_gpt4o_mini_custom_temperature(self):
        """Test 2: Get GPT-4o-mini model with custom temperature"""
        
        with patch('backend.code.llm.ChatOpenAI') as mock_openai:
            mock_instance = MagicMock()
            mock_openai.return_value = mock_instance
            
            from backend.code.llm import get_llm
            
            result = get_llm("gpt-4o-mini", temperature=0.7)
            
            # Verify ChatOpenAI was called with custom temperature
            mock_openai.assert_called_once_with(model="gpt-4o-mini", temperature=0.7)
            assert result == mock_instance

    def test_get_llm_gpt4o(self):
        """Test 3: Get GPT-4o model with default temperature"""
        
        with patch('backend.code.llm.ChatOpenAI') as mock_openai:
            mock_instance = MagicMock()
            mock_openai.return_value = mock_instance
            
            from backend.code.llm import get_llm
            
            result = get_llm("gpt-4o")
            
            # Verify ChatOpenAI was called with correct parameters
            mock_openai.assert_called_once_with(model="gpt-4o", temperature=0.2)
            assert result == mock_instance

    def test_get_llm_gpt4o_custom_temperature(self):
        """Test 4: Get GPT-4o model with custom temperature"""
        
        with patch('backend.code.llm.ChatOpenAI') as mock_openai:
            mock_instance = MagicMock()
            mock_openai.return_value = mock_instance
            
            from backend.code.llm import get_llm
            
            result = get_llm("gpt-4o", temperature=0.9)
            
            # Verify ChatOpenAI was called with custom temperature
            mock_openai.assert_called_once_with(model="gpt-4o", temperature=0.9)
            assert result == mock_instance

    def test_get_llm_llama3(self):
        """Test 5: Get Llama3 model with default temperature"""
        
        with patch('backend.code.llm.ChatGroq') as mock_groq:
            mock_instance = MagicMock()
            mock_groq.return_value = mock_instance
            
            from backend.code.llm import get_llm
            
            result = get_llm("llama3-8b-8192")
            
            # Verify ChatGroq was called with correct parameters
            mock_groq.assert_called_once_with(model="llama3-8b-8192", temperature=0.2)
            assert result == mock_instance

    def test_get_llm_llama3_custom_temperature(self):
        """Test 6: Get Llama3 model with custom temperature"""
        
        with patch('backend.code.llm.ChatGroq') as mock_groq:
            mock_instance = MagicMock()
            mock_groq.return_value = mock_instance
            
            from backend.code.llm import get_llm
            
            result = get_llm("llama3-8b-8192", temperature=0.5)
            
            # Verify ChatGroq was called with custom temperature
            mock_groq.assert_called_once_with(model="llama3-8b-8192", temperature=0.5)
            assert result == mock_instance

    def test_get_llm_unknown_model_raises_error(self):
        """Test 7: Unknown model name raises ValueError"""
        
        from backend.code.llm import get_llm
        
        with pytest.raises(ValueError, match="Unknown model name: unknown-model"):
            get_llm("unknown-model")

    def test_get_llm_empty_model_raises_error(self):
        """Test 8: Empty model name raises ValueError"""
        
        from backend.code.llm import get_llm
        
        with pytest.raises(ValueError, match="Unknown model name: "):
            get_llm("")

    def test_module_imports_and_dotenv_loading(self):
        """Test 9: Module imports and dotenv loading"""
        
        # Since the module might already be imported, we just verify the imports work
        # and that load_dotenv is available in the module
        import backend.code.llm
        
        # Verify the module has the expected functions and imports
        assert hasattr(backend.code.llm, 'get_llm')
        assert hasattr(backend.code.llm, 'ChatOpenAI')
        assert hasattr(backend.code.llm, 'ChatGroq')
        assert hasattr(backend.code.llm, 'BaseChatModel')
        assert hasattr(backend.code.llm, 'load_dotenv')
        
        # Verify load_dotenv was imported (function is available)
        assert callable(backend.code.llm.load_dotenv)

    def test_function_signature_and_type_hints(self):
        """Test 10: Function has correct signature and return type"""
        
        from backend.code.llm import get_llm
        import inspect
        
        # Check function signature
        sig = inspect.signature(get_llm)
        assert len(sig.parameters) == 2
        assert 'model_name' in sig.parameters
        assert 'temperature' in sig.parameters
        
        # Check default temperature value
        assert sig.parameters['temperature'].default == 0.2
        
        # Verify function exists and is callable
        assert callable(get_llm)

    def test_all_model_branches_coverage_verification(self):
        """Test 11: Verify all code branches are tested for complete coverage"""
        
        with patch('backend.code.llm.ChatOpenAI') as mock_openai, \
             patch('backend.code.llm.ChatGroq') as mock_groq:
            
            mock_openai_instance = MagicMock()
            mock_groq_instance = MagicMock() 
            mock_openai.return_value = mock_openai_instance
            mock_groq.return_value = mock_groq_instance
            
            from backend.code.llm import get_llm
            
            # Test all supported models with different temperatures
            models_temps = [
                ("gpt-4o-mini", 0.1),
                ("gpt-4o", 0.3), 
                ("llama3-8b-8192", 0.8)
            ]
            
            for model, temp in models_temps:
                result = get_llm(model, temperature=temp)
                assert result is not None
                
            # Verify all model types were called
            assert mock_openai.call_count == 2  # gpt-4o-mini and gpt-4o
            assert mock_groq.call_count == 1    # llama3-8b-8192
            
            # Test error case
            with pytest.raises(ValueError):
                get_llm("invalid-model")
