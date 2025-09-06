#!/usr/bin/env python3
"""
Django Vue MCP Documentation Server

A Model Context Protocol server that provides up-to-date documentation
for Django and Vue.js technology stacks.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    TextResourceContents
)
from pydantic import BaseModel

from custom_libraries import CustomLibraryHandler
from documentation_fetcher import DocumentationFetcher
from integration_examples import IntegrationExamplesGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LibraryInfo(BaseModel):
    """Model for library information"""
    name: str
    version: str
    description: str
    docs_url: str
    changelog_url: Optional[str] = None
    github_url: Optional[str] = None
    last_updated: datetime
    category: str  # 'django' or 'vue'

class CacheEntry(BaseModel):
    """Model for cache entries"""
    data: Dict[str, Any]
    timestamp: datetime
    ttl: int = 21600  # 6 hours default

class DjangoVueMCPServer:
    """Main MCP server class for Django/Vue documentation"""
    
    def __init__(self):
        self.cache: Dict[str, CacheEntry] = {}
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Load configuration from environment
        self.cache_ttl = int(os.getenv('CACHE_TTL', '21600'))  # 6 hours
        self.github_token = os.getenv('GITHUB_TOKEN', '')
        
        # Initialize handlers
        self.custom_handler = CustomLibraryHandler(self.github_token)
        self.doc_fetcher = DocumentationFetcher(self.github_token)
        self.examples_generator = IntegrationExamplesGenerator()
        
        # Define supported libraries
        self.django_libraries = [
            'django', 'djangorestframework', 'drf-spectacular', 
            'django-cors-headers', 'django-filter', 'django-allauth',
            'djangorestframework-simplejwt', 'stripe', 'twilio',
            'django-storages', 'django-anymail', 'gunicorn',
            'psycopg', 'redis', 'celery', 'django-celery-beat',
            'flower', 'pytest-django', 'factory-boy', 'pytest',
            'coverage', 'aida-permissions'
        ]
        
        self.vue_libraries = [
            'vue', '@vue/router', 'pinia', 'axios', 'tailwindcss',
            '@tiptap/core', 'vite', 'jest', 'cypress', 
            '@vue/test-utils', 'vitest', 'eslint', 'playwright'
        ]
        
        logger.info("Django Vue MCP Server initialized")
    
    def get_server_info(self):
        """Get server information"""
        return {
            "name": "django-vue-mcp-server",
            "version": "1.0.0",
            "description": "MCP server for Django and Vue.js documentation"
        }
    
    async def list_resources(self) -> List[Resource]:
        """List available documentation resources"""
        resources = []
        
        # Django libraries
        for lib in self.django_libraries:
            resources.append(Resource(
                uri=f"django://{lib}",
                name=f"Django: {lib}",
                description=f"Current version and documentation for {lib}",
                mimeType="text/plain"
            ))
        
        # Vue.js libraries
        for lib in self.vue_libraries:
            resources.append(Resource(
                uri=f"vue://{lib}",
                name=f"Vue.js: {lib}",
                description=f"Current version and documentation for {lib}",
                mimeType="text/plain"
            ))
        
        # Integration examples
        resources.extend([
            Resource(
                uri="integration://django-vue-auth",
                name="Django + Vue.js Authentication",
                description="JWT authentication integration examples",
                mimeType="text/markdown"
            ),
            Resource(
                uri="integration://django-vue-api",
                name="Django + Vue.js API Integration", 
                description="REST API integration patterns and examples",
                mimeType="text/markdown"
            ),
            Resource(
                uri="integration://django-vue-deployment",
                name="Django + Vue.js Deployment",
                description="Production deployment patterns and configurations",
                mimeType="text/markdown"
            )
        ])
        
        return resources
    
    async def read_resource(self, uri: str) -> List[TextResourceContents]:
        """Read a specific documentation resource"""
        try:
            if uri.startswith("django://"):
                library_name = uri.replace("django://", "")
                content = await self._get_django_library_info(library_name)
            elif uri.startswith("vue://"):
                library_name = uri.replace("vue://", "")
                content = await self._get_vue_library_info(library_name)
            elif uri.startswith("integration://"):
                integration_type = uri.replace("integration://", "")
                content = await self._get_integration_example(integration_type)
            else:
                content = f"Unknown resource type: {uri}"
            
            return [
                TextResourceContents(
                    uri=uri,
                    mimeType="text/plain",
                    text=content
                )
            ]
        
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            return [
                TextResourceContents(
                    uri=uri,
                    mimeType="text/plain",
                    text=f"Error retrieving {uri}: {str(e)}"
                )
            ]
    
    async def _get_django_library_info(self, library_name: str) -> str:
        """Get information about a Django library from PyPI or custom sources"""
        # Handle custom libraries first
        if library_name == 'aida-permissions':
            return await self.custom_handler.get_custom_library_info(library_name)
        
        # Check cache first
        cache_key = f"django:{library_name}"
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.now() - entry.timestamp < timedelta(seconds=entry.ttl):
                return entry.data.get('content', 'Cached data not found')
        
        try:
            # Use enhanced documentation fetcher
            package_details = await self.doc_fetcher.get_pypi_package_details(library_name)
            
            if 'error' in package_details:
                return f"Error fetching {library_name}: {package_details['error']}"
            
            # Get GitHub releases if available
            github_releases = []
            if package_details.get('github_url'):
                github_releases = await self.doc_fetcher.get_github_releases(
                    package_details['github_url'], limit=3
                )
            
            # Get documentation URLs
            doc_urls = await self.doc_fetcher.get_documentation_urls(library_name, 'pypi')
            
            # Format release history
            release_history_text = "No recent releases available."
            if package_details.get('release_history'):
                release_history_text = "\n".join([
                    f"- **v{rel['version']}** ({rel['release_date']}) - {rel['files_count']} files"
                    for rel in package_details['release_history'][:5]
                ])
            
            # Format GitHub releases
            github_releases_text = ""
            if github_releases:
                github_releases_text = "\n\n### Recent GitHub Releases\n"
                for release in github_releases:
                    github_releases_text += f"""
