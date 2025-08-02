"""MCP server implementation for Mnemo."""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
import logging

from mnemo.mcp.types import (
    MCPRequest, MCPResponse, MCPError,
    MCPResource, MCPTool, MCPPrompt
)
from mnemo.mcp.handlers import (
    ResourceHandler, ToolHandler, PromptHandler
)
from mnemo.memory.client import MnemoMemoryClient

# Use standard logging instead of structlog for now
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class MnemoMCPServer:
    """
    MCP Server for Mnemo memory system.
    
    Exposes Mnemo's memory capabilities via the Model Context Protocol,
    allowing AI assistants like Cursor to access and manipulate memories.
    """
    
    def __init__(
        self,
        memory_client: MnemoMemoryClient,
        host: str = "localhost",
        port: int = 3333
    ):
        self.memory_client = memory_client
        self.host = host
        self.port = port
        
        # Initialize handlers
        self.resource_handler = ResourceHandler(memory_client)
        self.tool_handler = ToolHandler(memory_client)
        self.prompt_handler = PromptHandler(memory_client)
        
        # Method registry
        self._methods: Dict[str, Callable] = {
            # Discovery methods
            "initialize": self._handle_initialize,
            "listResources": self._handle_list_resources,
            "listTools": self._handle_list_tools,
            "listPrompts": self._handle_list_prompts,
            
            # Resource methods
            "readResource": self._handle_read_resource,
            
            # Tool methods
            "callTool": self._handle_call_tool,
            
            # Prompt methods
            "getPrompt": self._handle_get_prompt,
            
            # Mnemo-specific methods
            "mnemo.setContext": self._handle_set_context,
            "mnemo.getStats": self._handle_get_stats,
        }
        
        self._server = None
    
    async def start(self):
        """Start the MCP server."""
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )
        
        logger.info(
            f"MCP server started on {self.host}:{self.port}"
        )
        
        async with self._server:
            await self._server.serve_forever()
    
    async def stop(self):
        """Stop the MCP server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("MCP server stopped")
    
    async def _handle_client(self, reader, writer):
        """Handle incoming client connections."""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"Client connected from {client_addr}")
        
        try:
            while True:
                # Read request
                data = await reader.readline()
                if not data:
                    break
                
                try:
                    request_str = data.decode('utf-8').strip()
                    if not request_str:
                        continue
                    
                    # Parse JSON-RPC request
                    request_data = json.loads(request_str)
                    request = MCPRequest(**request_data)
                    
                    # Process request
                    response = await self._process_request(request)
                    
                    # Send response
                    response_str = response.json() + '\n'
                    writer.write(response_str.encode('utf-8'))
                    await writer.drain()
                    
                except json.JSONDecodeError as e:
                    # Send parse error
                    error_response = MCPResponse(
                        error=MCPError(
                            code=-32700,
                            message="Parse error",
                            data=str(e)
                        ).dict()
                    )
                    writer.write((error_response.json() + '\n').encode('utf-8'))
                    await writer.drain()
                
                except Exception as e:
                    logger.error(f"Error handling request: {str(e)}")
                    # Send internal error
                    error_response = MCPResponse(
                        error=MCPError(
                            code=-32603,
                            message="Internal error",
                            data=str(e)
                        ).dict()
                    )
                    writer.write((error_response.json() + '\n').encode('utf-8'))
                    await writer.drain()
        
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Client disconnected: {client_addr}")
    
    async def _process_request(self, request: MCPRequest) -> MCPResponse:
        """Process a single MCP request."""
        
        # Check if method exists
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
            # Call the handler
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
    
    # Handler methods
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request."""
        return {
            "protocolVersion": "1.0",
            "serverInfo": {
                "name": "mnemo",
                "version": "0.2.0",
                "description": "LangChain-powered Universal Memory System"
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
        return {
            "resources": [r.dict() for r in resources]
        }
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools."""
        tools = await self.tool_handler.list_tools()
        return {
            "tools": [t.dict() for t in tools]
        }
    
    async def _handle_list_prompts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available prompts."""
        prompts = await self.prompt_handler.list_prompts()
        return {
            "prompts": [p.dict() for p in prompts]
        }
    
    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a specific resource."""
        uri = params.get("uri")
        if not uri:
            raise ValueError("Missing required parameter: uri")
        
        content = await self.resource_handler.read_resource(uri)
        return {
            "content": content
        }
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool."""
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if not tool_name:
            raise ValueError("Missing required parameter: name")
        
        result = await self.tool_handler.call_tool(tool_name, tool_args)
        return {
            "result": result
        }
    
    async def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a prompt template."""
        prompt_name = params.get("name")
        prompt_args = params.get("arguments", {})
        
        if not prompt_name:
            raise ValueError("Missing required parameter: name")
        
        prompt = await self.prompt_handler.get_prompt(prompt_name, prompt_args)
        return {
            "prompt": prompt
        }
    
    async def _handle_set_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set Mnemo context (workspace, project, etc)."""
        self.memory_client.set_context(**params)
        return {
            "success": True,
            "context": self.memory_client.get_context()
        }
    
    async def _handle_get_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory statistics."""
        stats = self.memory_client.get_stats()
        return {
            "stats": stats
        }