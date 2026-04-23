import json
import os
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from difflib import SequenceMatcher
import re

class AdvancedCacheManager:
    """
    Advanced JSON-based caching system with user tracking and security features
    """
    
    def __init__(self, cache_dir: str = "cache_data"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "personality_cache.json")
        self.users_file = os.path.join(cache_dir, "user_tracking.json")
        self.stats_file = os.path.join(cache_dir, "cache_stats.json")
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize cache files
        self._init_cache_files()
        
        # Configuration
        self.similarity_threshold = 0.90  # 90% match required
        self.cache_expiry_days = 30
        self.max_cache_entries = 10000
        self.rate_limit_per_hour = 100
    
    def _init_cache_files(self):
        """Initialize cache files if they don't exist"""
        
        # Main cache file
        if not os.path.exists(self.cache_file):
            with open(self.cache_file, 'w') as f:
                json.dump({
                    "metadata": {
                        "created": datetime.now().isoformat(),
                        "version": "1.0",
                        "total_entries": 0
                    },
                    "cache_entries": []
                }, f, indent=2)
        
        # User tracking file
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({
                    "metadata": {
                        "created": datetime.now().isoformat(),
                        "total_users": 0
                    },
                    "users": {}
                }, f, indent=2)
        
        # Stats file
        if not os.path.exists(self.stats_file):
            with open(self.stats_file, 'w') as f:
                json.dump({
                    "cache_hits": 0,
                    "cache_misses": 0,
                    "api_calls_saved": 0,
                    "total_requests": 0,
                    "average_response_time": 0,
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using multiple methods"""
        
        # Normalize texts
        text1_clean = re.sub(r'\s+', ' ', text1.lower().strip())
        text2_clean = re.sub(r'\s+', ' ', text2.lower().strip())
        
        # Method 1: Sequence Matcher (character-level)
        similarity1 = SequenceMatcher(None, text1_clean, text2_clean).ratio()
        
        # Method 2: Word-level similarity
        words1 = set(text1_clean.split())
        words2 = set(text2_clean.split())
        
        if len(words1) == 0 and len(words2) == 0:
            similarity2 = 1.0
        elif len(words1) == 0 or len(words2) == 0:
            similarity2 = 0.0
        else:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            similarity2 = intersection / union if union > 0 else 0.0
        
        # Method 3: Length-based similarity
        len_diff = abs(len(text1_clean) - len(text2_clean))
        max_len = max(len(text1_clean), len(text2_clean))
        similarity3 = 1.0 - (len_diff / max_len) if max_len > 0 else 1.0
        
        # Weighted average of all methods
        final_similarity = (similarity1 * 0.5) + (similarity2 * 0.3) + (similarity3 * 0.2)
        
        return final_similarity
    
    def _generate_user_fingerprint(self, request_data: Dict) -> str:
        """Generate unique fingerprint for user tracking"""
        
        # Extract identifying information
        ip = request_data.get('ip', 'unknown')
        user_agent = request_data.get('user_agent', 'unknown')
        accept_language = request_data.get('accept_language', 'unknown')
        
        # Create fingerprint
        fingerprint_data = f"{ip}:{user_agent}:{accept_language}"
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
        
        return fingerprint
    
    def _update_user_tracking(self, user_fingerprint: str, request_data: Dict):
        """Update user tracking information"""
        
        with open(self.users_file, 'r') as f:
            users_data = json.load(f)
        
        current_time = datetime.now().isoformat()
        
        if user_fingerprint not in users_data["users"]:
            # New user
            users_data["users"][user_fingerprint] = {
                "first_seen": current_time,
                "last_seen": current_time,
                "request_count": 1,
                "ip_addresses": [request_data.get('ip', 'unknown')],
                "user_agents": [request_data.get('user_agent', 'unknown')],
                "countries": [request_data.get('country', 'unknown')],
                "request_times": [current_time]
            }
            users_data["metadata"]["total_users"] += 1
        else:
            # Existing user
            user_data = users_data["users"][user_fingerprint]
            user_data["last_seen"] = current_time
            user_data["request_count"] += 1
            
            # Update IP if new
            if request_data.get('ip') not in user_data["ip_addresses"]:
                user_data["ip_addresses"].append(request_data.get('ip', 'unknown'))
            
            # Update user agent if new
            if request_data.get('user_agent') not in user_data["user_agents"]:
                user_data["user_agents"].append(request_data.get('user_agent', 'unknown'))
            
            # Keep only last 100 request times
            user_data["request_times"].append(current_time)
            if len(user_data["request_times"]) > 100:
                user_data["request_times"] = user_data["request_times"][-100:]
        
        # Save updated data
        with open(self.users_file, 'w') as f:
            json.dump(users_data, f, indent=2)
    
    def _check_rate_limit(self, user_fingerprint: str) -> bool:
        """Check if user has exceeded rate limit"""
        
        with open(self.users_file, 'r') as f:
            users_data = json.load(f)
        
        if user_fingerprint not in users_data["users"]:
            return True  # New user, allow
        
        user_data = users_data["users"][user_fingerprint]
        recent_requests = []
        
        # Check requests in last hour
        current_time = datetime.now()
        for request_time_str in user_data["request_times"]:
            request_time = datetime.fromisoformat(request_time_str)
            if current_time - request_time <= timedelta(hours=1):
                recent_requests.append(request_time)
        
        return len(recent_requests) <= self.rate_limit_per_hour
    
    def _update_stats(self, cache_hit: bool, response_time: float):
        """Update cache statistics"""
        
        with open(self.stats_file, 'r') as f:
            stats = json.load(f)
        
        stats["total_requests"] += 1
        
        if cache_hit:
            stats["cache_hits"] += 1
            stats["api_calls_saved"] += 1
        else:
            stats["cache_misses"] += 1
        
        # Update average response time
        current_avg = stats["average_response_time"]
        total_requests = stats["total_requests"]
        stats["average_response_time"] = ((current_avg * (total_requests - 1)) + response_time) / total_requests
        
        stats["last_updated"] = datetime.now().isoformat()
        
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def search_cache(self, text: str, request_data: Dict) -> Optional[Dict]:
        """Search for cached response with 90%+ similarity"""
        
        start_time = time.time()
        
        # Generate user fingerprint
        user_fingerprint = self._generate_user_fingerprint(request_data)
        
        # Check rate limit
        if not self._check_rate_limit(user_fingerprint):
            response_time = time.time() - start_time
            self._update_stats(False, response_time)
            return {
                "error": "Rate limit exceeded. Please try again later.",
                "rate_limited": True
            }
        
        # Update user tracking
        self._update_user_tracking(user_fingerprint, request_data)
        
        # Load cache
        with open(self.cache_file, 'r') as f:
            cache_data = json.load(f)
        
        best_match = None
        best_similarity = 0.0
        
        # Search through cache entries
        for entry in cache_data["cache_entries"]:
            # Check if entry is not expired
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if datetime.now() - entry_time > timedelta(days=self.cache_expiry_days):
                continue
            
            # Calculate similarity
            similarity = self._calculate_text_similarity(text, entry["input_text"])
            
            if similarity >= self.similarity_threshold and similarity > best_similarity:
                best_match = entry
                best_similarity = similarity
        
        response_time = time.time() - start_time
        
        if best_match:
            # Cache hit
            self._update_stats(True, response_time)
            
            # Add cache metadata to response
            result = best_match["response"].copy()
            result["cache_info"] = {
                "cache_hit": True,
                "similarity": round(best_similarity, 3),
                "cached_at": best_match["timestamp"],
                "response_time_ms": round(response_time * 1000, 2)
            }
            
            return result
        else:
            # Cache miss
            self._update_stats(False, response_time)
            return None
    
    def save_to_cache(self, text: str, response: Dict, request_data: Dict):
        """Save response to cache"""
        
        # Load current cache
        with open(self.cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Create cache entry
        cache_entry = {
            "id": f"cache_{int(time.time())}_{hashlib.md5(text.encode()).hexdigest()[:8]}",
            "timestamp": datetime.now().isoformat(),
            "input_text": text,
            "text_hash": hashlib.sha256(text.encode()).hexdigest(),
            "response": response,
            "user_fingerprint": self._generate_user_fingerprint(request_data),
            "metadata": {
                "text_length": len(text),
                "ip": request_data.get('ip', 'unknown'),
                "user_agent": request_data.get('user_agent', 'unknown')[:100],  # Truncate long user agents
                "country": request_data.get('country', 'unknown')
            }
        }
        
        # Add to cache
        cache_data["cache_entries"].append(cache_entry)
        cache_data["metadata"]["total_entries"] += 1
        
        # Clean old entries if cache is too large
        if len(cache_data["cache_entries"]) > self.max_cache_entries:
            # Remove oldest entries
            cache_data["cache_entries"] = sorted(
                cache_data["cache_entries"], 
                key=lambda x: x["timestamp"], 
                reverse=True
            )[:self.max_cache_entries]
        
        # Save updated cache
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def get_cache_stats(self) -> Dict:
        """Get comprehensive cache statistics"""
        
        with open(self.stats_file, 'r') as f:
            stats = json.load(f)
        
        with open(self.cache_file, 'r') as f:
            cache_data = json.load(f)
        
        with open(self.users_file, 'r') as f:
            users_data = json.load(f)
        
        # Calculate hit rate
        total_requests = stats["total_requests"]
        hit_rate = (stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate cache size
        cache_size_mb = os.path.getsize(self.cache_file) / (1024 * 1024)
        
        return {
            "cache_performance": {
                "hit_rate_percentage": round(hit_rate, 2),
                "total_requests": total_requests,
                "cache_hits": stats["cache_hits"],
                "cache_misses": stats["cache_misses"],
                "api_calls_saved": stats["api_calls_saved"],
                "average_response_time_ms": round(stats["average_response_time"] * 1000, 2)
            },
            "cache_storage": {
                "total_entries": cache_data["metadata"]["total_entries"],
                "cache_size_mb": round(cache_size_mb, 2),
                "similarity_threshold": self.similarity_threshold
            },
            "user_analytics": {
                "total_users": users_data["metadata"]["total_users"],
                "rate_limit_per_hour": self.rate_limit_per_hour
            },
            "last_updated": stats["last_updated"]
        }
    
    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries"""
        
        with open(self.cache_file, 'r') as f:
            cache_data = json.load(f)
        
        original_count = len(cache_data["cache_entries"])
        
        # Filter out expired entries
        current_time = datetime.now()
        valid_entries = []
        
        for entry in cache_data["cache_entries"]:
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if current_time - entry_time <= timedelta(days=self.cache_expiry_days):
                valid_entries.append(entry)
        
        cache_data["cache_entries"] = valid_entries
        cache_data["metadata"]["total_entries"] = len(valid_entries)
        
        # Save cleaned cache
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        removed_count = original_count - len(valid_entries)
        return removed_count
    
    def get_by_id(self, cache_id: str) -> Optional[Dict]:
        """Get a specific cache entry by ID"""
        
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Search for entry with matching ID
            for entry in cache_data["cache_entries"]:
                if entry["id"] == cache_id:
                    return entry
            
            return None
            
        except Exception as e:
            print(f"Error retrieving cache entry {cache_id}: {e}")
            return None