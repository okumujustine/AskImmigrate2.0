"""
Translation Service for AskImmigrate 2.0
Integrates with existing architecture
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import redis
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
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
    """Minimal translation service that integrates with existing architecture"""
    
    def __init__(self):
        # Initialize OpenAI client (reusing existing pattern)
        self.openai_client = ChatOpenAI(model="gpt-4o", temperature=0.1)
        
        # Try to initialize Redis cache (optional)
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
            self.redis_client.ping()
            self.has_redis = True
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.has_redis = False
        
        # Try to initialize Google Translate (optional)
        try:
            from google.cloud import translate_v2 as translate
            self.google_client = translate.Client()
            self.has_google = True
            logger.info("Google Translate initialized")
        except Exception as e:
            logger.warning(f"Google Translate not available: {e}")
            self.has_google = False
        
        # Statistics
        self.stats = {
            'cache_hits': 0,
            'google_translations': 0,
            'openai_translations': 0,
            'native_responses': 0,
            'language_detections': 0
        }
        
        # Spanish native prompt (highest quality)
        self.spanish_prompt = """Eres un asistente experto en inmigración estadounidense que responde en español de manera profesional y precisa.

INSTRUCCIONES CRÍTICAS:
- Responde SIEMPRE en español claro y profesional
- Mantén nombres oficiales de formularios en inglés (I-20, I-94, I-485, etc.)
- Usa terminología de inmigración precisa
- Proporciona información específica, actualizada y accionable
- Incluye fechas límite y requisitos cuando sean relevantes
- Usa "usted" para formalidad apropiada
- Estructura respuestas con títulos claros y viñetas

CONOCIMIENTO ESPECIALIZADO:
- Información actualizada sobre inmigración a EE.UU. hasta 2025
- Todos los tipos de visa y sus procesos específicos
- Formularios USCIS y procedimientos detallados
- Cambios recientes en políticas de inmigración

FORMATO DE RESPUESTA:
- Usa ## para títulos principales
- Organiza información en listas numeradas o con viñetas
- Usa **negrita** para información importante
- Menciona recursos oficiales cuando sea apropiado"""
    
    async def detect_language(self, text: str) -> LanguageDetectionResult:
        """Detect language using langdetect"""
        try:
            detected = langdetect.detect(text)
            confidence = 0.9
            
            # Validate against supported languages
            if detected not in [lang.value for lang in SupportedLanguage]:
                detected = SupportedLanguage.ENGLISH.value
                confidence = 0.5
            
            self.stats['language_detections'] += 1
            
            logger.info(f"Language detected: {detected} (confidence: {confidence})")
            
            return LanguageDetectionResult(
                language=detected,
                confidence=confidence,
                detection_method="langdetect"
            )
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}, defaulting to English")
            return LanguageDetectionResult(
                language=SupportedLanguage.ENGLISH.value,
                confidence=0.3,
                detection_method="fallback"
            )
    
    async def get_spanish_native_response(self, query: str) -> TranslationResult:
        """Generate native Spanish response for best quality"""
        start_time = time.time()
        
        try:
            messages = [
                SystemMessage(content=self.spanish_prompt),
                HumanMessage(content=query)
            ]
            
            response = await self.openai_client.ainvoke(messages)
            self.stats['native_responses'] += 1
            
            return TranslationResult(
                translated_text=response.content,
                source_language="es",
                target_language="es",
                confidence=0.95,
                translation_method="native_spanish_llm",
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Spanish native response failed: {e}")
            raise
    
    async def get_native_response(self, query: str, language: str) -> TranslationResult:
        """Alias for get_spanish_native_response to match synthesis calls"""
        if language == "es":
            return await self.get_spanish_native_response(query)
        else:
            raise ValueError(f"Native response not available for language: {language}")

    async def translate_text(self, text: str, target_lang: str, source_lang: str = "en", 
                            use_immigration_context: bool = True) -> TranslationResult:
        """Main translation method to match synthesis calls"""
        if source_lang == "en":
            return await self.translate_english_to_language(text, target_lang)
        else:
            # For now, only support English to other languages
            raise ValueError(f"Translation from {source_lang} to {target_lang} not supported")
    
    
    async def translate_english_to_language(self, text: str, target_lang: str) -> TranslationResult:
        """Translate English text to target language"""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"translate:{hashlib.md5(f'{text}:en:{target_lang}'.encode()).hexdigest()}"
        
        if self.has_redis:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    self.stats['cache_hits'] += 1
                    data = json.loads(cached)
                    return TranslationResult(**data)
            except Exception:
                pass
        
        try:
            # Use Google Translate if available
            if self.has_google:
                result = self.google_client.translate(
                    text,
                    target_language=target_lang,
                    source_language="en"
                )
                
                translated_text = result['translatedText']
                method = "google_translate"
                confidence = 0.85
                self.stats['google_translations'] += 1
            
            else:
                # Fallback to OpenAI
                lang_names = {"es": "Spanish", "fr": "French", "pt": "Portuguese"}
                
                prompt = f"""Translate this immigration text from English to {lang_names.get(target_lang, target_lang)}.

Keep form names (I-20, I-94, etc.) unchanged. Use professional, formal tone.

Text: {text}

Translation:"""
                
                response = await self.openai_client.ainvoke([HumanMessage(content=prompt)])
                translated_text = response.content
                method = "openai_translation"
                confidence = 0.80
                self.stats['openai_translations'] += 1
            
            result = TranslationResult(
                translated_text=translated_text,
                source_language="en",
                target_language=target_lang,
                confidence=confidence,
                translation_method=method,
                processing_time=time.time() - start_time
            )
            
            # Cache result
            if self.has_redis:
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
                except Exception:
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        total_operations = sum(self.stats.values())
        
        return {
            **self.stats,
            'total_operations': total_operations,
            'cache_hit_rate': (self.stats['cache_hits'] / total_operations * 100) if total_operations > 0 else 0,
            'has_google': self.has_google,
            'has_redis': self.has_redis
        }

# Global instance
translation_service = TranslationService()