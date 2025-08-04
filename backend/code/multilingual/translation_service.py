"""
Enhanced Translation Service for AskImmigrate 2.0
Fixed to use existing LLM system instead of separate OpenAI client
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import redis
import langdetect
from backend.code.structured_logging import get_logger

logger = get_logger("translation_service")

class SupportedLanguage(Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    PORTUGUESE = "pt"

@dataclass
class TranslationResult:
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    translation_method: str
    processing_time: float

@dataclass
class LanguageDetectionResult:
    language: str
    confidence: float
    detection_method: str

class TranslationService:
    """Enhanced translation service using existing LLM system"""
    
    def __init__(self):
        # Don't create separate OpenAI client, use the existing LLM system
        self.llm_client = None  # Will be set when needed
        
        # Try to initialize Redis cache (optional)
        self.has_redis = False
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
            self.redis_client.ping()
            self.has_redis = True
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.redis_client = None
        
        # Try to initialize Google Translate (optional)
        self.has_google = False
        try:
            from google.cloud import translate_v2 as translate
            self.google_client = translate.Client()
            self.has_google = True
            logger.info("Google Translate initialized")
        except Exception as e:
            logger.warning(f"Google Translate not available: {e}")
            self.google_client = None
        
        # Statistics
        self.stats = {
            'cache_hits': 0,
            'google_translations': 0,
            'openai_translations': 0,
            'native_responses': 0,
            'language_detections': 0,
            'errors': 0
        }
        
        # Enhanced Spanish native prompt
        self.spanish_prompt = """Eres un asistente experto en inmigración estadounidense que responde EXCLUSIVAMENTE en español de manera profesional y precisa.

REGLAS CRÍTICAS:
- Responde SIEMPRE en español claro y profesional, NUNCA en inglés
- Mantén nombres oficiales de formularios en inglés (I-20, I-94, I-485, etc.)
- Usa terminología de inmigración precisa en español
- Proporciona información específica, actualizada y accionable
- Incluye fechas límite y requisitos cuando sean relevantes
- Usa "usted" para formalidad apropiada
- Estructura respuestas con títulos claros y viñetas

CONOCIMIENTO ESPECIALIZADO:
- Información actualizada sobre inmigración a EE.UU. hasta 2025
- Todos los tipos de visa y sus procesos específicos
- Formularios USCIS y procedimientos detallados
- Cambios recientes en políticas de inmigración
- Tarifas actuales y tiempos de procesamiento

FORMATO DE RESPUESTA:
- Usa ## para títulos principales
- Organiza información en listas numeradas o con viñetas
- Usa **negrita** para información importante
- Menciona recursos oficiales cuando sea apropiado
- Incluye enlaces a USCIS en español cuando sea relevante

EJEMPLO DE ESTRUCTURA:
## Respuesta a su Consulta sobre [Tema]

### Información Principal
- Punto importante 1
- Punto importante 2

### Requisitos Necesarios
1. Requisito específico
2. Documentación requerida

### Recursos Oficiales
- **USCIS:** https://www.uscis.gov/es
- **Formularios:** https://www.uscis.gov/es/formularios