**{release['tag_name']}** - {release['published_at']}
{release['body'][:200]}{'...' if len(release['body']) > 200 else ''}
"""
            
            # Format the comprehensive information
            classifiers_text = '\n'.join(['- ' + classifier for classifier in package_details.get('classifiers', [])[:10]])
            official_docs_text = f"- **Official Docs**: {doc_urls.get('official', '')}" if doc_urls.get('official') else ""
            
            content = f"""# {library_name}

**Version**: {package_details.get('version', 'Unknown')}
**Description**: {package_details.get('summary', 'No description available')}
**Author**: {package_details.get('author', 'Unknown')}
**License**: {package_details.get('license', 'Unknown')}
**Homepage**: {package_details.get('homepage', 'Not provided')}
**Documentation**: {package_details.get('documentation_url', 'Not provided')}
**Python Requirements**: {package_details.get('requires_python', 'Not specified')}

## Installation
```bash
pip install {library_name}=={package_details.get('version', 'latest')}
```

## Dependencies
{len(package_details.get('dependencies', []))} dependencies required

## Keywords
{package_details.get('keywords', 'No keywords specified')}

## Recent Releases
{release_history_text}
{github_releases_text}

## Documentation Links
- **PyPI**: https://pypi.org/project/{library_name}/
- **Documentation**: {package_details.get('documentation_url', 'Not provided')}
- **Source Code**: {package_details.get('source_url', 'Not provided')}
- **Bug Tracker**: {package_details.get('bug_tracker', 'Not provided')}
{official_docs_text}

## Integration with Django
{await self._get_django_integration_notes(library_name)}

## Package Classifiers
{classifiers_text}

