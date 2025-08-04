"""Test SSE client for Mnemo MCP server."""

import asyncio
import aiohttp
import json


async def test_json_mode():
    """Test regular JSON mode."""
    print("=== Testing JSON mode ===")
    
    async with aiohttp.ClientSession() as session:
        # Test initialize
        request_data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        }
        
        async with session.post(
            "http://localhost:3334/mcp",
            json=request_data,
            headers={"Accept": "application/json"}
        ) as response:
            result = await response.json()
            print(f"Initialize response: {json.dumps(result, indent=2)}")
        
        # Test tools/list
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        
        async with session.post(
            "http://localhost:3334/mcp",
            json=request_data,
            headers={"Accept": "application/json"}
        ) as response:
            result = await response.json()
            print(f"\nTools list response: {json.dumps(result, indent=2)}")


async def test_sse_mode():
    """Test SSE mode."""
    print("\n\n=== Testing SSE mode ===")
    
    async with aiohttp.ClientSession() as session:
        # Test initialize with SSE
        request_data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        }
        
        async with session.post(
            "http://localhost:3334/mcp",
            json=request_data,
            headers={
                "Accept": "text/event-stream",
                "mcp-session-id": "test-session-001"
            }
        ) as response:
            print("SSE Response headers:", dict(response.headers))
            
            # Read SSE events
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(f"SSE Event: {json.dumps(data, indent=2)}")
                    break  # Just read the first event for this test


async def test_tool_call():
    """Test tool call with SSE."""
    print("\n\n=== Testing Tool Call with SSE ===")
    
    async with aiohttp.ClientSession() as session:
        # Remember something
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "remember",
                "arguments": {
                    "key": "test_sse",
                    "content": "SSE support is working correctly!",
                    "tags": ["test", "sse", "streamable"]
                }
            },
            "id": 3
        }
        
        async with session.post(
            "http://localhost:3334/mcp",
            json=request_data,
            headers={
                "Accept": "text/event-stream",
                "mcp-session-id": "test-session-001"
            }
        ) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(f"Remember result: {json.dumps(data, indent=2)}")
                    break
        
        # Search for it
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": "SSE support",
                    "limit": 5
                }
            },
            "id": 4
        }
        
        async with session.post(
            "http://localhost:3334/mcp",
            json=request_data,
            headers={
                "Accept": "text/event-stream",
                "mcp-session-id": "test-session-001"
            }
        ) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(f"\nSearch result: {json.dumps(data, indent=2)}")
                    break


async def test_standalone_sse():
    """Test standalone SSE endpoint."""
    print("\n\n=== Testing Standalone SSE Endpoint ===")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "http://localhost:3334/sse",
            headers={
                "mcp-session-id": "test-session-002"
            }
        ) as response:
            print("Standalone SSE connected!")
            print("Response headers:", dict(response.headers))
            print("Waiting for server-initiated messages...")
            
            # Just wait for a few seconds to see if any messages come
            try:
                async def read_events():
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = json.loads(line[6:])
                            print(f"Server message: {json.dumps(data, indent=2)}")
                
                await asyncio.wait_for(read_events(), timeout=5.0)
            except asyncio.TimeoutError:
                print("No server messages received in 5 seconds (this is normal)")


async def main():
    """Run all tests."""
    try:
        # Check if server is running
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:3334/health") as response:
                if response.status != 200:
                    print("❌ Server is not running! Start it with:")
                    print("   python -m mnemo.mcp.streamable_fastapi_server")
                    return
                health = await response.json()
                print(f"✅ Server is running: {health}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Start the server with: python -m mnemo.mcp.streamable_fastapi_server")
        return
    
    # Run tests
    await test_json_mode()
    await test_sse_mode()
    await test_tool_call()
    await test_standalone_sse()


if __name__ == "__main__":
    asyncio.run(main())