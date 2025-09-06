"""
Test suite for Custom Libraries

Tests custom library documentation generation, especially aida-permissions.
"""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from custom_libraries import CustomLibraryHandler


class TestCustomLibraryHandler:
    """Test cases for CustomLibraries"""

    @pytest.fixture
    def custom_libs(self):
        """Create test custom libraries instance"""
        return CustomLibraryHandler()

    def test_aida_permissions_documentation(self, custom_libs):
        """Test aida-permissions documentation generation"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should contain key concepts
        assert "aida-permissions" in result.lower()
        assert "role-based" in result.lower()
        assert "access control" in result.lower()
        assert "rbac" in result.lower()
        
        # Should have practical examples
        assert "install" in result.lower()
        assert "pip" in result.lower()
        assert "django" in result.lower()
        
        # Should be comprehensive
        assert len(result) > 1000

    def test_aida_permissions_installation(self, custom_libs):
        """Test installation instructions are included"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should have installation commands
        assert "pip install" in result.lower()
        assert "aida-permissions" in result
        
        # Should have Django integration steps
        assert "installed_apps" in result.lower()
        assert "migrate" in result.lower()

    def test_aida_permissions_usage_examples(self, custom_libs):
        """Test usage examples are comprehensive"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should have code examples
        assert "from aida_permissions" in result
        assert "class " in result
        assert "def " in result
        
        # Should cover main features
        assert "permission" in result.lower()
        assert "role" in result.lower()
        assert "user" in result.lower()

    def test_github_integration(self, custom_libs):
        """Test GitHub repository integration"""
        mock_response = {
            "name": "aida-permissions",
            "description": "Role-based access control for Django",
            "html_url": "https://github.com/gojjoapps/aida-permissions",
            "stargazers_count": 45,
            "forks_count": 12,
            "language": "Python",
            "license": {"name": "MIT License"},
            "updated_at": "2024-01-01T00:00:00Z",
            "topics": ["django", "rbac", "permissions", "access-control"]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            result = custom_libs.get_github_repo_info("gojjoapps", "aida-permissions")
            
            assert result["name"] == "aida-permissions"
            assert result["stargazers_count"] == 45
            assert "django" in result["topics"]

    @pytest.mark.asyncio
    async def test_repository_stats(self, custom_libs):
        """Test repository statistics fetching"""
        mock_response = {
            "stargazers_count": 45,
            "forks_count": 12,
            "open_issues_count": 3,
            "language": "Python",
            "license": {"name": "MIT License"}
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value.status = 200
            
            stats = await custom_libs.get_repository_stats("gojjoapps", "aida-permissions")
            
            assert stats["stars"] == 45
            assert stats["forks"] == 12
            assert stats["language"] == "Python"

    def test_documentation_structure(self, custom_libs):
        """Test documentation has proper structure"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should have clear sections
        assert "# " in result  # Markdown headers
        assert "## " in result  # Subheaders
        
        # Should have code blocks
        assert "```" in result
        
        # Should have practical examples
        code_blocks = result.count("```")
        assert code_blocks >= 4  # Should have multiple code examples

    def test_integration_with_django_patterns(self, custom_libs):
        """Test integration follows Django patterns"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should follow Django conventions
        assert "models.py" in result.lower()
        assert "views.py" in result.lower()
        assert "settings.py" in result.lower()
        
        # Should use Django ORM patterns
        assert "objects." in result
        assert "get_or_create" in result or "filter" in result

    def test_error_handling_examples(self, custom_libs):
        """Test error handling is covered in examples"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should show error handling
        assert "try:" in result or "except" in result
        assert "permission" in result.lower()
        assert "denied" in result.lower() or "error" in result.lower()

    def test_multiple_custom_libraries(self, custom_libs):
        """Test support for multiple custom libraries"""
        available = custom_libs.get_available_libraries()
        
        assert isinstance(available, dict)
        assert "aida-permissions" in available
        
        # Should support adding more libraries
        assert len(available) >= 1

    def test_library_metadata(self, custom_libs):
        """Test library metadata is complete"""
        metadata = custom_libs.get_library_metadata("aida-permissions")
        
        assert "name" in metadata
        assert "description" in metadata
        assert "repository" in metadata
        assert "documentation" in metadata

    def test_version_information(self, custom_libs):
        """Test version information is included"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should mention version compatibility
        assert "version" in result.lower()
        assert "django" in result.lower()
        assert "python" in result.lower()

    def test_best_practices_section(self, custom_libs):
        """Test best practices are included"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should include best practices
        assert "best practice" in result.lower() or "recommended" in result.lower()
        assert "security" in result.lower()
        assert "performance" in result.lower() or "efficient" in result.lower()

    def test_troubleshooting_section(self, custom_libs):
        """Test troubleshooting information is included"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should have troubleshooting info
        assert "troubleshoot" in result.lower() or "common issue" in result.lower() or "problem" in result.lower()
        assert "solution" in result.lower() or "fix" in result.lower()

    def test_real_world_examples(self, custom_libs):
        """Test real-world usage examples are provided"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should have practical, real-world examples
        assert "example" in result.lower()
        assert "user" in result.lower()
        assert "admin" in result.lower() or "staff" in result.lower()
        
        # Should show actual use cases
        assert "view" in result.lower()
        assert "create" in result.lower()
        assert "update" in result.lower() or "edit" in result.lower()
        assert "delete" in result.lower()

    def test_api_reference_section(self, custom_libs):
        """Test API reference is included"""
        result = custom_libs.get_aida_permissions_docs()
        
        # Should have API documentation
        assert "api" in result.lower() or "reference" in result.lower()
        assert "method" in result.lower() or "function" in result.lower()
        assert "parameter" in result.lower() or "argument" in result.lower()

    def test_changelog_integration(self, custom_libs):
        """Test changelog/release information"""
        # This would normally fetch from GitHub releases
        # For now, test that the structure supports it
        
        result = custom_libs.get_aida_permissions_docs()
        
        # Should mention recent changes or versions
        assert "recent" in result.lower() or "latest" in result.lower() or "change" in result.lower()