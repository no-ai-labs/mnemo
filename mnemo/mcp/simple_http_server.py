"""Simple HTTP-only MCP server for Mnemo."""

import os
import json
from typing import Dict, Any, Optional
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.mcp.handlers import ResourceHandler, ToolHandler, PromptHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global handlers
memory_client: Optional[MnemoMemoryClient] = None
resource_handler: Optional[ResourceHandler] = None
tool_handler: Optional[ToolHandler] = None
prompt_handler: Optional[PromptHandler] = None


class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP protocol."""
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests for JSON-RPC."""
        if self.path != '/mcp':
            self.send_error(404)
            return
        
        # Read request body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request = json.loads(post_data.decode('utf-8'))
            logger.info(f"Received request: {request.get('method')}")
            
            # Process request
            response = self.process_request(request)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request.get("id") if 'request' in locals() else None
            }
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        result = None
        
        if method == "initialize":
            result = {
                "protocolVersion": "1.0",
                "serverInfo": {
                    "name": "mnemo",
                    "version": "0.2.0",
                    "description": "LangChain-powered Universal Memory System for Cursor"
                },
                "capabilities": {
                    "resources": {},
                    "tools": {},
                    "prompts": {}
                }
            }
        
        elif method == "listTools":
            tools = tool_handler.list_tools()
            # Convert sync to async compatible
            import asyncio
            loop = asyncio.new_event_loop()
            tools = loop.run_until_complete(tools)
            loop.close()
            result = {"tools": [tool.dict() for tool in tools]}
        
        elif method == "callTool":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            # Convert sync to async compatible
            import asyncio
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(tool_handler.call_tool(tool_name, arguments))
            loop.close()
        
        elif method == "listResources":
            import asyncio
            loop = asyncio.new_event_loop()
            resources = loop.run_until_complete(resource_handler.list_resources())
            loop.close()
            result = {"resources": [res.dict() for res in resources]}
        
        elif method == "readResource":
            uri = params.get("uri")
            import asyncio
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(resource_handler.read_resource(uri))
            loop.close()
        
        elif method == "listPrompts":
            import asyncio
            loop = asyncio.new_event_loop()
            prompts = loop.run_until_complete(prompt_handler.list_prompts())
            loop.close()
            result = {"prompts": [prompt.dict() for prompt in prompts]}
        
        elif method == "getPrompt":
            name = params.get("name")
            arguments = params.get("arguments", {})
            import asyncio
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(prompt_handler.get_prompt(name, arguments))
            loop.close()
        
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }
        
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
    
    def log_message(self, format, *args):
        """Override to use logger instead of stderr."""
        logger.info("%s - - [%s] %s\n" %
                    (self.address_string(),
                     self.log_date_time_string(),
                     format % args))


def run_server(host: str = "127.0.0.1", port: int = 8080):
    """Run the HTTP server."""
    global memory_client, resource_handler, tool_handler, prompt_handler
    
    # Initialize memory system
    db_path = os.getenv("MNEMO_DB_PATH", "./mnemo_mcp_db")
    collection = os.getenv("MNEMO_COLLECTION", "cursor_memories")
    
    vector_store = MnemoVectorStore(
        collection_name=collection,
        persist_directory=db_path
    )
    memory_client = MnemoMemoryClient(vector_store)
    
    # Initialize handlers
    resource_handler = ResourceHandler(memory_client)
    tool_handler = ToolHandler(memory_client)
    prompt_handler = PromptHandler(memory_client)
    
    # Start server
    server = HTTPServer((host, port), MCPRequestHandler)
    logger.info(f"🚀 Mnemo Simple HTTP Server running on http://{host}:{port}/mcp")
    logger.info(f"   Database: {db_path}")
    logger.info(f"   Collection: {collection}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("👋 Shutting down server")
        server.shutdown()


if __name__ == "__main__":
    run_server()