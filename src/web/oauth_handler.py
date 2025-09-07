"""
Web interface for GitHub OAuth authentication and developer dashboard.
Provides HTML responses for OAuth flow and API key management.
"""

import os
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse, parse_qs
from dataclasses import asdict
import redis.asyncio as redis

from auth.github_oauth import GitHubOAuthManager, GitHubUser
from web.dashboard import DashboardRenderer


class OAuthWebHandler:
    """
    Web interface for GitHub OAuth authentication.
    
    Provides:
    - OAuth login page
    - OAuth callback handling
    - Developer dashboard
    - API key management interface
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.oauth_manager = GitHubOAuthManager(redis_client)
        self.dashboard_renderer = DashboardRenderer()
        self.base_url = os.getenv('BASE_URL', 'http://localhost:8000')
    
    async def render_login_page(self) -> Tuple[str, int, Dict[str, str]]:
        """Render the OAuth login page."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Django Vue MCP Server - Developer Login</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            padding: 3rem;
            max-width: 480px;
            width: 90%;
            text-align: center;
        }
        
        .logo {
            font-size: 2.5rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            color: #718096;
            margin-bottom: 2rem;
            font-size: 1.1rem;
        }
        
        .description {
            color: #4a5568;
            margin-bottom: 2rem;
            line-height: 1.6;
            text-align: left;
        }
        
        .features {
            list-style: none;
            margin: 1.5rem 0;
            text-align: left;
        }
        
        .features li {
            padding: 0.5rem 0;
            color: #4a5568;
            display: flex;
            align-items: center;
        }
        
        .features li::before {
            content: "✓";
            color: #48bb78;
            font-weight: bold;
            margin-right: 0.75rem;
        }
        
        .github-btn {
            background: #24292e;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 1rem 2rem;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            transition: all 0.2s ease;
            margin-top: 1rem;
        }
        
        .github-btn:hover {
            background: #1a1e22;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(36, 41, 46, 0.3);
        }
        
        .github-icon {
            width: 24px;
            height: 24px;
        }
        
        .benefits {
            background: #f7fafc;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1.5rem 0;
        }
        
        .benefits h3 {
            color: #2d3748;
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }
        
        .rate-limits {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-top: 1rem;
            font-size: 0.9rem;
        }
        
        .rate-limit-item {
            background: white;
            padding: 0.75rem;
            border-radius: 6px;
            border-left: 4px solid #4299e1;
        }
        
        .rate-limit-title {
            font-weight: 600;
            color: #2d3748;
        }
        
        .rate-limit-value {
            color: #4a5568;
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }
        
        .footer {
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid #e2e8f0;
            color: #718096;
            font-size: 0.9rem;
        }
        
        .footer a {
            color: #4299e1;
            text-decoration: none;
        }
        
        .footer a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🚀 MCP Server</div>
        <div class="subtitle">Django + Vue.js Documentation API</div>
        
        <div class="description">
            <p>Access real-time documentation for your Django and Vue.js tech stack. Get current versions, integration examples, and best practices for 34+ libraries including your custom packages.</p>
        </div>
        
        <div class="benefits">
            <h3>What you get:</h3>
            <ul class="features">
                <li>Real-time PyPI/NPM version information</li>
                <li>Custom library documentation (aida-permissions)</li>
                <li>Django + Vue integration examples</li>
                <li>Automatic API key generation</li>
                <li>Usage analytics and monitoring</li>
            </ul>
            
            <div class="rate-limits">
                <div class="rate-limit-item">
                    <div class="rate-limit-title">Basic Tier</div>
                    <div class="rate-limit-value">1,000 requests/hour</div>
                </div>
                <div class="rate-limit-item">
                    <div class="rate-limit-title">Premium Tier</div>
                    <div class="rate-limit-value">5,000 requests/hour</div>
                </div>
                <div class="rate-limit-item">
                    <div class="rate-limit-title">Developer Tier</div>
                    <div class="rate-limit-value">10,000 requests/hour</div>
                </div>
                <div class="rate-limit-item">
                    <div class="rate-limit-title">Open Source</div>
                    <div class="rate-limit-value">Unlimited access</div>
                </div>
            </div>
        </div>
        
        <a href="/auth/github" class="github-btn">
            <svg class="github-icon" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            Continue with GitHub
        </a>
        
        <div class="footer">
            <p>Your GitHub account is used for authentication only.<br>
            We only access your public profile information.</p>
            <p><a href="/docs">API Documentation</a> • <a href="https://github.com/yourusername/django-vue-mcp-server">Source Code</a></p>
        </div>
    </div>
