"""Test MCP server toolsets and tools discovery.

This script connects to the GenAI Toolbox MCP server and:
1. Lists all available toolsets
2. Lists tools in the supplier-classification-toolset
3. Tests calling a tool from that toolset
"""

import json
import subprocess
import sys

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: mcp package not found. Install with: pip install mcp")
    sys.exit(1)

import asyncio
import httpx


async def test_mcp_server():
    """Test MCP server using SSE transport."""
    
    # Get auth token
    token = subprocess.check_output(
        ["gcloud", "auth", "print-identity-token"], 
        text=True
    ).strip()
    
    url = "https://ai-mcp-server-genai-toolbox-386427107883.us-central1.run.app"
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=" * 60)
    print("Testing MCP Server Toolsets")
    print("=" * 60)
    
    # Test 1: List available resources (toolsets)
    print("\n1. Listing available resources/toolsets...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # MCP protocol uses JSON-RPC over SSE
            # Try listing resources
            response = await client.post(
                f"{url}/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "resources/list",
                    "params": {}
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Resources: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"Error listing resources: {e}")
    
    # Test 2: List available tools
    print("\n2. Listing available tools...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{url}/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                tools = data.get("result", {}).get("tools", [])
                print(f"\nFound {len(tools)} tools")
                
                # Filter for supplier-classification tools
                supplier_tools = [t for t in tools if t.get("name", "").startswith("supplier_classification_")]
                print(f"\nSupplier Classification Tools ({len(supplier_tools)}):")
                for tool in supplier_tools:
                    print(f"  - {tool.get('name')}: {tool.get('description', 'No description')[:80]}")
    except Exception as e:
        print(f"Error listing tools: {e}")
    
    # Test 3: Call a specific tool
    print("\n3. Testing tool call: supplier_classification_list_dataset_ids...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{url}/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "supplier_classification_list_dataset_ids",
                        "arguments": {}
                    }
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Result: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"Error calling tool: {e}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
