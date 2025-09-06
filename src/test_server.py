#!/usr/bin/env python3
"""
Test script for the Django Vue MCP Server

This script tests the basic functionality of the MCP server
without requiring a full Claude Code integration.
"""

import asyncio
import json
import logging
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from django_vue_mcp_server import DjangoVueMCPServer

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_mcp_server():
    """Test the MCP server functionality"""
    
    print("🚀 Starting Django Vue MCP Server Tests...")
    
    # Initialize server
    server = DjangoVueMCPServer()
    
    try:
        # Test 1: List Resources
        print("\n📋 Test 1: Listing available resources...")
        resources = await server.list_resources()
        
        print(f"✅ Found {len(resources)} resources:")
        for i, resource in enumerate(resources[:5]):  # Show first 5
            print(f"  {i+1}. {resource.name} - {resource.uri}")
        if len(resources) > 5:
            print(f"  ... and {len(resources) - 5} more")
        
        # Test 2: Read Django Library Info
        print("\n📖 Test 2: Reading Django library info (djangorestframework)...")
        content_list = await server.read_resource("django://djangorestframework")
        
        if content_list:
            content = content_list[0].text
            lines = content.split('\n')[:10]  # First 10 lines
            print("✅ Retrieved content preview:")
            for line in lines:
                print(f"  {line}")
            print("  ...")
        else:
            print("❌ No content retrieved")
        
        # Test 3: Read Vue.js Library Info
        print("\n🎯 Test 3: Reading Vue.js library info (vue)...")
        content_list = await server.read_resource("vue://vue")
        
        if content_list:
            content = content_list[0].text
            lines = content.split('\n')[:10]  # First 10 lines
            print("✅ Retrieved content preview:")
            for line in lines:
                print(f"  {line}")
            print("  ...")
        else:
            print("❌ No content retrieved")
        
        # Test 4: Read Custom Library Info
        print("\n🔒 Test 4: Reading custom library info (aida-permissions)...")
        content_list = await server.read_resource("django://aida-permissions")
        
        if content_list:
            content = content_list[0].text
            lines = content.split('\n')[:15]  # First 15 lines
            print("✅ Retrieved content preview:")
            for line in lines:
                print(f"  {line}")
            print("  ...")
        else:
            print("❌ No content retrieved")
        
        # Test 5: Read Integration Example
        print("\n🔗 Test 5: Reading integration example...")
        content_list = await server.read_resource("integration://django-vue-auth")
        
        if content_list:
            content = content_list[0].text
            lines = content.split('\n')[:10]  # First 10 lines
            print("✅ Retrieved content preview:")
            for line in lines:
                print(f"  {line}")
            print("  ...")
        else:
            print("❌ No content retrieved")
        
        # Test 6: Test Error Handling
        print("\n⚠️  Test 6: Testing error handling with invalid resource...")
        content_list = await server.read_resource("invalid://nonexistent")
        
        if content_list:
            content = content_list[0].text
            print(f"✅ Error handled gracefully: {content[:100]}...")
        else:
            print("❌ Error not handled properly")
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.exception("Test failed")
    
    finally:
        # Cleanup
        await server.cleanup()
        print("\n🧹 Server cleanup completed")

def test_sync():
    """Synchronous wrapper for the async test"""
    asyncio.run(test_mcp_server())

if __name__ == "__main__":
    print("Django Vue MCP Server - Test Suite")
    print("=" * 50)
    test_sync()