</body>
</html>
        """
        
        headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff'
        }
        
        return html, 200, headers
    
    async def handle_github_auth(self) -> Tuple[str, int, Dict[str, str]]:
        """Redirect to GitHub OAuth."""
        redirect_uri = f"{self.base_url}/auth/github/callback"
        auth_url, state = await self.oauth_manager.generate_auth_url(redirect_uri)
        
        headers = {
            'Location': auth_url,
            'Cache-Control': 'no-cache, no-store, must-revalidate'
        }
        
        return "", 302, headers
    
    async def handle_oauth_callback(
        self, 
        query_params: Dict[str, str],
        client_ip: str
    ) -> Tuple[str, int, Dict[str, str]]:
        """Handle OAuth callback from GitHub."""
        code = query_params.get('code')
        state = query_params.get('state')
        error = query_params.get('error')
        
        if error:
            return await self.render_error_page(
                "OAuth Error", 
                f"GitHub OAuth failed: {error}"
            )
        
        if not code or not state:
            return await self.render_error_page(
                "Invalid Request", 
                "Missing OAuth parameters"
            )
        
        # Process OAuth callback
        success, user_data, api_key, session_token = await self.oauth_manager.handle_callback(
            code, state, client_ip
        )
        
        if not success:
            return await self.render_error_page(
                "Authentication Failed", 
                api_key or "OAuth authentication failed"
            )
        
        # Render success page with API key and set session cookie
        return await self.render_success_page(user_data, api_key, session_token)
    
    async def render_success_page(
        self, 
        user_data: Dict[str, Any], 
        api_key: str,
        session_token: str
    ) -> Tuple[str, int, Dict[str, str]]:
        """Render successful authentication page."""
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to MCP Server - Authentication Successful</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            padding: 3rem;
            max-width: 600px;
            width: 90%;
        }}
        
        .success-header {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        
        .success-icon {{
            font-size: 4rem;
            margin-bottom: 1rem;
        }}
        
        .title {{
            font-size: 2rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: #718096;
            font-size: 1.1rem;
        }}
        
        .user-info {{
            background: #f7fafc;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 2rem 0;
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .avatar {{
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: 3px solid #e2e8f0;
        }}
        
        .user-details h3 {{
            color: #2d3748;
            margin-bottom: 0.25rem;
        }}
        
        .user-details p {{
            color: #718096;
            font-size: 0.9rem;
        }}
        
        .api-key-section {{
            background: #edf2f7;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 2rem 0;
        }}
        
        .api-key-title {{
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .api-key-display {{
            background: white;
            border: 1px solid #cbd5e0;
            border-radius: 6px;
            padding: 1rem;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9rem;
            color: #2d3748;
            word-break: break-all;
            position: relative;
        }}
        
        .copy-btn {{
            background: #4299e1;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.5rem 1rem;
            font-size: 0.8rem;
            cursor: pointer;
            margin-top: 0.5rem;
            transition: background-color 0.2s;
        }}
        
        .copy-btn:hover {{
            background: #3182ce;
        }}
        
        .next-steps {{
            margin: 2rem 0;
        }}
        
        .next-steps h3 {{
            color: #2d3748;
            margin-bottom: 1rem;
        }}
        
        .steps-list {{
            list-style: none;
        }}
        
        .steps-list li {{
            padding: 0.75rem 0;
            color: #4a5568;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
        }}
        
        .step-number {{
            background: #4299e1;
            color: white;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            font-weight: 600;
            flex-shrink: 0;
        }}
        
        .code-snippet {{
            background: #2d3748;
            color: #e2e8f0;
            border-radius: 6px;
            padding: 1rem;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.85rem;
            margin: 1rem 0;
            overflow-x: auto;
            max-width: 100%;
            word-break: break-all;
            white-space: pre-wrap;
        }}
        
        .dashboard-btn {{
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 1rem 2rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            text-align: center;
            transition: all 0.2s ease;
            margin-top: 1rem;
        }}
        
        .dashboard-btn:hover {{
            background: #5a67d8;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }}
        
        .warning {{
            background: #fed7d7;
            border: 1px solid #feb2b2;
            border-radius: 6px;
            padding: 1rem;
            color: #742a2a;
            margin: 1rem 0;
            font-size: 0.9rem;
        }}
        
        .warning strong {{
            color: #c53030;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success-header">
            <div class="success-icon">🎉</div>
            <h1 class="title">Welcome to MCP Server!</h1>
            <p class="subtitle">Your API key has been generated successfully</p>
        </div>
        
        <div class="user-info">
            <img src="{user_data['avatar_url']}" alt="Avatar" class="avatar">
            <div class="user-details">
                <h3>{user_data['name'] or user_data['login']}</h3>
                <p>@{user_data['login']} • {user_data.get('email', 'Email not public')}</p>
                {f"<p>{user_data['company']}</p>" if user_data.get('company') else ""}
            </div>
        </div>
        
        <div class="api-key-section">
            <h3 class="api-key-title">
                🔑 Your API Key
            </h3>
            <div class="api-key-display" id="apiKey">
                {api_key}
            </div>
            <button class="copy-btn" onclick="copyApiKey()">Copy to Clipboard</button>
            
            <div class="warning">
                <strong>Important:</strong> Store this API key securely. It provides access to the MCP server with your assigned rate limits.
            </div>
        </div>
        
        <div class="next-steps">
            <h3>Next Steps:</h3>
            <ol class="steps-list">
                <li>
                    <span class="step-number">1</span>
                    <div>
                        <strong>Configure Claude Code MCP Client</strong>
                        <div class="code-snippet">export MCP_API_KEY="{api_key}"
export MCP_SERVER_URL="{self.base_url}"
python src/mcp_http_client.py</div>
                    </div>
                </li>
                <li>
                    <span class="step-number">2</span>
                    <div>
                        <strong>Test API Access</strong>
                        <div class="code-snippet">curl -H "X-API-Key: {api_key}" \\
     "{self.base_url}/api/resources" | jq</div>
                    </div>
                </li>
                <li>
                    <span class="step-number">3</span>
                    <div>
                        <strong>View Documentation</strong><br>
                        Check out our <a href="/docs">API documentation</a> for complete integration guides.
                    </div>
                </li>
            </ol>
        </div>
        
        <div style="text-align: center;">
            <a href="/dashboard" class="dashboard-btn">
                View Dashboard
            </a>
        </div>
    </div>
    
    <script>
        function copyApiKey() {{
            const apiKeyElement = document.getElementById('apiKey');
            const apiKey = apiKeyElement.textContent;
            
            navigator.clipboard.writeText(apiKey).then(() => {{
                const button = document.querySelector('.copy-btn');
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                button.style.background = '#48bb78';
                
                setTimeout(() => {{
                    button.textContent = originalText;
                    button.style.background = '#4299e1';
                }}, 2000);
            }});
        }}
    </script>
</body>
</html>
        """
        
        headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Set-Cookie': f'session={session_token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000'  # 30 days
        }
        
        return html, 200, headers
    
    async def render_dashboard(
        self, 
        session_token: Optional[str] = None
    ) -> Tuple[str, int, Dict[str, str]]:
        """Render user dashboard."""
        if not session_token:
            # Redirect to login
            headers = {
                'Location': '/login',
                'Cache-Control': 'no-cache, no-store, must-revalidate'
            }
            return "", 302, headers
        
        # Get user data
        user = await self.oauth_manager.get_user_by_session(session_token)
        if not user:
            headers = {
                'Location': '/login',
                'Cache-Control': 'no-cache, no-store, must-revalidate'
            }
            return "", 302, headers
        
        # Get API keys and usage
        api_data = await self.oauth_manager.get_user_api_keys(str(user.id))
        
        # Render dashboard
        return await self.render_dashboard_page(user, api_data)
    
    async def render_dashboard_page(
        self, 
        user: GitHubUser, 
        api_data: Dict[str, Any]
    ) -> Tuple[str, int, Dict[str, str]]:
        """Render the user dashboard page."""
        html = self.dashboard_renderer.render_dashboard(user, api_data, self.base_url)
        
        headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
            'Cache-Control': 'no-cache, no-store, must-revalidate'
        }
        
        return html, 200, headers
    
    async def render_error_page(
        self, 
        title: str, 
        message: str
    ) -> Tuple[str, int, Dict[str, str]]:
        """Render error page."""
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - MCP Server</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #ed8077 0%, #e53e3e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }}
        
        .container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            padding: 3rem;
            max-width: 480px;
            width: 90%;
            text-align: center;
        }}
        
        .error-icon {{
            font-size: 4rem;
            margin-bottom: 1rem;
        }}
        
        h1 {{
            color: #2d3748;
            margin-bottom: 1rem;
        }}
        
        p {{
            color: #718096;
            line-height: 1.6;
            margin-bottom: 2rem;
        }}
        
        .back-btn {{
            background: #4299e1;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 1rem 2rem;
            font-size: 1rem;
            cursor: pointer;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">❌</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <a href="/login" class="back-btn">Try Again</a>
    </div>
</body>
</html>
        """
        
        headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff'
        }
        
        return html, 400, headers