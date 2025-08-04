"""StreamableHTTP FastAPI-based MCP server for Mnemo with SSE support."""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel
from sse_starlette import EventSourceResponse

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.mcp.handlers import ResourceHandler, ToolHandler, PromptHandler
from mnemo.mcp.types import MCPRequest, MCPResponse, MCPError
from mnemo.mcp.auto_tracker import AutoProjectTracker, SessionMemoryTracker


# Header names (following MCP spec)
MCP_SESSION_ID_HEADER = "mcp-session-id"
MCP_PROTOCOL_VERSION_HEADER = "mcp-protocol-version"
LAST_EVENT_ID_HEADER = "last-event-id"

# Content types
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_SSE = "text/event-stream"


class MCPRequestModel(BaseModel):
    """MCP request model for FastAPI."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = {}
    id: Optional[Any] = None


# Global memory client and handlers
memory_client: Optional[MnemoMemoryClient] = None
auto_tracking_client: Optional[MnemoMemoryClient] = None
auto_tracking_store: Optional[MnemoVectorStore] = None
resource_handler: Optional[ResourceHandler] = None
tool_handler: Optional[ToolHandler] = None
prompt_handler: Optional[PromptHandler] = None
auto_tracker: Optional[AutoProjectTracker] = None
session_tracker: Optional[SessionMemoryTracker] = None

# Active SSE connections
active_connections: Dict[str, asyncio.Queue] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize memory system on startup."""
    global memory_client, resource_handler, tool_handler, prompt_handler, auto_tracker, session_tracker
    global auto_tracking_client, auto_tracking_store
    
    # Get configuration from environment
    db_path = os.getenv("MNEMO_DB_PATH", "./mnemo_mcp_db")
    collection = os.getenv("MNEMO_COLLECTION", "cursor_memories")
    auto_tracking = os.getenv("MNEMO_AUTO_TRACKING", "true").lower() == "true"
    tracking_interval = int(os.getenv("MNEMO_TRACKING_INTERVAL", "300"))  # 5 minutes default
    session_tracking = os.getenv("MNEMO_SESSION_TRACKING", "true").lower() == "true"
    
    # Get embedding model from environment
    embedding_model = os.getenv("MNEMO_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
    
    # Initialize embeddings
    from mnemo.core.embeddings import MnemoEmbeddings
    embeddings = MnemoEmbeddings(
        sentence_transformer_model=embedding_model,
        use_mock=False
    )
    
    # Initialize memory system
    vector_store = MnemoVectorStore(
        collection_name=collection,
        persist_directory=db_path,
        embedding_function=embeddings
    )
    memory_client = MnemoMemoryClient(vector_store)
    
    # Initialize separate vector store for auto-tracking
    if auto_tracking:
        auto_tracking_store = MnemoVectorStore(
            collection_name=f"{collection}_autotrack",
            persist_directory=db_path,
            embedding_function=embeddings
        )
        auto_tracking_client = MnemoMemoryClient(auto_tracking_store)
    
    # Initialize handlers
    resource_handler = ResourceHandler(memory_client)
    tool_handler = ToolHandler(memory_client)
    prompt_handler = PromptHandler(memory_client)
    
    # Initialize auto tracker with separate client
    auto_tracker = AutoProjectTracker(auto_tracking_client if auto_tracking_client else memory_client)
    
    # Initialize session tracker with separate client
    if session_tracking:
        session_tracker = SessionMemoryTracker(auto_tracking_client if auto_tracking_client else memory_client)
    
    print(f"[Streamable MCP Server] Mnemo MCP Server initialized with SSE support")
    print(f"[MCP Server] Using embedding model: {embedding_model}")
    print(f"   Database: {db_path}")
    print(f"   Main collection: {collection}")
    if auto_tracking:
        print(f"   Auto-tracking collection: {collection}_autotrack")
    print(f"   Auto-tracking: {'Enabled' if auto_tracking else 'Disabled'}")
    print(f"   Session tracking: {'Enabled' if session_tracking else 'Disabled'}")
    
    # Start auto tracking if enabled
    if auto_tracking:
        await auto_tracker.start_tracking(tracking_interval)
    
    yield
    
    # Cleanup
    if auto_tracker and auto_tracker.is_tracking:
        await auto_tracker.stop_tracking()
    
    print("[Streamable MCP Server] Shutting down Mnemo MCP Server")


app = FastAPI(
    title="Mnemo Streamable MCP Server",
    description="FastAPI-based MCP server for Mnemo with SSE support",
    version="0.3.0",
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
    return {"status": "ok", "service": "mnemo-mcp-streamable"}


async def handle_mcp_method(request: MCPRequestModel) -> Dict[str, Any]:
    """Handle MCP method calls and return results."""
    try:
        # Process based on method
        if request.method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "serverInfo": {
                    "name": "mnemo-streamable",
                    "version": "0.3.0",
                    "description": "LangChain-powered Universal Memory System with SSE Support"
                },
                "capabilities": {
                    "resources": {},
                    "tools": {},
                    "prompts": {},
                    "extensions": ["mnemo", "streamable"]
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
                content = arguments.get("content") or arguments.get("query") or str(arguments)
                session_tracker.add_message("user", f"Tool: {tool_name} - {content}", "tool_call")
            
            result = await tool_handler.call_tool(tool_name, arguments)
            
            # Track result if session tracking enabled
            if session_tracker and tool_name in ["remember", "recall", "search"]:
                result_summary = str(result)[:200] if result else "No result"
                session_tracker.add_message("assistant", f"Result: {result_summary}", "tool_result")
        
        elif request.method == "resources/list":
            resources = await resource_handler.list_resources()
            result = {"resources": [res.dict(by_alias=True) for res in resources]}
        
        elif request.method == "resources/read":
            uri = request.params.get("uri")
            result = await resource_handler.read_resource(uri)
        
        elif request.method == "prompts/list":
            prompts = await prompt_handler.list_prompts()
            result = {"prompts": [prompt.dict(by_alias=True) for prompt in prompts]}
        
        elif request.method == "prompts/get":
            name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            result = await prompt_handler.get_prompt(name, arguments)
        
        else:
            raise ValueError(f"Method not found: {request.method}")
        
        return result
    
    except Exception as e:
        raise e


@app.post("/mcp")
async def handle_mcp_request(request: Request):
    """Handle MCP requests with optional SSE support."""
    # Check Accept header
    accept_header = request.headers.get("accept", "")
    wants_sse = "text/event-stream" in accept_header
    
    # Get session ID from headers
    session_id = request.headers.get(MCP_SESSION_ID_HEADER)
    
    # Parse request body
    try:
        body = await request.json()
        mcp_request = MCPRequestModel(**body)
    except Exception as e:
        return Response(
            content=json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": str(e)
                },
                "id": None
            }),
            status_code=400,
            media_type="application/json"
        )
    
    print(f"📥 Received MCP request: {mcp_request.method} (SSE: {wants_sse})")
    
    if wants_sse:
        # SSE mode - return streaming response
        async def event_generator():
            try:
                # Process the request
                result = await handle_mcp_method(mcp_request)
                
                # Send the response as an SSE event
                response_data = {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": mcp_request.id
                }
                
                yield {
                    "event": "message",
                    "data": json.dumps(response_data),
                    "id": str(mcp_request.id) if mcp_request.id else None
                }
                
            except Exception as e:
                # Send error as SSE event
                error_data = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    },
                    "id": mcp_request.id
                }
                
                yield {
                    "event": "message",
                    "data": json.dumps(error_data),
                    "id": str(mcp_request.id) if mcp_request.id else None
                }
        
        headers = {
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        }
        if session_id:
            headers[MCP_SESSION_ID_HEADER] = session_id
            
        return EventSourceResponse(event_generator(), headers=headers)
    
    else:
        # Regular JSON mode
        try:
            result = await handle_mcp_method(mcp_request)
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": mcp_request.id
            }
        
        except Exception as e:
            print(f"[MCP ERROR] Exception: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return Response(
                content=json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    },
                    "id": mcp_request.id
                }),
                status_code=500,
                media_type="application/json"
            )


@app.get("/sse")
async def sse_endpoint(request: Request):
    """Standalone SSE endpoint for server-initiated messages."""
    session_id = request.headers.get(MCP_SESSION_ID_HEADER, "default")
    
    # Create a queue for this connection
    queue = asyncio.Queue()
    active_connections[session_id] = queue
    
    async def event_generator():
        try:
            while True:
                # Wait for messages in the queue
                message = await queue.get()
                
                yield {
                    "event": "message",
                    "data": json.dumps(message),
                    "id": str(message.get("id")) if message.get("id") else None
                }
                
        except asyncio.CancelledError:
            # Clean up on disconnect
            if session_id in active_connections:
                del active_connections[session_id]
            raise
    
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
    }
    if session_id:
        headers[MCP_SESSION_ID_HEADER] = session_id
        
    return EventSourceResponse(event_generator(), headers=headers)


def run_server(host: str = "0.0.0.0", port: int = 3334):
    """Run the FastAPI server with SSE support."""
    uvicorn.run(
        "mnemo.mcp.streamable_fastapi_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()