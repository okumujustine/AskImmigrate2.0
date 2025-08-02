"""
Centralized structured logging for AskImmigrate2.0 multi-agent system.
Implements Week 11 requirements with correlation IDs, metrics, and JSON formatting.
"""

import logging
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
import os

from backend.code.paths import OUTPUTS_DIR

# Context variable for correlation ID tracking across agents
correlation_id_context: ContextVar[str] = ContextVar('correlation_id', default='')

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging with correlation IDs"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_context.get(''),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if provided
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        # Add performance metrics if available
        if hasattr(record, 'duration_ms'):
            log_entry["duration_ms"] = record.duration_ms
            
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
            
        return json.dumps(log_entry, ensure_ascii=False)

class ImmigrationLogger:
    """Centralized logger for AskImmigrate2.0 with agent-specific context"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"askimmigrate.{name}")
        self.logger.setLevel(logging.INFO)
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup file and console handlers with structured formatting"""
        if self.logger.handlers:
            return
            
        # Ensure logs directory exists
        logs_dir = os.path.join(OUTPUTS_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
            
        # File handler - structured JSON logs
        log_file = os.path.join(logs_dir, "askimmigrate.jsonl")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(StructuredFormatter())
        
        # Console handler - human readable for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def set_correlation_id(self, correlation_id: Optional[str] = None) -> str:
        """Set correlation ID for request tracking across agents"""
        if not correlation_id:
            correlation_id = str(uuid.uuid4())[:8]
        correlation_id_context.set(correlation_id)
        return correlation_id
    
    def info(self, message: str, **kwargs):
        """Log info level with structured extra fields"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level with structured extra fields"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error level with structured extra fields"""
        self._log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug level with structured extra fields"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging with performance tracking"""
        extra = {"extra_fields": kwargs}
        
        # Add session context if available
        if 'session_id' in kwargs:
            extra['session_id'] = kwargs['session_id']
            
        self.logger.log(level, message, extra=extra)

class PerformanceTimer:
    """Context manager for timing operations with automatic logging"""
    
    def __init__(self, logger: ImmigrationLogger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"{self.operation}_started", **self.context)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_type is None:
            self.logger.info(
                f"{self.operation}_completed",
                duration_ms=round(duration_ms, 2),
                **self.context
            )
        else:
            self.logger.error(
                f"{self.operation}_failed",
                duration_ms=round(duration_ms, 2),
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context
            )

# Agent-specific loggers
def get_logger(agent_name: str) -> ImmigrationLogger:
    """Get logger instance for specific agent"""
    return ImmigrationLogger(agent_name)

# Pre-configured loggers for each agent
manager_logger = get_logger("manager")
synthesis_logger = get_logger("synthesis") 
reviewer_logger = get_logger("reviewer")
workflow_logger = get_logger("workflow")
api_logger = get_logger("api")
cli_logger = get_logger("cli")

# Helper function to initialize correlation ID for new requests
def start_request_tracking(session_id: Optional[str] = None) -> str:
    """Initialize correlation ID for a new request"""
    correlation_id = str(uuid.uuid4())[:8]
    manager_logger.set_correlation_id(correlation_id)
    
    if session_id:
        manager_logger.info(
            "request_started",
            session_id=session_id,
            correlation_id=correlation_id
        )
    
    return correlation_id
