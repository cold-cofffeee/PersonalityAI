#!/usr/bin/env python3
"""
Demo script to showcase PersonalityAI improvements.
Demonstrates the enhanced features and professional capabilities.
"""

import asyncio
import time
from pathlib import Path

# Import the enhanced modules
from config import Config
from logging_config import get_logger
from validation import TextValidator, ValidationLevel, RateLimiter
from analyzer import analyze_personality
from utils import CacheLogger

# Initialize configuration and logging
config = Config()
logger = get_logger(__name__)


def demonstrate_configuration():
    """Demonstrate the configuration management system."""
    print("🔧 Configuration Management Demo")
    print("=" * 50)
    
    # Show configuration summary
    config_summary = config.get_summary()
    print(f"App Name: {config_summary['app']['name']}")
    print(f"Version: {config_summary['app']['version']}")
    print(f"Environment: {config_summary['app']['environment']}")
    print(f"API Timeout: {config_summary['api']['timeout']}s")
    print(f"Rate Limit: {config_summary['api']['rate_limit_rpm']} RPM")
    print(f"Text Length: {config_summary['api']['min_text_length']}-{config_summary['api']['max_text_length']} chars")
    print(f"Gemini API Configured: {'✅' if config_summary['gemini_api_configured'] else '❌'}")
    print()


def demonstrate_validation():
    """Demonstrate the enhanced validation system."""
    print("🛡️ Input Validation Demo")
    print("=" * 50)
    
    validator = TextValidator(ValidationLevel.STRICT)
    
    test_cases = [
        ("Valid text", "This is a perfectly valid text for personality analysis that meets all requirements and contains sufficient content."),
        ("Too short", "Short"),
        ("HTML injection", "<script>alert('xss')</script>" + "A" * 100),
        ("Repeated spam", "A" * 50 + " Some text here"),
        ("Empty text", ""),
        ("Very long text", "A" * 15000),
    ]
    
    for name, text in test_cases:
        result = validator.validate_text(text)
        status = "✅ VALID" if result.is_valid else "❌ INVALID"
        print(f"{name:15} | {status:10} | {result.error_message or 'OK'}")
    
    print()


def demonstrate_rate_limiting():
    """Demonstrate the rate limiting system."""
    print("⏱️ Rate Limiting Demo")
    print("=" * 50)
    
    limiter = RateLimiter(max_requests=3, window_minutes=1)
    
    # Simulate requests from a client
    client_id = "demo_client"
    
    for i in range(5):
        allowed, remaining = limiter.is_allowed(client_id)
        status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
        print(f"Request {i+1}: {status} (Remaining: {remaining})")
    
    print()


def demonstrate_caching():
    """Demonstrate the enhanced caching system."""
    print("💾 Caching System Demo")
    print("=" * 50)
    
    # Log some demo data
    cache_logger = CacheLogger()
    log_id = cache_logger.log_request({
        "demo": True,
        "text_length": 100,
        "timestamp": time.time()
    })
    
    cache_logger.log_response(log_id, {
        "success": True,
        "analysis_result": "Demo result"
    }, "Demo text")
    
    # Get cache statistics
    stats = cache_logger.get_cache_stats()
    print(f"Cache Directory: {stats['cache_directory']}")
    print(f"Total Files: {stats['total_files']}")
    print(f"Total Size: {stats.get('total_size_mb', 0):.2f} MB")
    print(f"File Types: {stats['file_types']}")
    print()


