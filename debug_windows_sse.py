"""Debug script for Windows SSE issues."""

import platform
import socket
import subprocess
import os


def check_environment():
    """Check various environment factors that might affect SSE."""
    print("=== System Information ===")
    print(f"OS: {platform.system()} {platform.version()}")
    print(f"Python: {platform.python_version()}")
    print(f"Machine: {platform.machine()}")
    print(f"Node: {platform.node()}")
    
    print("\n=== Network Configuration ===")
    # Check localhost resolution
    try:
        ipv4 = socket.gethostbyname('localhost')
        print(f"localhost (IPv4): {ipv4}")
    except:
        print("localhost (IPv4): FAILED")
    
    try:
        info = socket.getaddrinfo('localhost', None, socket.AF_INET6)
        if info:
            print(f"localhost (IPv6): {info[0][4][0]}")
    except:
        print("localhost (IPv6): Not available")
    
    # Check 127.0.0.1 explicitly
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 3334))
        sock.close()
        print(f"127.0.0.1:3334 connectivity: {'OK' if result == 0 else 'FAILED'}")
    except:
        print("127.0.0.1:3334 connectivity: ERROR")
    
    print("\n=== Environment Variables ===")
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'no_proxy']
    for var in proxy_vars:
        value = os.environ.get(var, "Not set")
        if value != "Not set":
            print(f"{var}: {value}")
    
    print("\n=== Windows Specific (if applicable) ===")
    if platform.system() == "Windows":
        # Check Windows Defender status
        try:
            result = subprocess.run(['powershell', 'Get-MpComputerStatus'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'RealTimeProtectionEnabled' in line:
                        print(f"Windows Defender: {line.strip()}")
        except:
            print("Windows Defender: Unable to check")
        
        # Check firewall
        try:
            result = subprocess.run(['netsh', 'advfirewall', 'show', 'currentprofile'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'State' in line:
                        print(f"Windows Firewall: {line.strip()}")
                        break
        except:
            print("Windows Firewall: Unable to check")
    
    print("\n=== Cursor MCP Config ===")
    cursor_config_paths = [
        os.path.expanduser("~/.cursor/mcp.json"),
        os.path.expanduser("~/.cursor-server/mcp.json"),
        ".cursor/mcp.json"
    ]
    
    for path in cursor_config_paths:
        if os.path.exists(path):
            print(f"Found config at: {path}")
            try:
                with open(path, 'r') as f:
                    print(f"Content: {f.read()[:200]}...")
            except:
                print("  (Unable to read)")


if __name__ == "__main__":
    check_environment()