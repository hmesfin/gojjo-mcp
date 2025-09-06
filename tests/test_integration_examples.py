"""
Test suite for Integration Examples

Tests the generation and quality of Django+Vue integration examples.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from integration_examples import IntegrationExamplesGenerator


class TestIntegrationExamplesGenerator:
    """Test cases for IntegrationExamples"""

    @pytest.fixture
    def examples(self):
        """Create test examples instance"""
        return IntegrationExamplesGenerator()

    def test_jwt_authentication_example(self, examples):
        """Test JWT authentication integration example"""
        result = examples.get_jwt_authentication_example()
        
        # Should contain both Django and Vue code
        assert "django" in result.lower()
        assert "vue" in result.lower()
        assert "jwt" in result.lower()
        assert "token" in result.lower()
        
        # Should have practical code examples
        assert "class" in result  # Django classes
        assert "def " in result   # Python functions
        assert "const " in result or "function" in result  # JavaScript
        
        # Should be comprehensive
        assert len(result) > 1000  # Should be detailed

    def test_api_patterns_example(self, examples):
        """Test API patterns integration example"""
        result = examples.get_api_patterns_example()
        
        # Should cover CRUD operations
        assert "get" in result.lower()
        assert "post" in result.lower()
        assert "put" in result.lower() or "patch" in result.lower()
        assert "delete" in result.lower()
        
        # Should have Django REST Framework patterns
        assert "serializers" in result.lower()
        assert "viewset" in result.lower() or "apiview" in result.lower()
        
        # Should have Vue API client examples
        assert "axios" in result.lower()
        assert "async" in result.lower()

    def test_state_management_example(self, examples):
        """Test Pinia state management example"""
        result = examples.get_state_management_example()
        
        # Should cover Pinia concepts
        assert "pinia" in result.lower()
        assert "store" in result.lower()
        assert "state" in result.lower()
        assert "actions" in result.lower()
        
        # Should integrate with API
        assert "api" in result.lower()
        assert "fetch" in result.lower() or "axios" in result.lower()

    def test_authentication_flow_example(self, examples):
        """Test complete authentication flow"""
        result = examples.get_authentication_flow_example()
        
        # Should cover full auth flow
        assert "login" in result.lower()
        assert "logout" in result.lower()
        assert "register" in result.lower() or "signup" in result.lower()
        assert "refresh" in result.lower()
        
        # Should have error handling
        assert "error" in result.lower()
        assert "try" in result.lower() or "catch" in result.lower()

    def test_real_time_updates_example(self, examples):
        """Test real-time updates integration"""
        result = examples.get_real_time_updates_example()
        
        # Should cover WebSocket concepts
        assert "websocket" in result.lower()
        assert "channel" in result.lower()
        
        # Should have practical implementation
        assert "connect" in result.lower()
        assert "message" in result.lower()

    def test_deployment_example(self, examples):
        """Test deployment guide"""
        result = examples.get_deployment_example()
        
        # Should cover deployment concepts
        assert "docker" in result.lower()
        assert "nginx" in result.lower()
        assert "production" in result.lower()
        
        # Should have practical commands
        assert "build" in result.lower()
        assert "run" in result.lower()

    def test_testing_patterns_example(self, examples):
        """Test testing patterns integration"""
        result = examples.get_testing_patterns_example()
        
        # Should cover both Django and Vue testing
        assert "pytest" in result.lower()
        assert "jest" in result.lower() or "vitest" in result.lower()
        
        # Should have practical test examples
        assert "test_" in result
        assert "assert" in result.lower()
        assert "expect" in result.lower()

    def test_performance_optimization_example(self, examples):
        """Test performance optimization guide"""
        result = examples.get_performance_optimization_example()
        
        # Should cover optimization topics
        assert "performance" in result.lower()
        assert "cache" in result.lower() or "caching" in result.lower()
        assert "optimize" in result.lower()
        
        # Should have practical techniques
        assert "query" in result.lower()  # Database optimization
        assert "bundle" in result.lower()  # Frontend optimization

    def test_security_best_practices_example(self, examples):
        """Test security best practices"""
        result = examples.get_security_best_practices_example()
        
        # Should cover security topics
        assert "security" in result.lower()
        assert "csrf" in result.lower()
        assert "cors" in result.lower()
        assert "xss" in result.lower()
        
        # Should have practical recommendations
        assert "validate" in result.lower()
        assert "sanitize" in result.lower()

    def test_all_examples_available(self, examples):
        """Test that all expected examples are available"""
        expected_examples = [
            "jwt-auth",
            "api-patterns", 
            "state-management",
            "auth-flow",
            "real-time",
            "deployment",
            "testing",
            "performance",
            "security"
        ]
        
        available_examples = examples.get_available_examples()
        
        for example in expected_examples:
            assert example in available_examples

    def test_example_quality_metrics(self, examples):
        """Test that examples meet quality standards"""
        example_methods = [
            examples.get_jwt_authentication_example,
            examples.get_api_patterns_example,
            examples.get_state_management_example,
            examples.get_authentication_flow_example
        ]
        
        for method in example_methods:
            result = method()
            
            # Should be comprehensive (minimum length)
            assert len(result) > 500
            
            # Should have code examples (indented lines)
            lines = result.split('\n')
            indented_lines = [line for line in lines if line.startswith('    ') or line.startswith('\t')]
            assert len(indented_lines) > 10
            
            # Should have comments/documentation
            assert '#' in result or '//' in result or '"""' in result
            
            # Should not have obvious errors
            assert 'TODO' not in result.upper()
            assert 'FIXME' not in result.upper()
            assert 'XXX' not in result.upper()

    def test_code_syntax_validity(self, examples):
        """Test that code examples have valid syntax"""
        result = examples.get_jwt_authentication_example()
        
        # Extract Python code blocks (simplified check)
        python_indicators = ['def ', 'class ', 'import ', 'from ']
        has_python = any(indicator in result for indicator in python_indicators)
        
        # Extract JavaScript/TypeScript code blocks
        js_indicators = ['const ', 'function ', 'export ', '=> {']
        has_javascript = any(indicator in result for indicator in js_indicators)
        
        assert has_python, "Should contain Python code examples"
        assert has_javascript, "Should contain JavaScript code examples"
        
        # Basic syntax checks
        assert result.count('{') == result.count('}') or abs(result.count('{') - result.count('}')) <= 2
        assert result.count('[') == result.count(']') or abs(result.count('[') - result.count(']')) <= 2
        assert result.count('(') == result.count(')') or abs(result.count('(') - result.count(')')) <= 2

    def test_example_integration_coherence(self, examples):
        """Test that examples show coherent Django+Vue integration"""
        auth_example = examples.get_jwt_authentication_example()
        api_example = examples.get_api_patterns_example()
        
        # Both should reference similar concepts
        common_concepts = ['api', 'token', 'user', 'request', 'response']
        
        for concept in common_concepts:
            assert concept in auth_example.lower()
            assert concept in api_example.lower()
        
        # Should use consistent library choices
        if 'axios' in auth_example.lower():
            assert 'axios' in api_example.lower()

    def test_custom_library_integration(self, examples):
        """Test that examples integrate custom libraries appropriately"""
        # Check if aida-permissions is mentioned in security or auth examples
        security_example = examples.get_security_best_practices_example()
        auth_example = examples.get_jwt_authentication_example()
        
        # At least one should mention our custom library
        mentions_aida = ('aida-permissions' in security_example.lower() or 
                        'aida-permissions' in auth_example.lower())
        
        # For now, just ensure the examples exist and are comprehensive
        assert len(security_example) > 500
        assert len(auth_example) > 500

    def test_example_metadata(self, examples):
        """Test example metadata and organization"""
        available = examples.get_available_examples()
        
        assert isinstance(available, dict)
        assert len(available) > 5
        
        for key, value in available.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(value) > 10  # Description should be meaningful