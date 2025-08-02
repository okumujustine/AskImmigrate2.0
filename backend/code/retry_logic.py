"""
Retry Logic Implementation for AskImmigrate2.0
Author: Hillary Arinda
Purpose: Implement retry logic with exponential backoff for LLM calls and tool operations

This module provides decorators and utilities for handling transient failures
in LLM calls, tool executions, and database operations with proper logging.
"""

import time
import random
import functools
from typing import Callable, Any, Optional, List, Type, Union
from dataclasses import dataclass
from backend.code.structured_logging import manager_logger

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff multiplier
    jitter: bool = True  # Add random jitter to prevent thundering herd
    
class RetryableError(Exception):
    """Base exception for errors that should trigger retries."""
    pass

class LLMRetryableError(RetryableError):
    """Specific exception for LLM-related retryable errors."""
    pass

class ToolRetryableError(RetryableError):
    """Specific exception for tool-related retryable errors."""
    pass

class DatabaseRetryableError(RetryableError):
    """Specific exception for database-related retryable errors."""
    pass

def is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Args:
        exception: The exception to check
        
    Returns:
        True if the exception should trigger a retry
    """
    # Network-related errors
    network_errors = [
        "Connection timeout",
        "Connection refused",
        "Connection reset",
        "Network unreachable",
        "DNS lookup failed",
        "SSL handshake failed",
        "Read timeout",
        "Request timeout"
    ]
    
    # API-related errors
    api_errors = [
        "Rate limit exceeded",
        "Service unavailable",
        "Internal server error",
        "Bad gateway",
        "Gateway timeout",
        "Service temporarily unavailable",
        "Temporary failure",
        "Too many requests"
    ]
    
    # LLM-specific errors
    llm_errors = [
        "Model overloaded",
        "Context length exceeded",
        "Token limit exceeded",
        "API quota exceeded",
        "Model temporarily unavailable"
    ]
    
    # Database errors
    db_errors = [
        "Database connection lost",
        "Transaction deadlock",
        "Lock timeout",
        "Connection pool exhausted"
    ]
    
    error_message = str(exception).lower()
    
    # Check if it's explicitly a retryable error type
    if isinstance(exception, RetryableError):
        return True
    
    # Check for known retryable patterns
    all_retryable_patterns = network_errors + api_errors + llm_errors + db_errors
    return any(pattern.lower() in error_message for pattern in all_retryable_patterns)

def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for retry attempt using exponential backoff.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        
    Returns:
        Delay in seconds before next attempt
    """
    # Exponential backoff: base_delay * (exponential_base ^ attempt)
    delay = config.base_delay * (config.exponential_base ** attempt)
    
    # Cap at maximum delay
    delay = min(delay, config.max_delay)
    
    # Add jitter to prevent thundering herd
    if config.jitter:
        jitter_range = delay * 0.1  # 10% jitter
        jitter = random.uniform(-jitter_range, jitter_range)
        delay += jitter
    
    return max(0.1, delay)  # Minimum 100ms delay

