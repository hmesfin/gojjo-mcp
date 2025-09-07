#!/usr/bin/env python3
"""
Simplified Web-enabled MCP Server with GitHub OAuth Authentication

Uses aiohttp for proper async handling instead of threading.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import redis.asyncio as redis
from aiohttp import web, ClientSession
from aiohttp.web import Request, Response, RouteTableDef

# Import our components
from secure_mcp_server import SecureDjangoVueMCPServer
from security.auth import create_admin_key
from web.oauth_handler import OAuthWebHandler
from health_server import HealthCheckServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

routes = RouteTableDef()


class SimpleWebMCPServer:
    """
    Simplified MCP Server with aiohttp for OAuth authentication.
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
        
        logger.info(f"Initialized Simple Web-enabled MCP Server")
        logger.info(f"Web interface: http://localhost:{web_port}")
        logger.info(f"Health checks: http://localhost:{health_port}")


# Global server instance
server_instance = None


@routes.get('/')
async def root_handler(request: Request) -> Response:
    """Redirect to login page."""
    return web.Response(status=302, headers={'Location': '/login'})


@routes.get('/login')
async def login_handler(request: Request) -> Response:
    """Show login page."""
    content, status, headers = await server_instance.oauth_handler.render_login_page()
    return web.Response(text=content, status=status, headers=headers)


@routes.get('/auth/github')
async def github_auth_handler(request: Request) -> Response:
    """Redirect to GitHub OAuth."""
    content, status, headers = await server_instance.oauth_handler.handle_github_auth()
    return web.Response(text=content, status=status, headers=headers)


@routes.get('/auth/github/callback')
async def github_callback_handler(request: Request) -> Response:
    """Handle GitHub OAuth callback."""
    params = {key: value for key, value in request.query.items()}
    client_ip = request.remote or '127.0.0.1'
    
    content, status, headers = await server_instance.oauth_handler.handle_oauth_callback(
        params, client_ip
    )
    return web.Response(text=content, status=status, headers=headers)


@routes.get('/dashboard')
async def dashboard_handler(request: Request) -> Response:
    """Show user dashboard."""
    # Get session token from cookies
    session_token = request.cookies.get('session')
    
    content, status, headers = await server_instance.oauth_handler.render_dashboard(
        session_token
    )
    return web.Response(text=content, status=status, headers=headers)


@routes.post('/auth/logout')
async def logout_handler(request: Request) -> Response:
    """Handle user logout."""
    session_token = request.cookies.get('session')
    
    if session_token:
        await server_instance.oauth_handler.oauth_manager.revoke_user_session(session_token)
    
    # Redirect to login
    response = web.Response(status=302, headers={'Location': '/login'})
    response.set_cookie('session', '', max_age=0)
    return response


@routes.get('/docs')
async def docs_handler(request: Request) -> Response:
    """Serve API documentation."""
    docs_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Server API Documentation</title>
    <style>
        body { font-family: system-ui; max-width: 800px; margin: 2rem auto; padding: 0 2rem; }
        .header { background: #667eea; color: white; padding: 2rem; border-radius: 8px; margin-bottom: 2rem; }
        .endpoint { background: #f7fafc; border-left: 4px solid #4299e1; padding: 1rem; margin: 1rem 0; }
        .method { background: #4299e1; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: bold; }
        code { background: #edf2f7; padding: 0.2rem 0.4rem; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 MCP Server API Documentation</h1>
        <p>Django + Vue.js Documentation API with GitHub OAuth Authentication</p>
    </div>
    
    <h2>OAuth Endpoints</h2>
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/login</code> - Login page with GitHub OAuth</p>
    </div>
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/auth/github</code> - Redirect to GitHub OAuth authorization</p>
    </div>
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/auth/github/callback</code> - GitHub OAuth callback handler</p>
    </div>
    <div class="endpoint">
        <p><span class="method">GET</span> <code>/dashboard</code> - User dashboard with API keys</p>
    </div>
    
    <p><a href="/login">← Back to Login</a></p>
</body>
</html>
    """
    
    return web.Response(
        text=docs_html, 
        content_type='text/html',
        headers={
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff'
        }
    )


async def create_app() -> web.Application:
    """Create the web application."""
    app = web.Application()
    app.add_routes(routes)
    
    # Add CORS headers if needed
    app.middlewares.append(cors_handler)
    app.middlewares.append(error_handler)
    
    return app


@web.middleware
async def cors_handler(request: Request, handler) -> Response:
    """Add CORS headers."""
    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@web.middleware
async def error_handler(request: Request, handler) -> Response:
    """Handle errors gracefully."""
    try:
        return await handler(request)
    except Exception as e:
        import traceback
        error_details = f"Error handling {request.path}: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(error_details)
        return web.Response(
            text=f"Internal Server Error: {str(e)}", 
            status=500,
            content_type='text/plain'
        )


async def main():
    """Main entry point for simple web-enabled MCP server."""
    global server_instance
    
    logger.info("Starting Django Vue MCP Documentation Server with OAuth (Simple)...")
    
    # Check required environment variables
    required_vars = ['GITHUB_CLIENT_ID', 'GITHUB_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    # Get port configuration
    web_port = int(os.getenv('WEB_PORT', '8000'))
    health_port = int(os.getenv('HEALTH_PORT', '8080'))
    
    # Create server instance
    server_instance = SimpleWebMCPServer(web_port=web_port, health_port=health_port)
    
    # Create admin key if needed
    try:
        key_id, api_key = await create_admin_key(server_instance.mcp_server.auth_manager)
        logger.info(f"🔑 Admin API key: {api_key.key}")
    except Exception as e:
        logger.warning(f"Could not create admin key: {e}")
    
    # Start health server
    health_task = asyncio.create_task(
        server_instance.health_server.start_server()
    )
    
    # Create and start web app
    app = await create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', web_port)
    await site.start()
    
    logger.info("🚀 All servers started successfully!")
    logger.info(f"📱 Web Interface: http://localhost:{web_port}")
    logger.info(f"❤️  Health Checks: http://localhost:{health_port}")
    
    # Keep running
    try:
        await health_task
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())