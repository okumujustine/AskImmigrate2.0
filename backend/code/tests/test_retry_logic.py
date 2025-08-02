"""
Comprehensive Retry Logic Tests
Author: Hillary Arinda
Purpose: Test retry logic, exponential backoff, and circuit breaker implementations

Tests cover:
1. Retry decorators and configurations
2. Exponential backoff calculations
3. Circuit breaker functionality
4. Error classification and handling
5. Integration with logging system
"""

import pytest
from unittest.mock import Mock, patch, call
import time
from typing import Any

# Import retry logic components
from backend.code.retry_logic import (
    RetryConfig,
    RetryableError,
    LLMRetryableError,
    ToolRetryableError,
    DatabaseRetryableError,
    is_retryable_error,
    calculate_delay,
    retry_with_backoff,
    retry_llm_call,
    retry_tool_call,
    retry_database_operation,
    CircuitBreaker,
    llm_circuit_breaker,
    tool_circuit_breaker,
    wrap_llm_call_with_retry,
    wrap_tool_call_with_retry
)

class TestRetryConfig:
    """Test retry configuration functionality."""
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_retry_config_defaults(self):
        """Test default retry configuration values."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter == True
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_retry_config_custom(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=1.5,
            jitter=False
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter == False

class TestErrorClassification:
    """Test error classification for retry logic."""
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_retryable_error_types(self):
        """Test that specific error types are classified as retryable."""
        # Test explicit retryable error types
        assert is_retryable_error(RetryableError("test")) == True
        assert is_retryable_error(LLMRetryableError("llm error")) == True
        assert is_retryable_error(ToolRetryableError("tool error")) == True
        assert is_retryable_error(DatabaseRetryableError("db error")) == True
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_network_error_classification(self):
        """Test classification of network-related errors."""
        network_errors = [
            ConnectionError("Connection timeout"),
            Exception("Connection refused"),
            Exception("Connection reset"),
            Exception("Network unreachable"),
            Exception("DNS lookup failed"),
            Exception("SSL handshake failed"),
            Exception("Read timeout"),
            Exception("Request timeout")
        ]
        
        for error in network_errors:
            assert is_retryable_error(error) == True
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_api_error_classification(self):
        """Test classification of API-related errors."""
        api_errors = [
            Exception("Rate limit exceeded"),
            Exception("Service unavailable"),
            Exception("Internal server error"),
            Exception("Bad gateway"),
            Exception("Gateway timeout"),
            Exception("Service temporarily unavailable"),
            Exception("Too many requests")
        ]
        
        for error in api_errors:
            assert is_retryable_error(error) == True
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_non_retryable_error_classification(self):
        """Test that certain errors are not classified as retryable."""
        non_retryable_errors = [
            ValueError("Invalid input"),
            TypeError("Wrong type"),
            KeyError("Missing key"),
            Exception("Authentication failed"),
            Exception("Unauthorized access"),
            Exception("Permission denied"),
            Exception("File not found")
        ]
        
        for error in non_retryable_errors:
            assert is_retryable_error(error) == False

class TestBackoffCalculation:
    """Test exponential backoff delay calculations."""
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        # Test progression: 1, 2, 4, 8, 16...
        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0
        assert calculate_delay(3, config) == 8.0
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_max_delay_cap(self):
        """Test that delays are capped at maximum."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False)
        
        # Large attempt number should be capped at max_delay
        delay = calculate_delay(10, config)  # Would be 1024 without cap
        assert delay == 5.0
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_jitter_variation(self):
        """Test that jitter adds variation to delays."""
        config = RetryConfig(base_delay=2.0, exponential_base=2.0, jitter=True)
        
        # Generate multiple delays for attempt=0 (base delay)
        delays = [calculate_delay(0, config) for _ in range(10)]
        
        # Should have variation (not all identical)
        assert len(set(delays)) > 1
        
        # All should be close to expected value (2.0) but with some jitter
        # Jitter is 10% of delay, so for delay=2.0, range is 1.8-2.2
        expected = 2.0
        for delay in delays:
            assert 1.6 <= delay <= 2.4  # Allow 20% range for jitter variation
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_minimum_delay(self):
        """Test that minimum delay is enforced."""
        config = RetryConfig(base_delay=0.01, exponential_base=1.0, jitter=True)
        
        delay = calculate_delay(0, config)
        assert delay >= 0.1  # Minimum 100ms delay

