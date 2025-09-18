import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

class AdminAuth:
    """
    Simple admin authentication system for the admin panel
    """
    
    def __init__(self):
        # Get credentials from configuration (lazy loading)
        self._config = None
        self._admin_credentials = None
        
        # Active sessions store
        self.active_sessions = {}  # token: {username, expires, created_at}
        
        # Session timeout (will be loaded from config)
        self.session_timeout = timedelta(hours=24)  # default
        
        # Security bearer for token validation
        self.security = HTTPBearer()

    @property
    def admin_credentials(self):
        """Lazy load admin credentials from config"""
        if self._admin_credentials is None:
            from config import get_config
            config = get_config()
            self._admin_credentials = {
                config.admin.username: config.admin.password
            }
            # Also update session timeout
            self.session_timeout = timedelta(hours=config.admin.session_timeout_hours)
        return self._admin_credentials
    
    def _hash_password(self, password: str) -> str:
        """Hash password for secure storage (basic implementation)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate user credentials"""
        return (username in self.admin_credentials and 
                self.admin_credentials[username] == password)
    
    def create_session(self, username: str) -> str:
        """Create a new session token"""
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Store session
        self.active_sessions[token] = {
            "username": username,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + self.session_timeout,
            "last_activity": datetime.now()
        }
        
        return token
    
    def validate_session(self, token: str) -> Optional[Dict]:
        """Validate session token"""
        if token not in self.active_sessions:
            return None
        
        session = self.active_sessions[token]
        
        # Check if session expired
        if datetime.now() > session["expires_at"]:
            del self.active_sessions[token]
            return None
        
        # Update last activity
        session["last_activity"] = datetime.now()
        
        return session
    
    def logout_session(self, token: str) -> bool:
        """Logout and remove session"""
        if token in self.active_sessions:
            del self.active_sessions[token]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        current_time = datetime.now()
        expired_tokens = []
        
        for token, session in self.active_sessions.items():
            if current_time > session["expires_at"]:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.active_sessions[token]
        
        return len(expired_tokens)
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """Dependency to get current authenticated user"""
        token = credentials.credentials
        session = self.validate_session(token)
        
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return session

# Global admin auth instance
admin_auth = AdminAuth()

