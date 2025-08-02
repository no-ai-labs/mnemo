#!/usr/bin/env python
"""Test MCP STDIO server."""

import json
import subprocess
import sys

def test_stdio_server():
    """Test the STDIO server with a simple request."""
    
    # Start the STDIO server
    proc = subprocess.Popen(
        [sys.executable, "-m", "mnemo.mcp.stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send initialize request
    request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {},
        "id": 1
    }
    
    proc.stdin.write(json.dumps(request) + '\n')
    proc.stdin.flush()
    
    # Read response
    response_line = proc.stdout.readline()
    print(f"Raw response: {repr(response_line)}")
    
    if response_line and response_line.strip():
        try:
            response = json.loads(response_line)
            print("✅ Server Response:")
            print(json.dumps(response, indent=2))
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse response: {e}")
            print(f"Response was: {response_line}")
    else:
        print("❌ No response from server")
    
    # Check stderr
    stderr = proc.stderr.read()
    if stderr:
        print("\nServer errors/logs:")
        print(stderr)
    
    # Terminate server
    proc.terminate()

if __name__ == "__main__":
    test_stdio_server()