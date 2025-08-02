"""
Input Validation and Sanitization Module
Author: Hillary Arinda
Purpose: Security measures for user input validation in AskImmigrate2.0

This module implements comprehensive input validation and sanitization
to prevent injection attacks, handle malformed input, and ensure system security.
"""

import re
import html
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from backend.code.structured_logging import manager_logger
import unicodedata

@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    sanitized_input: str
    warnings: List[str]
    errors: List[str]
    original_length: int
    sanitized_length: int

class InputValidator:
    """
    Comprehensive input validator for immigration queries.
    
    Handles:
    - Length validation
    - Content sanitization
    - Injection attack prevention
    - Character encoding normalization
    - Immigration-specific validation
    """
    
    # Configuration constants
    MAX_QUERY_LENGTH = 5000
    MIN_QUERY_LENGTH = 3
    MAX_SESSION_ID_LENGTH = 100
    
    # Dangerous patterns to detect
    INJECTION_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',               # JavaScript protocol
        r'on\w+\s*=',                # Event handlers
        r'<iframe[^>]*>.*?</iframe>', # Iframes
        r'<object[^>]*>.*?</object>', # Objects
        r'<embed[^>]*>.*?</embed>',   # Embeds
        r'<link[^>]*>',               # Link tags
        r'<meta[^>]*>',               # Meta tags
        r'<style[^>]*>.*?</style>',   # Style tags
        r'vbscript:',                 # VBScript protocol
        r'data:text/html',            # Data URLs
        r'expression\s*\(',           # CSS expressions
    ]
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r"('|(\\')|(;)|(\\;)|(--)|(\|\|)|(\/\*))",
        r"\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b",
        r"\b(or|and)\s+\d+\s*=\s*\d+",
        r"\bor\s+.+\s*=\s*.+",
        r"\band\s+.+\s*=\s*.+",
    ]
    
    # Immigration-specific validation
    VALID_VISA_PATTERNS = [
        r'\b[A-Z]-\d+[A-Z]?\b',  # Visa types like H-1B, F-1, etc.
        r'\bEB-[1-5]\b',         # Employment-based categories
        r'\bI-\d+\b',            # USCIS forms
        r'\bUSCIS\b',            # USCIS mentions
        r'\bgreen\s+card\b',     # Green card
    ]
    
    def __init__(self):
        """Initialize the input validator."""
        self.compiled_injection_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL) 
            for pattern in self.INJECTION_PATTERNS
        ]
        self.compiled_sql_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.SQL_PATTERNS
        ]
        
    def validate_query(self, query: str, session_id: Optional[str] = None) -> ValidationResult:
        """
        Comprehensive validation of user query.
        
        Args:
            query: User input query
            session_id: Optional session identifier for logging
            
        Returns:
            ValidationResult with validation status and sanitized input
        """
        manager_logger.info(
            "input_validation_started",
            original_length=len(query) if query else 0,
            session_id=session_id
        )
        
        warnings = []
        errors = []
        original_length = len(query) if query else 0
        
        # Step 1: Basic validation
        if not query:
            errors.append("Query cannot be empty")
            return ValidationResult(
                is_valid=False,
                sanitized_input="",
                warnings=warnings,
                errors=errors,
                original_length=0,
                sanitized_length=0
            )
        
        if not isinstance(query, str):
            errors.append("Query must be a string")
            return ValidationResult(
                is_valid=False,
                sanitized_input="",
                warnings=warnings,
                errors=errors,
                original_length=original_length,
                sanitized_length=0
            )
        
        # Step 2: Length validation
        if len(query) < self.MIN_QUERY_LENGTH:
            errors.append(f"Query too short (minimum {self.MIN_QUERY_LENGTH} characters)")
        
        if len(query) > self.MAX_QUERY_LENGTH:
            errors.append(f"Query too long (maximum {self.MAX_QUERY_LENGTH} characters)")
            query = query[:self.MAX_QUERY_LENGTH]
            warnings.append("Query truncated to maximum length")
        
        # Step 3: Security validation
        injection_detected = self._detect_injection_attempts(query)
        if injection_detected:
            errors.extend(injection_detected)
        
        # Step 4: Sanitization
        sanitized = self._sanitize_input(query)
        
        # Step 5: Content validation
        content_warnings = self._validate_content(sanitized)
        warnings.extend(content_warnings)
        
        is_valid = len(errors) == 0
        
        manager_logger.info(
            "input_validation_completed",
            is_valid=is_valid,
            sanitized_length=len(sanitized),
            warnings_count=len(warnings),
            errors_count=len(errors),
            session_id=session_id
        )
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_input=sanitized,
            warnings=warnings,
            errors=errors,
            original_length=original_length,
            sanitized_length=len(sanitized)
        )
    
    def validate_session_id(self, session_id: str) -> Tuple[bool, str]:
        """
        Validate and sanitize session ID.
        
        Args:
            session_id: Session identifier to validate
            
        Returns:
            Tuple of (is_valid, sanitized_session_id)
        """
        if not session_id:
            return False, ""
        
        if not isinstance(session_id, str):
            return False, ""
        
        if len(session_id) > self.MAX_SESSION_ID_LENGTH:
            return False, ""
        
        # Only allow alphanumeric, hyphens, and underscores
        sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '', session_id)
        
        if not sanitized or len(sanitized) < 3:
            return False, ""
        
        return True, sanitized
    
    def _detect_injection_attempts(self, query: str) -> List[str]:
        """Detect potential injection attacks."""
        errors = []
        
        # Check for XSS/HTML injection
        for pattern in self.compiled_injection_patterns:
            if pattern.search(query):
                errors.append("Potential XSS/HTML injection detected")
                break
        
        # Check for SQL injection
        for pattern in self.compiled_sql_patterns:
            if pattern.search(query):
                errors.append("Potential SQL injection detected")
                break
        
        # Check for suspicious character combinations
        suspicious_chars = ['<', '>', '{', '}', '${', '{{', '<%', '%>', '<?']
        found_suspicious = [char for char in suspicious_chars if char in query]
        if found_suspicious:
            errors.append(f"Suspicious characters detected: {', '.join(found_suspicious)}")
        
        return errors
    
    def _sanitize_input(self, query: str) -> str:
        """Sanitize input by removing dangerous content."""
        # Normalize unicode
        sanitized = unicodedata.normalize('NFKC', query)
        
        # HTML escape
        sanitized = html.escape(sanitized)
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Remove potentially dangerous protocols
        sanitized = re.sub(r'(javascript|vbscript|data):', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def _validate_content(self, query: str) -> List[str]:
        """Validate content for immigration context."""
        warnings = []
        
        # Check if query contains immigration-related terms
        immigration_terms = [
            'visa', 'immigration', 'uscis', 'green card', 'status', 
            'petition', 'adjustment', 'naturalization', 'citizenship'
        ]
        
        query_lower = query.lower()
        has_immigration_terms = any(term in query_lower for term in immigration_terms)
        
        if not has_immigration_terms:
            warnings.append("Query may not be immigration-related")
        
        # Check for excessive repetition (potential spam)
        words = query.split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            max_count = max(word_counts.values())
            if max_count > len(words) * 0.3:  # More than 30% repetition
                warnings.append("Excessive word repetition detected")
        
        return warnings

# Rate limiting class for input validation
class RateLimiter:
    """Simple rate limiter for input validation."""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.requests = {}  # session_id -> list of timestamps
    
    def is_allowed(self, session_id: str) -> bool:
        """Check if request is allowed under rate limits."""
        import time
        
        current_time = time.time()
        minute_ago = current_time - 60
        
        if session_id not in self.requests:
            self.requests[session_id] = []
        
        # Clean old requests
        self.requests[session_id] = [
            timestamp for timestamp in self.requests[session_id] 
            if timestamp > minute_ago
        ]
        
        # Check limit
        if len(self.requests[session_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[session_id].append(current_time)
        return True

# Global instances
input_validator = InputValidator()
rate_limiter = RateLimiter()

def validate_immigration_query(query: str, session_id: Optional[str] = None) -> ValidationResult:
    """
    Convenience function for validating immigration queries.
    
    Args:
        query: User input query
        session_id: Optional session identifier
        
    Returns:
        ValidationResult with validation status and sanitized input
    """
    return input_validator.validate_query(query, session_id)

def check_rate_limit(session_id: str) -> bool:
    """
    Check if session is within rate limits.
    
    Args:
        session_id: Session identifier
        
    Returns:
        True if allowed, False if rate limited
    """
    return rate_limiter.is_allowed(session_id)
