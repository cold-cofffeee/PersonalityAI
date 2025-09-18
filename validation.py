"""
Input validation and security utilities for PersonalityAI.
Provides comprehensive validation for text inputs and API security.
"""

import re
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from collections import defaultdict, deque

from config import get_config
from logging_config import get_logger

logger = get_logger(__name__)
config = get_config()


class ValidationLevel(Enum):
    """Validation severity levels."""
    BASIC = "basic"
    STRICT = "strict"
    PARANOID = "paranoid"


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    cleaned_text: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class RateLimiter:
    """Simple in-memory rate limiter for API requests."""
    
    def __init__(self, max_requests: int = 60, window_minutes: int = 1):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.requests = defaultdict(deque)
    
    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            client_id: Unique identifier for client (IP, user_id, etc.)
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = time.time()
        client_requests = self.requests[client_id]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] < now - self.window_seconds:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) >= self.max_requests:
            return False, 0
        
        # Add current request
        client_requests.append(now)
        remaining = self.max_requests - len(client_requests)
        
        return True, remaining
    
    def get_reset_time(self, client_id: str) -> Optional[float]:
        """Get timestamp when rate limit will reset for client."""
        client_requests = self.requests[client_id]
        if not client_requests:
            return None
        
        oldest_request = client_requests[0]
        return oldest_request + self.window_seconds


