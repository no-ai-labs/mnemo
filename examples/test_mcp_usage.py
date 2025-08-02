#!/usr/bin/env python
"""Test MCP usage with actual memory operations."""

import json
import subprocess
import sys
import time

def send_request(proc, request):
    """Send a request and get response."""
    proc.stdin.write(json.dumps(request) + '\n')
    proc.stdin.flush()
    response_line = proc.stdout.readline()
    return json.loads(response_line)

def test_mnemo_mcp():
    """Test Mnemo MCP with actual operations."""
    
    # Start the STDIO server
    proc = subprocess.Popen(
        [sys.executable, "-m", "mnemo.mcp.stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            "MNEMO_DB_PATH": "./test_mcp_memories",
            "MNEMO_COLLECTION": "test_collection"
        }
    )
    
    print("🚀 Testing Mnemo MCP Server...")
    time.sleep(1)  # Give server time to start
    
    # 1. Initialize
    print("\n1️⃣ Initializing...")
    response = send_request(proc, {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {},
        "id": 1
    })
    print(f"✅ Server: {response['result']['serverInfo']['name']} v{response['result']['serverInfo']['version']}")
    
    # 2. List available tools
    print("\n2️⃣ Listing available tools...")
    response = send_request(proc, {
        "jsonrpc": "2.0",
        "method": "listTools",
        "params": {},
        "id": 2
    })
    print("Available tools:")
    for tool in response['result']['tools']:
        print(f"  - {tool['name']}: {tool['description']}")
    
    # 3. Store a memory
    print("\n3️⃣ Storing a memory...")
    response = send_request(proc, {
        "jsonrpc": "2.0",
        "method": "callTool",
        "params": {
            "name": "remember",
            "arguments": {
                "key": "test_memory",
                "content": "This is a test memory from MCP!",
                "memory_type": "fact",
                "tags": ["test", "mcp", "demo"]
            }
        },
        "id": 3
    })
    memory_id = response['result']['result']['memory_id']
    print(f"✅ Memory stored with ID: {memory_id}")
    
    # 4. Search for the memory
    print("\n4️⃣ Searching for memories...")
    response = send_request(proc, {
        "jsonrpc": "2.0",
        "method": "callTool",
        "params": {
            "name": "search",
            "arguments": {
                "query": "test memory MCP",
                "limit": 5
            }
        },
        "id": 4
    })
    print(f"Found {response['result']['result']['count']} memories:")
    for mem in response['result']['result']['results']:
        print(f"  - [{mem['type']}] {mem['content'][:50]}...")
    
    # 5. Use recall
    print("\n5️⃣ Recalling most relevant memory...")
    response = send_request(proc, {
        "jsonrpc": "2.0",
        "method": "callTool",
        "params": {
            "name": "recall",
            "arguments": {
                "query": "MCP test"
            }
        },
        "id": 5
    })
    if response['result']['result']['found']:
        print(f"✅ Recalled: {response['result']['result']['content']}")
    
    # Cleanup
    proc.terminate()
    print("\n✨ Test completed!")

if __name__ == "__main__":
    test_mnemo_mcp()