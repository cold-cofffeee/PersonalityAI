
import os
import httpx
import json
from dotenv import load_dotenv
from utils import utc_timestamp, cache_logger

# Load environment variables from .env file in the same directory
load_dotenv()

# Retrieve the API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Error: GEMINI_API_KEY is not set in .env file.")

print(f"GEMINI_API_KEY loaded successfully: {GEMINI_API_KEY[:5]}...")

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"

PROMPT = """You are a psychological language analyst trained in personality assessment based on written communication.

Analyze the user's writing using the Big Five (OCEAN) personality model and the MBTI system. Consider linguistic tone, emotional depth, vocabulary complexity, subject matter, and implicit preferences. The user is fluent in English and expresses themselves naturally.

Return ONLY a valid JSON object with the following fields (no additional text):
{
    "openness": 0.0-1.0,
    "conscientiousness": 0.0-1.0,
    "extraversion": 0.0-1.0,
    "agreeableness": 0.0-1.0,
    "neuroticism": 0.0-1.0,
    "mbti_type": "4-letter MBTI type",
    "tone_analysis": "brief tone description",
    "writing_style": "brief style description",
    "summary": "brief personality summary"
}

Analyze this text:
"""


async def analyze_text(text: str, log_id: str = None) -> dict:
    """Analyze text using Gemini API and return structured response"""
    if not text.strip():
        error_result = {
            "success": False,
            "timestamp": utc_timestamp(),
            "error": "Text input cannot be empty",
            "response": None,
        }
        
        if log_id:
            cache_logger.log_error(log_id, error_result, text)
        
        return error_result

    # Prepare the payload
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT + text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1000,
        }
    }

    headers = {"Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GEMINI_URL, headers=headers, json=payload)

        # Log the Gemini API call
        gemini_response_data = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text if response.status_code != 200 else "Success"
        }
        
        if log_id:
            cache_logger.log_gemini_request(log_id, payload, gemini_response_data)

        # Check for successful response
        if response.status_code != 200:
            error_msg = f"Gemini API request failed with status {response.status_code}"
            print(f"Error: {error_msg}")
            print("Response body:", response.text)
            
            error_result = {
                "success": False,
                "timestamp": utc_timestamp(),
                "error": error_msg,
                "response": None,
            }
            
            if log_id:
                cache_logger.log_error(log_id, error_result, text)
            
            return error_result

        # Process the response from Gemini
        response_data = response.json()
        candidates = response_data.get("candidates", [])
        
        if not candidates:
            print("Error: No candidates found in Gemini response")
            error_result = {
                "success": False,
                "timestamp": utc_timestamp(),
                "error": "No candidates in Gemini response",
                "response": None,
            }
            
            if log_id:
                cache_logger.log_error(log_id, error_result, text)
            
            return error_result

        # Extract the text response
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        
        if not parts:
            error_result = {
                "success": False,
                "timestamp": utc_timestamp(),
                "error": "No content parts in Gemini response",
                "response": None,
            }
            
            if log_id:
                cache_logger.log_error(log_id, error_result, text)
            
            return error_result

        text_response = parts[0].get("text", "")

        # Clean and parse the JSON response
        try:
            # Remove any markdown formatting or extra text
            clean_text = text_response.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            json_response = json.loads(clean_text)
            
            # Validate required fields
            required_fields = ["openness", "conscientiousness", "extraversion", 
                             "agreeableness", "neuroticism", "mbti_type", 
                             "tone_analysis", "writing_style", "summary"]
            
            for field in required_fields:
                if field not in json_response:
                    error_result = {
                        "success": False,
                        "timestamp": utc_timestamp(),
                        "error": f"Missing required field: {field}",
                        "response": None
                    }
                    
                    if log_id:
                        cache_logger.log_error(log_id, error_result, text)
                    
                    return error_result

        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini response as JSON: {e}")
            print(f"Raw response: {text_response}")
            error_result = {
                "success": False,
                "timestamp": utc_timestamp(),
                "error": "Failed to parse Gemini response as JSON",
                "response": None
            }
            
            if log_id:
                cache_logger.log_error(log_id, error_result, text)
            
            return error_result

        success_result = {
            "success": True,
            "timestamp": utc_timestamp(),
            "error": None,
            "response": json_response
        }
        
        if log_id:
            cache_logger.log_response(log_id, success_result, text)
        
        return success_result

    except httpx.TimeoutException:
        error_result = {
            "success": False,
            "timestamp": utc_timestamp(),
            "error": "Request timeout - Gemini API took too long to respond",
            "response": None
        }
        
        if log_id:
            cache_logger.log_error(log_id, error_result, text)
        
        return error_result
    except Exception as e:
        print(f"Exception occurred: {e}")
        error_result = {
            "success": False,
            "timestamp": utc_timestamp(),
            "error": str(e),
            "response": None
        }
        
        if log_id:
            cache_logger.log_error(log_id, error_result, text)
        
        return error_result