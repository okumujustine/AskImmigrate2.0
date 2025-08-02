"""
Comprehensive Input Validation Tests
Author: Hillary Arinda
Purpose: Security-focused testing for input validation and sanitization

Tests cover:
1. Input validation and sanitization
2. Security measures and injection prevention
3. Rate limiting
4. Immigration-specific content validation
5. Edge cases and error handling
"""

import pytest
from unittest.mock import patch, Mock
import time
from typing import List, Dict

# Import our validation module
from backend.code.input_validation import (
    InputValidator, 
    ValidationResult,
    RateLimiter,
    validate_immigration_query,
    check_rate_limit,
    input_validator,
    rate_limiter
)

class TestInputValidatorCore:
    """Core input validation functionality tests."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_validator_initialization(self):
        """Test that InputValidator initializes correctly."""
        validator = InputValidator()
        
        assert isinstance(validator, InputValidator)
        assert validator.MAX_QUERY_LENGTH == 5000
        assert validator.MIN_QUERY_LENGTH == 3
        assert len(validator.compiled_injection_patterns) > 0
        assert len(validator.compiled_sql_patterns) > 0
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_valid_immigration_query(self):
        """Test validation of a normal immigration query."""
        validator = InputValidator()
        
        query = "How do I change from F-1 to H-1B status?"
        result = validator.validate_query(query, "test-session-123")
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid == True
        assert result.sanitized_input == query  # Should be unchanged for clean input
        assert len(result.errors) == 0
        assert result.original_length == len(query)
        assert result.sanitized_length == len(query)
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_empty_query_validation(self):
        """Test that empty queries are rejected."""
        validator = InputValidator()
        
        # Test empty string
        result = validator.validate_query("", "test-session")
        assert result.is_valid == False
        assert "Query cannot be empty" in result.errors
        
        # Test None input
        result = validator.validate_query(None, "test-session")
        assert result.is_valid == False
        assert "Query cannot be empty" in result.errors
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_query_length_validation(self):
        """Test query length limits."""
        validator = InputValidator()
        
        # Test too short
        short_query = "Hi"
        result = validator.validate_query(short_query, "test-session")
        assert result.is_valid == False
        assert any("too short" in error for error in result.errors)
        
        # Test too long
        long_query = "A" * (validator.MAX_QUERY_LENGTH + 100)
        result = validator.validate_query(long_query, "test-session")
        assert result.is_valid == False
        assert any("too long" in error for error in result.errors)
        assert any("Query truncated" in warning for warning in result.warnings)
        assert result.sanitized_length <= validator.MAX_QUERY_LENGTH
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_non_string_input_validation(self):
        """Test that non-string inputs are rejected."""
        validator = InputValidator()
        
        # Test integer input
        result = validator.validate_query(12345, "test-session")
        assert result.is_valid == False
        assert any("Query must be a string" in error for error in result.errors)
        
        # Test list input
        result = validator.validate_query(["test", "query"], "test-session")
        assert result.is_valid == False
        assert any("Query must be a string" in error for error in result.errors)

class TestSecurityValidation:
    """Security-focused validation tests."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_xss_injection_detection(self):
        """Test detection of XSS injection attempts."""
        validator = InputValidator()
        
        xss_attempts = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<object data='javascript:alert(1)'></object>",
            "<embed src='javascript:alert(1)'></embed>",
            "What is H-1B? <script>steal_data()</script>",
            "onclick=alert('xss') Tell me about green cards"
        ]
        
        for xss_attempt in xss_attempts:
            result = validator.validate_query(xss_attempt, "test-session")
            assert result.is_valid == False
            assert any("XSS" in error or "injection" in error for error in result.errors), \
                f"Failed to detect XSS in: {xss_attempt}"
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_sql_injection_detection(self):
        """Test detection of SQL injection attempts."""
        validator = InputValidator()
        
        sql_attempts = [
            "How do I apply' OR 1=1 --",
            "Tell me about UNION SELECT * FROM users",
            "What is H-1B'; DROP TABLE applications; --",
            "Green card info' AND 1=1",
            "Immigration OR 1=1",
            "Status AND password='admin'",
            "How do I; DELETE FROM sessions WHERE 1=1"
        ]
        
        for sql_attempt in sql_attempts:
            result = validator.validate_query(sql_attempt, "test-session")
            assert result.is_valid == False
            assert any("SQL" in error or "injection" in error for error in result.errors), \
                f"Failed to detect SQL injection in: {sql_attempt}"
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_suspicious_character_detection(self):
        """Test detection of suspicious character combinations."""
        validator = InputValidator()
        
        suspicious_queries = [
            "What is H-1B status? ${malicious_var}",
            "Tell me about green cards {{template_injection}}",
            "Immigration info <% server_code %>",
            "H-1B process <? php_code ?>",
            "Green card {dangerous_template}",
        ]
        
        for suspicious_query in suspicious_queries:
            result = validator.validate_query(suspicious_query, "test-session")
            assert result.is_valid == False
            assert any("Suspicious characters" in error for error in result.errors), \
                f"Failed to detect suspicious chars in: {suspicious_query}"
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_input_sanitization(self):
        """Test that input is properly sanitized."""
        validator = InputValidator()
        
        # Test HTML escaping
        query_with_html = "What is <b>H-1B</b> status & requirements?"
        result = validator.validate_query(query_with_html, "test-session")
        
        # HTML should be escaped
        assert "&lt;b&gt;" in result.sanitized_input
        assert "&gt;" in result.sanitized_input
        assert "&amp;" in result.sanitized_input
        
        # Test whitespace normalization
        query_with_spaces = "What    is     H-1B     status?"
        result = validator.validate_query(query_with_spaces, "test-session")
        assert "    " not in result.sanitized_input  # Multiple spaces should be normalized
        
        # Test control character removal
        query_with_control = "What is H-1B\x00\x01\x02 status?"
        result = validator.validate_query(query_with_control, "test-session")
        assert "\x00" not in result.sanitized_input
        assert "\x01" not in result.sanitized_input
        assert "\x02" not in result.sanitized_input

