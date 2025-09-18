
import json
import os
import shutil
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

def utc_timestamp() -> datetime:
    """Return current UTC timestamp as datetime object"""
    return datetime.now(timezone.utc)

def utc_timestamp_str() -> str:
    """Return current UTC timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()

class CacheLogger:
    """
    Enhanced caching system for API requests and responses.
    Handles file operations, cleanup, and statistics with better error handling.
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.ensure_cache_directory()
        self._stats = {
            "requests_logged": 0,
            "responses_logged": 0,
            "errors_logged": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def ensure_cache_directory(self):
        """Create cache directory structure if it doesn't exist"""
        try:
            # Create main cache directory
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories for organization
            subdirs = ["requests", "responses", "errors", "gemini", "logs"]
            for subdir in subdirs:
                (self.cache_dir / subdir).mkdir(exist_ok=True)
                
            # Create .gitignore for cache directory
            gitignore_path = self.cache_dir / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text("*\n!.gitignore\n")
                
        except Exception as e:
            # Fallback to basic directory creation
            os.makedirs(self.cache_dir, exist_ok=True)
            print(f"Warning: Could not create cache subdirectories: {e}")
    
    def generate_filename(self, prefix: str = "log", category: str = "") -> str:
        """Generate filename with timestamp and category"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        if category:
            return f"{prefix}_{category}_{timestamp}.json"
        return f"{prefix}_{timestamp}.json"
    
    def _safe_write_json(self, filepath: Path, data: Dict[str, Any]) -> bool:
        """
        Safely write JSON data to file with error handling.
        
        Args:
            filepath: Path to write to
            data: Data to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first, then rename for atomicity
            temp_filepath = filepath.with_suffix('.tmp')
            
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # Atomic rename
            temp_filepath.rename(filepath)
            return True
            
        except Exception as e:
            print(f"Failed to write cache file {filepath}: {e}")
            # Clean up temporary file if it exists
            if temp_filepath.exists():
                try:
                    temp_filepath.unlink()
                except:
                    pass
            return False
    
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