class TestRetryDecorator:
    """Test retry decorator functionality."""
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_successful_function_no_retry(self):
        """Test that successful functions don't trigger retries."""
        config = RetryConfig(max_attempts=3)
        call_count = 0
        
        @retry_with_backoff(config)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        
        assert result == "success"
        assert call_count == 1  # Should only be called once
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_function_succeeds_after_retries(self):
        """Test function that succeeds after some failures."""
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        call_count = 0
        
        @retry_with_backoff(config)
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("Temporary failure")
            return "success"
        
        with patch('time.sleep'):  # Speed up test
            result = eventually_successful_function()
        
        assert result == "success"
        assert call_count == 3  # Should be called 3 times
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_function_fails_after_max_attempts(self):
        """Test function that fails after exhausting retries."""
        config = RetryConfig(max_attempts=2, base_delay=0.1)
        call_count = 0
        
        @retry_with_backoff(config)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise RetryableError("Always fails")
        
        with patch('time.sleep'):  # Speed up test
            with pytest.raises(RetryableError):
                always_failing_function()
        
        assert call_count == 2  # Should be called max_attempts times
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_non_retryable_error_no_retry(self):
        """Test that non-retryable errors don't trigger retries."""
        config = RetryConfig(max_attempts=3)
        call_count = 0
        
        @retry_with_backoff(config)
        def function_with_non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError):
            function_with_non_retryable_error()
        
        assert call_count == 1  # Should only be called once
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_retry_logging(self):
        """Test that retry operations are properly logged."""
        config = RetryConfig(max_attempts=2, base_delay=0.1)
        
        @retry_with_backoff(config, session_id="test-session")
        def failing_function():
            raise RetryableError("Test failure")
        
        with patch('time.sleep'), \
             patch('backend.code.retry_logic.manager_logger') as mock_logger:
            
            with pytest.raises(RetryableError):
                failing_function()
            
            # Verify logging calls
            assert mock_logger.info.call_count >= 1  # Start attempts
            assert mock_logger.warning.call_count >= 1  # Failed attempts
            assert mock_logger.error.call_count == 1  # Final failure

class TestSpecificRetryDecorators:
    """Test specific retry decorators for different use cases."""
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_llm_retry_decorator(self):
        """Test LLM-specific retry decorator."""
        call_count = 0
        
        @retry_llm_call(max_attempts=2, base_delay=0.1)
        def mock_llm_call():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LLMRetryableError("LLM overloaded")
            return "LLM response"
        
        with patch('time.sleep'):
            result = mock_llm_call()
        
        assert result == "LLM response"
        assert call_count == 2
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_tool_retry_decorator(self):
        """Test tool-specific retry decorator."""
        call_count = 0
        
        @retry_tool_call(max_attempts=2, base_delay=0.1)
        def mock_tool_call():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ToolRetryableError("Tool connection failed")
            return "Tool result"
        
        with patch('time.sleep'):
            result = mock_tool_call()
        
        assert result == "Tool result"
        assert call_count == 2
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_database_retry_decorator(self):
        """Test database-specific retry decorator."""
        call_count = 0
        
        @retry_database_operation(max_attempts=2, base_delay=0.1)
        def mock_db_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise DatabaseRetryableError("Connection lost")
            return "DB result"
        
        with patch('time.sleep'):
            result = mock_db_operation()
        
        assert result == "DB result"
        assert call_count == 2

