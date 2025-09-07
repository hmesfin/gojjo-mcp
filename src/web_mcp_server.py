#!/usr/bin/env python3
"""
Web-enabled MCP Server with GitHub OAuth Authentication

Combines the secure MCP server with web interface for OAuth authentication,
dashboard, and API key management.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import redis.asyncio as redis

# Import our components
from secure_mcp_server import SecureDjangoVueMCPServer
from security.auth import create_admin_key
from web.oauth_handler import OAuthWebHandler
from health_server import HealthCheckServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Thread-based HTTP server for handling OAuth requests."""
    allow_reuse_address = True


class WebMCPHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth and web interface."""
    
    oauth_handler = None  # Will be set by the server
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # Flatten query parameters
        params = {k: v[0] if v else '' for k, v in query_params.items()}
        
        # Get client IP
        client_ip = self.get_client_ip()
        
        try:
            if path == '/':
                # Redirect to login page
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                
            elif path == '/login':
                # Show login page
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    content, status, headers = loop.run_until_complete(
                        self.oauth_handler.render_login_page()
                    )
                finally:
                    loop.close()
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                
            elif path == '/auth/github':
                # Redirect to GitHub OAuth
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    content, status, headers = loop.run_until_complete(
                        self.oauth_handler.handle_github_auth()
                    )
                finally:
                    loop.close()
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                if content:
                    self.wfile.write(content.encode('utf-8'))
                    
            elif path == '/auth/github/callback':
                # Handle OAuth callback
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    content, status, headers = loop.run_until_complete(
                        self.oauth_handler.handle_oauth_callback(params, client_ip)
                    )
                finally:
                    loop.close()
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                
            elif path == '/dashboard':
                # Show user dashboard
                session_token = self.get_session_token()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    content, status, headers = loop.run_until_complete(
                        self.oauth_handler.render_dashboard(session_token)
                    )
                finally:
                    loop.close()
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                
            elif path == '/docs':
                # API documentation
                self.serve_api_docs()
                
            else:
                # 404 Not Found
                self.send_error(404, "Page not found")
                
        except Exception as e:
            logger.error(f"Error handling request {path}: {e}")
            self.send_error(500, "Internal server error")
    
    def do_POST(self):
        """Handle POST requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            if path == '/auth/logout':
                # Handle logout
                session_token = self.get_session_token()
                if session_token:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        success = loop.run_until_complete(
                            self.oauth_handler.oauth_manager.revoke_user_session(session_token)
                        )
                    finally:
                        loop.close()
                
                # Redirect to login
                self.send_response(302)
                self.send_header('Location', '/login')
                self.send_header('Set-Cookie', 'session=; Max-Age=0; Path=/')
                self.end_headers()
                
            else:
                self.send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger.error(f"Error handling POST request {path}: {e}")
            self.send_error(500, "Internal server error")
    
    def get_client_ip(self) -> str:
        """Get client IP address."""
        # Check for forwarded IP (behind proxy)
        forwarded_for = self.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = self.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return self.client_address[0]
    
    def get_session_token(self) -> Optional[str]:
        """Extract session token from cookies."""
        cookies = self.headers.get('Cookie', '')
        for cookie in cookies.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('session='):
                return cookie.split('=', 1)[1]
        return None
    
    def serve_api_docs(self):
        """Serve API documentation."""
        docs_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Server API Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }
        
        .endpoint {
            background: #f7fafc;
            border-left: 4px solid #4299e1;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        }
        
        .method {
            background: #4299e1;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.8rem;
        }
        
        code {
            background: #edf2f7;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Monaco', 'Courier New', monospace;
        }
        
        pre {
            background: #2d3748;
            color: #e2e8f0;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 MCP Server API Documentation</h1>
        <p>Django + Vue.js Documentation API with GitHub OAuth Authentication</p>
    </div>
    
    <h2>Authentication</h2>
    <p>All API requests require authentication via API key header:</p>
    <pre>X-API-Key: your_api_key_here</pre>
    
    <h2>Base URL</h2>
    <p><code>https://mcp.gojjoapps.com</code> (Production)</p>
    <p><code>http://localhost:8000</code> (Development)</p>
    
    <h2>OAuth Endpoints</h2>
    
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/login</code></p>
        <p>Login page with GitHub OAuth</p>
    </div>
    
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/auth/github</code></p>
        <p>Redirect to GitHub OAuth authorization</p>
    </div>
    
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/auth/github/callback</code></p>
        <p>GitHub OAuth callback handler</p>
    </div>
    
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/dashboard</code></p>
        <p>User dashboard with API keys and usage</p>
    </div>
    
    <h2>MCP Protocol Endpoints</h2>
    
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/api/resources</code></p>
        <p>List all available documentation resources</p>
        <pre>curl -H "X-API-Key: your_key" https://mcp.gojjoapps.com/api/resources</pre>
    </div>
    
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/api/resources/{uri}</code></p>
        <p>Get specific resource content</p>
        <pre>curl -H "X-API-Key: your_key" https://mcp.gojjoapps.com/api/resources/django/current-version</pre>
    </div>
    
    <h2>Health Endpoints</h2>
    
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/health</code></p>
        <p>Basic health check</p>
    </div>
    
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/health/detailed</code></p>
        <p>Detailed health information</p>
    </div>
    
    <h2>Rate Limits</h2>
    <ul>
        <li><strong>Anonymous:</strong> 100 requests/hour</li>
        <li><strong>Basic:</strong> 1,000 requests/hour</li>
        <li><strong>Premium:</strong> 5,000 requests/hour</li>
        <li><strong>Developer:</strong> 10,000 requests/hour</li>
        <li><strong>Admin:</strong> Unlimited</li>
    </ul>
    
    <p><a href="/login">← Back to Login</a></p>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(docs_html.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to use structured logging."""
        logger.info(f"{self.client_address[0]} - {format % args}")


class WebEnabledMCPServer:
    """
    MCP Server with integrated web interface for OAuth authentication.
    
    Provides both MCP protocol access and web-based authentication.
    """
    
    def __init__(self, web_port: int = 8000, health_port: int = 8080):
        self.web_port = web_port
        self.health_port = health_port
        
        # Initialize Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        
        # Initialize components
        self.mcp_server = SecureDjangoVueMCPServer()
        self.oauth_handler = OAuthWebHandler(self.redis_client)
        self.health_server = HealthCheckServer(port=health_port)
        
        logger.info(f"Initialized Web-enabled MCP Server")
        logger.info(f"Web interface: http://localhost:{web_port}")
        logger.info(f"Health checks: http://localhost:{health_port}")
    
    async def start_servers(self):
        """Start all server components."""
        # Start health check server
        health_task = asyncio.create_task(
            self.health_server.start_server()
        )
        
        # Start MCP server (if not in HTTP mode)
        mcp_task = None
        if not os.getenv('HTTP_MODE', 'false').lower() == 'true':
            mcp_task = asyncio.create_task(
                self.mcp_server.run()
            )
        
        # Start web server in a separate thread
        web_server = self.start_web_server()
        
        logger.info("🚀 All servers started successfully!")
        logger.info(f"📱 Web Interface: http://localhost:{self.web_port}")
        logger.info(f"❤️  Health Checks: http://localhost:{self.health_port}")
        
        if mcp_task:
            logger.info("🔗 MCP Protocol: stdio")
        
        # Wait for tasks
        try:
            tasks = [health_task]
            if mcp_task:
                tasks.append(mcp_task)
            
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down servers...")
        finally:
            web_server.shutdown()
    
    def start_web_server(self) -> ThreadingHTTPServer:
        """Start the web server for OAuth and dashboard."""
        # Set the OAuth handler as a class attribute
        WebMCPHandler.oauth_handler = self.oauth_handler
        
        server = ThreadingHTTPServer(('0.0.0.0', self.web_port), WebMCPHandler)
        
        import threading
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        return server
    
    async def create_admin_key(self) -> Optional[str]:
        """Create admin API key for initial setup."""
        try:
            key_id, api_key = await create_admin_key(self.mcp_server.auth_manager)
            return api_key.key
        except Exception as e:
            logger.error(f"Failed to create admin key: {e}")
            return None


async def main():
    """Main entry point for web-enabled MCP server."""
    logger.info("Starting Django Vue MCP Documentation Server with OAuth...")
    
    # Check required environment variables
    required_vars = ['GITHUB_CLIENT_ID', 'GITHUB_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please configure GitHub OAuth credentials:")
        logger.error("  export GITHUB_CLIENT_ID=your_client_id")
        logger.error("  export GITHUB_CLIENT_SECRET=your_client_secret")
        logger.error("  export BASE_URL=http://localhost:8000")
        return
    
    # Get port configuration
    web_port = int(os.getenv('WEB_PORT', '8000'))
    health_port = int(os.getenv('HEALTH_PORT', '8080'))
    
    # Create and start server
    server = WebEnabledMCPServer(web_port=web_port, health_port=health_port)
    
    # Create admin key if needed
    admin_key = await server.create_admin_key()
    if admin_key:
        logger.info(f"🔑 Admin API key created: {admin_key}")
    
    # Start all servers
    await server.start_servers()


if __name__ == "__main__":
    asyncio.run(main())