**Importante:** Siempre verifique la información más reciente en el sitio web oficial de USCIS."""
    
    def _get_llm_client(self):
        """Get LLM client using the existing system"""
        if self.llm_client is None:
            try:
                from backend.code.llm import get_llm
                self.llm_client = get_llm("gpt-4o-mini")
                logger.info("Using existing LLM system for translations")
            except Exception as e:
                logger.error(f"Failed to get LLM client: {e}")
                return None
        return self.llm_client
    
    async def detect_language(self, text: str) -> LanguageDetectionResult:
        """Enhanced language detection with better error handling"""
        try:
            # Use langdetect for primary detection
            detected = langdetect.detect(text)
            confidence = 0.9
            method = "langdetect"
            
            # Validate against supported languages
            if detected not in [lang.value for lang in SupportedLanguage]:
                detected = SupportedLanguage.ENGLISH.value
                confidence = 0.5
                method = "fallback_unsupported"
            
            # Additional pattern-based validation for Spanish
            if detected == "es" or any(char in text.lower() for char in ['¿', '¡', 'ñ']):
                if any(word in text.lower() for word in ['visa', 'inmigración', 'uscis', 'formulario']):
                    confidence = min(confidence + 0.1, 1.0)
                    method = "langdetect_enhanced"
            
            self.stats['language_detections'] += 1
            
            logger.info(f"Language detected: {detected} (confidence: {confidence}, method: {method})")
            
            return LanguageDetectionResult(
                language=detected,
                confidence=confidence,
                detection_method=method
            )
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}, using pattern fallback")
            self.stats['errors'] += 1
            
            # Pattern-based fallback detection
            text_lower = text.lower()
            if any(char in text_lower for char in ['¿', '¡', 'ñ']) or any(word in text_lower for word in ['inmigración', 'visa', 'español']):
                detected_lang = "es"
                confidence = 0.7
            elif any(char in text_lower for char in ['ç', 'où']) or 'français' in text_lower:
                detected_lang = "fr"
                confidence = 0.6
            elif 'ção' in text_lower or 'português' in text_lower:
                detected_lang = "pt"
                confidence = 0.6
            else:
                detected_lang = "en"
                confidence = 0.8
                
            return LanguageDetectionResult(
                language=detected_lang,
                confidence=confidence,
                detection_method="pattern_fallback"
            )
    
    async def get_spanish_native_response(self, query: str) -> TranslationResult:
        """Generate native Spanish response using existing LLM system"""
        start_time = time.time()
        
        llm_client = self._get_llm_client()
        if not llm_client:
            raise Exception("LLM client not available")
        
        try:
            # Build the complete prompt
            full_prompt = f"{self.spanish_prompt}\n\nPregunta del usuario: {query}"
            
            # Use the existing LLM system
            response = llm_client.invoke(full_prompt)
            self.stats['native_responses'] += 1
            
            # Extract content properly
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Validate response is in Spanish
            if not self._validate_spanish_response(response_text):
                logger.warning("Generated response may not be in Spanish, but proceeding")
            
            logger.info(f"Spanish native response generated: {len(response_text)} characters")
            
            return TranslationResult(
                translated_text=response_text,
                source_language="es",
                target_language="es",
                confidence=0.95,
                translation_method="native_spanish_llm",
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Spanish native response failed: {e}")
            self.stats['errors'] += 1
            raise
    
    def _validate_spanish_response(self, text: str) -> bool:
        """Basic validation that response is in Spanish"""
        if not text:
            return False
        
        # Check for Spanish characteristics
        spanish_indicators = ['de', 'la', 'el', 'que', 'es', 'en', 'un', 'su', 'con', 'para']
        english_indicators = ['the', 'and', 'or', 'but', 'you', 'your', 'this', 'that']
        
        text_lower = text.lower()
        spanish_count = sum(1 for word in spanish_indicators if f' {word} ' in text_lower)
        english_count = sum(1 for word in english_indicators if f' {word} ' in text_lower)
        
        return spanish_count > english_count
    
    async def get_native_response(self, query: str, language: str) -> TranslationResult:
        """Improved native response method with better language support"""
        if language == "es":
            return await self.get_spanish_native_response(query)
        else:
            raise ValueError(f"Native response not available for language: {language}")

    async def translate_text(self, text: str, target_lang: str, source_lang: str = "en", 
                            use_immigration_context: bool = True) -> TranslationResult:
        """Enhanced translation with immigration context and better error handling"""
        if not text or not text.strip():
            raise ValueError("Text to translate cannot be empty")
        
        if source_lang == target_lang:
            return TranslationResult(
                translated_text=text,
                source_language=source_lang,
                target_language=target_lang,
                confidence=1.0,
                translation_method="no_translation_needed",
                processing_time=0.0
            )
        
        if source_lang == "en":
            return await self.translate_english_to_language(text, target_lang, use_immigration_context)
        else:
            raise ValueError(f"Translation from {source_lang} to {target_lang} not supported")
    
    async def translate_english_to_language(self, text: str, target_lang: str, 
                                          use_immigration_context: bool = True) -> TranslationResult:
        """Enhanced English to target language translation"""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"translate:{hashlib.md5(f'{text}:en:{target_lang}:{use_immigration_context}'.encode()).hexdigest()}"
        
        if self.has_redis and self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    self.stats['cache_hits'] += 1
                    data = json.loads(cached)
                    return TranslationResult(**data)
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")
        
        try:
            translated_text = ""
            method = ""
            confidence = 0.0
            
            # Use Google Translate if available (preferred for speed and quality)
            if self.has_google and self.google_client:
                try:
                    result = self.google_client.translate(
                        text,
                        target_language=target_lang,
                        source_language="en"
                    )
                    
                    translated_text = result['translatedText']
                    method = "google_translate"
                    confidence = 0.85
                    self.stats['google_translations'] += 1
                    
                except Exception as e:
                    logger.warning(f"Google Translate failed: {e}, falling back to LLM")
            
            # Fallback to existing LLM with immigration context
            if not translated_text:
                llm_client = self._get_llm_client()
                if not llm_client:
                    raise Exception("No translation service available")
                
                lang_names = {"es": "Spanish", "fr": "French", "pt": "Portuguese"}
                
                if use_immigration_context:
                    context_instruction = """Keep these immigration-specific guidelines:
