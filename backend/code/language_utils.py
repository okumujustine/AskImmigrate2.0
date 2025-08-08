"""
Language detection utilities for multilingual immigration assistant.

This module provides robust language detection and language-specific utilities
for the AskImmigrate system.
"""

from typing import Dict, Any, Optional, List
import re
from backend.code.structured_logging import multilingual_logger

# Language detection import with fallback
try:
    from langdetect import detect, DetectorFactory, LangDetectException
    # Set seed for consistent results
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

# Supported languages configuration
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish", 
    "fr": "French",
    "pt": "Portuguese"
}

DEFAULT_LANGUAGE = "en"

# Language-specific keyword patterns for enhanced detection
LANGUAGE_PATTERNS = {
    "es": [
        # Question words
        r'\b(qué|cómo|cuál|cuáles|dónde|cuándo|por qué|quién|quiénes)\b',
        # Common immigration terms in Spanish
        r'\b(visa|solicitar|formulario|inmigración|ciudadanía|residencia)\b',
        # Common verbs/phrases
        r'\b(necesito|quiero|puedo|cuesta|tarifa|precio)\b'
    ],
    "fr": [
        # Question words
        r'\b(qu\'est|qu\'est-ce|comment|quel|quelle|où|quand|pourquoi|qui)\b',
        # Common immigration terms in French
        r'\b(visa|demande|formulaire|immigration|citoyenneté|résidence)\b',
        # Common verbs/phrases
        r'\b(j\'ai besoin|je veux|puis-je|coûte|frais|prix)\b'
    ],
    "pt": [
        # Question words
        r'\b(que|o que|como|qual|quais|onde|quando|por que|quem)\b',
        # Common immigration terms in Portuguese
        r'\b(visto|solicitar|formulário|imigração|cidadania|residência)\b',
        # Common verbs/phrases
        r'\b(preciso|quero|posso|custa|taxa|preço)\b'
    ]
}

def detect_language_with_patterns(text: str) -> str:
    """
    Enhanced language detection using both library and pattern matching.
    
    Args:
        text: Input text to analyze
        
    Returns:
        language_code: ISO 639-1 language code or default language
    """
    
    if not text or len(text.strip()) < 3:
        return DEFAULT_LANGUAGE
    
    text_lower = text.lower()
    
    # Method 1: Pattern-based detection (fast and reliable for immigration queries)
    pattern_scores = {}
    for lang_code, patterns in LANGUAGE_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
            score += matches
        pattern_scores[lang_code] = score
    
    # Get highest scoring language from patterns
    if pattern_scores and max(pattern_scores.values()) > 0:
        pattern_detected = max(pattern_scores, key=pattern_scores.get)
        pattern_confidence = pattern_scores[pattern_detected] / len(text.split())
        
        # If pattern confidence is high, use it
        if pattern_confidence > 0.1:  # At least 10% of words match pattern
            multilingual_logger.log_language_detection(
                user_question=text,
                detected_language=pattern_detected,
                confidence=pattern_confidence,
                session_id=""
            )
            return pattern_detected
    
    # Method 2: Library-based detection (fallback)
    if LANGDETECT_AVAILABLE:
        try:
            library_detected = detect(text)
            
            # Only accept if it's a supported language
            if library_detected in SUPPORTED_LANGUAGES:
                multilingual_logger.log_language_detection(
                    user_question=text,
                    detected_language=library_detected,
                    confidence=0.8,  # Library doesn't provide confidence
                    session_id=""
                )
                return library_detected
            
        except (LangDetectException, Exception) as e:
            multilingual_logger.logger.warning(
                "library_detection_failed",
                error_message=str(e),
                fallback_language=DEFAULT_LANGUAGE
            )
    
    # Method 3: Default fallback
    multilingual_logger.log_language_fallback(
        original_language="unknown",
        fallback_language=DEFAULT_LANGUAGE,
        reason="no_reliable_detection",
        session_id=""
    )
    
    return DEFAULT_LANGUAGE

def get_language_name(language_code: str) -> str:
    """
    Get human-readable language name from code.
    
    Args:
        language_code: ISO 639-1 language code
        
    Returns:
        language_name: Human-readable language name
    """
    return SUPPORTED_LANGUAGES.get(language_code, "English")

def is_supported_language(language_code: str) -> bool:
    """
    Check if a language code is supported.
    
    Args:
        language_code: ISO 639-1 language code
        
    Returns:
        bool: True if supported, False otherwise
    """
    return language_code in SUPPORTED_LANGUAGES