class TestSessionIDValidation:
    """Test session ID validation."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_valid_session_id(self):
        """Test validation of valid session IDs."""
        validator = InputValidator()
        
        valid_session_ids = [
            "session-123-abc",
            "user_456_789",
            "SESSION123",
            "test-session-2024",
            "abc123def456"
        ]
        
        for session_id in valid_session_ids:
            is_valid, sanitized = validator.validate_session_id(session_id)
            assert is_valid == True
            assert len(sanitized) >= 3
            assert sanitized.replace('-', '').replace('_', '').isalnum()
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_invalid_session_id(self):
        """Test rejection of invalid session IDs."""
        validator = InputValidator()
        
        invalid_session_ids = [
            "",  # Empty
            None,  # None
            "ab",  # Too short
            "session with spaces",  # Spaces
            "session@special!chars",  # Special characters
            "a" * 150,  # Too long
            "session<script>",  # HTML
            123,  # Non-string
        ]
        
        for session_id in invalid_session_ids:
            is_valid, sanitized = validator.validate_session_id(session_id)
            assert is_valid == False

class TestContentValidation:
    """Test immigration-specific content validation."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_immigration_content_recognition(self):
        """Test recognition of immigration-related content."""
        validator = InputValidator()
        
        immigration_queries = [
            "How do I apply for an H-1B visa?",
            "What are the green card requirements?",
            "USCIS processing times for I-485",
            "Immigration status change procedures",
            "Naturalization eligibility requirements"
        ]
        
        for query in immigration_queries:
            result = validator.validate_query(query, "test-session")
            # Should not have "not immigration-related" warning
            assert not any("not be immigration-related" in warning for warning in result.warnings)
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_non_immigration_content_warning(self):
        """Test warning for non-immigration-related content."""
        validator = InputValidator()
        
        non_immigration_queries = [
            "What's the weather like today?",
            "How do I cook pasta?",
            "What are the latest stock prices?",
            "Tell me a joke",
            "How do I fix my car?"
        ]
        
        for query in non_immigration_queries:
            result = validator.validate_query(query, "test-session")
            assert any("not be immigration-related" in warning for warning in result.warnings)
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_excessive_repetition_detection(self):
        """Test detection of excessive word repetition (potential spam)."""
        validator = InputValidator()
        
        # Create query with excessive repetition
        repetitive_query = "immigration " * 50 + "what is the process?"
        result = validator.validate_query(repetitive_query, "test-session")
        
        assert any("repetition" in warning for warning in result.warnings)

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_rate_limiter_initialization(self):
        """Test that RateLimiter initializes correctly."""
        limiter = RateLimiter(max_requests_per_minute=10)
        
        assert limiter.max_requests == 10
        assert isinstance(limiter.requests, dict)
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_rate_limiting_allows_normal_usage(self):
        """Test that rate limiting allows normal usage patterns."""
        limiter = RateLimiter(max_requests_per_minute=5)
        
        session_id = "test-session-rate-1"
        
        # Should allow first few requests
        for i in range(3):
            assert limiter.is_allowed(session_id) == True
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_rate_limiting_blocks_excessive_requests(self):
        """Test that rate limiting blocks excessive requests."""
        limiter = RateLimiter(max_requests_per_minute=3)
        
        session_id = "test-session-rate-2"
        
        # Use up the rate limit
        for i in range(3):
            assert limiter.is_allowed(session_id) == True
        
        # Next request should be blocked
        assert limiter.is_allowed(session_id) == False
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_rate_limiting_per_session(self):
        """Test that rate limiting is per-session."""
        limiter = RateLimiter(max_requests_per_minute=2)
        
        session_1 = "test-session-1"
        session_2 = "test-session-2"
        
        # Each session should have independent limits
        assert limiter.is_allowed(session_1) == True
        assert limiter.is_allowed(session_2) == True
        assert limiter.is_allowed(session_1) == True
        assert limiter.is_allowed(session_2) == True
        
        # Both should now be at limit
        assert limiter.is_allowed(session_1) == False
        assert limiter.is_allowed(session_2) == False
    
    @pytest.mark.unit
    @pytest.mark.security
    @patch('time.time')
    def test_rate_limiting_time_window_reset(self, mock_time):
        """Test that rate limiting resets after time window."""
        limiter = RateLimiter(max_requests_per_minute=2)
        
        # Start at time 0
        mock_time.return_value = 0
        
        session_id = "test-session-time"
        
        # Use up limit
        assert limiter.is_allowed(session_id) == True
        assert limiter.is_allowed(session_id) == True
        assert limiter.is_allowed(session_id) == False  # Blocked
        
        # Move forward 61 seconds (past the 1-minute window)
        mock_time.return_value = 61
        
        # Should be allowed again
        assert limiter.is_allowed(session_id) == True

