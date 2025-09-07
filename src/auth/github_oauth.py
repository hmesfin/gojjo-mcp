"""
GitHub OAuth integration for Django Vue MCP Documentation Server
Provides seamless developer authentication with automatic API key generation.
"""

import os
import json
import logging
import secrets
import hashlib
import base64
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs
import httpx
import redis.asyncio as redis
from dataclasses import dataclass, asdict

from security.auth import AuthManager, UserRole, APIKeyType

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class GitHubUser:
    """GitHub user information (only fields we actually use)."""
    id: int
    login: str
    name: Optional[str]
    email: Optional[str]
    avatar_url: str
    company: Optional[str] = None
    bio: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    created_at: str = ""
    # Additional useful fields
    node_id: Optional[str] = None
    location: Optional[str] = None
    blog: Optional[str] = None
    twitter_username: Optional[str] = None
    following: int = 0
    updated_at: Optional[str] = None


@dataclass
class OAuthSession:
    """OAuth session data."""
    state: str
    code_verifier: str
    redirect_uri: str
    created_at: datetime
    expires_at: datetime


class GitHubOAuthManager:
    """
    GitHub OAuth integration for developer authentication.
    
    Features:
    - PKCE flow for enhanced security
    - Automatic API key generation
    - Role assignment based on GitHub profile
    - Session management with Redis
    - Rate limiting for OAuth endpoints
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.auth_manager = AuthManager(redis_client)
        
        # OAuth configuration
        self.client_id = os.getenv('GITHUB_CLIENT_ID')
        self.client_secret = os.getenv('GITHUB_CLIENT_SECRET')
        self.base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("GitHub OAuth credentials not configured")
        
        # GitHub API endpoints
        self.auth_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.api_url = "https://api.github.com"
        
        # Redis keys
        self.session_key = "oauth:session:{state}"
        self.user_key = "oauth:user:{user_id}"
        self.token_key = "oauth:token:{user_id}"
        
        # Session configuration
        self.session_timeout = 3600  # 1 hour
        self.token_timeout = 86400 * 30  # 30 days
    
    async def generate_auth_url(self, redirect_uri: str) -> Tuple[str, str]:
        """
        Generate GitHub OAuth authorization URL with PKCE.
        
        Returns:
            Tuple of (auth_url, state) for session tracking
        """
        # Generate PKCE parameters
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)
        state = secrets.token_urlsafe(32)
        
        # Store session data
        session = OAuthSession(
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=self.session_timeout)
        )
        
        await self.redis_client.setex(
            self.session_key.format(state=state),
            self.session_timeout,
            json.dumps(asdict(session), default=str)
        )
        
        # Build authorization URL
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': 'read:user user:email',
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'allow_signup': 'true'
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        return auth_url, state
    
    async def handle_callback(
        self, 
        code: str, 
        state: str, 
        client_ip: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        """
        Handle OAuth callback and complete authentication.
        
        Returns:
            Tuple of (success, user_data, api_key, session_token)
        """
        # Validate session
        session_data = await self.redis_client.get(
            self.session_key.format(state=state)
        )
        
        if not session_data:
            return False, None, "Invalid or expired OAuth session", None
        
        try:
            session = json.loads(session_data)
            
            # Check session expiry
            expires_at = datetime.fromisoformat(session['expires_at'])
            if datetime.utcnow() > expires_at:
                return False, None, "OAuth session expired", None
            
            # Exchange code for access token
            token_data = await self._exchange_code_for_token(
                code, session['code_verifier'], session['redirect_uri']
            )
            
            if not token_data:
                return False, None, "Failed to exchange OAuth code", None
            
            # Get user information
            user_data = await self._get_user_info(token_data['access_token'])
            if not user_data:
                return False, None, "Failed to fetch user information", None
            
            # Create or update user in our system
            # Extract only the fields we need from GitHub user data
            github_user = GitHubUser(
                id=user_data['id'],
                login=user_data['login'],
                name=user_data.get('name'),
                email=user_data.get('email'),
                avatar_url=user_data['avatar_url'],
                company=user_data.get('company'),
                bio=user_data.get('bio'),
                public_repos=user_data.get('public_repos', 0),
                followers=user_data.get('followers', 0),
                created_at=user_data.get('created_at', ''),
                # Optional fields
                node_id=user_data.get('node_id'),
                location=user_data.get('location'),
                blog=user_data.get('blog'),
                twitter_username=user_data.get('twitter_username'),
                following=user_data.get('following', 0),
                updated_at=user_data.get('updated_at')
            )
            api_key = await self._create_or_update_user(github_user, client_ip)
            
            # Store user session
            session_token = await self._store_user_session(github_user, token_data['access_token'])
            
            # Clean up OAuth session
            await self.redis_client.delete(self.session_key.format(state=state))
            
            return True, asdict(github_user), api_key, session_token
            
        except Exception as e:
            import traceback
            error_details = f"OAuth error: {str(e)}\nTraceback: {traceback.format_exc()}"
            logger.error(error_details)
            return False, None, f"OAuth error: {str(e)}", None
    
    async def get_user_by_session(self, session_token: str) -> Optional[GitHubUser]:
        """Get user data by session token."""
        try:
            # Extract user ID from session token
            user_id = await self.redis_client.get(f"session:{session_token}")
            if not user_id:
                return None
            
            # Get user data
            user_data = await self.redis_client.get(
                self.user_key.format(user_id=user_id.decode())
            )
            
            if not user_data:
                return None
            
            return GitHubUser(**json.loads(user_data))
            
        except Exception:
            return None
    
    async def revoke_user_session(self, session_token: str) -> bool:
        """Revoke user session."""
        try:
            user_id = await self.redis_client.get(f"session:{session_token}")
            if user_id:
                # Remove session mapping
                await self.redis_client.delete(f"session:{session_token}")
                
                # Remove user session data
                user_id_str = user_id.decode()
                await self.redis_client.delete(
                    self.token_key.format(user_id=user_id_str)
                )
                
                return True
            return False
            
        except Exception:
            return False
    
    async def get_user_api_keys(self, github_user_id: str) -> Dict[str, Any]:
        """Get API keys for a GitHub user."""
        api_keys = await self.auth_manager.get_user_api_keys(f"github:{github_user_id}")
        return {
            "keys": api_keys,
            "usage": await self.auth_manager.get_user_usage(f"github:{github_user_id}")
        }
    
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier (43-128 characters)."""
        return secrets.token_urlsafe(96)[:128]  # Ensure max length
    
    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge using S256 method."""
        # SHA256 hash the verifier
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        # Base64url encode (without padding)
        challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        return challenge
    
    async def _exchange_code_for_token(
        self, 
        code: str, 
        code_verifier: str, 
        redirect_uri: str
    ) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        try:
            async with httpx.AsyncClient() as client:
                data = {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'code_verifier': code_verifier,
                    'redirect_uri': redirect_uri
                }
                
                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'Django-Vue-MCP-Server/1.0'
                }
                
                response = await client.post(
                    self.token_url, 
                    data=data, 
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                    
        except Exception:
            pass
        
        return None
    
    async def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from GitHub API."""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Django-Vue-MCP-Server/1.0'
                }
                
                # Get user profile
                user_response = await client.get(
                    f'{self.api_url}/user',
                    headers=headers,
                    timeout=30
                )
                
                if user_response.status_code != 200:
                    return None
                
                user_data = user_response.json()
                
                # Get user email if not public
                if not user_data.get('email'):
                    email_response = await client.get(
                        f'{self.api_url}/user/emails',
                        headers=headers,
                        timeout=30
                    )
                    
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        primary_email = next(
                            (email for email in emails if email['primary']), 
                            None
                        )
                        if primary_email:
                            user_data['email'] = primary_email['email']
                
                return user_data
                
        except Exception:
            pass
        
        return None
    
    async def _create_or_update_user(
        self, 
        github_user: GitHubUser, 
        client_ip: str
    ) -> str:
        """Create or update user and return API key."""
        user_id = f"github:{github_user.id}"
        
        # Determine user role based on GitHub profile
        role = self._determine_user_role(github_user)
        
        # Check if user already exists
        existing_keys = await self.auth_manager.get_user_keys(user_id)
        
        if existing_keys:
            # Return existing API key (full key, not truncated)
            # We need to reconstruct the full key from the stored data
            existing_key = existing_keys[0]
            full_key = f"{self.auth_manager.api_key_prefix}_{existing_key.key_id}"
            return full_key
        else:
            # Create new API key
            key_string, api_key = await self.auth_manager.generate_api_key(
                user_id=user_id,
                role=role,
                key_type=APIKeyType.STANDARD,
                description=f"GitHub OAuth for @{github_user.login}",
                ip_whitelist=[client_ip] if role in [UserRole.PREMIUM, UserRole.DEVELOPER] else None
            )
            
            return key_string
    
    def _determine_user_role(self, github_user: GitHubUser) -> UserRole:
        """Determine user role based on GitHub profile."""
        # Premium role criteria
        if (github_user.public_repos >= 10 or 
            github_user.followers >= 50 or
            github_user.company):
            return UserRole.PREMIUM
        
        # Developer role criteria
        if github_user.public_repos >= 5:
            return UserRole.DEVELOPER
        
        # Default to basic
        return UserRole.BASIC
    
    async def _store_user_session(self, github_user: GitHubUser, access_token: str):
        """Store user session data."""
        user_id = str(github_user.id)
        session_token = secrets.token_urlsafe(32)
        
        # Store user data
        await self.redis_client.setex(
            self.user_key.format(user_id=user_id),
            self.token_timeout,
            json.dumps(asdict(github_user))
        )
        
        # Store access token
        await self.redis_client.setex(
            self.token_key.format(user_id=user_id),
            self.token_timeout,
            access_token
        )
        
        # Create session mapping
        await self.redis_client.setex(
            f"session:{session_token}",
            self.token_timeout,
            user_id
        )
        
        return session_token


class GitHubOAuthError(Exception):
    """GitHub OAuth specific errors."""
    pass