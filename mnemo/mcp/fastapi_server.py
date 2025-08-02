"""FastAPI-based MCP server for Mnemo."""

import os
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel
import json
import asyncio

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.mcp.handlers import ResourceHandler, ToolHandler, PromptHandler
from mnemo.mcp.types import MCPRequest, MCPResponse, MCPError
from mnemo.mcp.auto_tracker import AutoProjectTracker, SessionMemoryTracker


class MCPRequestModel(BaseModel):
    """MCP request model for FastAPI."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = {}
    id: Optional[Any] = None


# Global memory client
memory_client: Optional[MnemoMemoryClient] = None
resource_handler: Optional[ResourceHandler] = None
tool_handler: Optional[ToolHandler] = None
prompt_handler: Optional[PromptHandler] = None
auto_tracker: Optional[AutoProjectTracker] = None
session_tracker: Optional[SessionMemoryTracker] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize memory system on startup."""
    global memory_client, resource_handler, tool_handler, prompt_handler, auto_tracker, session_tracker
    
    # Get configuration from environment
    db_path = os.getenv("MNEMO_DB_PATH", "./mnemo_mcp_db")
    collection = os.getenv("MNEMO_COLLECTION", "cursor_memories")
    auto_tracking = os.getenv("MNEMO_AUTO_TRACKING", "true").lower() == "true"
    tracking_interval = int(os.getenv("MNEMO_TRACKING_INTERVAL", "300"))  # 5 minutes default
    session_tracking = os.getenv("MNEMO_SESSION_TRACKING", "true").lower() == "true"
    
    # Initialize memory system
    vector_store = MnemoVectorStore(
        collection_name=collection,
        persist_directory=db_path
    )
    memory_client = MnemoMemoryClient(vector_store)
    
    # Initialize handlers
    resource_handler = ResourceHandler(memory_client)
    tool_handler = ToolHandler(memory_client)
    prompt_handler = PromptHandler(memory_client)
    
    # Initialize auto tracker
    auto_tracker = AutoProjectTracker(memory_client)
    
    # Initialize session tracker
    if session_tracking:
        session_tracker = SessionMemoryTracker(memory_client)
    
    print(f"[MCP Server] Mnemo MCP Server initialized")
    print(f"   Database: {db_path}")
    print(f"   Collection: {collection}")
    print(f"   Auto-tracking: {'Enabled' if auto_tracking else 'Disabled'}")
    print(f"   Session tracking: {'Enabled' if session_tracking else 'Disabled'}")
    
    # Start auto tracking if enabled
    if auto_tracking:
        await auto_tracker.start_tracking(tracking_interval)
    
    yield
    
    # Cleanup
    if auto_tracker and auto_tracker.is_tracking:
        await auto_tracker.stop_tracking()
    
    print("[MCP Server] Shutting down Mnemo MCP Server")


app = FastAPI(
    title="Mnemo MCP Server",
    description="FastAPI-based MCP server for Mnemo memory system",
    version="0.2.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "mnemo-mcp"}


# SSE endpoint removed - Cursor uses HTTP transport only


@app.post("/mcp")
async def handle_mcp_request(request: MCPRequestModel):
    """Handle MCP requests."""
    print(f"📥 Received MCP request: {request.method}")
    try:
        # Process based on method
        if request.method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "serverInfo": {
                    "name": "mnemo",
                    "version": "0.2.0",
                    "description": "LangChain-powered Universal Memory System for Cursor"
                },
                "capabilities": {
                    "resources": {},
                    "tools": {},
                    "prompts": {},
                    "extensions": ["mnemo"]
                }
            }
        
        elif request.method == "tools/list":
            tools = await tool_handler.list_tools()
            result = {"tools": [tool.dict(by_alias=True) for tool in tools]}
        
        elif request.method == "listTools":  # Legacy support
            tools = await tool_handler.list_tools()
            result = {"tools": [tool.dict() for tool in tools]}
        
        elif request.method == "tools/call":
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            
            # Track session if enabled
            if session_tracker and tool_name in ["remember", "recall", "search"]:
                # Extract meaningful content from arguments
                content = arguments.get("content") or arguments.get("query") or str(arguments)
                session_tracker.add_message("user", f"Tool: {tool_name} - {content}", "tool_call")
            
            result = await tool_handler.call_tool(tool_name, arguments)
            
            # Track result if session tracking enabled
            if session_tracker and tool_name in ["remember", "recall", "search"]:
                result_summary = str(result)[:200] if result else "No result"
                session_tracker.add_message("assistant", f"Result: {result_summary}", "tool_result")
        
        elif request.method == "callTool":  # Legacy support
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            result = await tool_handler.call_tool(tool_name, arguments)
        
        elif request.method == "resources/list":
            resources = await resource_handler.list_resources()
            result = {"resources": [res.dict(by_alias=True) for res in resources]}
        
        elif request.method == "listResources":  # Legacy support
            resources = await resource_handler.list_resources()
            result = {"resources": [res.dict() for res in resources]}
        
        elif request.method == "resources/read":
            uri = request.params.get("uri")
            result = await resource_handler.read_resource(uri)
        
        elif request.method == "readResource":  # Legacy support
            uri = request.params.get("uri")
            result = await resource_handler.read_resource(uri)
        
        elif request.method == "prompts/list":
            prompts = await prompt_handler.list_prompts()
            result = {"prompts": [prompt.dict(by_alias=True) for prompt in prompts]}
        
        elif request.method == "listPrompts":  # Legacy support
            prompts = await prompt_handler.list_prompts()
            result = {"prompts": [prompt.dict() for prompt in prompts]}
        
        elif request.method == "prompts/get":
            name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            result = await prompt_handler.get_prompt(name, arguments)
        
        elif request.method == "getPrompt":  # Legacy support
            name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            result = await prompt_handler.get_prompt(name, arguments)
        
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                },
                "id": request.id
            }
        
        # Return success response
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request.id
        }
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            },
            "id": request.id
        }


def run_server(host: str = "0.0.0.0", port: int = 3333):
    """Run the FastAPI server."""
    uvicorn.run(
        "mnemo.mcp.fastapi_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()