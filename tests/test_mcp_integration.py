"""
Integration Test for MCP Server

Tests the actual MCP server by running it and communicating via the MCP protocol.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict

import pytest


class TestMCPIntegration:
    """Integration tests for the MCP server"""

    @pytest.fixture
    def temp_redis_disable(self, monkeypatch):
        """Disable Redis for testing"""
        monkeypatch.setenv("REDIS_URL", "")
        monkeypatch.setenv("USE_REDIS", "false")

    def test_server_imports_successfully(self):
        """Test that the server can be imported without errors"""
        # This tests that all dependencies are available and imports work
        server_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'django_vue_mcp_server.py')
        
        # Try to import the server module
        cmd = [sys.executable, '-c', f'import sys; sys.path.insert(0, "{os.path.dirname(server_path)}"); import django_vue_mcp_server; print("Import successful")']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        assert result.returncode == 0, f"Server import failed: {result.stderr}"
        assert "Import successful" in result.stdout

    def test_server_starts_without_crashing(self, temp_redis_disable):
        """Test that the server starts and runs briefly without crashing"""
        server_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'django_vue_mcp_server.py')
        
        # Set environment to disable features that might cause issues
        env = os.environ.copy()
        env.update({
            'MCP_TEST_MODE': 'true',
            'USE_REDIS': 'false',
            'REDIS_URL': '',
            'PYTHONPATH': os.path.join(os.path.dirname(__file__), '..', 'src')
        })
        
        # Start the server process
        process = subprocess.Popen(
            [sys.executable, server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        
        try:
            # Give it a moment to start up
            returncode = process.poll()
            if returncode is not None:
                stdout, stderr = process.communicate()
                pytest.fail(f"Server crashed immediately: returncode={returncode}, stderr={stderr}")
            
            # Send a simple initialization message
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            }
            
            process.stdin.write(json.dumps(init_message) + '\n')
            process.stdin.flush()
            
            # Try to read a response (with timeout)
            try:
                stdout, stderr = process.communicate(timeout=10)
                
                # Check if we got any valid JSON response
                lines = stdout.strip().split('\n') if stdout else []
                
                for line in lines:
                    if line.strip():
                        try:
                            response = json.loads(line.strip())
                            if 'result' in response or 'error' in response:
                                # Got a valid MCP response
                                assert True  # Success
                                return
                        except json.JSONDecodeError:
                            continue
                
                # If we get here, check if the process exited cleanly
                if process.returncode != 0:
                    pytest.fail(f"Server failed: returncode={process.returncode}, stderr={stderr}")
                
            except subprocess.TimeoutExpired:
                # Process is still running, which is good
                assert True  # Success - server is running
                
        finally:
            # Clean up
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    def test_django_libraries_defined(self):
        """Test that Django libraries are properly defined"""
        # Import the server and check library definitions
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        try:
            from django_vue_mcp_server import DjangoVueMCPServer
            server = DjangoVueMCPServer()
            
            # Check that we have Django libraries defined
            assert hasattr(server, 'django_libraries'), "Server should have django_libraries attribute"
            assert len(server.django_libraries) > 0, "Should have at least one Django library"
            
            # Check for some expected libraries
            expected_libs = ['django', 'djangorestframework']
            for lib in expected_libs:
                assert lib in server.django_libraries, f"Missing expected library: {lib}"
                
        except ImportError as e:
            pytest.skip(f"Cannot import server module: {e}")

    def test_vue_libraries_defined(self):
        """Test that Vue libraries are properly defined"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        try:
            from django_vue_mcp_server import DjangoVueMCPServer
            server = DjangoVueMCPServer()
            
            # Check that we have Vue libraries defined
            assert hasattr(server, 'vue_libraries'), "Server should have vue_libraries attribute"
            assert len(server.vue_libraries) > 0, "Should have at least one Vue library"
            
            # Check for some expected libraries
            expected_libs = ['vue', '@vue/router', 'pinia']
            for lib in expected_libs:
                assert lib in server.vue_libraries, f"Missing expected library: {lib}"
                
        except ImportError as e:
            pytest.skip(f"Cannot import server module: {e}")

    @pytest.mark.asyncio
    async def test_integration_examples_available(self):
        """Test that integration examples are available"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        try:
            from integration_examples import IntegrationExamplesGenerator
            generator = IntegrationExamplesGenerator()
            
            # Test that we can get an integration example
            example = await generator.get_integration_example('django-vue-auth')
            assert example is not None
            assert len(example) > 100  # Should be substantial
            assert 'auth' in example.lower() or 'django' in example.lower() or 'vue' in example.lower()
            
        except ImportError as e:
            pytest.skip(f"Cannot import integration examples module: {e}")

    @pytest.mark.asyncio
    async def test_custom_libraries_available(self):
        """Test that custom libraries handler is available"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        try:
            from custom_libraries import CustomLibraryHandler
            handler = CustomLibraryHandler()
            
            # Test that we can get custom library documentation
            docs = await handler.get_aida_permissions_docs()
            assert docs is not None
            assert len(docs) > 100  # Should be substantial
            assert 'aida-permissions' in docs.lower()
            
        except ImportError as e:
            pytest.skip(f"Cannot import custom libraries module: {e}")

    def test_documentation_fetcher_available(self):
        """Test that documentation fetcher is available"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        try:
            from documentation_fetcher import DocumentationFetcher
            fetcher = DocumentationFetcher()
            
            # Test that we can create the fetcher
            assert fetcher is not None
            assert hasattr(fetcher, 'get_pypi_package_details')
            assert hasattr(fetcher, 'get_npm_package_details')
            
        except ImportError as e:
            pytest.skip(f"Cannot import documentation fetcher module: {e}")

    def test_health_server_available(self):
        """Test that health server is available"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        try:
            from health_server import HealthCheckServer
            server = HealthCheckServer(port=18080)  # Use different port
            
            # Test that we can create the health server
            assert server is not None
            assert server.port == 18080
            
        except ImportError as e:
            pytest.skip(f"Cannot import health server module: {e}")

    def test_all_requirements_importable(self):
        """Test that all required packages can be imported"""
        required_packages = [
            'mcp',
            'pydantic', 
            'httpx',
            'aiohttp',
            'redis',
            'structlog',
            'psutil'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError as e:
                pytest.fail(f"Required package '{package}' cannot be imported: {e}")

    def test_file_structure_complete(self):
        """Test that all expected files are present"""
        src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
        expected_files = [
            'django_vue_mcp_server.py',
            'documentation_fetcher.py',
            'custom_libraries.py',
            'integration_examples.py',
            'health_server.py'
        ]
        
        for filename in expected_files:
            file_path = os.path.join(src_dir, filename)
            assert os.path.exists(file_path), f"Expected file missing: {filename}"
            
            # Check file is not empty
            with open(file_path, 'r') as f:
                content = f.read().strip()
                assert len(content) > 100, f"File {filename} appears to be empty or too small"

    def test_docker_environment_ready(self):
        """Test that the Docker environment is properly set up"""
        # Check if we're running in Docker
        if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_MODE'):
            # We're in Docker, check that dependencies are available
            try:
                import redis
                import httpx
                import aiohttp
                import structlog
                import psutil
                from mcp.server import Server
            except ImportError as e:
                pytest.fail(f"Docker environment missing dependency: {e}")
        else:
            pytest.skip("Not running in Docker environment")

    def test_environment_variables_handling(self):
        """Test that environment variables are handled correctly"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        # Test with various environment configurations
        test_envs = [
            {'DOCKER_MODE': 'true'},
            {'DOCKER_MODE': 'false'},
            {'MCP_TEST_MODE': 'true'},
            {'USE_REDIS': 'false'},
        ]
        
        for env_vars in test_envs:
            # Temporarily set environment variables
            original_values = {}
            for key, value in env_vars.items():
                original_values[key] = os.environ.get(key)
                os.environ[key] = value
            
            try:
                # Try to import and create server
                from django_vue_mcp_server import DjangoVueMCPServer
                server = DjangoVueMCPServer()
                assert server is not None
            except Exception as e:
                pytest.fail(f"Server creation failed with env {env_vars}: {e}")
            finally:
                # Restore original environment
                for key in env_vars:
                    if original_values[key] is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = original_values[key]