class AdminDataManager:
    """
    Manager for admin panel data access and operations
    """
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
    
    def get_user_analytics(self) -> Dict:
        """Get comprehensive user analytics"""
        try:
            with open(self.cache_manager.users_file, 'r') as f:
                users_data = json.load(f)
            
            # Calculate statistics
            total_users = len(users_data["users"])
            active_users_24h = 0
            top_users = []
            countries = {}
            browsers = {}
            devices = {}
            
            current_time = datetime.now()
            
            for fingerprint, user_data in users_data["users"].items():
                # Check if active in last 24 hours
                last_seen = datetime.fromisoformat(user_data["last_seen"])
                if current_time - last_seen <= timedelta(hours=24):
                    active_users_24h += 1
                
                # Top users by request count
                top_users.append({
                    "fingerprint": fingerprint,  # Keep full fingerprint for API calls
                    "fingerprint_display": fingerprint[:12] + "...",  # Truncated for display
                    "request_count": user_data["request_count"],
                    "first_seen": user_data["first_seen"],
                    "last_seen": user_data["last_seen"],
                    "ip_count": len(user_data.get("ip_addresses", [])),
                    "countries": user_data.get("countries", ["unknown"])
                })
                
                # Country statistics
                for country in user_data.get("countries", ["unknown"]):
                    countries[country] = countries.get(country, 0) + 1
                
                # Browser statistics (from user agents)
                for ua in user_data.get("user_agents", []):
                    if "chrome" in ua.lower():
                        browsers["Chrome"] = browsers.get("Chrome", 0) + 1
                    elif "firefox" in ua.lower():
                        browsers["Firefox"] = browsers.get("Firefox", 0) + 1
                    elif "safari" in ua.lower():
                        browsers["Safari"] = browsers.get("Safari", 0) + 1
                    elif "edge" in ua.lower():
                        browsers["Edge"] = browsers.get("Edge", 0) + 1
                    else:
                        browsers["Other"] = browsers.get("Other", 0) + 1
            
            # Sort top users
            top_users.sort(key=lambda x: x["request_count"], reverse=True)
            
            return {
                "total_users": total_users,
                "active_users_24h": active_users_24h,
                "top_users": top_users[:10],  # Top 10 users
                "country_distribution": dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]),
                "browser_distribution": browsers,
                "registration_trend": self._get_registration_trend(users_data["users"])
            }
            
        except Exception as e:
            return {"error": f"Could not load user analytics: {str(e)}"}
    
    def get_cache_details(self) -> Dict:
        """Get detailed cache information"""
        try:
            with open(self.cache_manager.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            entries = cache_data["cache_entries"]
            
            # Calculate statistics
            total_entries = len(entries)
            total_size = sum(len(str(entry)) for entry in entries)
            
            # Recent entries
            recent_entries = sorted(entries, key=lambda x: x["timestamp"], reverse=True)[:20]
            
            # Text length distribution
            text_lengths = [entry["metadata"]["text_length"] for entry in entries]
            avg_text_length = sum(text_lengths) / len(text_lengths) if text_lengths else 0
            
            # Popular analysis patterns
            mbti_types = {}
            for entry in entries:
                if "response" in entry and "mbti_type" in entry["response"]:
                    mbti = entry["response"]["mbti_type"]
                    mbti_types[mbti] = mbti_types.get(mbti, 0) + 1
            
            return {
                "total_entries": total_entries,
                "cache_size_bytes": total_size,
                "cache_size_mb": round(total_size / (1024 * 1024), 2),
                "average_text_length": round(avg_text_length, 1),
                "recent_entries": [
                    {
                        "id": entry["id"],
                        "timestamp": entry["timestamp"],
                        "text_preview": entry["input_text"][:100] + "..." if len(entry["input_text"]) > 100 else entry["input_text"],
                        "text_length": entry["metadata"]["text_length"],
                        "user_ip": entry["metadata"]["ip"],
                        "mbti_type": entry.get("response", {}).get("mbti_type", "N/A")
                    }
                    for entry in recent_entries
                ],
                "mbti_distribution": dict(sorted(mbti_types.items(), key=lambda x: x[1], reverse=True)),
                "cache_performance": self.cache_manager.get_cache_stats()["cache_performance"]
            }
            
        except Exception as e:
            return {"error": f"Could not load cache details: {str(e)}"}
    
    def get_error_logs(self) -> Dict:
        """Get error logs and analysis"""
        try:
            import os
            import glob
            
            error_files = glob.glob(os.path.join(self.cache_manager.cache_dir, "error_*.json"))
            error_logs = []
            
            for file_path in sorted(error_files, reverse=True)[:50]:  # Last 50 errors
                try:
                    with open(file_path, 'r') as f:
                        error_data = json.load(f)
                        error_logs.append({
                            "file": os.path.basename(file_path),
                            "timestamp": error_data.get("timestamp", "unknown"),
                            "error_type": error_data.get("error_type", "unknown"),
                            "message": error_data.get("message", "unknown"),
                            "text_preview": error_data.get("text", "")[:100] + "..." if error_data.get("text", "") else "N/A"
                        })
                except:
                    continue
            
            # Error statistics
            error_types = {}
            for error in error_logs:
                error_type = error["error_type"]
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            return {
                "total_errors": len(error_logs),
                "recent_errors": error_logs[:20],
                "error_type_distribution": error_types,
                "error_files_found": len(error_files)
            }
            
        except Exception as e:
            return {"error": f"Could not load error logs: {str(e)}"}
    
    def _get_registration_trend(self, users_data: Dict) -> Dict:
        """Calculate user registration trend"""
        daily_registrations = {}
        
        for user_data in users_data.values():
            try:
                first_seen = datetime.fromisoformat(user_data["first_seen"])
                date_key = first_seen.strftime("%Y-%m-%d")
                daily_registrations[date_key] = daily_registrations.get(date_key, 0) + 1
            except:
                continue
        
        # Get last 30 days
        dates = sorted(daily_registrations.keys())[-30:]
        trend = {date: daily_registrations.get(date, 0) for date in dates}
        
        return trend
    
    def get_user_details(self, fingerprint: str) -> Optional[Dict]:
        """Get detailed information for a specific user"""
        try:
            with open(self.cache_manager.users_file, 'r') as f:
                users_data = json.load(f)
            
            if fingerprint not in users_data["users"]:
                return None
            
            user_data = users_data["users"][fingerprint]
            
            # Enhance user data with additional processing
            enhanced_data = user_data.copy()
            enhanced_data["fingerprint"] = fingerprint
            
            # Parse browser info if available
            if "user_agents" in user_data and user_data["user_agents"]:
                from user_tracker import UserInfoExtractor
                # Use the first user agent for browser info
                enhanced_data["browser_info"] = UserInfoExtractor._parse_user_agent(user_data["user_agents"][0])
            
            return enhanced_data
            
        except Exception as e:
            return None

import json