def get_prompt_key_for_language(language_code: str) -> str:
    """
    Get the prompt configuration key for a specific language.
    
    Args:
        language_code: ISO 639-1 language code
        
    Returns:
        prompt_key: Configuration key for language-specific prompt
    """
    prompt_mapping = {
        "en": "synthesis_agent_prompt_english",
        "es": "synthesis_agent_prompt_spanish",
        "fr": "synthesis_agent_prompt_french", 
        "pt": "synthesis_agent_prompt_portuguese"
    }
    
    return prompt_mapping.get(language_code, prompt_mapping["en"])

def validate_language_response(response_text: str, expected_language: str) -> Dict[str, Any]:
    """
    Validate that the response is in the expected language.
    
    Args:
        response_text: Generated response text
        expected_language: Expected language code
        
    Returns:
        validation_result: Dictionary with validation results
    """
    
    if not response_text:
        return {
            "is_valid": False,
            "detected_language": None,
            "expected_language": expected_language,
            "confidence": 0.0,
            "issues": ["empty_response"]
        }
    
    # Quick pattern check for expected language
    if expected_language in LANGUAGE_PATTERNS:
        patterns = LANGUAGE_PATTERNS[expected_language]
        matches = 0
        for pattern in patterns:
            matches += len(re.findall(pattern, response_text.lower(), re.IGNORECASE))
        
        pattern_confidence = matches / len(response_text.split()) if response_text.split() else 0
        
        # If we have good pattern matching, consider it valid
        if pattern_confidence > 0.05:  # 5% threshold for response validation
            return {
                "is_valid": True,
                "detected_language": expected_language,
                "expected_language": expected_language,
                "confidence": pattern_confidence,
                "issues": []
            }
    
    # Library-based validation as fallback
    if LANGDETECT_AVAILABLE:
        try:
            detected_response_lang = detect(response_text)
            is_match = detected_response_lang == expected_language
            
            return {
                "is_valid": is_match,
                "detected_language": detected_response_lang,
                "expected_language": expected_language,
                "confidence": 0.8 if is_match else 0.2,
                "issues": [] if is_match else ["language_mismatch"]
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "detected_language": None,
                "expected_language": expected_language,
                "confidence": 0.0,
                "issues": ["detection_error", str(e)]
            }
    
    # Unable to validate - assume valid
    return {
        "is_valid": True,
        "detected_language": expected_language,
        "expected_language": expected_language,
        "confidence": 0.5,
        "issues": ["validation_unavailable"]
    }

# Cultural formatting utilities
def get_language_specific_formatting(language_code: str) -> Dict[str, str]:
    """
    Get language-specific formatting preferences.
    
    Args:
        language_code: ISO 639-1 language code
        
    Returns:
        formatting_rules: Dictionary with language-specific formatting
    """
    
    formatting_rules = {
        "en": {
            "formal_address": "you",
            "bullet_style": "•",
            "number_format": "1.",
            "verification_phrase": "Verify current requirements at uscis.gov",
            "official_source_intro": "According to USCIS",
            "process_intro": "To apply for"
        },
        
        "es": {
            "formal_address": "usted",
            "bullet_style": "•", 
            "number_format": "1.",
            "verification_phrase": "Verifique los requisitos actuales en uscis.gov",
            "official_source_intro": "Según USCIS",
            "process_intro": "Para solicitar"
        },
        
        "fr": {
            "formal_address": "vous",
            "bullet_style": "•",
            "number_format": "1.",
            "verification_phrase": "Vérifiez les exigences actuelles sur uscis.gov",
            "official_source_intro": "Selon l'USCIS",
            "process_intro": "Pour faire une demande de"
        },
        
        "pt": {
            "formal_address": "você",
            "bullet_style": "•",
            "number_format": "1.",
            "verification_phrase": "Verifique os requisitos atuais em uscis.gov",
            "official_source_intro": "De acordo com o USCIS",
            "process_intro": "Para solicitar"
        }
    }
    
    return formatting_rules.get(language_code, formatting_rules["en"])

# Export main functions
__all__ = [
    'detect_language_with_patterns',
    'get_language_name',
    'is_supported_language', 
    'get_prompt_key_for_language',
    'validate_language_response',
    'get_language_specific_formatting',
    'SUPPORTED_LANGUAGES',
    'DEFAULT_LANGUAGE'
]