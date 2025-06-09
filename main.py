
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import AnalyzeRequest, APIResponse, PersonalityProfile
from analyzer import analyze_text
from utils import cache_logger

app = FastAPI(
    title="Personality Insight API",
    description="Analyzes English text to extract personality traits using LLMs.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Personality Insight API is running!"}

@app.get("/cache-stats")
async def cache_stats():
    """Get cache statistics"""
    return cache_logger.get_cache_stats()

@app.post("/analyze", response_model=APIResponse)
async def analyze(request: AnalyzeRequest):
    """Analyze text for personality insights"""
    # Log the incoming request
    log_id = cache_logger.log_request({
        "text": request.text,
        "text_length": len(request.text),
        "endpoint": "/analyze"
    })
    
    try:
        result = await analyze_text(request.text, log_id)

        if not result["success"]:
            # Error is already logged in analyze_text function
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )

        api_response = APIResponse(
            success=result["success"],
            timestamp=result["timestamp"],
            error=result["error"],
            response=PersonalityProfile(**result["response"]) if result["response"] else None
        )
        
        return api_response
    
    except ValueError as e:
        error_data = {"error_type": "ValueError", "message": str(e)}
        cache_logger.log_error(log_id, error_data, request.text)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_data = {"error_type": "Exception", "message": str(e)}
        cache_logger.log_error(log_id, error_data, request.text)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Personality Insight API with caching enabled...")
    print(f"Cache directory: {cache_logger.cache_dir}")
    uvicorn.run(app, host="0.0.0.0", port=8000)