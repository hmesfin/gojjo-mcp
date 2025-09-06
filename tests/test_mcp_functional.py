"""
Functional Tests for MCP Server

Tests the main functionality without complex protocol communication.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.mark.asyncio
class TestMCPFunctional:
    """Functional tests for MCP server components"""

    async def test_django_documentation_generation(self):
        """Test Django library documentation generation"""
        from documentation_fetcher import DocumentationFetcher
        
        fetcher = DocumentationFetcher()
        
        # Mock PyPI response
        mock_response = {
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
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            result = await fetcher.get_pypi_package_details("django")
            
            assert result["name"] == "django"
            assert result["version"] == "5.0.0"
            assert "web framework" in result["summary"].lower()

    async def test_vue_documentation_generation(self):
        """Test Vue library documentation generation"""
        from documentation_fetcher import DocumentationFetcher
        
        fetcher = DocumentationFetcher()
        
        # Mock NPM response
        mock_response = {
            "name": "vue",
            "version": "3.4.0",
            "description": "The progressive JavaScript framework",
            "homepage": "https://vuejs.org/",
            "repository": {
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
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            result = await fetcher.get_npm_package_details("vue")
            
            assert result["name"] == "vue"
            assert result["version"] == "3.4.0"
            assert "javascript framework" in result["description"].lower()

    async def test_integration_example_generation(self):
        """Test integration example generation"""
        from integration_examples import IntegrationExamplesGenerator
        
        generator = IntegrationExamplesGenerator()
        
        # Test Django/Vue auth integration
        auth_example = await generator.get_integration_example("django-vue-auth")
        
        assert auth_example is not None
        assert len(auth_example) > 500
        assert 'django' in auth_example.lower()
        assert 'vue' in auth_example.lower()
        assert 'authentication' in auth_example.lower() or 'auth' in auth_example.lower()
        
        # Should contain code examples
        assert 'class ' in auth_example or 'def ' in auth_example
        assert 'const ' in auth_example or 'function' in auth_example

    async def test_custom_library_documentation(self):
        """Test custom library documentation generation"""
        from custom_libraries import CustomLibraryHandler
        
        handler = CustomLibraryHandler()
        
        # Test aida-permissions documentation
        docs = await handler.get_aida_permissions_docs()
        
        assert docs is not None
        assert len(docs) > 500
        assert 'aida-permissions' in docs.lower()
        assert 'role-based' in docs.lower()
        assert 'access control' in docs.lower() or 'rbac' in docs.lower()
        
        # Should contain installation instructions
        assert 'pip install' in docs.lower()
        assert 'django' in docs.lower()

    async def test_library_coverage_comprehensive(self):
        """Test that we have comprehensive library coverage"""
        from django_vue_mcp_server import DjangoVueMCPServer
        
        server = DjangoVueMCPServer()
        
        # Test Django libraries coverage
        django_libs = server.django_libraries
        expected_django = [
            'django',
            'djangorestframework', 
            'drf-spectacular',
            'django-cors-headers',
            'django-filter',
            'django-allauth'
        ]
        
        for lib in expected_django:
            assert lib in django_libs, f"Missing Django library: {lib}"
        
        # Test Vue libraries coverage  
        vue_libs = server.vue_libraries
        expected_vue = [
            'vue',
            '@vue/router',
            'pinia', 
            'axios',
            'tailwindcss'
        ]
        
        for lib in expected_vue:
            assert lib in vue_libs, f"Missing Vue library: {lib}"
        
        # Test we have substantial coverage
        assert len(django_libs) >= 15, f"Expected at least 15 Django libraries, got {len(django_libs)}"
        assert len(vue_libs) >= 10, f"Expected at least 10 Vue libraries, got {len(vue_libs)}"

    async def test_caching_behavior(self):
        """Test caching functionality"""
        from documentation_fetcher import DocumentationFetcher
        
        fetcher = DocumentationFetcher()
        
        # Mock Redis client
        fetcher.redis_client = AsyncMock()
        
        # Test cache miss scenario
        fetcher.redis_client.get.return_value = None
        
        mock_response = {"info": {"name": "test", "version": "1.0.0"}}
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            result = await fetcher.get_pypi_package_details("test")
            
            # Should have made API call
            assert mock_get.called
            # Should have set cache
            assert fetcher.redis_client.setex.called
            assert result["name"] == "test"

    async def test_error_handling_robustness(self):
        """Test error handling in various scenarios"""
        from documentation_fetcher import DocumentationFetcher
        
        fetcher = DocumentationFetcher()
        
        # Test API failure handling
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 404
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            result = await fetcher.get_pypi_package_details("nonexistent")
            
            assert "error" in result
            assert "404" in result["error"]

    async def test_performance_characteristics(self):
        """Test basic performance characteristics"""
        from integration_examples import IntegrationExamplesGenerator
        from custom_libraries import CustomLibraryHandler
        
        import time
        
        # Test that local content generation is fast
        start_time = time.time()
        
        generator = IntegrationExamplesGenerator()
        handler = CustomLibraryHandler()
        
        # Generate multiple examples
        auth_example = await generator.get_integration_example("django-vue-auth")
        api_example = await generator.get_integration_example("django-vue-api")
        custom_docs = await handler.get_aida_permissions_docs()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be fast since these are local operations
        assert duration < 5.0, f"Local content generation took too long: {duration}s"
        
        # Verify we got substantial content
        assert len(auth_example) > 100
        assert len(api_example) > 100
        assert len(custom_docs) > 100

    async def test_content_quality_standards(self):
        """Test that generated content meets quality standards"""
        from integration_examples import IntegrationExamplesGenerator
        from custom_libraries import CustomLibraryHandler
        
        generator = IntegrationExamplesGenerator()
        handler = CustomLibraryHandler()
        
        # Test various content types
        auth_example = await generator.get_integration_example("django-vue-auth")
        custom_docs = await handler.get_aida_permissions_docs()
        
        # Content should be substantial
        assert len(auth_example) > 500, "Auth example too short"
        assert len(custom_docs) > 500, "Custom docs too short"
        
        # Should have structure (markdown headers, code blocks, etc.)
        assert '#' in auth_example or '*' in auth_example, "Auth example lacks structure"
        assert '#' in custom_docs or '*' in custom_docs, "Custom docs lack structure"
        
        # Should not have placeholder text
        for content in [auth_example, custom_docs]:
            assert 'TODO' not in content.upper(), f"Content contains TODO: {content[:100]}"
            assert 'PLACEHOLDER' not in content.upper(), f"Content contains PLACEHOLDER: {content[:100]}"
            assert 'FIXME' not in content.upper(), f"Content contains FIXME: {content[:100]}"

    async def test_concurrent_operations(self):
        """Test handling of concurrent operations"""
        from integration_examples import IntegrationExamplesGenerator
        from custom_libraries import CustomLibraryHandler
        
        generator = IntegrationExamplesGenerator()
        handler = CustomLibraryHandler()
        
        # Create multiple concurrent tasks
        tasks = [
            generator.get_integration_example("django-vue-auth"),
            generator.get_integration_example("django-vue-api"),
            generator.get_integration_example("django-vue-deployment"),
            handler.get_aida_permissions_docs(),
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed (no exceptions)
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed: {result}"
            assert isinstance(result, str), f"Task {i} returned wrong type: {type(result)}"
            assert len(result) > 50, f"Task {i} returned insufficient content: {len(result)}"