async def demonstrate_analysis():
    """Demonstrate the enhanced text analysis."""
    print("🧠 Text Analysis Demo")
    print("=" * 50)
    
    sample_texts = [
        """I love meeting new people and attending social gatherings. I'm always 
        optimistic and energetic, preferring to think on my feet rather than 
        spending too much time planning. I enjoy variety and spontaneity in my life.""",
        
        """I prefer quiet evenings at home with a good book. Deep thinking and 
        reflection are very important to me. I like to plan things carefully and 
        pay attention to details. I value harmony and avoid conflicts when possible.""",
        
        """I'm very organized and methodical in my approach to life. I always 
        plan ahead and never miss deadlines. I believe in traditional values 
        and prefer proven methods over experimental approaches."""
    ]
    
    for i, text in enumerate(sample_texts, 1):
        print(f"Analysis {i}:")
        print("-" * 20)
        
        try:
            result = await analyze_personality(text, config)
            
            if result["success"]:
                response = result["response"]
                print(f"MBTI Type: {response['mbti_type']}")
                print(f"Openness: {response['openness']:.2f}")
                print(f"Conscientiousness: {response['conscientiousness']:.2f}")
                print(f"Extraversion: {response['extraversion']:.2f}")
                print(f"Agreeableness: {response['agreeableness']:.2f}")
                print(f"Neuroticism: {response['neuroticism']:.2f}")
                print(f"Tone: {response['tone_analysis']}")
                print(f"Style: {response['writing_style']}")
                print(f"Summary: {response['summary'][:100]}...")
            else:
                print(f"❌ Analysis failed: {result['error']}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()


def demonstrate_logging():
    """Demonstrate the structured logging system."""
    print("📝 Logging System Demo")
    print("=" * 50)
    
    # Log different types of messages
    logger.info("This is an info message", extra={'demo': True})
    logger.warning("This is a warning message", extra={'demo': True, 'severity': 'medium'})
    logger.error("This is an error message", extra={'demo': True, 'component': 'demo'})
    
    print("✅ Logged various message types with structured data")
    print("Check the logs directory for JSON-formatted log files")
    print()


def show_project_structure():
    """Show the improved project structure."""
    print("📁 Project Structure")
    print("=" * 50)
    
    structure = {
        "🐍 Core Application": ["main.py", "analyzer.py", "models.py"],
        "🔧 Configuration": ["config.py", ".env.example"],
        "🛡️ Security & Validation": ["validation.py"],
        "📝 Logging & Utils": ["logging_config.py", "utils.py"],
        "🧪 Testing": ["test_suite.py"],
        "🐳 Deployment": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
        "🎨 Frontend": ["index.html"],
        "📖 Documentation": ["README.md"]
    }
    
    for category, files in structure.items():
        print(f"{category}:")
        for file in files:
            exists = "✅" if Path(file).exists() else "❌"
            print(f"  {exists} {file}")
        print()


def show_improvements_summary():
    """Show summary of all improvements made."""
    print("🚀 PersonalityAI Improvements Summary")
    print("=" * 60)
    
    improvements = [
        "✅ Enhanced Configuration Management (config.py)",
        "✅ Structured Logging System (logging_config.py)",
        "✅ Comprehensive Input Validation (validation.py)",
        "✅ Rate Limiting & Security Features",
        "✅ Improved Error Handling & User Messages",
        "✅ Professional API with Health Checks",
        "✅ Docker Containerization & Deployment",
        "✅ Comprehensive Test Suite (test_suite.py)",
        "✅ Enhanced Caching with Statistics",
        "✅ Production-Ready Architecture",
        "✅ Professional Documentation (README.md)",
        "✅ Environment Variable Management (.env.example)"
    ]
    
    for improvement in improvements:
        print(f"  {improvement}")
    
    print("\n🎯 Professional Features Added:")
    features = [
        "🔒 Security: Input sanitization, rate limiting, validation",
        "📊 Monitoring: Health checks, metrics, structured logging",
        "🚀 Deployment: Docker, docker-compose, production configs",
        "🧪 Testing: Unit tests, integration tests, coverage reports",
        "📖 Documentation: Comprehensive README, API docs",
        "⚙️ Configuration: Environment-based config management",
        "🛠️ DevOps: CI/CD ready, containerized deployment"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print(f"\n📈 Code Quality Improvements:")
    quality = [
        "🎯 Type hints and documentation throughout",
        "🏗️ Modular architecture with separation of concerns",
        "🔄 Async/await patterns for better performance",
        "🚨 Comprehensive error handling and logging",
        "🧹 Code organization and best practices",
        "📋 Validation and sanitization at all levels"
    ]
    
    for item in quality:
        print(f"  {item}")


async def main():
    """Run the complete demonstration."""
    print("🎉 Welcome to PersonalityAI Professional Demo!")
    print("=" * 60)
    print()
    
    # Run all demonstrations
    show_improvements_summary()
    print()
    
    demonstrate_configuration()
    demonstrate_validation()
    demonstrate_rate_limiting()
    demonstrate_caching()
    demonstrate_logging()
    show_project_structure()
    
    # Only run analysis if API key is configured
    if config.gemini_api_key and config.gemini_api_key != "your_gemini_api_key_here":
        await demonstrate_analysis()
    else:
        print("🧠 Text Analysis Demo")
        print("=" * 50)
        print("⚠️ Skipping analysis demo - Gemini API key not configured")
        print("To test analysis, set GEMINI_API_KEY in your .env file")
        print()
    
    print("✨ Demo completed! Your PersonalityAI project is now professional-grade.")
    print("🚀 Ready for production deployment!")


if __name__ == "__main__":
    asyncio.run(main())