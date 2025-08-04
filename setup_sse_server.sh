#!/bin/bash

echo "🚀 Mnemo SSE Server Setup Script"
echo "================================"

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p mnemo_mcp_db
mkdir -p logs

# Test the server
echo "🧪 Testing SSE server..."
python -m mnemo.mcp.cli serve-streamable --port 3334 &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Check if server is running
if curl -s http://localhost:3334/health > /dev/null; then
    echo "✅ Server is running successfully!"
    
    # Run test client
    echo "🔍 Running test client..."
    python test_sse_client.py
    
    # Kill the server
    kill $SERVER_PID
else
    echo "❌ Server failed to start"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "To start the server:"
echo "  python -m mnemo.mcp.cli serve-streamable --port 3334"
echo ""
echo "For Cursor integration, add this to .cursor/mcp.json:"
echo '  "mnemo-streamable": {'
echo '    "url": "http://localhost:3334/mcp"'
echo '  }'