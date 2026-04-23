"""
Configuration management for PersonalityAI application.
Handles environment variables, validation, and application settings.
"""

import os
from typing import Optional, List
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


@dataclass
class APIConfig:
    """API configuration settings."""
    timeout: int = 30
    rate_limit_rpm: int = 60
    max_text_length: int = 10000
    min_text_length: int = 50
    validate_api_key: bool = True


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    cache_dir: str = "cache"
    enable_logging: bool = True
    log_retention_days: int = 30


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    enable_cors: bool = True
    allowed_origins: List[str] = None
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["*"]


@dataclass
class AppConfig:
    """Application configuration settings."""
    name: str = "PersonalityAI"
    version: str = "1.0.0"
    description: str = "Advanced AI-Powered Personality Analysis"
    environment: str = "development"


@dataclass
class AdminConfig:
    """Admin panel configuration settings."""
    username: str = "admin"
    password: str = "admin123"
    session_timeout_hours: int = 24


class Config:
    """Main configuration class that aggregates all settings."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration from environment variables.
        
        Args:
            env_file: Optional path to .env file
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self._validate_required_vars()
        self._load_config()
    
    def _validate_required_vars(self):
        """Validate that required environment variables are set."""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please check your .env file or environment variables."
            )
    
    def _load_config(self):
        """Load all configuration sections."""
        self.server = ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            debug=os.getenv("DEBUG_MODE", "false").lower() == "true"
        )
        
        self.api = APIConfig(
            timeout=int(os.getenv("API_TIMEOUT", "30")),
            rate_limit_rpm=int(os.getenv("RATE_LIMIT_RPM", "60")),
            max_text_length=int(os.getenv("MAX_TEXT_LENGTH", "10000")),
            min_text_length=int(os.getenv("MIN_TEXT_LENGTH", "50")),
            validate_api_key=os.getenv("VALIDATE_API_KEY", "true").lower() == "true"
        )
        
        self.cache = CacheConfig(
            cache_dir=os.getenv("CACHE_DIR", "cache"),
            enable_logging=os.getenv("ENABLE_LOGGING", "true").lower() == "true",
            log_retention_days=int(os.getenv("LOG_RETENTION_DAYS", "30"))
        )
        
        # Parse allowed origins
        origins_str = os.getenv("ALLOWED_ORIGINS", "*")
        allowed_origins = [origin.strip() for origin in origins_str.split(",")]
        
        self.security = SecurityConfig(
            enable_cors=os.getenv("ENABLE_CORS", "true").lower() == "true",
            allowed_origins=allowed_origins
        )
        
        self.app = AppConfig(
            name=os.getenv("APP_NAME", "PersonalityAI"),
            version=os.getenv("APP_VERSION", "1.0.0"),
            description=os.getenv("APP_DESCRIPTION", "Advanced AI-Powered Personality Analysis"),
            environment=os.getenv("ENVIRONMENT", "development")
        )
        
        self.admin = AdminConfig(
            username=os.getenv("ADMIN_USERNAME", "admin"),
            password=os.getenv("ADMIN_PASSWORD", "admin123"),
            session_timeout_hours=int(os.getenv("ADMIN_SESSION_TIMEOUT_HOURS", "24"))
        )
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment.lower() == "production"
    
    @property
    def gemini_url(self) -> str:
        """Get the Gemini API URL with the API key."""
        return f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.gemini_api_key}"
    
    def get_summary(self) -> dict:
        """Get a summary of current configuration (excluding sensitive data)."""
        return {
            "app": {
                "name": self.app.name,
                "version": self.app.version,
                "environment": self.app.environment,
                "description": self.app.description
            },
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "debug": self.server.debug
            },
            "api": {
                "timeout": self.api.timeout,
                "rate_limit_rpm": self.api.rate_limit_rpm,
                "max_text_length": self.api.max_text_length,
                "min_text_length": self.api.min_text_length,
                "validate_api_key": self.api.validate_api_key
            },
            "cache": {
                "cache_dir": self.cache.cache_dir,
                "enable_logging": self.cache.enable_logging,
                "log_retention_days": self.cache.log_retention_days
            },
            "security": {
                "enable_cors": self.security.enable_cors,
                "allowed_origins": self.security.allowed_origins
            },
            "gemini_api_configured": bool(self.gemini_api_key)
        }


# Global configuration instance
config = None


def get_config(env_file: Optional[str] = None) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        env_file: Optional path to .env file (only used on first call)
        
    Returns:
        Config instance
    """
    global config
    if config is None:
        config = Config(env_file)
    return config


def reload_config(env_file: Optional[str] = None) -> Config:
    """
    Force reload of configuration.
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        New Config instance
    """
    global config
    config = Config(env_file)
    return config


# Convenience function to get configuration
def settings() -> Config:
    """Get the current configuration settings."""
    return get_config()