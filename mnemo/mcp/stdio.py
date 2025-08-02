"""STDIO-based MCP server for Cursor integration."""

import sys
import json
import asyncio
import os
from typing import Dict, Any
import logging

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.mcp.handlers import ResourceHandler, ToolHandler, PromptHandler
from mnemo.mcp.types import MCPRequest, MCPResponse, MCPError

# Configure logging to stderr to not interfere with stdio
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StdioMCPServer:
    """MCP server that communicates via stdio (for Cursor integration)."""
    
    def __init__(self):
        # Get configuration from environment
        db_path = os.getenv("MNEMO_DB_PATH", "./mnemo_mcp_db")
        collection = os.getenv("MNEMO_COLLECTION", "cursor_memories")
        
        # Initialize memory system
        self.vector_store = MnemoVectorStore(
            collection_name=collection,
            persist_directory=db_path
        )
        self.memory_client = MnemoMemoryClient(self.vector_store)
        
        # Initialize handlers
        self.resource_handler = ResourceHandler(self.memory_client)
        self.tool_handler = ToolHandler(self.memory_client)
        self.prompt_handler = PromptHandler(self.memory_client)
        
        # Method registry
        self._methods = {
            "initialize": self._handle_initialize,
            "listResources": self._handle_list_resources,
            "listTools": self._handle_list_tools,
            "listPrompts": self._handle_list_prompts,
            "readResource": self._handle_read_resource,
            "callTool": self._handle_call_tool,
            "getPrompt": self._handle_get_prompt,
            "mnemo.setContext": self._handle_set_context,
            "mnemo.getStats": self._handle_get_stats,
        }
    
    async def run(self):
        """Run the stdio server."""
        logger.info("Starting Mnemo MCP stdio server")
        
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        
        try:
            await asyncio.get_event_loop().connect_read_pipe(
                lambda: protocol, sys.stdin
            )
            
            while True:
                # Read line from stdin
                line_bytes = await reader.readline()
                if not line_bytes:
                    break
                
                line = line_bytes.decode('utf-8').strip()
                if not line:
                    continue
                
                try:
                    # Parse request
                    request_data = json.loads(line)
                    request = MCPRequest(**request_data)
                    
                    # Process request
                    response = await self._process_request(request)
                    
                    # Write response to stdout
                    response_json = response.json()
                    sys.stdout.write(response_json + '\n')
                    sys.stdout.flush()
                    
                except json.JSONDecodeError as e:
                    # Send parse error
                    error_response = MCPResponse(
                        error=MCPError(
                            code=-32700,
                            message="Parse error",
                            data=str(e)
                        ).dict()
                    )
                    sys.stdout.write(error_response.json() + '\n')
                    sys.stdout.flush()
                
                except Exception as e:
                    logger.error(f"Error processing request: {str(e)}")
                    # Send internal error
                    error_response = MCPResponse(
                        error=MCPError(
                            code=-32603,
                            message="Internal error",
                            data=str(e)
                        ).dict()
                    )
                    sys.stdout.write(error_response.json() + '\n')
                    sys.stdout.flush()
        
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
        finally:
            logger.info("Stopping Mnemo MCP stdio server")
    
    async def _process_request(self, request: MCPRequest) -> MCPResponse:
        """Process a single MCP request."""
        
        if request.method not in self._methods:
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=-32601,
                    message="Method not found",
                    data=f"Unknown method: {request.method}"
                ).dict()
            )
        
        try:
            handler = self._methods[request.method]
            result = await handler(request.params or {})
            
            return MCPResponse(
                id=request.id,
                result=result
            )
        
        except Exception as e:
            logger.error(
                f"Error processing request method '{request.method}': {str(e)}"
            )
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=-32603,
                    message="Internal error",
                    data=str(e)
                ).dict()
            )
    
    # Handler methods (reuse from TCP server)
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request."""
        return {
            "protocolVersion": "1.0",
            "serverInfo": {
                "name": "mnemo",
                "version": "0.2.0",
                "description": "LangChain-powered Universal Memory System for Cursor"
            },
            "capabilities": {
                "resources": True,
                "tools": True,
                "prompts": True,
                "extensions": ["mnemo"]
            }
        }
    
    async def _handle_list_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available resources."""
        resources = await self.resource_handler.list_resources()
        return {"resources": [r.dict() for r in resources]}
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools."""
        tools = await self.tool_handler.list_tools()
        return {"tools": [t.dict() for t in tools]}
    
    async def _handle_list_prompts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available prompts."""
        prompts = await self.prompt_handler.list_prompts()
        return {"prompts": [p.dict() for p in prompts]}
    
    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a specific resource."""
        uri = params.get("uri")
        if not uri:
            raise ValueError("Missing required parameter: uri")
        
        content = await self.resource_handler.read_resource(uri)
        return {"content": content}
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool."""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if not tool_name:
            raise ValueError("Missing required parameter: name")
        
        result = await self.tool_handler.call_tool(tool_name, tool_args)
        return {"result": result}
    
    async def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a prompt template."""
        prompt_name = params.get("name")
        prompt_args = params.get("arguments", {})
        
        if not prompt_name:
            raise ValueError("Missing required parameter: name")
        
        prompt = await self.prompt_handler.get_prompt(prompt_name, prompt_args)
        return {"prompt": prompt}
    
    async def _handle_set_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set Mnemo context."""
        self.memory_client.set_context(**params)
        return {
            "success": True,
            "context": self.memory_client.get_context()
        }
    
    async def _handle_get_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory statistics."""
        stats = self.memory_client.get_stats()
        return {"stats": stats}


def main():
    """Main entry point for stdio server."""
    server = StdioMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()