def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    session_id: Optional[str] = None
):
    """
    Decorator for adding retry logic with exponential backoff.
    
    Args:
        config: Retry configuration (uses default if None)
        retryable_exceptions: Specific exceptions to retry on
        session_id: Session ID for logging context
        
    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()
    
    if retryable_exceptions is None:
        retryable_exceptions = [RetryableError, ConnectionError, TimeoutError]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    manager_logger.info(
                        "retry_attempt_started",
                        function_name=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=config.max_attempts,
                        session_id=session_id
                    )
                    
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Log success if this wasn't the first attempt
                    if attempt > 0:
                        manager_logger.info(
                            "retry_success",
                            function_name=func.__name__,
                            successful_attempt=attempt + 1,
                            total_attempts=attempt + 1,
                            session_id=session_id
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception should trigger a retry
                    should_retry = (
                        isinstance(e, tuple(retryable_exceptions)) or
                        is_retryable_error(e)
                    )
                    
                    # Don't retry on the last attempt
                    if attempt == config.max_attempts - 1 or not should_retry:
                        manager_logger.error(
                            "retry_exhausted" if should_retry else "retry_not_applicable",
                            function_name=func.__name__,
                            final_attempt=attempt + 1,
                            total_attempts=config.max_attempts,
                            error_type=type(e).__name__,
                            error_message=str(e),
                            session_id=session_id
                        )
                        raise e
                    
                    # Calculate delay and log retry info
                    delay = calculate_delay(attempt, config)
                    
                    manager_logger.warning(
                        "retry_attempt_failed",
                        function_name=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=config.max_attempts,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        next_delay_seconds=delay,
                        session_id=session_id
                    )
                    
                    # Wait before next attempt
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator

# Specific retry decorators for different use cases
def retry_llm_call(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    session_id: Optional[str] = None
):
    """
    Decorator specifically for LLM API calls.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        session_id: Session ID for logging
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True
    )
    
    retryable_exceptions = [
        LLMRetryableError,
        ConnectionError,
        TimeoutError,
        # Add specific LLM provider exceptions as needed
    ]
    
    return retry_with_backoff(config, retryable_exceptions, session_id)

def retry_tool_call(
    max_attempts: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 15.0,
    session_id: Optional[str] = None
):
    """
    Decorator specifically for tool calls.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        session_id: Session ID for logging
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=1.5,
        jitter=True
    )
    
    retryable_exceptions = [
        ToolRetryableError,
        ConnectionError,
        TimeoutError,
    ]
    
    return retry_with_backoff(config, retryable_exceptions, session_id)

def retry_database_operation(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    session_id: Optional[str] = None
):
    """
    Decorator specifically for database operations.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        session_id: Session ID for logging
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True
    )
    
    retryable_exceptions = [
        DatabaseRetryableError,
        ConnectionError,
        # Add specific database exceptions as needed
    ]
    
    return retry_with_backoff(config, retryable_exceptions, session_id)

# Circuit breaker pattern for additional resilience
class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold exceeded, requests fail fast
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self.state == "OPEN"
    
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open."""
        return self.state == "HALF_OPEN"
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if self.last_failure_time and \
               time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                manager_logger.info(
                    "circuit_breaker_half_open",
                    function_name=func.__name__,
                    failure_count=self.failure_count
                )
            else:
                manager_logger.warning(
                    "circuit_breaker_open_rejection",
                    function_name=func.__name__,
                    failure_count=self.failure_count
                )
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset if we were testing recovery
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                manager_logger.info(
                    "circuit_breaker_closed",
                    function_name=func.__name__
                )
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                manager_logger.error(
                    "circuit_breaker_opened",
                    function_name=func.__name__,
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold
                )
            
            raise e

# Global circuit breakers for common operations
llm_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
    expected_exception=Exception
)

tool_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception=Exception
)

# Utility functions for integration with existing code
def wrap_llm_call_with_retry(llm_func: Callable, session_id: Optional[str] = None) -> Callable:
    """
    Wrap an LLM function call with retry logic and circuit breaker.
    
    Args:
        llm_func: LLM function to wrap
        session_id: Session ID for logging
        
    Returns:
        Wrapped function with retry and circuit breaker
    """
    @retry_llm_call(session_id=session_id)
    def wrapped_llm_call(*args, **kwargs):
        return llm_circuit_breaker.call(llm_func, *args, **kwargs)
    
    return wrapped_llm_call

def wrap_tool_call_with_retry(tool_func: Callable, session_id: Optional[str] = None) -> Callable:
    """
    Wrap a tool function call with retry logic and circuit breaker.
    
    Args:
        tool_func: Tool function to wrap
        session_id: Session ID for logging
        
    Returns:
        Wrapped function with retry and circuit breaker
    """
    @retry_tool_call(session_id=session_id)
    def wrapped_tool_call(*args, **kwargs):
        return tool_circuit_breaker.call(tool_func, *args, **kwargs)
    
    return wrapped_tool_call
