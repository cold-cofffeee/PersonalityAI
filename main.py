
import time
import uuid
from fastapi import FastAPI, HTTPException, Request, Depends
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
from cache_manager import AdvancedCacheManager
from user_tracker import UserInfoExtractor, SecurityUtils
from admin_auth import AdminAuth, AdminDataManager

# Initialize configuration and logging
config = Config()
logger = get_logger(__name__)
cache_manager = AdvancedCacheManager()  # Initialize cache manager
cache_logger = CacheLogger()
admin_auth = AdminAuth()  # Initialize admin authentication
admin_data = AdminDataManager(cache_manager)  # Initialize admin data manager


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


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    """Serve the admin panel."""
    try:
        # Get the directory where main.py is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        admin_path = os.path.join(current_dir, "admin_panel.html")
        
        if os.path.exists(admin_path):
            with open(admin_path, "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content)
        else:
            raise HTTPException(status_code=404, detail="Admin panel file not found")
    except Exception as e:
        logger.error(f"Error serving admin panel: {e}")
        raise HTTPException(status_code=500, detail="Error loading admin panel")


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
async def analyze(request: AnalyzeRequest, http_request: Request):
    """
    Analyze text for personality insights with advanced caching.
    
    This endpoint analyzes the provided text and returns personality traits
    based on the Big Five model and MBTI classification. Uses intelligent
    caching with 90% similarity matching to reduce API calls.
    """
    start_time = time.time()
    
    # Extract comprehensive user information
    user_info = UserInfoExtractor.extract_client_info(http_request)
    
    # Add geolocation if possible
    try:
        geo_info = await UserInfoExtractor.get_ip_geolocation(user_info["ip"])
        user_info.update(geo_info)
    except:
        pass  # Continue without geolocation if it fails
    
    # Validate text input for security
    validation_result = SecurityUtils.validate_text_input(request.text)
    if not validation_result["valid"]:
        raise HTTPException(status_code=400, detail=validation_result["error"])
    
    text = validation_result["cleaned_text"]
    
    # Check for suspicious requests
    if SecurityUtils.is_suspicious_request(user_info):
        logger.warning(
            f"Suspicious request detected",
            extra={
                'ip': user_info["ip"],
                'user_agent': user_info["user_agent"],
                'browser': user_info.get("browser_info", {}).get("browser", "unknown")
            }
        )
        # Still process but log for monitoring
    
    # Log the incoming request
    log_id = cache_logger.log_request({
        "text_length": len(text),
        "endpoint": "/analyze",
        "timestamp": time.time(),
        "user_info": user_info
    })
    
    logger.info(
        f"Analysis request received",
        extra={
            'request_id': log_id,
            'text_length': len(text),
            'endpoint': '/analyze',
            'ip': user_info["ip"],
            'browser': user_info.get("browser_info", {}).get("browser", "unknown")
        }
    )
    
    try:
        # 🎯 STEP 1: Check cache first (90% similarity threshold)
        cached_result = cache_manager.search_cache(text, user_info)
        
        if cached_result:
            # Handle rate limiting
            if cached_result.get("rate_limited"):
                raise HTTPException(status_code=429, detail=cached_result["error"])
            
            # Cache hit! Return cached result
            logger.info(
                f"Cache hit - returning cached result",
                extra={
                    'request_id': log_id,
                    'similarity': cached_result.get("cache_info", {}).get("similarity", 0),
                    'response_time_ms': cached_result.get("cache_info", {}).get("response_time_ms", 0)
                }
            )
            
            # Convert cached result to API response format
            api_response = APIResponse(
                success=True,
                timestamp=cached_result.get("timestamp", time.time()),
                error=None,
                response=PersonalityProfile(**cached_result["response"]) if cached_result.get("response") else None
            )
            
            # Add cache metadata
            if hasattr(api_response, "cache_info"):
                api_response.cache_info = cached_result.get("cache_info")
            
            return api_response
        
        # 🤖 STEP 2: Cache miss - call Gemini API
        logger.info(
            f"Cache miss - calling AI analysis",
            extra={'request_id': log_id}
        )
        
        result = await analyze_personality(text, config)

        if not result["success"]:
            logger.warning(
                f"Analysis failed: {result['error']}",
                extra={'request_id': log_id}
            )
            
            raise HTTPException(
                status_code=400 if "validation" in result["error"].lower() or "too short" in result["error"].lower() or "too long" in result["error"].lower() else 500,
                detail=result["error"]
            )

        # 💾 STEP 3: Save successful result to cache
        cache_manager.save_to_cache(text, result, user_info)
        
        # Create successful response
        api_response = APIResponse(
            success=result["success"],
            timestamp=result["timestamp"],
            error=result.get("error"),
            response=PersonalityProfile(**result["response"]) if result["response"] else None
        )
        
        # Add cache info for API miss
        total_time = time.time() - start_time
        if hasattr(api_response, "cache_info"):
            api_response.cache_info = {
                "cache_hit": False,
                "response_time_ms": round(total_time * 1000, 2),
                "source": "gemini_api"
            }
        
        logger.info(
            f"Analysis completed successfully and cached",
            extra={
                'request_id': log_id,
                'mbti_type': result["response"].get("mbti_type", "Unknown") if result["response"] else None,
                'response_time_ms': round(total_time * 1000, 2),
                'cached': True
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


# 📊 Cache Management Endpoints

@app.get("/admin/cache-stats")
async def get_cache_statistics(http_request: Request):
    """
    Get comprehensive cache statistics and performance metrics.
    Admin endpoint for monitoring cache performance.
    """
    user_info = UserInfoExtractor.extract_client_info(http_request)
    
    logger.info(
        f"Cache stats requested",
        extra={
            'ip': user_info["ip"],
            'browser': user_info.get("browser_info", {}).get("browser", "unknown")
        }
    )
    
    try:
        stats = cache_manager.get_cache_stats()
        return {
            "success": True,
            "timestamp": time.time(),
            "cache_statistics": stats
        }
    except Exception as e:
        logger.error(f"Error retrieving cache stats: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve cache statistics")


@app.post("/admin/cache-cleanup")
async def cleanup_cache(http_request: Request):
    """
    Clean up expired cache entries.
    Admin endpoint for cache maintenance.
    """
    user_info = UserInfoExtractor.extract_client_info(http_request)
    
    logger.info(
        f"Cache cleanup requested",
        extra={
            'ip': user_info["ip"],
            'browser': user_info.get("browser_info", {}).get("browser", "unknown")
        }
    )
    
    try:
        removed_count = cache_manager.cleanup_expired_cache()
        
        logger.info(f"Cache cleanup completed - removed {removed_count} expired entries")
        
        return {
            "success": True,
            "timestamp": time.time(),
            "message": f"Cache cleanup completed",
            "removed_entries": removed_count
        }
    except Exception as e:
        logger.error(f"Error during cache cleanup: {e}")
        raise HTTPException(status_code=500, detail="Cache cleanup failed")


@app.get("/cache-info")
async def get_cache_info():
    """
    Get basic cache information for frontend display.
    Public endpoint with limited cache stats.
    """
    try:
        stats = cache_manager.get_cache_stats()
        
        # Return only public-safe information
        return {
            "cache_enabled": True,
            "hit_rate_percentage": stats["cache_performance"]["hit_rate_percentage"],
            "total_cached_analyses": stats["cache_storage"]["total_entries"],
            "similarity_threshold": stats["cache_storage"]["similarity_threshold"],
            "average_response_time_ms": stats["cache_performance"]["average_response_time_ms"]
        }
    except Exception as e:
        logger.error(f"Error retrieving public cache info: {e}")
        return {
            "cache_enabled": False,
            "error": "Cache information unavailable"
        }


# 👑 Admin Panel Routes

@app.post("/admin/login")
async def admin_login(credentials: dict, http_request: Request):
    """
    Admin login endpoint
    """
    user_info = UserInfoExtractor.extract_client_info(http_request)
    
    username = credentials.get("username")
    password = credentials.get("password")
    
    logger.info(
        f"Admin login attempt",
        extra={
            'username': username,
            'ip': user_info["ip"],
            'user_agent': user_info.get("user_agent", "unknown")
        }
    )
    
    if admin_auth.authenticate_user(username, password):
        token = admin_auth.create_session(username)
        
        logger.info(
            f"Admin login successful",
            extra={
                'username': username,
                'ip': user_info["ip"]
            }
        )
        
        return {
            "success": True,
            "token": token,
            "username": username
        }
    else:
        logger.warning(
            f"Admin login failed",
            extra={
                'username': username,
                'ip': user_info["ip"]
            }
        )
        
        raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/admin/logout")
async def admin_logout(session = Depends(admin_auth.get_current_user)):
    """
    Admin logout endpoint
    """
    # This would be called with the auth token
    return {"success": True, "message": "Logged out successfully"}


@app.get("/admin/dashboard")
async def serve_admin_panel():
    """
    Serve the admin panel HTML
    """
    return FileResponse("admin_panel.html")


@app.get("/admin/user-analytics")
async def get_user_analytics(session = Depends(admin_auth.get_current_user)):
    """
    Get comprehensive user analytics for admin panel
    """
    try:
        analytics = admin_data.get_user_analytics()
        
        return {
            "success": True,
            "timestamp": time.time(),
            "user_analytics": analytics
        }
    except Exception as e:
        logger.error(f"Error retrieving user analytics: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve user analytics")


@app.get("/admin/cache-details")
async def get_admin_cache_details(session = Depends(admin_auth.get_current_user)):
    """
    Get detailed cache information for admin panel
    """
    try:
        cache_details = admin_data.get_cache_details()
        
        return {
            "success": True,
            "timestamp": time.time(),
            "cache_details": cache_details
        }
    except Exception as e:
        logger.error(f"Error retrieving cache details: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve cache details")


@app.get("/admin/error-logs")
async def get_error_logs(session = Depends(admin_auth.get_current_user)):
    """
    Get error logs for admin panel
    """
    try:
        error_logs = admin_data.get_error_logs()
        
        return {
            "success": True,
            "timestamp": time.time(),
            "error_logs": error_logs
        }
    except Exception as e:
        logger.error(f"Error retrieving error logs: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve error logs")


@app.get("/admin/system-info")
async def get_system_info(session = Depends(admin_auth.get_current_user)):
    """
    Get system information and health status
    """
    try:
        import psutil
        import os
        
        # Get system stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get cache directory size
        cache_size = 0
        if os.path.exists(cache_manager.cache_dir):
            for dirpath, dirnames, filenames in os.walk(cache_manager.cache_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    cache_size += os.path.getsize(filepath)
        
        return {
            "success": True,
            "system_stats": {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "disk_usage_percent": disk.percent,
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "cache_size_mb": round(cache_size / (1024**2), 2)
            },
            "active_sessions": len(admin_auth.active_sessions),
            "cache_performance": cache_manager.get_cache_stats()
        }
    except ImportError:
        # psutil not available
        return {
            "success": True,
            "system_stats": {"error": "System monitoring not available"},
            "active_sessions": len(admin_auth.active_sessions),
            "cache_performance": cache_manager.get_cache_stats()
        }
    except Exception as e:
        logger.error(f"Error retrieving system info: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve system information")


@app.get("/admin/user-details")
async def get_user_details(fingerprint: str, session = Depends(admin_auth.get_current_user)):
    """
    Get detailed information about a specific user
    """
    try:
        # Get user tracking data
        user_data = admin_data.get_user_details(fingerprint)
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "success": True,
            "user_details": user_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user details: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve user details")


@app.get("/admin/cache-entry")
async def get_cache_entry_details(id: str, session = Depends(admin_auth.get_current_user)):
    """
    Get detailed information about a specific cache entry
    """
    try:
        # Get cache entry
        cache_entry = cache_manager.get_by_id(id)
        
        if not cache_entry:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        
        # Get user fingerprint from cache entry metadata if available
        user_fingerprint = cache_entry.get('user_fingerprint')
        
        return {
            "success": True,
            "cache_entry": {
                "id": id,
                "input_text": cache_entry.get('input_text', ''),
                "response": cache_entry.get('response', {}),
                "timestamp": cache_entry.get('timestamp'),
                "user_fingerprint": user_fingerprint,
                "metadata": cache_entry.get('metadata', {})
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cache entry: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve cache entry")


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