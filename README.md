# 🧠 PersonalityAI

**Advanced AI-Powered Personality Analysis Platform**

PersonalityAI is a sophisticated full-stack web application with a beautiful user interface that analyzes written text to extract personality traits using state-of-the-art AI models. Built with FastAPI and powered by Google's Gemini API, it provides detailed personality assessments based on the Big Five personality model and MBTI classification through both a modern web frontend and a robust developer API.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)

## ✨ Features

### 🔍 **Comprehensive Personality Analysis**
- **Big Five Personality Traits**: Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism
- **MBTI Classification**: 16 personality types with detailed descriptions
- **Tone Analysis**: Emotional undertones and communication style
- **Writing Style Assessment**: Vocabulary, complexity, and expression patterns

### 🛡️ **Enterprise-Grade Security**
- Input validation and sanitization
- Rate limiting and DDoS protection
- HTML/Script injection prevention
- Comprehensive error handling

### 🚀 **Production-Ready Features**
- Docker containerization
- Comprehensive logging system
- Health checks and monitoring
- Configuration management
- Automated testing suite

### 🎨 **Modern Web Interface**
- Responsive design with dark theme
- Real-time analysis progress
- Interactive personality visualizations
- Export and sharing capabilities

## 🏗️ Architecture

```
PersonalityAI/
├── 🐍 Backend (FastAPI)
│   ├── main.py              # API server and endpoints
│   ├── analyzer.py          # AI analysis engine
│   ├── validation.py        # Input validation & security
│   ├── config.py           # Configuration management
│   ├── logging_config.py   # Structured logging
│   ├── models.py           # Data models
│   └── utils.py            # Utilities and caching
├── 🎨 Frontend (Vanilla JS)
│   └── index.html          # Modern SPA interface
├── 🧪 Testing
│   └── test_suite.py       # Comprehensive test suite
├── 🐳 Deployment
│   ├── Dockerfile          # Container configuration
│   ├── docker-compose.yml  # Multi-service setup
│   └── .env.example        # Environment template
└── 📁 Data
    ├── cache/              # API response caching
    └── logs/               # Application logs
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- Docker (optional, for containerized deployment)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/PersonalityAI.git
cd PersonalityAI
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API key
# GEMINI_API_KEY=your_api_key_here
```

### 3. Installation Options

#### Option A: Docker (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Access the application
open http://localhost:8000
```

#### Option B: Local Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### 4. Access the Application

- **🎨 Web Interface**: http://localhost:8000 (Beautiful frontend for users)
- **📚 API Documentation**: http://localhost:8000/docs (Interactive API docs)
- **💾 Direct API**: http://localhost:8000/analyze (For developers)
- **❤️ Health Check**: http://localhost:8000/health (System status)

## 🎯 Usage

### For End Users (Web Interface)

1. **Visit** http://localhost:8000 in your browser
2. **Enter text** in the analysis box (journal entries, emails, social media posts, etc.)
3. **Click "Analyze Personality"** to get instant AI-powered insights
4. **View results** including Big Five traits, MBTI type, and detailed explanations
5. **Copy or download** your analysis results

### For Developers (API)

Use the REST API for integration into your applications:

```python
import requests

response = requests.post('http://localhost:8000/analyze', 
    json={'text': 'Your text to analyze here...'})
result = response.json()
```

## 📖 API Documentation

### Core Endpoints

#### `POST /analyze`
Analyze text for personality traits.

**Request:**
```json
{
  "text": "Your text to analyze goes here..."
}
```

**Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "response": {
    "openness": 0.8,
    "conscientiousness": 0.7,
    "extraversion": 0.4,
    "agreeableness": 0.9,
    "neuroticism": 0.3,
    "mbti_type": "INFP",
    "tone_analysis": "Reflective and introspective",
    "writing_style": "Thoughtful and analytical",
    "summary": "A creative individual who values deep thinking..."
  }
}
```

#### `GET /health`
System health and configuration status.

#### `GET /cache-stats`
Caching system statistics and performance metrics.

### Error Handling

The API provides detailed error responses with appropriate HTTP status codes:

- `400`: Invalid input (validation errors)
- `429`: Rate limit exceeded
- `500`: Internal server error

## 🧪 Testing

### Run Test Suite

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests with coverage
python -m pytest test_suite.py -v --cov=. --cov-report=html

# Run specific test categories
python -m pytest test_suite.py::TestAPI -v
python -m pytest test_suite.py::TestValidation -v
```

### Manual Testing

```bash
# Test the API with sample data
python test.py
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | **Required** |
| `SERVER_HOST` | Server bind address | `0.0.0.0` |
| `SERVER_PORT` | Server port | `8000` |
| `ENVIRONMENT` | Environment mode | `development` |
| `DEBUG_MODE` | Enable debug logging | `false` |
| `RATE_LIMIT_RPM` | Requests per minute limit | `60` |
| `MAX_TEXT_LENGTH` | Maximum text length | `10000` |
| `MIN_TEXT_LENGTH` | Minimum text length | `50` |
| `CACHE_DIR` | Cache directory path | `cache` |
| `LOG_RETENTION_DAYS` | Log retention period | `30` |

### Advanced Configuration

See `config.py` for comprehensive configuration options including:
- Security settings
- Caching policies
- Logging levels
- API timeouts
- Validation rules

## 🐳 Docker Deployment

### Production Deployment

```bash
# Production build
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f personalityai

# Scale the application
docker-compose up -d --scale personalityai=3
```

### Development Mode

```bash
# Development with hot reload
docker-compose --profile dev up

# Run tests in container
docker-compose exec personalityai pytest
```

### Monitoring Stack

```bash
# Deploy with monitoring
docker-compose --profile monitoring up -d

# Access Grafana dashboard
open http://localhost:3000
```

## 📊 Monitoring & Observability

### Built-in Monitoring

- **Health Checks**: Automated endpoint monitoring
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Performance Metrics**: Request duration and success rates
- **Cache Statistics**: Hit rates and storage usage

### Optional Monitoring Stack

- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Redis**: Enhanced caching layer

## 🔒 Security Features

### Input Validation
- Text length limits
- Content sanitization
- HTML/script injection prevention
- Character encoding validation

### Rate Limiting
- Per-client request limits
- Sliding window algorithm
- Automatic ban for abuse

### Data Protection
- No sensitive data storage
- Request/response logging with privacy controls
- Secure environment variable handling

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation
- Ensure all tests pass

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Google Gemini API](https://ai.google.dev/) for AI capabilities
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Big Five Personality Model](https://en.wikipedia.org/wiki/Big_Five_personality_traits) research
- [MBTI Foundation](https://www.myersbriggs.org/) for personality type theory

## 📞 Support

- **Documentation**: Check this README and API docs
- **Issues**: [GitHub Issues](https://github.com/yourusername/PersonalityAI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/PersonalityAI/discussions)

---

**Built with ❤️ for understanding human personality through AI** 