Last updated: {package_details.get('last_updated', datetime.now().isoformat())}
"""
            
            # Cache the result
            self.cache[cache_key] = CacheEntry(
                data={'content': content},
                timestamp=datetime.now(),
                ttl=self.cache_ttl
            )
            
            return content
        
        except Exception as e:
            logger.error(f"Error fetching Django library {library_name}: {e}")
            return f"Error fetching information for {library_name}: {str(e)}"
    
    async def _get_vue_library_info(self, library_name: str) -> str:
        """Get information about a Vue.js library from NPM"""
        # Check cache first
        cache_key = f"vue:{library_name}"
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.now() - entry.timestamp < timedelta(seconds=entry.ttl):
                return entry.data.get('content', 'Cached data not found')
        
        try:
            # Use enhanced documentation fetcher
            package_details = await self.doc_fetcher.get_npm_package_details(library_name)
            
            if 'error' in package_details:
                return f"Error fetching {library_name}: {package_details['error']}"
            
            # Get GitHub releases if available
            github_releases = []
            if package_details.get('github_url'):
                github_releases = await self.doc_fetcher.get_github_releases(
                    package_details['github_url'], limit=3
                )
            
            # Get documentation URLs
            doc_urls = await self.doc_fetcher.get_documentation_urls(library_name, 'npm')
            
            # Format release history
            release_history_text = "No recent releases available."
            if package_details.get('release_history'):
                release_history_text = "\n".join([
                    f"- **v{rel['version']}** ({rel['release_date']}) - {rel['dependencies_count']} deps"
                    for rel in package_details['release_history'][:5]
                ])
            
            # Format GitHub releases
            github_releases_text = ""
            if github_releases:
                github_releases_text = "\n\n### Recent GitHub Releases\n"
                for release in github_releases:
                    github_releases_text += f"""
**{release['tag_name']}** - {release['published_at']}
{release['body'][:200]}{'...' if len(release['body']) > 200 else ''}
"""
            
            # Format dependencies
            deps_info = []
            if package_details.get('dependencies'):
                deps_info.append(f"**Dependencies**: {len(package_details['dependencies'])} packages")
            if package_details.get('dev_dependencies'):
                deps_info.append(f"**Dev Dependencies**: {len(package_details['dev_dependencies'])} packages")
            if package_details.get('peer_dependencies'):
                deps_info.append(f"**Peer Dependencies**: {len(package_details['peer_dependencies'])} packages")
            
            # Format various sections
            deps_text = '\n'.join(deps_info) if deps_info else 'No dependency information available'
            keywords_text = ', '.join(package_details.get('keywords', [])) if package_details.get('keywords') else 'No keywords specified'
            engines_text = '\n'.join([f"- {engine}: {version}" for engine, version in package_details.get('engines', {}).items()]) if package_details.get('engines') else 'No engine requirements specified'
            official_docs_text = f"- **Official Docs**: {doc_urls.get('official', '')}" if doc_urls.get('official') else ""
            scripts_text = '\n'.join([f"- `{script}`: {command}" for script, command in package_details.get('scripts', {}).items()][:10]) if package_details.get('scripts') else 'No scripts defined'
            
            content = f"""# {library_name}

**Version**: {package_details.get('version', 'Unknown')}
**Description**: {package_details.get('description', 'No description available')}
**Author**: {package_details.get('author', 'Unknown')}
**License**: {package_details.get('license', 'Unknown')}
**Homepage**: {package_details.get('homepage', 'Not provided')}
**Repository**: {package_details.get('repository_url', 'Not provided')}

## Installation
```bash
npm install {library_name}@{package_details.get('version', 'latest')}
# or
yarn add {library_name}@{package_details.get('version', 'latest')}
```

## Dependencies
{deps_text}

## Keywords
{keywords_text}

## Engine Requirements
{engines_text}

## Recent Releases
{release_history_text}
{github_releases_text}

