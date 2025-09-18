"""
Comprehensive unit tests for PersonalityAI application.
Tests all major components including API endpoints, validation, and analysis.
"""

import pytest
import pytest_asyncio
import json
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

# Import application modules
from main import app
from analyzer import analyze_text, TextValidator, GeminiAPIClient, ResponseParser
from validation import TextValidator as ValidationTextValidator, RateLimiter, ValidationLevel
from utils import CacheLogger, utc_timestamp, utc_timestamp_str
from config import Config
from models import AnalyzeRequest, PersonalityProfile


class TestConfig:
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test that configuration initializes properly."""
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'}):
            config = Config()
            assert config.gemini_api_key == 'test_key'
            assert config.server.host == "0.0.0.0"
            assert config.server.port == 8000
            assert config.api.timeout == 30
    
    def test_config_missing_api_key(self):
        """Test that missing API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
                Config()
    
    def test_config_environment_detection(self):
        """Test environment detection."""
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': 'test_key',
            'ENVIRONMENT': 'production'
        }):
            config = Config()
            assert config.is_production
            assert not config.is_development


class TestCacheLogger:
    """Test cache logging functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_logger = CacheLogger(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_directory_creation(self):
        """Test that cache directories are created properly."""
        expected_dirs = ["requests", "responses", "errors", "gemini", "logs"]
        for dir_name in expected_dirs:
            assert (self.cache_logger.cache_dir / dir_name).exists()
    
    def test_log_request(self):
        """Test request logging."""
        request_data = {"text": "test text", "endpoint": "/analyze"}
        log_id = self.cache_logger.log_request(request_data)
        
        assert log_id is not None
        request_file = self.cache_logger.cache_dir / "requests" / f"request_{log_id}.json"
        assert request_file.exists()
        
        with open(request_file, 'r') as f:
            logged_data = json.load(f)
        
        assert logged_data["log_id"] == log_id
        assert logged_data["type"] == "request"
        assert logged_data["data"] == request_data
    
    def test_log_response(self):
        """Test response logging."""
        log_id = "test_123"
        response_data = {"success": True, "result": "test"}
        self.cache_logger.log_response(log_id, response_data, "test request")
        
        response_file = self.cache_logger.cache_dir / "responses" / f"response_{log_id}.json"
        assert response_file.exists()
    
    def test_cache_stats(self):
        """Test cache statistics."""
        # Log some test data
        self.cache_logger.log_request({"test": "data"})
        self.cache_logger.log_error("test_123", {"error": "test"}, "test text")
        
        stats = self.cache_logger.get_cache_stats()
        assert stats["directory_exists"]
        assert stats["total_files"] >= 2
        assert "requests" in stats["file_types"]
        assert "errors" in stats["file_types"]


class TestValidation:
    """Test input validation functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.validator = ValidationTextValidator(ValidationLevel.STRICT)
    
    def test_valid_text(self):
        """Test validation of valid text."""
        text = "This is a perfectly normal text that should pass validation. It has multiple sentences and reasonable length."
        result = self.validator.validate_text(text)
        
        assert result.is_valid
        assert result.cleaned_text is not None
        assert result.error_message is None
        assert len(result.cleaned_text) >= 50
    
    def test_empty_text(self):
        """Test validation of empty text."""
        result = self.validator.validate_text("")
        assert not result.is_valid
        assert "empty" in result.error_message.lower()
    
    def test_text_too_short(self):
        """Test validation of text that's too short."""
        result = self.validator.validate_text("Short")
        assert not result.is_valid
        assert "too short" in result.error_message.lower()
    
    def test_text_too_long(self):
        """Test validation of text that's too long."""
        long_text = "A" * 20000  # Exceed max length
        result = self.validator.validate_text(long_text)
        assert not result.is_valid
        assert "too long" in result.error_message.lower()
    
    def test_html_injection(self):
        """Test detection of HTML injection."""
        malicious_text = "<script>alert('xss')</script>" + "A" * 100
        result = self.validator.validate_text(malicious_text)
        assert not result.is_valid
        assert "script" in result.error_message.lower()
    
    def test_repeated_characters(self):
        """Test detection of repeated character spam."""
        spam_text = "A" * 50 + " This is some text with excessive repetition."
        result = self.validator.validate_text(spam_text)
        assert not result.is_valid
        assert "repetition" in result.error_message.lower()
    
    def test_rate_limiter(self):
        """Test rate limiting functionality."""
        limiter = RateLimiter(max_requests=2, window_minutes=1)
        
        # First two requests should be allowed
        allowed, remaining = limiter.is_allowed("client1")
        assert allowed
        assert remaining == 1
        
        allowed, remaining = limiter.is_allowed("client1")
        assert allowed
        assert remaining == 0
        
        # Third request should be blocked
        allowed, remaining = limiter.is_allowed("client1")
        assert not allowed
        assert remaining == 0