class TestConvenienceFunctions:
    """Test convenience functions and global instances."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_immigration_query_function(self):
        """Test the convenience validate_immigration_query function."""
        query = "How do I apply for a green card?"
        session_id = "test-session-convenience"
        
        result = validate_immigration_query(query, session_id)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid == True
        assert result.sanitized_input == query
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_check_rate_limit_function(self):
        """Test the convenience check_rate_limit function."""
        session_id = "test-session-rate-limit"
        
        # Should initially be allowed
        assert check_rate_limit(session_id) == True
        
        # Use up rate limit (global rate limiter allows 60 per minute)
        for i in range(60):
            check_rate_limit(session_id)
        
        # Should now be blocked
        assert check_rate_limit(session_id) == False

class TestEdgeCases:
    """Test edge cases and unusual inputs."""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_unicode_handling(self):
        """Test handling of Unicode characters."""
        validator = InputValidator()
        
        unicode_queries = [
            "¿Cómo aplico para una visa H-1B?",  # Spanish
            "如何申请H-1B签证？",  # Chinese
            "Comment puis-je demander un visa H-1B?",  # French
            "Immigration café résumé naïve",  # Accented characters
        ]
        
        for query in unicode_queries:
            result = validator.validate_query(query, "test-session")
            # Should handle unicode without crashing
            assert isinstance(result, ValidationResult)
            assert len(result.sanitized_input) > 0
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_mixed_content_queries(self):
        """Test queries with mixed legitimate and suspicious content."""
        validator = InputValidator()
        
        # Query that contains immigration terms but also suspicious patterns
        mixed_query = "What is H-1B status and <script>alert('test')</script>"
        result = validator.validate_query(mixed_query, "test-session")
        
        # Should be invalid due to script tag
        assert result.is_valid == False
        assert any("injection" in error for error in result.errors)
        
        # But sanitized version should remove the dangerous part
        assert "<script>" not in result.sanitized_input
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_very_long_session_ids(self):
        """Test handling of very long session IDs."""
        validator = InputValidator()
        
        long_session_id = "a" * 200  # Longer than MAX_SESSION_ID_LENGTH
        is_valid, sanitized = validator.validate_session_id(long_session_id)
        
        assert is_valid == False
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_logging_integration(self):
        """Test that validation integrates with logging system."""
        validator = InputValidator()
        
        with patch('backend.code.input_validation.manager_logger') as mock_logger:
            query = "How do I apply for H-1B status?"
            result = validator.validate_query(query, "test-session-logging")
            
            # Verify logging calls were made
            mock_logger.info.assert_any_call(
                "input_validation_started",
                original_length=len(query),
                session_id="test-session-logging"
            )
            
            mock_logger.info.assert_any_call(
                "input_validation_completed",
                is_valid=result.is_valid,
                sanitized_length=len(result.sanitized_input),
                warnings_count=len(result.warnings),
                errors_count=len(result.errors),
                session_id="test-session-logging"
            )

class TestPerformance:
    """Test performance characteristics of validation."""
    
    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.performance
    def test_validation_performance(self):
        """Test that validation completes in reasonable time."""
        validator = InputValidator()
        
        # Test with reasonably long but valid query
        long_query = "How do I change from F-1 to H-1B status? " * 50  # Repeat 50 times
        
        start_time = time.time()
        result = validator.validate_query(long_query, "test-session-perf")
        end_time = time.time()
        
        # Should complete within 1 second
        assert (end_time - start_time) < 1.0
        assert isinstance(result, ValidationResult)
    
    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.performance
    def test_rate_limiter_performance(self):
        """Test that rate limiter performs well with many sessions."""
        limiter = RateLimiter(max_requests_per_minute=10)
        
        start_time = time.time()
        
        # Test with 100 different sessions
        for i in range(100):
            session_id = f"test-session-{i}"
            limiter.is_allowed(session_id)
        
        end_time = time.time()
        
        # Should handle 100 sessions quickly
        assert (end_time - start_time) < 0.5

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
