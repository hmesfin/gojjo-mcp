#!/usr/bin/env python3
"""
MCP Test Client

A simple client to test MCP protocol communication with our server.
This validates that the MCP server correctly implements the protocol.
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class MCPTestClient:
    """Simple MCP test client for protocol validation"""
    
    def __init__(self, server_path: str):
        self.server_path = server_path
        self.process = None
        self.message_id = 0
    
    async def start_server(self):
        """Start the MCP server process"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "MCP_TEST_MODE": "true"}
            )
            print("✅ MCP Server started successfully")
        except Exception as e:
            print(f"❌ Failed to start MCP server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            print("✅ MCP Server stopped")
    
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to the MCP server and get response"""
        if not self.process:
            raise RuntimeError("Server not started")
        
        # Add message ID
        message["id"] = self.message_id
        self.message_id += 1
        
        # Send message
        message_json = json.dumps(message) + "\n"
        self.process.stdin.write(message_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            stderr = await self.process.stderr.read()
            raise RuntimeError(f"No response from server. Error: {stderr.decode()}")
        
        try:
            response = json.loads(response_line.decode().strip())
            return response
        except json.JSONDecodeError as e:
            print(f"Invalid JSON response: {response_line.decode()}")
            raise
    
    async def test_initialize(self) -> bool:
        """Test server initialization"""
        print("\n🧪 Testing initialization...")
        
        message = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "resources": {"subscribe": True},
                    "tools": {},
                    "prompts": {}
                },
                "clientInfo": {
                    "name": "mcp-test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        try:
            response = await self.send_message(message)
            
            if response.get("result"):
                capabilities = response["result"].get("capabilities", {})
                server_info = response["result"].get("serverInfo", {})
                
                print(f"  ✅ Server initialized: {server_info.get('name', 'Unknown')}")
                print(f"  ✅ Version: {server_info.get('version', 'Unknown')}")
                print(f"  ✅ Resources supported: {'resources' in capabilities}")
                print(f"  ✅ Tools supported: {'tools' in capabilities}")
                return True
            else:
                print(f"  ❌ Initialization failed: {response}")
                return False
        
        except Exception as e:
            print(f"  ❌ Initialization error: {e}")
            return False
    
    async def test_list_resources(self) -> bool:
        """Test listing available resources"""
        print("\n🧪 Testing resource listing...")
        
        message = {
            "jsonrpc": "2.0",
            "method": "resources/list",
            "params": {}
        }
        
        try:
            response = await self.send_message(message)
            
            if response.get("result") and "resources" in response["result"]:
                resources = response["result"]["resources"]
                print(f"  ✅ Found {len(resources)} resources")
                
                # Check for expected resource types
                django_resources = [r for r in resources if r["uri"].startswith("django://")]
                vue_resources = [r for r in resources if r["uri"].startswith("vue://")]
                integration_resources = [r for r in resources if r["uri"].startswith("integration://")]
                custom_resources = [r for r in resources if r["uri"].startswith("custom://")]
                
                print(f"  ✅ Django resources: {len(django_resources)}")
                print(f"  ✅ Vue resources: {len(vue_resources)}")  
                print(f"  ✅ Integration resources: {len(integration_resources)}")
                print(f"  ✅ Custom resources: {len(custom_resources)}")
                
                # Show some example resources
                for i, resource in enumerate(resources[:5]):
                    print(f"    - {resource['uri']}: {resource.get('name', 'No name')}")
                
                if len(resources) > 5:
                    print(f"    ... and {len(resources) - 5} more")
                
                return len(resources) > 0
            else:
                print(f"  ❌ No resources found: {response}")
                return False
        
        except Exception as e:
            print(f"  ❌ Resource listing error: {e}")
            return False
    
    async def test_read_resource(self, uri: str) -> bool:
        """Test reading a specific resource"""
        print(f"\n🧪 Testing resource read: {uri}")
        
        message = {
            "jsonrpc": "2.0",
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        }
        
        try:
            response = await self.send_message(message)
            
            if response.get("result") and "contents" in response["result"]:
                contents = response["result"]["contents"]
                if contents and len(contents) > 0:
                    content_text = contents[0].get("text", "")
                    print(f"  ✅ Resource read successfully ({len(content_text)} chars)")
                    
                    # Show a snippet
                    snippet = content_text[:200] + "..." if len(content_text) > 200 else content_text
                    print(f"  📄 Content snippet: {snippet}")
                    return True
                else:
                    print(f"  ❌ Empty resource content")
                    return False
            else:
                print(f"  ❌ Resource read failed: {response}")
                return False
        
        except Exception as e:
            print(f"  ❌ Resource read error: {e}")
            return False
    
    async def test_call_tool(self, name: str, arguments: Dict[str, Any]) -> bool:
        """Test calling a tool"""
        print(f"\n🧪 Testing tool call: {name}")
        
        message = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        
        try:
            response = await self.send_message(message)
            
            if response.get("result") and "content" in response["result"]:
                content = response["result"]["content"]
                if content and len(content) > 0:
                    result_text = content[0].get("text", "")
                    print(f"  ✅ Tool call successful ({len(result_text)} chars)")
                    
                    # Show a snippet
                    snippet = result_text[:200] + "..." if len(result_text) > 200 else result_text
                    print(f"  🔧 Result snippet: {snippet}")
                    return True
                else:
                    print(f"  ❌ Empty tool result")
                    return False
            else:
                print(f"  ❌ Tool call failed: {response}")
                return False
        
        except Exception as e:
            print(f"  ❌ Tool call error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        results = {}
        
        try:
            await self.start_server()
            
            # Test initialization
            results["initialize"] = await self.test_initialize()
            
            # Test resource listing
            results["list_resources"] = await self.test_list_resources()
            
            # Test reading specific resources
            test_resources = [
                "django://django",
                "vue://vue", 
                "integration://jwt-auth",
                "custom://aida-permissions"
            ]
            
            for resource_uri in test_resources:
                key = f"read_{resource_uri.replace('://', '_').replace('/', '_')}"
                results[key] = await self.test_read_resource(resource_uri)
            
            # Test tool calls
            results["tool_refresh"] = await self.test_call_tool(
                "refresh_cache", 
                {"resource": "django://django"}
            )
            
        finally:
            await self.stop_server()
        
        return results
    
    def print_test_summary(self, results: Dict[str, bool]):
        """Print test results summary"""
        print("\n" + "="*50)
        print("🧪 MCP TEST RESULTS SUMMARY")
        print("="*50)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print("-"*50)
        print(f"📊 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All tests passed! MCP server is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        return passed == total


async def main():
    """Main test function"""
    print("🚀 Starting MCP Server Tests")
    
    # Path to our MCP server
    server_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'django_vue_mcp_server.py')
    
    if not os.path.exists(server_path):
        print(f"❌ Server not found at: {server_path}")
        return False
    
    client = MCPTestClient(server_path)
    
    try:
        results = await client.run_all_tests()
        success = client.print_test_summary(results)
        return success
    
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)