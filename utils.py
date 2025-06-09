
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

def utc_timestamp() -> datetime:
    """Return current UTC timestamp as datetime object"""
    return datetime.now(timezone.utc)

def utc_timestamp_str() -> str:
    """Return current UTC timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()

class CacheLogger:
    """Handles caching of API requests and responses to JSON files"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.ensure_cache_directory()
    
    def ensure_cache_directory(self):
        """Create cache directory if it doesn't exist"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            print(f"Created cache directory: {self.cache_dir}")
    
    def generate_filename(self, prefix: str = "log") -> str:
        """Generate filename with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        return f"{prefix}_{timestamp}.json"
    
    def log_request(self, request_data: Dict[str, Any]) -> str:
        """Log incoming request and return the log ID"""
        log_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        log_entry = {
            "log_id": log_id,
            "type": "request",
            "timestamp": utc_timestamp_str(),
            "data": request_data
        }
        
        filename = os.path.join(self.cache_dir, f"request_{log_id}.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
            print(f"Request logged: {filename}")
        except Exception as e:
            print(f"Failed to log request: {e}")
        
        return log_id
    
    def log_response(self, log_id: str, response_data: Dict[str, Any], request_text: str = ""):
        """Log API response"""
        log_entry = {
            "log_id": log_id,
            "type": "response",
            "timestamp": utc_timestamp_str(),
            "request_text": request_text,
            "response": response_data
        }
        
        filename = os.path.join(self.cache_dir, f"response_{log_id}.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
            print(f"Response logged: {filename}")
        except Exception as e:
            print(f"Failed to log response: {e}")
    
    def log_error(self, log_id: str, error_data: Dict[str, Any], request_text: str = ""):
        """Log API error"""
        log_entry = {
            "log_id": log_id,
            "type": "error",
            "timestamp": utc_timestamp_str(),
            "request_text": request_text,
            "error": error_data
        }
        
        filename = os.path.join(self.cache_dir, f"error_{log_id}.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
            print(f"Error logged: {filename}")
        except Exception as e:
            print(f"Failed to log error: {e}")
    
    def log_gemini_request(self, log_id: str, payload: Dict[str, Any], response_data: Dict[str, Any]):
        """Log Gemini API request and response"""
        log_entry = {
            "log_id": log_id,
            "type": "gemini_api",
            "timestamp": utc_timestamp_str(),
            "request_payload": payload,
            "response": response_data
        }
        
        filename = os.path.join(self.cache_dir, f"gemini_{log_id}.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
            print(f"Gemini API call logged: {filename}")
        except Exception as e:
            print(f"Failed to log Gemini API call: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached files"""
        if not os.path.exists(self.cache_dir):
            return {"total_files": 0, "file_types": {}}
        
        files = os.listdir(self.cache_dir)
        file_types = {}
        
        for file in files:
            if file.endswith('.json'):
                file_type = file.split('_')[0]
                file_types[file_type] = file_types.get(file_type, 0) + 1
        
        return {
            "total_files": len(files),
            "file_types": file_types,
            "cache_directory": self.cache_dir
        }

# Global cache logger instance
cache_logger = CacheLogger()
