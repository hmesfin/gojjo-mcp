"""
Authentication and Authorization System

Provides API key authentication, JWT tokens, role-based access control,
and IP whitelisting for the MCP documentation server.
"""

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from enum import Enum

import jwt
from pydantic import BaseModel
import redis.asyncio as redis


class UserRole(Enum):
    """User roles with different access levels"""
    ANONYMOUS = "anonymous"      # 100 requests/hour
    BASIC = "basic"             # 1000 requests/hour
    PREMIUM = "premium"         # 5000 requests/hour
    DEVELOPER = "developer"     # 10000 requests/hour
    ADMIN = "admin"            # Unlimited


class APIKeyType(Enum):
    """Types of API keys"""
    TEMPORARY = "temp"          # 24 hours
    STANDARD = "standard"       # 30 days
    PREMIUM = "premium"         # 1 year
    PERMANENT = "permanent"     # No expiration


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for different user roles"""
    requests_per_hour: int
    burst_limit: int
    cost_multiplier: float = 1.0


# Rate limit configurations by role
RATE_LIMITS = {
    UserRole.ANONYMOUS: RateLimitConfig(100, 20, 1.5),
    UserRole.BASIC: RateLimitConfig(1000, 50, 1.0),
    UserRole.PREMIUM: RateLimitConfig(5000, 100, 0.8),
    UserRole.DEVELOPER: RateLimitConfig(10000, 200, 0.6),
    UserRole.ADMIN: RateLimitConfig(999999, 999, 0.1)
}


class APIKey(BaseModel):
    """API Key model"""
    key_id: str
    key_hash: str
    user_id: str
    role: UserRole
    key_type: APIKeyType
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool = True
    description: str = ""
    ip_whitelist: List[str] = []
    usage_count: int = 0
    last_used: Optional[datetime] = None


class AuthResult(BaseModel):
    """Authentication result"""
    success: bool
    user_id: Optional[str] = None
    role: UserRole = UserRole.ANONYMOUS
    api_key: Optional[APIKey] = None
    error: Optional[str] = None
    rate_limit: Optional[RateLimitConfig] = None


class AuthManager:
    """Authentication and authorization manager"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.jwt_secret = os.getenv('JWT_SECRET', 'dev-secret-change-in-production')
        self.api_key_prefix = "gojjo_mcp"
        self.key_cache = {}  # In-memory cache for API keys
        self.cache_ttl = 300  # 5 minutes
        
    async def generate_api_key(
        self,
        user_id: str,
        role: UserRole = UserRole.BASIC,
        key_type: APIKeyType = APIKeyType.STANDARD,
        description: str = "",
        ip_whitelist: List[str] = None
    ) -> Tuple[str, APIKey]:
        """Generate a new API key"""
        
        # Generate secure random key
        key_id = secrets.token_urlsafe(16)
        raw_key = secrets.token_urlsafe(32)
        full_key = f"{self.api_key_prefix}_{key_id}_{raw_key}"
        
        # Hash the key for storage
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        # Calculate expiration
        expires_at = None
        if key_type == APIKeyType.TEMPORARY:
            expires_at = datetime.utcnow() + timedelta(hours=24)
        elif key_type == APIKeyType.STANDARD:
            expires_at = datetime.utcnow() + timedelta(days=30)
        elif key_type == APIKeyType.PREMIUM:
            expires_at = datetime.utcnow() + timedelta(days=365)
        # PERMANENT keys don't expire
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            role=role,
            key_type=key_type,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            description=description,
            ip_whitelist=ip_whitelist or []
        )
        
        # Store in Redis
        if self.redis_client:
            await self.redis_client.setex(
                f"api_key:{key_id}",
                86400 * 365,  # 1 year in Redis
                api_key.json()
            )
        
        return full_key, api_key
    
    async def authenticate_api_key(
        self,
        api_key: str,
        client_ip: str = None
    ) -> AuthResult:
        """Authenticate an API key"""
        
        try:
            # Parse API key
            if not api_key.startswith(f"{self.api_key_prefix}_"):
                return AuthResult(
                    success=False,
                    error="Invalid API key format"
                )
            
            parts = api_key.split("_")
            if len(parts) != 4:  # prefix_keyid_rawkey
                return AuthResult(
                    success=False,
                    error="Invalid API key format"
                )
            
            key_id = parts[2]
            
            # Get from cache first
            cached_key = self.key_cache.get(key_id)
            if cached_key and cached_key['expires'] > time.time():
                api_key_obj = APIKey(**cached_key['data'])
            else:
                # Get from Redis
                if self.redis_client:
                    key_data = await self.redis_client.get(f"api_key:{key_id}")
                    if not key_data:
                        return AuthResult(
                            success=False,
                            error="API key not found"
                        )
                    api_key_obj = APIKey.parse_raw(key_data)
                else:
                    return AuthResult(
                        success=False,
                        error="Authentication service unavailable"
                    )
            
            # Verify key hash
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            if key_hash != api_key_obj.key_hash:
                return AuthResult(
                    success=False,
                    error="Invalid API key"
                )
            
            # Check if key is active
            if not api_key_obj.is_active:
                return AuthResult(
                    success=False,
                    error="API key is disabled"
                )
            
            # Check expiration
            if api_key_obj.expires_at and datetime.utcnow() > api_key_obj.expires_at:
                return AuthResult(
                    success=False,
                    error="API key has expired"
                )
            
            # Check IP whitelist
            if api_key_obj.ip_whitelist and client_ip:
                if client_ip not in api_key_obj.ip_whitelist:
                    return AuthResult(
                        success=False,
                        error="IP address not authorized"
                    )
            
            # Update usage statistics
            api_key_obj.usage_count += 1
            api_key_obj.last_used = datetime.utcnow()
            
            # Update cache
            self.key_cache[key_id] = {
                'data': api_key_obj.dict(),
                'expires': time.time() + self.cache_ttl
            }
            
            # Update Redis (async, don't wait)
            if self.redis_client:
                asyncio.create_task(
                    self.redis_client.setex(
                        f"api_key:{key_id}",
                        86400 * 365,
                        api_key_obj.json()
                    )
                )
            
            return AuthResult(
                success=True,
                user_id=api_key_obj.user_id,
                role=api_key_obj.role,
                api_key=api_key_obj,
                rate_limit=RATE_LIMITS[api_key_obj.role]
            )
            
        except Exception as e:
            return AuthResult(
                success=False,
                error=f"Authentication error: {str(e)}"
            )
    
    async def authenticate_request(
        self,
        headers: Dict[str, str],
        client_ip: str = None
    ) -> AuthResult:
        """Authenticate an HTTP request"""
        
        # Try API key in header
        api_key = headers.get('X-API-Key') or headers.get('Authorization', '').replace('Bearer ', '')
        
        if api_key:
            return await self.authenticate_api_key(api_key, client_ip)
        
        # No authentication provided - return anonymous access
        return AuthResult(
            success=True,
            role=UserRole.ANONYMOUS,
            rate_limit=RATE_LIMITS[UserRole.ANONYMOUS]
        )
    
    def generate_jwt_token(
        self,
        user_id: str,
        role: UserRole,
        expires_hours: int = 24
    ) -> str:
        """Generate a JWT token"""
        
        payload = {
            'user_id': user_id,
            'role': role.value,
            'exp': datetime.utcnow() + timedelta(hours=expires_hours),
            'iat': datetime.utcnow(),
            'iss': 'gojjo-mcp-server'
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> AuthResult:
        """Verify a JWT token"""
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            role = UserRole(payload.get('role', 'anonymous'))
            
            return AuthResult(
                success=True,
                user_id=payload.get('user_id'),
                role=role,
                rate_limit=RATE_LIMITS[role]
            )
            
        except jwt.ExpiredSignatureError:
            return AuthResult(
                success=False,
                error="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            return AuthResult(
                success=False,
                error=f"Invalid token: {str(e)}"
            )
    
    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key"""
        
        try:
            if self.redis_client:
                # Mark as inactive in Redis
                key_data = await self.redis_client.get(f"api_key:{key_id}")
                if key_data:
                    api_key_obj = APIKey.parse_raw(key_data)
                    api_key_obj.is_active = False
                    
                    await self.redis_client.setex(
                        f"api_key:{key_id}",
                        86400 * 365,
                        api_key_obj.json()
                    )
                    
                    # Remove from cache
                    self.key_cache.pop(key_id, None)
                    
                    return True
            
            return False
            
        except Exception:
            return False
    
    async def get_user_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user"""
        
        keys = []
        
        if self.redis_client:
            try:
                # Get all user's API key IDs
                key_ids = await self.redis_client.smembers(f"user:{user_id}:keys")
                
                for key_id in key_ids:
                    key_data = await self.redis_client.hgetall(f"api_key:{key_id}")
                    if key_data:
                        api_key = APIKey(
                            key_id=key_id,
                            key_hash=key_data.get('key_hash', ''),
                            user_id=key_data.get('user_id', ''),
                            role=UserRole(key_data.get('role', 'basic')),
                            key_type=APIKeyType(key_data.get('key_type', 'standard')),
                            created_at=datetime.fromisoformat(key_data.get('created_at', datetime.utcnow().isoformat())),
                            expires_at=datetime.fromisoformat(key_data['expires_at']) if key_data.get('expires_at') else None,
                            is_active=key_data.get('is_active', 'true').lower() == 'true',
                            description=key_data.get('description', ''),
                            ip_whitelist=json.loads(key_data.get('ip_whitelist', '[]')),
                            usage_count=int(key_data.get('usage_count', 0)),
                            last_used=datetime.fromisoformat(key_data['last_used']) if key_data.get('last_used') else None
                        )
                        keys.append(api_key)
            except Exception as e:
                print(f"Error getting user keys: {e}")
        
        return keys
    
    async def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get API key information for a user (for web interface)"""
        try:
            keys = await self.get_user_keys(user_id)
            return [{
                'id': key.key_id,
                'key': f"{self.api_key_prefix}_{key.key_id[:8]}..." if key.key_id else "N/A",
                'role': key.role.value,
                'type': key.key_type.value,
                'created_at': key.created_at.isoformat(),
                'last_used': key.last_used.isoformat() if key.last_used else None,
                'usage_count': key.usage_count,
                'is_active': key.is_active,
                'description': key.description
            } for key in keys]
        except Exception as e:
            print(f"Error getting user API keys: {e}")
            return []
    
    async def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        try:
            if not self.redis_client:
                return {'current': {}, 'historical': [], 'total_requests': 0}
                
            # Get current rate limit usage
            current_usage = {}
            for period in ['per_second', 'per_minute', 'per_hour']:
                key = f"rate_limit:{user_id}:{period}"
                usage = await self.redis_client.get(key)
                current_usage[period] = int(usage) if usage else 0
            
            # Get historical usage (last 24 hours)
            now = datetime.utcnow()
            historical_usage = []
            
            for hour in range(24):
                hour_key = f"usage:{user_id}:{(now - timedelta(hours=hour)).strftime('%Y%m%d%H')}"
                usage = await self.redis_client.get(hour_key)
                historical_usage.append({
                    'hour': (now - timedelta(hours=hour)).strftime('%Y-%m-%d %H:00'),
                    'requests': int(usage) if usage else 0
                })
            
            return {
                'current': current_usage,
                'historical': list(reversed(historical_usage)),
                'total_requests': sum(item['requests'] for item in historical_usage)
            }
        except Exception as e:
            print(f"Error getting user usage: {e}")
            return {'current': {}, 'historical': [], 'total_requests': 0}
    
    def is_admin(self, auth_result: AuthResult) -> bool:
        """Check if user has admin privileges"""
        return auth_result.success and auth_result.role == UserRole.ADMIN
    
    def has_role(self, auth_result: AuthResult, required_role: UserRole) -> bool:
        """Check if user has required role or higher"""
        if not auth_result.success:
            return False
        
        role_hierarchy = {
            UserRole.ANONYMOUS: 0,
            UserRole.BASIC: 1,
            UserRole.PREMIUM: 2,
            UserRole.DEVELOPER: 3,
            UserRole.ADMIN: 4
        }
        
        user_level = role_hierarchy.get(auth_result.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level


class AuthMiddleware:
    """Authentication middleware for web requests"""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
    
    async def authenticate_request(self, request) -> AuthResult:
        """Authenticate a web request"""
        
        headers = dict(request.headers)
        client_ip = self._get_client_ip(request)
        
        return await self.auth_manager.authenticate_request(headers, client_ip)
    
    def _get_client_ip(self, request) -> str:
        """Extract client IP from request"""
        
        # Check common proxy headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to remote address
        return getattr(request, 'remote', '127.0.0.1')


# Example usage and admin utilities
async def create_admin_key(auth_manager: AuthManager) -> Tuple[str, APIKey]:
    """Create an admin API key - for initial setup only"""
    
    return await auth_manager.generate_api_key(
        user_id="admin",
        role=UserRole.ADMIN,
        key_type=APIKeyType.PERMANENT,
        description="Admin key for server management"
    )


async def create_developer_key(auth_manager: AuthManager, user_id: str) -> Tuple[str, APIKey]:
    """Create a developer API key"""
    
    return await auth_manager.generate_api_key(
        user_id=user_id,
        role=UserRole.DEVELOPER,
        key_type=APIKeyType.PREMIUM,
        description=f"Developer key for {user_id}"
    )


def create_public_demo_keys(auth_manager: AuthManager) -> Dict[str, str]:
    """Create some demo keys for documentation"""
    
    # This would be used to generate example keys for documentation
    # NOT for production use
    return {
        "basic_demo": "gojjo_mcp_demo_basic_key_example",
        "premium_demo": "gojjo_mcp_demo_premium_key_example"
    }