class TextValidator:
    """Comprehensive text validation with security and quality checks."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT):
        self.validation_level = validation_level
        self.min_length = config.api.min_text_length
        self.max_length = config.api.max_text_length
        
        # Compile regex patterns for efficiency
        self._patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for validation."""
        return {
            # Security patterns
            'script_tags': re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            'html_tags': re.compile(r'<[^>]+>'),
            'sql_injection': re.compile(r'(union|select|insert|update|delete|drop|create|alter)\s+', re.IGNORECASE),
            'repeated_chars': re.compile(r'(.)\1{10,}'),  # 10+ repeated characters
            'excessive_symbols': re.compile(r'[^\w\s\.,!?;:\'"-]{5,}'),  # 5+ consecutive special chars
            'url_pattern': re.compile(r'https?://[^\s]+'),
            'email_pattern': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            
            # Quality patterns
            'multiple_spaces': re.compile(r'\s{3,}'),  # 3+ consecutive spaces
            'multiple_newlines': re.compile(r'\n{4,}'),  # 4+ consecutive newlines
            'gibberish': re.compile(r'\b[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{8,}\b'),  # Consonant-only words
        }
    
    def validate_text(self, text: str, client_id: Optional[str] = None) -> ValidationResult:
        """
        Perform comprehensive text validation.
        
        Args:
            text: Text to validate
            client_id: Optional client identifier for rate limiting
            
        Returns:
            ValidationResult with validation status and cleaned text
        """
        if not isinstance(text, str):
            return ValidationResult(
                is_valid=False,
                error_message="Input must be a string"
            )
        
        # Basic sanitization
        cleaned_text = self._basic_cleanup(text)
        warnings = []
        metadata = {
            'original_length': len(text),
            'cleaned_length': len(cleaned_text),
            'validation_level': self.validation_level.value
        }
        
        # Length validation
        if len(cleaned_text) == 0:
            return ValidationResult(
                is_valid=False,
                error_message="Text cannot be empty after cleanup"
            )
        
        if len(cleaned_text) < self.min_length:
            return ValidationResult(
                is_valid=False,
                error_message=f"Text too short. Minimum {self.min_length} characters required, got {len(cleaned_text)}"
            )
        
        if len(cleaned_text) > self.max_length:
            return ValidationResult(
                is_valid=False,
                error_message=f"Text too long. Maximum {self.max_length} characters allowed, got {len(cleaned_text)}"
            )
        
        # Security validation
        security_result = self._check_security(cleaned_text)
        if not security_result['is_safe']:
            return ValidationResult(
                is_valid=False,
                error_message=f"Security validation failed: {security_result['reason']}"
            )
        warnings.extend(security_result['warnings'])
        
        # Quality validation
        quality_result = self._check_quality(cleaned_text)
        if not quality_result['is_acceptable']:
            if self.validation_level == ValidationLevel.PARANOID:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Quality validation failed: {quality_result['reason']}"
                )
            else:
                warnings.extend(quality_result['warnings'])
        
        # Content analysis
        content_analysis = self._analyze_content(cleaned_text)
        metadata.update(content_analysis)
        
        # Final cleanup
        final_text = self._final_cleanup(cleaned_text)
        
        return ValidationResult(
            is_valid=True,
            cleaned_text=final_text,
            warnings=warnings,
            metadata=metadata
        )
    
    def _basic_cleanup(self, text: str) -> str:
        """Perform basic text cleanup and normalization."""
        # Normalize unicode
        text = unicodedata.normalize('NFKC', text)
        
        # Remove null bytes and control characters (except whitespace)
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
        
        # Normalize whitespace
        text = re.sub(r'\r\n', '\n', text)  # Windows line endings
        text = re.sub(r'\r', '\n', text)    # Mac line endings
        text = ' '.join(text.split())       # Normalize spaces
        
        return text.strip()
    
    def _check_security(self, text: str) -> Dict[str, Any]:
        """Check for security threats in text."""
        warnings = []
        
        # Check for script injection
        if self._patterns['script_tags'].search(text):
            return {'is_safe': False, 'reason': 'Script tags detected', 'warnings': []}
        
        # Check for HTML injection (warn but don't block)
        if self._patterns['html_tags'].search(text):
            warnings.append("HTML tags detected and will be removed")
        
        # Check for SQL injection patterns
        if self._patterns['sql_injection'].search(text):
            return {'is_safe': False, 'reason': 'Potential SQL injection detected', 'warnings': []}
        
        # Check for excessive repeated characters (potential spam)
        if self._patterns['repeated_chars'].search(text):
            if self.validation_level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                return {'is_safe': False, 'reason': 'Excessive character repetition detected', 'warnings': []}
            else:
                warnings.append("Repeated character patterns detected")
        
        # Check for excessive special characters
        if self._patterns['excessive_symbols'].search(text):
            warnings.append("Unusual symbol patterns detected")
        
        return {'is_safe': True, 'reason': None, 'warnings': warnings}
    
    def _check_quality(self, text: str) -> Dict[str, Any]:
        """Check text quality and readability."""
        warnings = []
        
        # Check for excessive URLs
        urls = self._patterns['url_pattern'].findall(text)
        if len(urls) > 3:
            warnings.append(f"Many URLs detected ({len(urls)})")
            if self.validation_level == ValidationLevel.PARANOID:
                return {'is_acceptable': False, 'reason': 'Too many URLs', 'warnings': warnings}
        
        # Check for excessive emails
        emails = self._patterns['email_pattern'].findall(text)
        if len(emails) > 2:
            warnings.append(f"Multiple email addresses detected ({len(emails)})")
        
        # Check for gibberish patterns
        gibberish_matches = self._patterns['gibberish'].findall(text)
        if len(gibberish_matches) > 3:
            warnings.append("Potential gibberish text detected")
            if self.validation_level == ValidationLevel.PARANOID:
                return {'is_acceptable': False, 'reason': 'Too much gibberish', 'warnings': warnings}
        
        # Check character distribution
        char_stats = self._analyze_character_distribution(text)
        if char_stats['ascii_ratio'] < 0.8:
            warnings.append(f"Low ASCII ratio: {char_stats['ascii_ratio']:.2%}")
            if self.validation_level == ValidationLevel.PARANOID:
                return {'is_acceptable': False, 'reason': 'Too many non-ASCII characters', 'warnings': warnings}
        
        return {'is_acceptable': True, 'reason': None, 'warnings': warnings}
    
    def _analyze_content(self, text: str) -> Dict[str, Any]:
        """Analyze text content for metadata."""
        words = text.split()
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_word_length': sum(len(word) for word in words) / len(words) if words else 0,
            'avg_sentence_length': len(words) / len(sentences) if sentences else 0,
            'character_stats': self._analyze_character_distribution(text),
            'detected_language': self._detect_language_hints(text)
        }
    
    def _analyze_character_distribution(self, text: str) -> Dict[str, float]:
        """Analyze character distribution in text."""
        if not text:
            return {'ascii_ratio': 0.0, 'letter_ratio': 0.0, 'digit_ratio': 0.0, 'space_ratio': 0.0}
        
        ascii_count = sum(1 for char in text if ord(char) < 128)
        letter_count = sum(1 for char in text if char.isalpha())
        digit_count = sum(1 for char in text if char.isdigit())
        space_count = sum(1 for char in text if char.isspace())
        
        total_chars = len(text)
        
        return {
            'ascii_ratio': ascii_count / total_chars,
            'letter_ratio': letter_count / total_chars,
            'digit_ratio': digit_count / total_chars,
            'space_ratio': space_count / total_chars
        }
    
    def _detect_language_hints(self, text: str) -> str:
        """Simple language detection based on character patterns."""
        # This is a very basic implementation
        # In production, you might want to use a proper language detection library
        
        if not text:
            return "unknown"
        
        # Count common English patterns
        english_patterns = [
            r'\bthe\b', r'\band\b', r'\bof\b', r'\bto\b', r'\ba\b', r'\bin\b',
            r'\bthat\b', r'\bhave\b', r'\bi\b', r'\bit\b', r'\bfor\b', r'\bnot\b'
        ]
        
        english_score = sum(
            len(re.findall(pattern, text.lower())) 
            for pattern in english_patterns
        )
        
        # Simple heuristic: if we find common English words, assume English
        word_count = len(text.split())
        if word_count > 0 and english_score / word_count > 0.05:
            return "english"
        
        return "unknown"
    
    def _final_cleanup(self, text: str) -> str:
        """Final text cleanup before analysis."""
        # Remove HTML tags
        text = self._patterns['html_tags'].sub('', text)
        
        # Clean up excessive whitespace
        text = self._patterns['multiple_spaces'].sub(' ', text)
        text = self._patterns['multiple_newlines'].sub('\n\n', text)
        
        return text.strip()


# Global instances
rate_limiter = RateLimiter(
    max_requests=config.api.rate_limit_rpm,
    window_minutes=1
)

text_validator = TextValidator(
    validation_level=ValidationLevel.STRICT if config.is_production else ValidationLevel.BASIC
)