class TestAnalyzer:
    """Test text analysis functionality."""
    
    def test_text_validator_basic(self):
        """Test basic text validation in analyzer."""
        validator = TextValidator()
        
        # Valid text
        result = validator.validate_text("This is a valid text for analysis with sufficient length.")
        assert result["valid"]
        assert "cleaned_text" in result
        
        # Invalid text
        result = validator.validate_text("")
        assert not result["valid"]
        assert "error" in result
    
    def test_response_parser(self):
        """Test response parsing from Gemini API."""
        # Mock valid Gemini response
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "openness": 0.7,
                            "conscientiousness": 0.8,
                            "extraversion": 0.6,
                            "agreeableness": 0.9,
                            "neuroticism": 0.3,
                            "mbti_type": "ENFJ",
                            "tone_analysis": "Positive and engaging",
                            "writing_style": "Conversational",
                            "summary": "A friendly and organized individual"
                        })
                    }]
                }
            }]
        }
        
        result = ResponseParser.parse_response(mock_response)
        assert result["success"]
        assert result["data"]["mbti_type"] == "ENFJ"
        assert 0 <= result["data"]["openness"] <= 1
    
    def test_response_parser_invalid_json(self):
        """Test response parser with invalid JSON."""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "Invalid JSON response"
                    }]
                }
            }]
        }
        
        result = ResponseParser.parse_response(mock_response)
        assert not result["success"]
        assert "json" in result["error"].lower()
    
    def test_response_parser_missing_fields(self):
        """Test response parser with missing required fields."""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "openness": 0.7,
                            "conscientiousness": 0.8,
                            # Missing other required fields
                        })
                    }]
                }
            }]
        }
        
        result = ResponseParser.parse_response(mock_response)
        assert not result["success"]
        assert "missing" in result["error"].lower()


class TestAPI:
    """Test API endpoints."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "PersonalityAI" in data["message"]
        assert "version" in data
    
    def test_detailed_health_endpoint(self):
        """Test detailed health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "config" in data
    
    def test_cache_stats_endpoint(self):
        """Test cache statistics endpoint."""
        response = self.client.get("/cache-stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_files" in data
        assert "config" in data
    
    def test_analyze_endpoint_validation(self):
        """Test analyze endpoint input validation."""
        # Test empty text
        response = self.client.post("/analyze", json={"text": ""})
        assert response.status_code == 400
        
        # Test text too short
        response = self.client.post("/analyze", json={"text": "Short"})
        assert response.status_code == 400
        
        # Test invalid JSON
        response = self.client.post("/analyze", data="invalid json")
        assert response.status_code == 422
    
    @patch('analyzer.GeminiAPIClient.make_request')
    async def test_analyze_endpoint_success(self, mock_request):
        """Test successful analysis endpoint."""
        # Mock successful API response
        mock_request.return_value = {
            "success": True,
            "data": {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": json.dumps({
                                "openness": 0.7,
                                "conscientiousness": 0.8,
                                "extraversion": 0.6,
                                "agreeableness": 0.9,
                                "neuroticism": 0.3,
                                "mbti_type": "ENFJ",
                                "tone_analysis": "Positive and engaging",
                                "writing_style": "Conversational",
                                "summary": "A friendly and organized individual"
                            })
                        }]
                    }
                }]
            }
        }
        
        valid_text = "This is a sufficiently long text for personality analysis. It contains multiple sentences and provides enough content for meaningful analysis of personality traits."
        
        response = self.client.post("/analyze", json={"text": valid_text})
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"]
        assert data["response"]["mbti_type"] == "ENFJ"
        assert "timestamp" in data


class TestModels:
    """Test data models."""
    
    def test_analyze_request_model(self):
        """Test AnalyzeRequest model validation."""
        # Valid request
        request = AnalyzeRequest(text="Valid text for analysis")
        assert request.text == "Valid text for analysis"
        
        # Invalid request (empty text would be caught by Pydantic)
        with pytest.raises(ValueError):
            AnalyzeRequest(text="")
    
    def test_personality_profile_model(self):
        """Test PersonalityProfile model validation."""
        # Valid profile
        profile = PersonalityProfile(
            openness=0.7,
            conscientiousness=0.8,
            extraversion=0.6,
            agreeableness=0.9,
            neuroticism=0.3,
            mbti_type="ENFJ",
            tone_analysis="Positive",
            writing_style="Conversational",
            summary="Test summary"
        )
        
        assert profile.mbti_type == "ENFJ"
        assert 0 <= profile.openness <= 1
        
        # Invalid profile (out of range values)
        with pytest.raises(ValueError):
            PersonalityProfile(
                openness=1.5,  # Out of range
                conscientiousness=0.8,
                extraversion=0.6,
                agreeableness=0.9,
                neuroticism=0.3,
                mbti_type="ENFJ",
                tone_analysis="Positive",
                writing_style="Conversational",
                summary="Test summary"
            )


class TestUtilities:
    """Test utility functions."""
    
    def test_utc_timestamp(self):
        """Test UTC timestamp generation."""
        timestamp = utc_timestamp()
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo == timezone.utc
    
    def test_utc_timestamp_str(self):
        """Test UTC timestamp string generation."""
        timestamp_str = utc_timestamp_str()
        assert isinstance(timestamp_str, str)
        assert "T" in timestamp_str  # ISO format
        assert timestamp_str.endswith("+00:00") or timestamp_str.endswith("Z")


# Test fixtures and utilities
@pytest.fixture
def sample_valid_text():
    """Provide sample valid text for testing."""
    return """
    I find myself drawn to creative pursuits and intellectual discussions. 
    When faced with challenges, I prefer to think through problems systematically 
    rather than rushing into action. I enjoy spending time alone to reflect, 
    but I also value meaningful connections with others. My friends would 
    describe me as thoughtful and reliable, someone who considers multiple 
    perspectives before making decisions.
    """


@pytest.fixture
def sample_personality_response():
    """Provide sample personality analysis response."""
    return {
        "openness": 0.8,
        "conscientiousness": 0.7,
        "extraversion": 0.4,
        "agreeableness": 0.8,
        "neuroticism": 0.3,
        "mbti_type": "INFP",
        "tone_analysis": "Reflective and introspective",
        "writing_style": "Thoughtful and measured",
        "summary": "A creative and introspective individual who values deep thinking and meaningful relationships"
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=.", "--cov-report=html"])