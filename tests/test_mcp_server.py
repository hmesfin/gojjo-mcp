"""
Test suite for Django Vue MCP Documentation Server

Tests MCP protocol communication, resource handling, and documentation fetching.
"""

import asyncio
import json
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

import pytest
from mcp.types import (
    Resource,
    TextResourceContents,
    ListResourcesResult,
    ReadResourceResult,
    CallToolResult,
)

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from django_vue_mcp_server import DjangoVueMCPServer


class TestDjangoVueMCPServer:
    """Test cases for the main MCP server"""

    @pytest.fixture
    async def server(self):
        """Create a test server instance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = DjangoVueMCPServer()
            # Mock Redis for testing
            server.redis_client = AsyncMock()
            server.redis_client.get = AsyncMock(return_value=None)
            server.redis_client.setex = AsyncMock()
            server.redis_client.ping = AsyncMock()
            yield server

    def test_server_initialization(self):
        """Test server initializes correctly"""
        server = DjangoVueMCPServer()
        assert server.name == "django-vue-mcp-docs"
        assert server.version == "1.0.0"
        assert len(server.django_libraries) > 0
        assert len(server.vue_libraries) > 0

    @pytest.mark.asyncio
    async def test_list_resources(self, server):
        """Test listing all available resources"""
        result = await server.list_resources()
        
        assert isinstance(result, ListResourcesResult)
        assert len(result.resources) > 0
        
        # Check for expected Django resources
        django_resources = [r for r in result.resources if r.uri.startswith("django://")]
        assert len(django_resources) > 0
        
        # Check for expected Vue resources
        vue_resources = [r for r in result.resources if r.uri.startswith("vue://")]
        assert len(vue_resources) > 0
        
        # Check for integration examples
        integration_resources = [r for r in result.resources if r.uri.startswith("integration://")]
        assert len(integration_resources) > 0

    @pytest.mark.asyncio
    async def test_read_django_resource(self, server):
        """Test reading Django library documentation"""
        # Mock PyPI API response
        mock_response = {
            "info": {
                "name": "django",
                "version": "5.0.0",
                "summary": "A high-level Python web framework",
                "description": "Django is a high-level Python web framework...",
                "home_page": "https://djangoproject.com/",
                "docs_url": "https://docs.djangoproject.com/",
                "project_urls": {
                    "Documentation": "https://docs.djangoproject.com/",
                    "Source": "https://github.com/django/django"
                }
            },
            "releases": {
                "5.0.0": [{"upload_time": "2024-01-01T00:00:00"}],
                "4.2.0": [{"upload_time": "2023-04-01T00:00:00"}]
            }
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            result = await server.read_resource("django://django")
            
            assert isinstance(result, ReadResourceResult)
            assert len(result.contents) == 1
            assert isinstance(result.contents[0], TextResourceContents)
            
            content = result.contents[0].text
            assert "django" in content.lower()
            assert "5.0.0" in content
            assert "web framework" in content.lower()

    @pytest.mark.asyncio
    async def test_read_vue_resource(self, server):
        """Test reading Vue.js library documentation"""
        # Mock NPM API response
        mock_response = {
            "name": "vue",
            "version": "3.4.0",
            "description": "The progressive JavaScript framework",
            "homepage": "https://vuejs.org/",
            "repository": {
                "type": "git",
                "url": "git+https://github.com/vuejs/core.git"
            },
            "versions": {
                "3.4.0": {},
                "3.3.0": {}
            },
            "time": {
                "3.4.0": "2024-01-01T00:00:00.000Z",
                "3.3.0": "2023-12-01T00:00:00.000Z"
            }
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            result = await server.read_resource("vue://vue")
            
            assert isinstance(result, ReadResourceResult)
            assert len(result.contents) == 1
            assert isinstance(result.contents[0], TextResourceContents)
            
            content = result.contents[0].text
            assert "vue" in content.lower()
            assert "3.4.0" in content
            assert "javascript framework" in content.lower()

    @pytest.mark.asyncio
    async def test_read_custom_library_resource(self, server):
        """Test reading custom library (aida-permissions) documentation"""
        result = await server.read_resource("custom://aida-permissions")
        
        assert isinstance(result, ReadResourceResult)
        assert len(result.contents) == 1
        assert isinstance(result.contents[0], TextResourceContents)
        
        content = result.contents[0].text
        assert "aida-permissions" in content.lower()
        assert "role-based access control" in content.lower()
        assert "django" in content.lower()

    @pytest.mark.asyncio
    async def test_read_integration_example(self, server):
        """Test reading integration examples"""
        result = await server.read_resource("integration://jwt-auth")
        
        assert isinstance(result, ReadResourceResult)
        assert len(result.contents) == 1
        assert isinstance(result.contents[0], TextResourceContents)
        
        content = result.contents[0].text
        assert "jwt" in content.lower()
        assert "authentication" in content.lower()
        assert "django" in content.lower()
        assert "vue" in content.lower()

    @pytest.mark.asyncio
    async def test_caching_functionality(self, server):
        """Test Redis caching works correctly"""
        # Test cache miss
        server.redis_client.get.return_value = None
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = {"info": {"name": "test", "version": "1.0.0"}}
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            result = await server.read_resource("django://test")
            
            # Should have called API and set cache
            assert mock_get.called
            assert server.redis_client.setex.called
        
        # Test cache hit
        server.redis_client.get.return_value = json.dumps({"cached": "data"})
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            result = await server.read_resource("django://test")
            
            # Should not have called API again
            assert not mock_get.called

    @pytest.mark.asyncio
    async def test_error_handling(self, server):
        """Test error handling for invalid resources"""
        with pytest.raises(ValueError, match="Unknown resource"):
            await server.read_resource("invalid://resource")
        
        with pytest.raises(ValueError, match="Unknown resource"):
            await server.read_resource("django://nonexistent")

    @pytest.mark.asyncio
    async def test_api_failure_handling(self, server):
        """Test handling of API failures"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 404
            mock_get.return_value.__aenter__.return_value.text = AsyncMock(return_value="Not found")
            
            result = await server.read_resource("django://django")
            
            assert isinstance(result, ReadResourceResult)
            content = result.contents[0].text
            assert "error" in content.lower() or "failed" in content.lower()

    @pytest.mark.asyncio
    async def test_tool_calls(self, server):
        """Test tool calling functionality"""
        # Test refresh cache tool
        result = await server.call_tool("refresh_cache", {"resource": "django://django"})
        
        assert isinstance(result, CallToolResult)
        assert "refreshed" in result.content[0].text.lower()

    def test_library_coverage(self, server):
        """Test that all expected libraries are covered"""
        expected_django_libs = [
            "django", "djangorestframework", "drf-spectacular", 
            "django-cors-headers", "django-filter", "django-allauth",
            "djangorestframework-simplejwt", "stripe", "twilio"
        ]
        
        expected_vue_libs = [
            "vue", "vue-router", "pinia", "axios", "tailwindcss",
            "@tiptap/core", "vite", "jest", "cypress"
        ]
        
        for lib in expected_django_libs:
            assert lib in server.django_libraries
        
        for lib in expected_vue_libs:
            assert lib in server.vue_libraries

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, server):
        """Test server handles concurrent requests correctly"""
        tasks = []
        
        for i in range(10):
            task = server.read_resource("integration://api-patterns")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        for result in results:
            assert isinstance(result, ReadResourceResult)
            assert len(result.contents) == 1

    @pytest.mark.asyncio
    async def test_performance_metrics(self, server):
        """Test performance is within acceptable limits"""
        import time
        
        start_time = time.time()
        
        # Test multiple resource reads
        for resource in ["django://django", "vue://vue", "integration://jwt-auth"]:
            await server.read_resource(resource)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete within reasonable time (allowing for API calls)
        assert total_time < 30  # 30 seconds should be plenty for 3 resources