- Preserve all form numbers (I-20, I-94, I-485, etc.) unchanged
- Maintain official terminology accuracy
- Use formal, professional tone appropriate for immigration matters
- Keep USCIS and official agency names in English"""
                else:
                    context_instruction = "Use professional, formal tone."
                
                prompt = f"""Translate this text from English to {lang_names.get(target_lang, target_lang)}.

{context_instruction}

Text to translate: {text}

Translation:"""
                
                try:
                    response = llm_client.invoke(prompt)
                    translated_text = response.content if hasattr(response, 'content') else str(response)
                    method = "llm_immigration_context" if use_immigration_context else "llm_translation"
                    confidence = 0.80
                    self.stats['openai_translations'] += 1
                    
                except Exception as e:
                    logger.error(f"LLM translation failed: {e}")
                    self.stats['errors'] += 1
                    raise Exception(f"All translation methods failed. Last error: {e}")
            
            if not translated_text:
                raise Exception("No translation service available")
            
            result = TranslationResult(
                translated_text=translated_text,
                source_language="en",
                target_language=target_lang,
                confidence=confidence,
                translation_method=method,
                processing_time=time.time() - start_time
            )
            
            # Cache result if Redis is available
            if self.has_redis and self.redis_client:
                try:
                    self.redis_client.setex(
                        cache_key, 
                        86400,  # 24 hours
                        json.dumps({
                            'translated_text': result.translated_text,
                            'source_language': result.source_language,
                            'target_language': result.target_language,
                            'confidence': result.confidence,
                            'translation_method': result.translation_method,
                            'processing_time': result.processing_time
                        })
                    )
                except Exception as e:
                    logger.warning(f"Cache storage failed: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            self.stats['errors'] += 1
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        total_operations = sum(self.stats.values())
        
        return {
            **self.stats,
            'total_operations': total_operations,
            'cache_hit_rate': (self.stats['cache_hits'] / total_operations * 100) if total_operations > 0 else 0,
            'error_rate': (self.stats['errors'] / total_operations * 100) if total_operations > 0 else 0,
            'has_google': self.has_google,
            'has_redis': self.has_redis,
            'has_llm': self._get_llm_client() is not None,
            'service_health': self._get_service_health()
        }
    
    def _get_service_health(self) -> str:
        """Determine overall service health"""
        llm_client = self._get_llm_client()
        if not llm_client:
            return "critical"  # No primary service
        
        error_rate = (self.stats['errors'] / sum(self.stats.values()) * 100) if sum(self.stats.values()) > 0 else 0
        
        if error_rate > 50:
            return "poor"
        elif error_rate > 20:
            return "degraded"
        elif self.has_google and self.has_redis:
            return "excellent"
        elif self.has_google or self.has_redis:
            return "good"
        else:
            return "basic"

# Global instance
translation_service = TranslationService()

# Utility functions for easy integration
async def detect_user_language(text: str) -> LanguageDetectionResult:
    """Convenience function for language detection"""
    return await translation_service.detect_language(text)

async def translate_to_spanish(text: str) -> TranslationResult:
    """Convenience function for English to Spanish translation"""
    return await translation_service.translate_text(text, "es", "en", use_immigration_context=True)

async def get_spanish_response(query: str) -> TranslationResult:
    """Convenience function for native Spanish response"""
    return await translation_service.get_native_response(query, "es")

# Test function
def test_translation_service():
    """Test function to verify translation service works"""
    print("🧪 Testing Translation Service...")
    
    service = TranslationService()
    
    try:
        # Test LLM client
        llm_client = service._get_llm_client()
        if llm_client:
            print("✅ LLM client available")
        else:
            print("❌ LLM client not available")
            return False
        
        # Test Spanish native response
        import asyncio
        result = asyncio.run(service.get_spanish_native_response("¿Qué es una visa H-1B?"))
        print(f"✅ Spanish response generated: {len(result.translated_text)} characters")
        print(f"Method: {result.translation_method}")
        print(f"Confidence: {result.confidence}")
        return True
    except Exception as e:
        print(f"❌ Translation service test failed: {e}")
        return False

if __name__ == "__main__":
    test_translation_service()