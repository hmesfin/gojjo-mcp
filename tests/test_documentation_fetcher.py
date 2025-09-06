"""
Test suite for DocumentationFetcher

Tests API integration, caching, and documentation parsing.
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, patch
from typing import Any, Dict

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from documentation_fetcher import DocumentationFetcher


class TestDocumentationFetcher:
    """Test cases for DocumentationFetcher"""

    @pytest.fixture
    async def fetcher(self):
        """Create a test fetcher instance"""
        fetcher = DocumentationFetcher()
        # Mock Redis for testing
        fetcher.redis_client = AsyncMock()
        fetcher.redis_client.get = AsyncMock(return_value=None)
        fetcher.redis_client.setex = AsyncMock()
        yield fetcher

    @pytest.mark.asyncio
    async def test_pypi_package_details(self, fetcher):
        """Test PyPI package details fetching"""
        mock_response = {
            "info": {
                "name": "django",
                "version": "5.0.0",
                "summary": "A high-level Python web framework",
                "description": "Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design.",
                "home_page": "https://www.djangoproject.com/",
                "docs_url": "https://docs.djangoproject.com/",
                "project_urls": {
                    "Documentation": "https://docs.djangoproject.com/",
                    "Source": "https://github.com/django/django",
                    "Tracker": "https://github.com/django/django/issues"
                },
                "author": "Django Software Foundation",
                "license": "BSD-3-Clause",
                "keywords": "django web framework",
                "classifiers": [
                    "Development Status :: 5 - Production/Stable",
                    "Framework :: Django"
                ]
            },
            "releases": {
                "5.0.0": [{"upload_time": "2024-01-01T00:00:00"}],
                "4.2.0": [{"upload_time": "2023-04-01T00:00:00"}],
                "4.1.0": [{"upload_time": "2023-01-01T00:00:00"}]
            }
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            result = await fetcher.get_pypi_package_details("django")
            
            assert result["name"] == "django"
            assert result["version"] == "5.0.0"
            assert result["summary"] == "A high-level Python web framework"
            assert "releases" in result
            assert len(result["releases"]) == 3

    @pytest.mark.asyncio
    async def test_npm_package_details(self, fetcher):
        """Test NPM package details fetching"""
        mock_response = {
            "name": "vue",
            "version": "3.4.0",
            "description": "The progressive JavaScript framework",
            "homepage": "https://vuejs.org/",
            "repository": {
                "type": "git",
                "url": "git+https://github.com/vuejs/core.git"
            },
            "keywords": ["vue", "framework", "frontend"],
            "license": "MIT",
            "maintainers": [{"name": "Evan You"}],
            "versions": {
                "3.4.0": {},
                "3.3.0": {},
                "3.2.0": {}
            },
            "time": {
                "3.4.0": "2024-01-01T00:00:00.000Z",
                "3.3.0": "2023-12-01T00:00:00.000Z",
                "3.2.0": "2023-11-01T00:00:00.000Z"
            }
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            result = await fetcher.get_npm_package_details("vue")
            
            assert result["name"] == "vue"
            assert result["version"] == "3.4.0"
            assert result["description"] == "The progressive JavaScript framework"
            assert "versions" in result
            assert len(result["versions"]) == 3

    @pytest.mark.asyncio
    async def test_github_releases(self, fetcher):
        """Test GitHub releases fetching"""
        mock_response = [
            {
                "tag_name": "v5.0.0",
                "name": "Django 5.0.0",
                "published_at": "2024-01-01T00:00:00Z",
                "prerelease": False,
                "body": "# Django 5.0.0 Release Notes\n\n## New Features\n- Feature 1\n- Feature 2\n\n## Bug Fixes\n- Fix 1\n- Fix 2"
            },
            {
                "tag_name": "v4.2.0",
                "name": "Django 4.2.0",
                "published_at": "2023-04-01T00:00:00Z",
                "prerelease": False,
                "body": "# Django 4.2.0 Release Notes\n\n## Changes\n- Change 1"
            }
        ]
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            result = await fetcher.get_github_releases("django", "django")
            
            assert len(result) == 2
            assert result[0]["tag_name"] == "v5.0.0"
            assert result[0]["name"] == "Django 5.0.0"
            assert "New Features" in result[0]["body"]

    @pytest.mark.asyncio
    async def test_documentation_urls(self, fetcher):
        """Test documentation URL discovery"""
        # Test known documentation URLs
        django_urls = fetcher.get_documentation_urls("django", "pypi")
        assert "https://docs.djangoproject.com/" in django_urls
        
        vue_urls = fetcher.get_documentation_urls("vue", "npm")
        assert "https://vuejs.org/" in vue_urls
        
        # Test unknown package fallback
        unknown_urls = fetcher.get_documentation_urls("unknown-package", "pypi")
        assert len(unknown_urls) > 0  # Should have fallback URLs

    @pytest.mark.asyncio
    async def test_caching_behavior(self, fetcher):
        """Test caching works correctly"""
        # Test cache miss
        fetcher.redis_client.get.return_value = None
        
        mock_response = {"info": {"name": "test", "version": "1.0.0"}}
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            result = await fetcher.get_pypi_package_details("test")
            
            # Should have made API call and set cache
            assert mock_get.called
            assert fetcher.redis_client.setex.called
        
        # Test cache hit
        cached_data = json.dumps({"name": "test", "version": "2.0.0"})
        fetcher.redis_client.get.return_value = cached_data
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            result = await fetcher.get_pypi_package_details("test")
            
            # Should not have made API call
            assert not mock_get.called
            assert result["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_error_handling(self, fetcher):
        """Test error handling for API failures"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Test HTTP error
            mock_get.return_value.__aenter__.return_value.status = 404
            
            result = await fetcher.get_pypi_package_details("nonexistent")
            
            assert "error" in result
            assert result["error"] == "Package not found (404)"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Test network error
            mock_get.side_effect = Exception("Network error")
            
            result = await fetcher.get_pypi_package_details("test")
            
            assert "error" in result
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_rate_limiting(self, fetcher):
        """Test rate limiting doesn't break functionality"""
        # Simulate rate limiting by making many concurrent requests
        tasks = []
        
        mock_response = {"info": {"name": "test", "version": "1.0.0"}}
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            for i in range(20):
                task = fetcher.get_pypi_package_details(f"package{i}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Most should succeed (some might be rate limited)
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) > 10

    @pytest.mark.asyncio
    async def test_format_package_info(self, fetcher):
        """Test package information formatting"""
        package_data = {
            "name": "django",
            "version": "5.0.0",
            "summary": "A high-level Python web framework",
            "description": "Long description...",
            "home_page": "https://djangoproject.com/",
            "project_urls": {
                "Documentation": "https://docs.djangoproject.com/",
                "Source": "https://github.com/django/django"
            },
            "releases": {
                "5.0.0": [{"upload_time": "2024-01-01T00:00:00"}],
                "4.2.0": [{"upload_time": "2023-04-01T00:00:00"}]
            }
        }
        
        github_releases = [
            {
                "tag_name": "v5.0.0",
                "name": "Django 5.0.0",
                "published_at": "2024-01-01T00:00:00Z",
                "body": "Release notes..."
            }
        ]
        
        formatted = fetcher.format_package_documentation(
            package_data, github_releases, ["https://docs.djangoproject.com/"]
        )
        
        assert "Django 5.0.0" in formatted
        assert "web framework" in formatted.lower()
        assert "documentation" in formatted.lower()
        assert "github.com/django/django" in formatted
        assert len(formatted) > 100  # Should be comprehensive

    @pytest.mark.asyncio 
    async def test_concurrent_api_calls(self, fetcher):
        """Test handling of concurrent API calls"""
        mock_response = {"info": {"name": "test", "version": "1.0.0"}}
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            # Make concurrent requests for different packages
            tasks = [
                fetcher.get_pypi_package_details("django"),
                fetcher.get_pypi_package_details("flask"),
                fetcher.get_npm_package_details("vue"),
                fetcher.get_npm_package_details("react")
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 4
            for result in results:
                assert "name" in result or "error" in result