class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed (normal) state."""
        breaker = CircuitBreaker(failure_threshold=3)
        
        def successful_function():
            return "success"
        
        # Should pass through normally
        result = breaker.call(successful_function)
        assert result == "success"
        assert breaker.state == "CLOSED"
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=2)
        call_count = 0
        
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")
        
        # First failure
        with pytest.raises(Exception):
            breaker.call(failing_function)
        assert breaker.state == "CLOSED"
        
        # Second failure - should open circuit
        with pytest.raises(Exception):
            breaker.call(failing_function)
        assert breaker.state == "OPEN"
        assert call_count == 2
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_circuit_breaker_open_state_rejection(self):
        """Test that circuit breaker rejects calls when open."""
        breaker = CircuitBreaker(failure_threshold=1)
        
        def failing_function():
            raise Exception("Failure")
        
        # Trigger circuit to open
        with pytest.raises(Exception):
            breaker.call(failing_function)
        
        assert breaker.state == "OPEN"
        
        # Next call should be rejected without executing function
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            breaker.call(failing_function)
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        def function_that_recovers():
            return "recovered"
        
        def function_that_fails():
            raise Exception("fail")
        
        # Force circuit open
        with pytest.raises(Exception):
            breaker.call(function_that_fails)
        
        assert breaker.state == "OPEN"
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Should transition to half-open and succeed
        result = breaker.call(function_that_recovers)
        assert result == "recovered"
        assert breaker.state == "CLOSED"
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_circuit_breaker_logging(self):
        """Test that circuit breaker operations are logged."""
        breaker = CircuitBreaker(failure_threshold=1)
        
        def function_that_fails():
            raise Exception("test failure")
        
        with patch('backend.code.retry_logic.manager_logger') as mock_logger:
            # Force circuit open
            with pytest.raises(Exception):
                breaker.call(function_that_fails)
            
            # Verify logging
            mock_logger.error.assert_called_once()
            assert "circuit_breaker_opened" in str(mock_logger.error.call_args)

class TestRetryIntegration:
    """Test integration of retry logic with other components."""
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_wrap_llm_call_with_retry(self):
        """Test wrapping LLM calls with retry logic."""
        call_count = 0
        
        def mock_llm_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Service unavailable")  # Retryable
            return "LLM response"
        
        wrapped_function = wrap_llm_call_with_retry(mock_llm_function, "test-session")
        
        with patch('time.sleep'):
            result = wrapped_function()
        
        assert result == "LLM response"
        assert call_count == 2
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_wrap_tool_call_with_retry(self):
        """Test wrapping tool calls with retry logic."""
        call_count = 0
        
        def mock_tool_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Connection failed")  # Retryable
            return "Tool response"
        
        wrapped_function = wrap_tool_call_with_retry(mock_tool_function, "test-session")
        
        with patch('time.sleep'):
            result = wrapped_function()
        
        assert result == "Tool response"
        assert call_count == 2
    
    @pytest.mark.unit
    @pytest.mark.retry
    def test_global_circuit_breakers(self):
        """Test that global circuit breakers are properly initialized."""
        assert isinstance(llm_circuit_breaker, CircuitBreaker)
        assert isinstance(tool_circuit_breaker, CircuitBreaker)
        
        assert llm_circuit_breaker.failure_threshold == 5
        assert tool_circuit_breaker.failure_threshold == 3
        
        assert llm_circuit_breaker.state == "CLOSED"
        assert tool_circuit_breaker.state == "CLOSED"

class TestRetryPerformance:
    """Test performance characteristics of retry logic."""
    
    @pytest.mark.unit
    @pytest.mark.retry
    @pytest.mark.performance
    def test_retry_performance_overhead(self):
        """Test that retry logic doesn't add significant overhead."""
        config = RetryConfig(max_attempts=1)  # No retries
        
        @retry_with_backoff(config)
        def fast_function():
            return "result"
        
        # Measure time for function with retry decorator
        start_time = time.time()
        for _ in range(100):
            fast_function()
        end_time = time.time()
        
        # Should complete quickly (under 1 second for 100 calls)
        assert (end_time - start_time) < 1.0
    
    @pytest.mark.unit
    @pytest.mark.retry
    @pytest.mark.performance
    def test_circuit_breaker_performance(self):
        """Test circuit breaker performance overhead."""
        breaker = CircuitBreaker()
        
        def fast_function():
            return "result"
        
        # Measure time for function with circuit breaker
        start_time = time.time()
        for _ in range(100):
            breaker.call(fast_function)
        end_time = time.time()
        
        # Should complete quickly (under 1 second for 100 calls)
        assert (end_time - start_time) < 1.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
