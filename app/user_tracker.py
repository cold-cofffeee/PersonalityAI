from fastapi import Request
import httpx
import json
from typing import Dict, Optional

class UserInfoExtractor:
    """
    Extract comprehensive user information for tracking and security
    """
    
    @staticmethod
    def extract_client_info(request: Request) -> Dict:
        """Extract detailed client information from request"""
        
        # Get basic request info
        client_ip = UserInfoExtractor._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Extract browser and device info from user agent
        browser_info = UserInfoExtractor._parse_user_agent(user_agent)
        
        # Get additional headers for detailed tracking
        accept_language = request.headers.get("accept-language", "unknown")
        accept_encoding = request.headers.get("accept-encoding", "unknown")
        referer = request.headers.get("referer", "unknown")
        dnt = request.headers.get("dnt", "unknown")  # Do Not Track
        upgrade_insecure = request.headers.get("upgrade-insecure-requests", "unknown")
        
        # Extract more detailed browser capabilities
        detailed_info = UserInfoExtractor._extract_detailed_capabilities(request.headers)
        
        return {
            "ip": client_ip,
            "user_agent": user_agent,
            "browser_info": browser_info,
            "accept_language": accept_language,
            "accept_encoding": accept_encoding,
            "referer": referer,
            "host": request.headers.get("host", "unknown"),
            "connection": request.headers.get("connection", "unknown"),
            "request_method": request.method,
            "request_url": str(request.url),
            "country": "unknown",  # Will be updated by IP geolocation if needed
            "detailed_capabilities": detailed_info,
            "security_headers": {
                "dnt": dnt,
                "upgrade_insecure_requests": upgrade_insecure,
                "sec_fetch_site": request.headers.get("sec-fetch-site", "unknown"),
                "sec_fetch_mode": request.headers.get("sec-fetch-mode", "unknown"),
                "sec_fetch_dest": request.headers.get("sec-fetch-dest", "unknown")
            }
        }
    
    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Get real client IP, considering proxies"""
        
        # Check for forwarded headers (common with proxies/load balancers)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP if there are multiple
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    @staticmethod
    def _parse_user_agent(user_agent: str) -> Dict:
        """Parse user agent string to extract browser and device info"""
        
        if not user_agent or user_agent == "unknown":
            return {
                "browser": "unknown",
                "version": "unknown",
                "os": "unknown",
                "device": "unknown",
                "is_mobile": False,
                "is_bot": False
            }
        
        user_agent_lower = user_agent.lower()
        
        # Detect bots
        bot_indicators = ["bot", "crawler", "spider", "scraper", "fetch", "curl", "wget"]
        is_bot = any(indicator in user_agent_lower for indicator in bot_indicators)
        
        # Detect mobile
        mobile_indicators = ["mobile", "android", "iphone", "ipad", "tablet"]
        is_mobile = any(indicator in user_agent_lower for indicator in mobile_indicators)
        
        # Detect browser
        browser = "unknown"
        version = "unknown"
        
        if "chrome" in user_agent_lower and "edg" not in user_agent_lower:
            browser = "Chrome"
            # Extract version
            try:
                version = user_agent.split("Chrome/")[1].split(" ")[0]
            except:
                pass
        elif "firefox" in user_agent_lower:
            browser = "Firefox"
            try:
                version = user_agent.split("Firefox/")[1].split(" ")[0]
            except:
                pass
        elif "safari" in user_agent_lower and "chrome" not in user_agent_lower:
            browser = "Safari"
            try:
                version = user_agent.split("Safari/")[1].split(" ")[0]
            except:
                pass
        elif "edg" in user_agent_lower:
            browser = "Edge"
            try:
                version = user_agent.split("Edg/")[1].split(" ")[0]
            except:
                pass
        elif "opera" in user_agent_lower or "opr" in user_agent_lower:
            browser = "Opera"
        
        # Detect OS
        os_name = "unknown"
        if "windows" in user_agent_lower:
            os_name = "Windows"
            if "windows nt 10" in user_agent_lower:
                os_name = "Windows 10/11"
            elif "windows nt 6" in user_agent_lower:
                os_name = "Windows 7/8"
        elif "mac os" in user_agent_lower or "macos" in user_agent_lower:
            os_name = "macOS"
        elif "linux" in user_agent_lower:
            os_name = "Linux"
        elif "android" in user_agent_lower:
            os_name = "Android"
        elif "ios" in user_agent_lower or "iphone" in user_agent_lower:
            os_name = "iOS"
        
        # Detect device type
        device = "desktop"
        if is_mobile:
            if "ipad" in user_agent_lower or "tablet" in user_agent_lower:
                device = "tablet"
            else:
                device = "mobile"
        
        return {
            "browser": browser,
            "version": version,
            "os": os_name,
            "device": device,
            "is_mobile": is_mobile,
            "is_bot": is_bot
        }
    
    @staticmethod
    def _extract_detailed_capabilities(headers) -> Dict:
        """Extract detailed browser and device capabilities from headers"""
        
        # Extract supported compression methods
        accept_encoding = headers.get("accept-encoding", "").lower()
        compression_support = {
            "gzip": "gzip" in accept_encoding,
            "deflate": "deflate" in accept_encoding,
            "br": "br" in accept_encoding,  # Brotli compression
            "zstd": "zstd" in accept_encoding
        }
        
        # Extract language preferences with priority
        accept_language = headers.get("accept-language", "")
        languages = []
        if accept_language and accept_language != "unknown":
            # Parse language preference format: en-US,en;q=0.9,es;q=0.8
            lang_parts = accept_language.split(",")
            for part in lang_parts[:5]:  # Limit to top 5 languages
                lang = part.split(";")[0].strip()
                if lang:
                    languages.append(lang)
        
        # Analyze user agent for more capabilities
        user_agent = headers.get("user-agent", "").lower()
        
        # Detect browser engine
        engine = "unknown"
        if "webkit" in user_agent:
            if "blink" in user_agent or "chrome" in user_agent:
                engine = "blink"
            else:
                engine = "webkit"
        elif "gecko" in user_agent:
            engine = "gecko"
        elif "trident" in user_agent:
            engine = "trident"
        
        # Detect 64-bit vs 32-bit
        architecture = "unknown"
        if "win64" in user_agent or "x64" in user_agent or "amd64" in user_agent:
            architecture = "64-bit"
        elif "win32" in user_agent or "i386" in user_agent:
            architecture = "32-bit"
        elif "arm64" in user_agent or "aarch64" in user_agent:
            architecture = "ARM64"
        elif "arm" in user_agent:
            architecture = "ARM"
        
        # Detect security capabilities
        security_info = {
            "https_supported": headers.get("upgrade-insecure-requests") == "1",
            "strict_transport_security": "strict-transport-security" in str(headers.keys()).lower(),
            "fetch_metadata_support": any(key.startswith("sec-fetch-") for key in headers.keys())
        }
        
        # Screen and viewport hints (from various headers)
        display_hints = {
            "viewport_width": "unknown",
            "device_pixel_ratio": "unknown",
            "color_depth": "unknown"
        }
        
        # Try to extract from client hints if available
        if "sec-ch-viewport-width" in headers:
            display_hints["viewport_width"] = headers.get("sec-ch-viewport-width")
        if "sec-ch-dpr" in headers:
            display_hints["device_pixel_ratio"] = headers.get("sec-ch-dpr")
        
        return {
            "compression_support": compression_support,
            "preferred_languages": languages,
            "browser_engine": engine,
            "architecture": architecture,
            "security_capabilities": security_info,
            "display_hints": display_hints,
            "connection_type": headers.get("connection", "unknown").lower(),
            "cache_control": headers.get("cache-control", "unknown")
        }
    
    @staticmethod
    async def get_ip_geolocation(ip: str) -> Optional[Dict]:
        """Get geolocation info for IP address (optional, requires external API)"""
        
        # Skip for local/private IPs
        if ip in ["unknown", "127.0.0.1", "localhost"] or ip.startswith("192.168.") or ip.startswith("10."):
            return {"country": "Local", "city": "Local", "region": "Local"}
        
        try:
            # Using a free IP geolocation service (ip-api.com)
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"http://ip-api.com/json/{ip}?fields=country,regionName,city,status")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        return {
                            "country": data.get("country", "unknown"),
                            "region": data.get("regionName", "unknown"),
                            "city": data.get("city", "unknown")
                        }
        except:
            # If geolocation fails, continue without it
            pass
        
        return {"country": "unknown", "region": "unknown", "city": "unknown"}

# Security utility functions
class SecurityUtils:
    """
    Security utilities for request validation and abuse prevention
    """
    
    @staticmethod
    def is_suspicious_request(request_data: Dict) -> bool:
        """Check if request shows suspicious patterns"""
        
        browser_info = request_data.get("browser_info", {})
        
        # Check for known bot patterns
        if browser_info.get("is_bot", False):
            return True
        
        # Check for missing or suspicious user agent
        user_agent = request_data.get("user_agent", "").lower()
        suspicious_patterns = [
            "python-requests", "curl", "wget", "postman", "insomnia",
            "test", "scan", "hack", "exploit"
        ]
        
        if any(pattern in user_agent for pattern in suspicious_patterns):
            return True
        
        # Check for unusual browser combinations
        browser = browser_info.get("browser", "unknown")
        if browser == "unknown" and not browser_info.get("is_mobile", False):
            return True
        
        return False
    
    @staticmethod
    def validate_text_input(text: str) -> Dict:
        """Validate text input for security and quality"""
        
        if not text or not text.strip():
            return {"valid": False, "error": "Empty text provided"}
        
        text_clean = text.strip()
        
        # Length checks
        if len(text_clean) < 10:
            return {"valid": False, "error": "Text too short (minimum 10 characters)"}
        
        if len(text_clean) > 5000:
            return {"valid": False, "error": "Text too long (maximum 5000 characters)"}
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r"<script", r"javascript:", r"eval\(", r"alert\(",
            r"document\.", r"window\.", r"__", r"sql", r"drop table"
        ]
        
        text_lower = text_clean.lower()
        for pattern in suspicious_patterns:
            if pattern.lower() in text_lower:
                return {"valid": False, "error": "Text contains potentially harmful content"}
        
        # Check for repeated characters (spam detection)
        if len(set(text_clean)) < len(text_clean) * 0.1:  # Less than 10% unique characters
            return {"valid": False, "error": "Text appears to be spam or low quality"}
        
        return {"valid": True, "cleaned_text": text_clean}