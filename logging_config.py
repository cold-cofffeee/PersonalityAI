"""
Logging configuration for PersonalityAI application.
Provides structured logging with different levels and formatters.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional
import json


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration
        if hasattr(record, 'api_response_code'):
            log_data['api_response_code'] = record.api_response_code
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }
    
    def format(self, record):
        """Format log record with colors."""
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Create formatted message
        formatted_message = (
            f"{log_color}[{timestamp}] {record.levelname:8s}{reset_color} "
            f"{record.name}: {record.getMessage()}"
        )
        
        # Add location info for debug level
        if record.levelno == logging.DEBUG:
            formatted_message += f" ({record.filename}:{record.lineno})"
        
        return formatted_message


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    app_name: str = "personalityai",
    enable_json_logs: bool = False,
    enable_file_logs: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup comprehensive logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        app_name: Application name for log files
        enable_json_logs: Whether to enable JSON structured logging
        enable_file_logs: Whether to enable file logging
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logs directory if needed
    if enable_file_logs and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if enable_json_logs:
        console_formatter = JSONFormatter()
    else:
        console_formatter = ColoredFormatter()
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    if enable_file_logs:
        # File handler for general logs
        log_file = os.path.join(log_dir, f"{app_name}.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        
        # Use JSON formatter for file logs
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Separate error log file
        error_log_file = os.path.join(log_dir, f"{app_name}_error.log")
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
    
    # Log the setup completion
    logger.info(f"Logging setup complete - Level: {level}, JSON: {enable_json_logs}, File: {enable_file_logs}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class RequestLogger:
    """Utility class for logging HTTP requests and API calls."""
    
    def __init__(self, logger_name: str = "api"):
        self.logger = get_logger(logger_name)
    
    def log_request(self, request_id: str, method: str, path: str, **kwargs):
        """Log incoming HTTP request."""
        self.logger.info(
            f"Request started: {method} {path}",
            extra={
                'request_id': request_id,
                'method': method,
                'path': path,
                **kwargs
            }
        )
    
    def log_response(self, request_id: str, status_code: int, duration: float, **kwargs):
        """Log HTTP response."""
        level = logging.INFO if status_code < 400 else logging.ERROR
        self.logger.log(
            level,
            f"Request completed: {status_code} in {duration:.3f}s",
            extra={
                'request_id': request_id,
                'api_response_code': status_code,
                'duration': duration,
                **kwargs
            }
        )
    
    def log_external_api_call(self, api_name: str, method: str, url: str, 
                            status_code: int, duration: float, **kwargs):
        """Log external API calls."""
        level = logging.INFO if status_code < 400 else logging.ERROR
        self.logger.log(
            level,
            f"External API call: {api_name} {method} -> {status_code} in {duration:.3f}s",
            extra={
                'api_name': api_name,
                'method': method,
                'url': url,
                'api_response_code': status_code,
                'duration': duration,
                **kwargs
            }
        )


class PerformanceLogger:
    """Utility class for performance monitoring and logging."""
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = get_logger(logger_name)
    
    def log_function_performance(self, function_name: str, duration: float, **kwargs):
        """Log function execution time."""
        if duration > 1.0:  # Log slow functions
            level = logging.WARNING
        else:
            level = logging.DEBUG
            
        self.logger.log(
            level,
            f"Function {function_name} executed in {duration:.3f}s",
            extra={
                'function_name': function_name,
                'duration': duration,
                **kwargs
            }
        )
    
    def log_cache_stats(self, cache_hits: int, cache_misses: int, hit_ratio: float):
        """Log cache performance statistics."""
        self.logger.info(
            f"Cache stats - Hits: {cache_hits}, Misses: {cache_misses}, Ratio: {hit_ratio:.2%}",
            extra={
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'hit_ratio': hit_ratio
            }
        )


# Global logger instances
request_logger = None
performance_logger = None


def init_loggers(config=None):
    """Initialize global logger instances."""
    global request_logger, performance_logger
    
    # Setup main logging
    if config:
        setup_logging(
            level="DEBUG" if config.is_development else "INFO",
            log_dir=os.path.join(config.cache.cache_dir, "logs"),
            app_name=config.app.name.lower(),
            enable_json_logs=config.is_production,
            enable_file_logs=config.cache.enable_logging
        )
    else:
        setup_logging()
    
    # Initialize specialized loggers
    request_logger = RequestLogger()
    performance_logger = PerformanceLogger()


def get_request_logger() -> RequestLogger:
    """Get the global request logger instance."""
    global request_logger
    if request_logger is None:
        request_logger = RequestLogger()
    return request_logger


def get_performance_logger() -> PerformanceLogger:
    """Get the global performance logger instance."""
    global performance_logger
    if performance_logger is None:
        performance_logger = PerformanceLogger()
    return performance_logger