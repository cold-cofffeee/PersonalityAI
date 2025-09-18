# PersonalityAI Production Deployment Guide

## Prerequisites

- Python 3.11+ installed
- Virtual environment support
- Access to Gemini API (valid API key)
- Web server access (if deploying to remote server)

## Quick Production Setup

### 1. Environment Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd PersonalityAI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copy environment template
cp .env.template .env

# Edit .env file with your actual values
# IMPORTANT: Change default credentials and API keys!
```

### 3. Production Configuration
Ensure your `.env` file contains:
```
GEMINI_API_KEY=your_actual_api_key
ENVIRONMENT=production
DEBUG_MODE=false
ADMIN_USERNAME=your_secure_username
ADMIN_PASSWORD=your_secure_password
```

### 4. Start Production Server
```bash
python main.py
```

### 5. Verify Deployment
- Server should start on `http://0.0.0.0:8000`
- Admin panel accessible at `http://your-server:8000/admin`
- API endpoints working correctly

## Advanced Production Setup

### Using Gunicorn (Recommended for Linux)
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

### Nginx Reverse Proxy Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring and Maintenance

### Health Check Endpoint
- `GET /health` - Server health status
- `GET /admin/system-info` - Detailed system information (admin only)

### Log Files
- Application logs: Check console output or configure log files
- Admin access logs: Available in admin panel
- System metrics: Available via `/admin/system-info`

### Regular Maintenance
- Monitor cache directory size
- Clean old cache entries periodically
- Update dependencies regularly
- Monitor API usage quotas

## Troubleshooting

### Common Issues
1. **Import errors**: Ensure all dependencies are installed
2. **Permission errors**: Check file permissions on cache directory
3. **API key errors**: Verify Gemini API key is valid and has quota
4. **Admin access issues**: Verify credentials in `.env` file

### Performance Optimization
- Use SSD storage for cache directory
- Monitor memory usage for large cache files
- Consider implementing Redis for distributed caching
- Use CDN for static admin panel assets

## Security Best Practices
See `SECURITY.md` for detailed security guidelines.

## Support
For issues and support, check the README.md file or create an issue in the repository.