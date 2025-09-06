"""
Test suite for MCP Server Functionality

Tests the actual MCP server functionality by importing and testing it directly.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from django_vue_mcp_server import DjangoVueMCPServer


class TestMCPServerFunctionality:
    """Test the actual MCP server functionality"""

    @pytest.fixture
    async def server(self):
        """Create a test server instance with mocked dependencies"""
        server = DjangoVueMCPServer()
        
        # Mock Redis client
        server.redis_client = AsyncMock()
        server.redis_client.get = AsyncMock(return_value=None)
        server.redis_client.setex = AsyncMock()
        server.redis_client.ping = AsyncMock()
        
        # Initialize the server
        await server.setup()
        
        yield server
        
        # Cleanup
        if hasattr(server, 'redis_client') and server.redis_client:
            await server.redis_client.close()

    def test_server_initialization(self):
        """Test that server initializes with correct metadata"""
        server = DjangoVueMCPServer()
        
        assert server.name == "django-vue-mcp-docs"
        assert server.version == "1.0.0"
        assert hasattr(server, 'django_libraries')
        assert hasattr(server, 'vue_libraries')
        assert len(server.django_libraries) > 0
        assert len(server.vue_libraries) > 0

    @pytest.mark.asyncio
    async def test_list_resources(self, server):
        """Test that we can list all resources"""
        result = await server.list_resources()
        
        assert hasattr(result, 'resources')
        assert len(result.resources) > 0
        
        # Check we have different resource types
        resource_uris = [r.uri for r in result.resources]
        
        django_resources = [uri for uri in resource_uris if uri.startswith("django://")]
        vue_resources = [uri for uri in resource_uris if uri.startswith("vue://")]
        integration_resources = [uri for uri in resource_uris if uri.startswith("integration://")]
        custom_resources = [uri for uri in resource_uris if uri.startswith("custom://")]
        
        assert len(django_resources) > 0, "Should have Django resources"
        assert len(vue_resources) > 0, "Should have Vue resources"
        assert len(integration_resources) > 0, "Should have integration resources"
        assert len(custom_resources) > 0, "Should have custom resources"

    @pytest.mark.asyncio
    async def test_read_django_resource_with_mock(self, server):
        """Test reading a Django resource with mocked API"""
        mock_pypi_response = {
            "info": {
                "name": "django",
                "version": "5.0.0",
                "summary": "A high-level Python web framework",
                "description": "Django makes it easier to build web applications faster.",
                "home_page": "https://www.djangoproject.com/",
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
            # Mock the aiohttp response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_pypi_response)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await server.read_resource("django://django")
            
            assert hasattr(result, 'contents')
            assert len(result.contents) > 0
            
            content_text = result.contents[0].text
            assert "django" in content_text.lower()
            assert "5.0.0" in content_text
            assert len(content_text) > 100  # Should be comprehensive

    @pytest.mark.asyncio
    async def test_read_integration_resource(self, server):
        """Test reading integration examples"""
        result = await server.read_resource("integration://jwt-auth")
        
        assert hasattr(result, 'contents')
        assert len(result.contents) > 0
        
        content_text = result.contents[0].text
        assert "jwt" in content_text.lower()
        assert "authentication" in content_text.lower()
        assert len(content_text) > 500  # Should be detailed

    @pytest.mark.asyncio
    async def test_read_custom_resource(self, server):
        """Test reading custom library documentation"""
        result = await server.read_resource("custom://aida-permissions")
        
        assert hasattr(result, 'contents')
        assert len(result.contents) > 0
        
        content_text = result.contents[0].text
        assert "aida-permissions" in content_text.lower()
        assert "role-based" in content_text.lower()
        assert len(content_text) > 300  # Should be informative

    @pytest.mark.asyncio
    async def test_caching_with_redis(self, server):
        """Test that caching works correctly"""
        # First call - cache miss
        server.redis_client.get.return_value = None
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"info": {"name": "test", "version": "1.0.0"}})
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result1 = await server.read_resource("django://django")
            
            # Should have called the API
            assert mock_get.called
            # Should have set cache
            assert server.redis_client.setex.called
        
        # Second call - cache hit
        server.redis_client.get.return_value = '{"cached": "data"}'
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            result2 = await server.read_resource("django://django")
            
            # Should not have called API again
            assert not mock_get.called

    @pytest.mark.asyncio
    async def test_error_handling_for_invalid_resource(self, server):
        """Test error handling for invalid resources"""
        with pytest.raises(ValueError):
            await server.read_resource("invalid://nonexistent")

    @pytest.mark.asyncio
    async def test_tool_functionality(self, server):
        """Test tool calling functionality"""
        result = await server.call_tool("refresh_cache", {"resource": "django://django"})
        
        assert hasattr(result, 'content')
        assert len(result.content) > 0
        
        content_text = result.content[0].text
        assert "refresh" in content_text.lower()

    def test_library_coverage(self, server):
        """Test that all expected libraries are included"""
        # Check Django libraries
        expected_django = ["django", "djangorestframework", "drf-spectacular"]
        for lib in expected_django:
            assert lib in server.django_libraries, f"Missing Django library: {lib}"
        
        # Check Vue libraries
        expected_vue = ["vue", "vue-router", "pinia", "axios"]
        for lib in expected_vue:
            assert lib in server.vue_libraries, f"Missing Vue library: {lib}"

    @pytest.mark.asyncio
    async def test_concurrent_resource_reads(self, server):
        """Test handling concurrent resource reads"""
        tasks = []
        
        # Create multiple concurrent read tasks
        for resource in ["integration://jwt-auth", "integration://api-patterns", "custom://aida-permissions"]:
            task = server.read_resource(resource)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 3
        for result in results:
            assert hasattr(result, 'contents')
            assert len(result.contents) > 0
            assert len(result.contents[0].text) > 100

    @pytest.mark.asyncio
    async def test_resource_content_quality(self, server):
        """Test that resource content meets quality standards"""
        # Test a few different resource types
        test_resources = [
            "integration://jwt-auth",
            "integration://api-patterns", 
            "custom://aida-permissions"
        ]
        
        for resource_uri in test_resources:
            result = await server.read_resource(resource_uri)
            content = result.contents[0].text
            
            # Should be substantial
            assert len(content) > 200, f"Content too short for {resource_uri}"
            
            # Should have structure (headers, code blocks, etc)
            assert '#' in content or '*' in content, f"No structure markers in {resource_uri}"
            
            # Should not have obvious placeholder text
            assert 'TODO' not in content.upper(), f"Contains TODO in {resource_uri}"
            assert 'PLACEHOLDER' not in content.upper(), f"Contains PLACEHOLDER in {resource_uri}"

    @pytest.mark.asyncio
    async def test_performance_benchmark(self, server):
        """Test basic performance characteristics"""
        import time
        
        start_time = time.time()
        
        # Read multiple resources
        resources = ["integration://jwt-auth", "integration://api-patterns", "custom://aida-permissions"]
        
        for resource in resources:
            await server.read_resource(resource)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete reasonably quickly (integration examples are local)
        assert total_time < 5.0, f"Performance too slow: {total_time}s for {len(resources)} resources"

    def test_server_metadata_completeness(self):
        """Test that server metadata is complete"""
        server = DjangoVueMCPServer()
        
        # Check required metadata
        assert server.name
        assert server.version
        assert isinstance(server.name, str)
        assert isinstance(server.version, str)
        
        # Check library definitions
        assert isinstance(server.django_libraries, list)
        assert isinstance(server.vue_libraries, list)
        assert len(server.django_libraries) >= 10  # Should have substantial Django coverage
        assert len(server.vue_libraries) >= 8     # Should have substantial Vue coverage