## Documentation Links
- **NPM**: https://www.npmjs.com/package/{library_name}
- **Repository**: {package_details.get('repository_url', 'Not provided')}
{official_docs_text}

## Integration with Vue.js
{await self._get_vue_integration_notes(library_name)}

## Available Scripts
{scripts_text}

Last updated: {package_details.get('last_updated', datetime.now().isoformat())}
"""
            
            # Cache the result
            self.cache[cache_key] = CacheEntry(
                data={'content': content},
                timestamp=datetime.now(),
                ttl=self.cache_ttl
            )
            
            return content
        
        except Exception as e:
            logger.error(f"Error fetching Vue library {library_name}: {e}")
            return f"Error fetching information for {library_name}: {str(e)}"
    
    
    async def _get_django_integration_notes(self, library_name: str) -> str:
        """Get Django-specific integration notes"""
        integration_notes = {
            'djangorestframework': """
## Common DRF Patterns
- Use `APIView` for custom endpoints
- Implement serializers for data validation
- Use permissions for access control
- Configure pagination in settings
""",
            'django-cors-headers': """
## CORS Configuration
Add to INSTALLED_APPS and configure CORS_ALLOWED_ORIGINS for Vue.js frontend.
""",
            'aida-permissions': """
## Custom RBAC Integration
This is a custom library for role-based access control.
See the custom documentation for integration patterns.
"""
        }
        
        return integration_notes.get(library_name, "No specific integration notes available.")
    
    async def _get_vue_integration_notes(self, library_name: str) -> str:
        """Get Vue.js-specific integration notes"""
        integration_notes = {
            'pinia': """
## State Management with Pinia
- Define stores for application state
- Use composition API style
- Integrate with Vue DevTools
""",
            'axios': """
## API Integration
- Configure base URL for Django backend
- Add request/response interceptors
- Handle JWT tokens automatically
"""
        }
        
        return integration_notes.get(library_name, "No specific integration notes available.")
    
    async def _get_integration_example(self, integration_type: str) -> str:
        """Get integration examples between Django and Vue.js"""
        return await self.examples_generator.get_integration_example(integration_type)
    
    async def cleanup(self):
        """Clean up resources"""
        await self.client.aclose()
        await self.custom_handler.cleanup()
        await self.doc_fetcher.cleanup()
        logger.info("MCP server cleanup completed")

async def main():
    """Main function to run the MCP server"""
    import sys
    import os
    
    server_instance = DjangoVueMCPServer()
    
    # Check if we should run in Docker container mode or MCP protocol mode
    docker_mode = os.getenv('DOCKER_MODE', 'false').lower() == 'true'
    
    if docker_mode:
        logger.info("Running in Docker container mode - starting health server")
        
        # Import and start health server
        from health_server import HealthCheckServer
        
        health_port = int(os.getenv('HEALTH_PORT', '8080'))
        health_server = HealthCheckServer(port=health_port)
        
        try:
            # Start health server in background
            health_task = asyncio.create_task(health_server.start_server())
            
            # Keep the MCP server alive in Docker mode
            logger.info("MCP server and health server running - ready for connections")
            while True:
                await asyncio.sleep(300)  # Sleep for 5 minutes at a time
                logger.info("MCP server heartbeat - ready for MCP client connections")
                
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
            health_task.cancel()
        finally:
            await server_instance.cleanup()
            await health_server.cleanup()
    else:
        # Normal MCP protocol mode
        server = Server("django-vue-mcp-server")
        
        # Register list resources handler
        @server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            return await server_instance.list_resources()
        
        # Register read resource handler
        @server.read_resource()
        async def handle_read_resource(uri: str) -> List[TextResourceContents]:
            return await server_instance.read_resource(uri)
        
        try:
            logger.info("Starting MCP server with stdio transport")
            # Run server with stdio transport
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream, 
                    write_stream,
                    server_instance.get_server_info()
                )
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except EOFError:
            logger.info("EOF received - server shutting down")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await server_instance.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise