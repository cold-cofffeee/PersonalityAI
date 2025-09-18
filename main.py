
import time
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from models import AnalyzeRequest, APIResponse, PersonalityProfile
from analyzer import analyze_personality
from utils import CacheLogger
from config import Config
from logging_config import get_logger

# Initialize configuration and logging
config = Config()
logger = get_logger(__name__)
cache_logger = CacheLogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting PersonalityAI application")
    logger.info(f"Configuration summary: {config.get_summary()}")
    yield
    # Shutdown
    logger.info("Shutting down PersonalityAI application")


app = FastAPI(
    title=config.app.name,
    description=config.app.description,
    version=config.app.version,
    lifespan=lifespan
)

# Add security middleware
if config.is_production:
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )

# Add CORS middleware
if config.security.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.security.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        max_age=3600,
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all HTTP requests and responses."""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            'request_id': request_id,
            'method': request.method,
            'path': str(request.url.path),
            'client_ip': request.client.host if request.client else "unknown",
            'user_agent': request.headers.get("user-agent", "unknown")
        }
    )
    
    # Process request
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} in {duration:.3f}s",
            extra={
                'request_id': request_id,
                'status_code': response.status_code,
                'duration': duration
            }
        )
        
        # Add request ID to response headers for tracking
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Request failed: {e}",
            extra={'request_id': request_id, 'duration': duration},
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
            headers={"X-Request-ID": request_id}
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={'request_id': request_id, 'status_code': exc.status_code}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request_id,
            "timestamp": time.time()
        },
        headers={"X-Request-ID": request_id}
    )

@app.get("/")
async def root():
    """Redirect to frontend application."""
    return RedirectResponse(url="/app")


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    logger.info("Detailed health check endpoint accessed")
    return {
        "status": "healthy",
        "version": config.app.version,
        "environment": config.app.environment,
        "config": {
            "cache_enabled": config.cache.enable_logging,
            "cors_enabled": config.security.enable_cors,
            "api_timeout": config.api.timeout,
            "max_text_length": config.api.max_text_length,
            "min_text_length": config.api.min_text_length
        },
        "timestamp": time.time()
    }


@app.get("/app", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend application."""
    try:
        # Get the directory where main.py is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_path = os.path.join(current_dir, "frontend.html")
        
        if os.path.exists(frontend_path):
            with open(frontend_path, "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content)
        else:
            raise HTTPException(status_code=404, detail="Frontend file not found")
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        raise HTTPException(status_code=500, detail="Error loading frontend")


@app.get("/cache-stats")
async def cache_stats():
    """Get cache statistics and system information."""
    logger.info("Cache stats endpoint accessed")
    stats = cache_logger.get_cache_stats()
    
    return {
        **stats,
        "config": {
            "cache_dir": config.cache.cache_dir,
            "logging_enabled": config.cache.enable_logging,
            "log_retention_days": config.cache.log_retention_days
        },
        "timestamp": time.time()
    }


@app.post("/analyze", response_model=APIResponse)
async def analyze(request: AnalyzeRequest):
    """
    Analyze text for personality insights.
    
    This endpoint analyzes the provided text and returns personality traits
    based on the Big Five model and MBTI classification.
    """
    # Log the incoming request
    log_id = cache_logger.log_request({
        "text_length": len(request.text),
        "endpoint": "/analyze",
        "timestamp": time.time()
    })
    
    logger.info(
        f"Analysis request received",
        extra={
            'request_id': log_id,
            'text_length': len(request.text),
            'endpoint': '/analyze'
        }
    )
    
    try:
        # Perform analysis
        result = await analyze_personality(request.text, config)

        if not result["success"]:
            # Error is already logged in analyze_text function
            logger.warning(
                f"Analysis failed: {result['error']}",
                extra={'request_id': log_id}
            )
            
            raise HTTPException(
                status_code=400 if "validation" in result["error"].lower() or "too short" in result["error"].lower() or "too long" in result["error"].lower() else 500,
                detail=result["error"]
            )

        # Create successful response
        api_response = APIResponse(
            success=result["success"],
            timestamp=result["timestamp"],
            error=result.get("error"),  # Use .get() to handle missing error key
            response=PersonalityProfile(**result["response"]) if result["response"] else None
        )
        
        logger.info(
            f"Analysis completed successfully",
            extra={
                'request_id': log_id,
                'mbti_type': result["response"].get("mbti_type", "Unknown") if result["response"] else None
            }
        )
        
        return api_response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        error_data = {"error_type": "ValueError", "message": str(e)}
        cache_logger.log_error(log_id, error_data, request.text)
        
        logger.error(
            f"Validation error: {e}",
            extra={'request_id': log_id},
            exc_info=True
        )
        
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_data = {"error_type": "Exception", "message": str(e)}
        cache_logger.log_error(log_id, error_data, request.text)
        
        logger.error(
            f"Unexpected error: {e}",
            extra={'request_id': log_id},
            exc_info=True
        )
        
        raise HTTPException(status_code=500, detail="Internal server error occurred")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting PersonalityAI server...")
    logger.info(f"Server configuration: {config.server.host}:{config.server.port}")
    logger.info(f"Debug mode: {config.server.debug}")
    logger.info(f"Cache directory: {config.cache.cache_dir}")
    
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level="debug" if config.server.debug else "info",
        reload=config.server.debug and config.is_development
    )