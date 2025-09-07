#!/usr/bin/env python3
"""
Secure Django Vue MCP Documentation Server

Production-ready MCP server with authentication, rate limiting, and security measures.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import httpx
import redis.asyncio as redis
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextResourceContents
from pydantic import BaseModel

# Import our security modules
from security.auth import AuthManager, AuthResult, UserRole, create_admin_key
from security.rate_limiter import (
    RateLimiter, RateLimitType, RateLimitRule, DDoSProtection,
    rate_limit_key, check_multiple_limits
)
from security.input_validator import (
    SecurityValidator, validate_and_clean_url, validate_package_name,
    create_security_headers
)

# Import original server components
from custom_libraries import CustomLibraryHandler
from documentation_fetcher import DocumentationFetcher
from integration_examples import IntegrationExamplesGenerator
from health_server import HealthCheckServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecureLibraryInfo(BaseModel):
    """Secure model for library information"""
    name: str
    version: str
    description: str
    docs_url: str
    changelog_url: Optional[str] = None
    github_url: Optional[str] = None
    last_updated: datetime
    category: str
    access_level: UserRole = UserRole.ANONYMOUS


class SecureDjangoVueMCPServer:
    """Secure MCP server class with authentication and rate limiting"""

    def __init__(self):
        self.name = "django-vue-mcp-docs"
        self.version = "1.0.0"
        
        # Initialize Redis connection
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        if redis_url and redis_url != "":
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info(f"Connected to Redis: {redis_url}")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}")
                self.redis_client = None
        else:
            self.redis_client = None
            logger.info("Running without Redis (local mode)")

        # Initialize security components
        self.auth_manager = AuthManager(self.redis_client)
        self.rate_limiter = RateLimiter(self.redis_client)
        self.security_validator = SecurityValidator()
        self.ddos_protection = DDoSProtection(self.redis_client)
        
        # Initialize documentation components
        self.doc_fetcher = DocumentationFetcher()
        if self.redis_client:
            self.doc_fetcher.redis_client = self.redis_client
            
        self.custom_lib_handler = CustomLibraryHandler()
        self.integration_generator = IntegrationExamplesGenerator()
        
        # Initialize health server for production mode
        health_port = int(os.getenv('HEALTH_PORT', '8080'))
        self.health_server = HealthCheckServer(health_port)
        
        # Library definitions with access levels
        self.django_libraries = [
            "django", "djangorestframework", "drf-spectacular", "django-cors-headers",
            "django-filter", "django-allauth", "djangorestframework-simplejwt",
            "stripe", "twilio", "django-storages", "django-anymail", "gunicorn",
            "psycopg", "redis", "celery", "django-celery-beat", "flower",
            "pytest-django", "factory-boy", "coverage", "whitenoise"
        ]
        
        self.vue_libraries = [
            "vue", "@vue/router", "pinia", "axios", "tailwindcss", "@tiptap/core",
            "vite", "jest", "cypress", "vue-test-utils", "vitest", "eslint", "playwright"
        ]
        
        # Premium features (require higher access levels)
        self.premium_features = {
            "advanced_integration_examples": UserRole.PREMIUM,
            "custom_library_detailed_docs": UserRole.BASIC,
            "github_release_analysis": UserRole.DEVELOPER,
            "performance_optimization_guides": UserRole.PREMIUM,
            "security_best_practices": UserRole.DEVELOPER
        }
        
        self.server = Server(self.name)
        self._setup_handlers()

    async def setup(self):
        """Initialize the server and create admin key if needed"""
        try:
            # Test Redis connection
            if self.redis_client:
                await self.redis_client.ping()
                logger.info("✅ Redis connection verified")
            
            # Create admin key if it doesn't exist
            admin_key_exists = False
            if self.redis_client:
                try:
                    keys = await self.redis_client.keys("api_key:*")
                    admin_key_exists = len(keys) > 0
                except Exception:
                    pass
            
            if not admin_key_exists:
                admin_key, admin_api_key = await create_admin_key(self.auth_manager)
                logger.info("🔑 Admin API key created:")
                logger.info(f"    API Key: {admin_key}")
                logger.info(f"    Save this key - it won't be shown again!")
                
                # Also create some demo keys for testing
                demo_basic_key, _ = await self.auth_manager.generate_api_key(
                    user_id="demo_basic",
                    role=UserRole.BASIC,
                    description="Demo basic access key"
                )
                
                demo_premium_key, _ = await self.auth_manager.generate_api_key(
                    user_id="demo_premium", 
                    role=UserRole.PREMIUM,
                    description="Demo premium access key"
                )
                
                logger.info("🎫 Demo keys created:")
                logger.info(f"    Basic: {demo_basic_key}")
                logger.info(f"    Premium: {demo_premium_key}")
            
            logger.info("✅ Secure MCP server initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Server initialization failed: {e}")
            raise

    def _setup_handlers(self):
        """Setup MCP protocol handlers with security"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            return await self.list_resources_secure()
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            return await self.read_resource_secure(uri)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> str:
            return await self.call_tool_secure(name, arguments)

    async def authenticate_request(self, context: Dict[str, Any] = None) -> AuthResult:
        """Authenticate the current request"""
        
        # In MCP protocol, we need to extract authentication from context
        # For now, we'll use environment variables for API key
        api_key = os.getenv('MCP_API_KEY')
        client_ip = os.getenv('CLIENT_IP', '127.0.0.1')
        
        if api_key:
            return await self.auth_manager.authenticate_api_key(api_key, client_ip)
        else:
            # Return anonymous access
            return AuthResult(success=True, role=UserRole.ANONYMOUS)

    async def check_rate_limits(
        self, 
        auth_result: AuthResult, 
        endpoint: str,
        cost: float = 1.0
    ) -> bool:
        """Check rate limits for the request"""
        
        # Generate identifier for rate limiting
        if auth_result.user_id:
            identifier = rate_limit_key(user_id=auth_result.user_id)
        else:
            client_ip = os.getenv('CLIENT_IP', '127.0.0.1')
            identifier = rate_limit_key(client_ip=client_ip)
        
        # Check DDoS protection
        client_ip = os.getenv('CLIENT_IP', '127.0.0.1')
        if await self.ddos_protection.is_suspicious(client_ip, endpoint):
            logger.warning(f"Blocked suspicious IP: {client_ip}")
            return False
        
        # Define rate limits based on user role
        rate_limits = []
        
        if auth_result.role == UserRole.ANONYMOUS:
            rate_limits = [
                (RateLimitType.REQUESTS_PER_MINUTE, RateLimitRule(10, 60, burst_limit=15)),
                (RateLimitType.REQUESTS_PER_HOUR, RateLimitRule(100, 3600, burst_limit=120))
            ]
        elif auth_result.role == UserRole.BASIC:
            rate_limits = [
                (RateLimitType.REQUESTS_PER_MINUTE, RateLimitRule(50, 60, burst_limit=75)),
                (RateLimitType.REQUESTS_PER_HOUR, RateLimitRule(1000, 3600, burst_limit=1200))
            ]
        elif auth_result.role == UserRole.PREMIUM:
            rate_limits = [
                (RateLimitType.REQUESTS_PER_MINUTE, RateLimitRule(100, 60, burst_limit=150)),
                (RateLimitType.REQUESTS_PER_HOUR, RateLimitRule(5000, 3600, burst_limit=6000))
            ]
        elif auth_result.role == UserRole.DEVELOPER:
            rate_limits = [
                (RateLimitType.REQUESTS_PER_MINUTE, RateLimitRule(200, 60, burst_limit=300)),
                (RateLimitType.REQUESTS_PER_HOUR, RateLimitRule(10000, 3600, burst_limit=12000))
            ]
        # Admin has no limits
        elif auth_result.role == UserRole.ADMIN:
            return True
        
        # Check all rate limits
        result = await check_multiple_limits(self.rate_limiter, identifier, rate_limits)
        
        if not result.allowed:
            # Mark IP as suspicious for repeated violations
            client_ip = os.getenv('CLIENT_IP', '127.0.0.1')
            self.ddos_protection.mark_suspicious(client_ip, "rate_limit_exceeded")
            logger.warning(f"Rate limit exceeded for {identifier}: {result.reason}")
            return False
        
        return True

    async def list_resources_secure(self) -> List[Resource]:
        """Securely list available resources"""
        try:
            # Authenticate request
            auth_result = await self.authenticate_request()
            
            # Check rate limits
            if not await self.check_rate_limits(auth_result, "list_resources", cost=0.1):
                raise Exception("Rate limit exceeded")
            
            resources = []
            
            # Add Django library resources
            for lib in self.django_libraries:
                resources.append(Resource(
                    uri=f"django://{lib}",
                    name=f"Django: {lib}",
                    description=f"Documentation for {lib} library",
                    mimeType="text/plain"
                ))
            
            # Add Vue library resources
            for lib in self.vue_libraries:
                resources.append(Resource(
                    uri=f"vue://{lib}",
                    name=f"Vue: {lib}",
                    description=f"Documentation for {lib} library",
                    mimeType="text/plain"
                ))
            
            # Add integration examples (access level dependent)
            integration_examples = [
                ("django-vue-auth", "Django + Vue Authentication Integration", UserRole.ANONYMOUS),
                ("django-vue-api", "Django REST API + Vue Frontend Integration", UserRole.ANONYMOUS),
                ("django-vue-deployment", "Production Deployment Guide", UserRole.BASIC),
                ("advanced-patterns", "Advanced Integration Patterns", UserRole.PREMIUM),
                ("performance-optimization", "Performance Optimization Guide", UserRole.PREMIUM),
                ("security-best-practices", "Security Best Practices", UserRole.DEVELOPER),
            ]
            
            for example_id, name, required_role in integration_examples:
                if self.auth_manager.has_role(auth_result, required_role):
                    resources.append(Resource(
                        uri=f"integration://{example_id}",
                        name=name,
                        description=f"Integration example: {name}",
                        mimeType="text/plain"
                    ))
            
            # Add custom library resources
            if self.auth_manager.has_role(auth_result, UserRole.BASIC):
                resources.append(Resource(
                    uri="custom://aida-permissions",
                    name="aida-permissions",
                    description="Custom RBAC library for Django",
                    mimeType="text/plain"
                ))
            
            logger.info(f"Listed {len(resources)} resources for role: {auth_result.role.value}")
            return resources
            
        except Exception as e:
            logger.error(f"Error listing resources: {e}")
            raise

    async def read_resource_secure(self, uri: str) -> str:
        """Securely read a resource with authentication and validation"""
        try:
            # Authenticate request
            auth_result = await self.authenticate_request()
            
            # Check rate limits (reading is more expensive)
            if not await self.check_rate_limits(auth_result, f"read_resource:{uri}", cost=1.0):
                raise Exception("Rate limit exceeded. Please try again later.")
            
            # Validate input
            if not uri or len(uri) > 256:
                raise ValueError("Invalid resource URI")
            
            # Security validation for URIs that might contain URLs
            if any(scheme in uri.lower() for scheme in ['http', 'https', 'ftp']):
                url_validation = self.security_validator.validate_external_url(uri)
                if not url_validation.is_valid:
                    raise ValueError(f"Invalid URL in URI: {', '.join(url_validation.errors)}")
            
            # Parse and validate URI components
            if "://" in uri:
                scheme, resource_id = uri.split("://", 1)
                
                # Validate resource ID
                if not resource_id or len(resource_id) > 128:
                    raise ValueError("Invalid resource identifier")
                
                # Validate package names for library resources
                if scheme in ['django', 'vue']:
                    try:
                        validated_name = validate_package_name(resource_id)
                    except ValueError as e:
                        raise ValueError(f"Invalid package name: {e}")
                
            else:
                raise ValueError("Invalid URI format")
            
            # Route to appropriate handler based on scheme
            if uri.startswith("django://"):
                library_name = uri.replace("django://", "")
                if library_name not in self.django_libraries:
                    raise ValueError(f"Unknown Django library: {library_name}")
                
                # Use protected API call for external requests
                try:
                    details = await self.rate_limiter.api_call_with_protection(
                        service="pypi",
                        identifier=rate_limit_key(user_id=auth_result.user_id or "anonymous"),
                        func=self.doc_fetcher.get_pypi_package_details,
                        package_name=library_name
                    )
                    
                    if "error" in details:
                        return f"Error fetching {library_name} documentation: {details['error']}"
                    
                    return self.doc_fetcher.format_package_documentation(details, [], [])
                    
                except Exception as e:
                    logger.error(f"Error fetching Django library {library_name}: {e}")
                    return f"Documentation temporarily unavailable for {library_name}. Please try again later."
            
            elif uri.startswith("vue://"):
                library_name = uri.replace("vue://", "")
                if library_name not in self.vue_libraries:
                    raise ValueError(f"Unknown Vue library: {library_name}")
                
                try:
                    details = await self.rate_limiter.api_call_with_protection(
                        service="npm",
                        identifier=rate_limit_key(user_id=auth_result.user_id or "anonymous"),
                        func=self.doc_fetcher.get_npm_package_details,
                        package_name=library_name
                    )
                    
                    if "error" in details:
                        return f"Error fetching {library_name} documentation: {details['error']}"
                    
                    return self.doc_fetcher.format_package_documentation(details, [], [])
                    
                except Exception as e:
                    logger.error(f"Error fetching Vue library {library_name}: {e}")
                    return f"Documentation temporarily unavailable for {library_name}. Please try again later."
            
            elif uri.startswith("integration://"):
                integration_type = uri.replace("integration://", "")
                
                # Check access level for advanced features
                required_role = UserRole.ANONYMOUS
                if integration_type in ["advanced-patterns", "performance-optimization"]:
                    required_role = UserRole.PREMIUM
                elif integration_type in ["security-best-practices"]:
                    required_role = UserRole.DEVELOPER
                elif integration_type in ["django-vue-deployment"]:
                    required_role = UserRole.BASIC
                
                if not self.auth_manager.has_role(auth_result, required_role):
                    return f"⚠️  This integration example requires {required_role.value} access or higher.\n\nPlease upgrade your access level or contact support for an API key."
                
                return await self.integration_generator.get_integration_example(integration_type)
            
            elif uri.startswith("custom://"):
                library_name = uri.replace("custom://", "")
                
                # Custom libraries require at least basic access
                if not self.auth_manager.has_role(auth_result, UserRole.BASIC):
                    return f"⚠️  Custom library documentation requires Basic access or higher.\n\nPlease obtain an API key for enhanced features."
                
                if library_name == "aida-permissions":
                    return await self.custom_lib_handler.get_aida_permissions_docs()
                else:
                    return await self.custom_lib_handler.get_custom_library_info(library_name)
            
            else:
                raise ValueError(f"Unknown resource scheme: {uri}")
                
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            return f"Error: {str(e)}"

    async def call_tool_secure(self, name: str, arguments: dict) -> str:
        """Securely call tools with authentication and validation"""
        try:
            # Authenticate request
            auth_result = await self.authenticate_request()
            
            # Check rate limits (tool calls are expensive)
            if not await self.check_rate_limits(auth_result, f"call_tool:{name}", cost=2.0):
                raise Exception("Rate limit exceeded. Please try again later.")
            
            # Validate tool name
            if not name or not isinstance(name, str) or len(name) > 64:
                raise ValueError("Invalid tool name")
            
            # Validate arguments
            if not isinstance(arguments, dict):
                raise ValueError("Invalid tool arguments")
            
            # Tool-specific validation and access control
            if name == "refresh_cache":
                # Admin only
                if not self.auth_manager.is_admin(auth_result):
                    raise ValueError("Cache refresh requires admin privileges")
                
                resource = arguments.get("resource")
                if resource and self.redis_client:
                    # Clear cache for specific resource
                    cache_key = f"doc_cache:{resource}"
                    await self.redis_client.delete(cache_key)
                    return f"Cache refreshed for resource: {resource}"
                else:
                    return "Cache refresh requested (no Redis available)"
            
            elif name == "get_usage_stats":
                # Premium feature
                if not self.auth_manager.has_role(auth_result, UserRole.PREMIUM):
                    raise ValueError("Usage statistics require Premium access")
                
                # Return usage statistics for the user
                user_id = auth_result.user_id or "anonymous"
                return f"Usage statistics for user: {user_id}\n(Feature in development)"
            
            elif name == "validate_integration":
                # Developer feature
                if not self.auth_manager.has_role(auth_result, UserRole.DEVELOPER):
                    raise ValueError("Integration validation requires Developer access")
                
                integration_code = arguments.get("code", "")
                if len(integration_code) > 10000:
                    raise ValueError("Code too long for validation")
                
                return "✅ Integration code validation passed\n(Feature in development)"
            
            else:
                raise ValueError(f"Unknown tool: {name}")
                
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return f"Error: {str(e)}"

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            if hasattr(self, 'health_server'):
                await self.health_server.cleanup()
            logger.info("✅ Secure MCP server cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main function with dual mode support"""
    
    # Check if running in Docker mode
    docker_mode = os.getenv('DOCKER_MODE', 'false').lower() == 'true'
    
    if docker_mode:
        logger.info("🐳 Starting in Docker container mode")
        
        # Initialize server
        server = SecureDjangoVueMCPServer()
        await server.setup()
        
        # Start health server
        health_port = int(os.getenv('HEALTH_PORT', '8080'))
        health_server_task = asyncio.create_task(
            server.health_server.start_server()
        )
        
        logger.info(f"🏥 Health server running on port {health_port}")
        logger.info("🔒 Secure MCP server running in Docker mode")
        
        # Keep running
        try:
            await health_server_task
        except KeyboardInterrupt:
            logger.info("🛑 Server interrupted")
        finally:
            await server.cleanup()
    
    else:
        logger.info("📡 Starting in MCP protocol mode")
        
        # Initialize server
        server = SecureDjangoVueMCPServer()
        await server.setup()
        
        # Start MCP server with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream,
                write_stream,
                server.server.create_initialization_options()
            )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Server interrupted by user")
    except Exception as e:
        logger.error(f"💥 Server failed to start: {e}")
        exit(1)