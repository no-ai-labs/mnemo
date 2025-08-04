"""CLI for running MCP server."""

import asyncio
import typer
from rich.console import Console
from rich.panel import Panel

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.mcp.server import MnemoMCPServer

app = typer.Typer(help="Mnemo MCP Server")
console = Console()


@app.command()
def serve(
    host: str = typer.Option("localhost", help="Host to bind to"),
    port: int = typer.Option(3333, help="Port to bind to"),
    collection: str = typer.Option("mnemo_memories", help="ChromaDB collection name"),
    db_dir: str = typer.Option("./mnemo_db", help="Database directory")
):
    """Start the MCP server."""
    
    console.print(Panel(
        f"🚀 Starting Mnemo MCP Server\n"
        f"Host: {host}:{port}\n"
        f"Collection: {collection}\n"
        f"Database: {db_dir}",
        title="Mnemo MCP Server",
        border_style="blue"
    ))
    
    async def run_server():
        # Initialize memory system
        vector_store = MnemoVectorStore(
            collection_name=collection,
            persist_directory=db_dir
        )
        memory_client = MnemoMemoryClient(vector_store)
        
        # Create and start server
        server = MnemoMCPServer(
            memory_client=memory_client,
            host=host,
            port=port
        )
        
        try:
            await server.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down server...[/yellow]")
            await server.stop()
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        console.print("\n[red]Server stopped[/red]")


@app.command()
def test_connection(
    host: str = typer.Option("localhost", help="Server host"),
    port: int = typer.Option(3333, help="Server port")
):
    """Test connection to MCP server."""
    
    import socket
    import json
    
    console.print(f"Testing connection to {host}:{port}...")
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        # Send initialize request
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        }
        
        sock.send((json.dumps(request) + '\n').encode('utf-8'))
        
        # Read response
        response = sock.recv(4096).decode('utf-8')
        response_data = json.loads(response.strip())
        
        if "result" in response_data:
            console.print(Panel(
                f"✅ Connection successful!\n"
                f"Server: {response_data['result']['serverInfo']['name']}\n"
                f"Version: {response_data['result']['serverInfo']['version']}\n"
                f"Protocol: {response_data['result']['protocolVersion']}",
                title="Connection Test",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"❌ Connection failed: {response_data.get('error', 'Unknown error')}",
                title="Connection Test",
                border_style="red"
            ))
        
        sock.close()
        
    except Exception as e:
        console.print(Panel(
            f"❌ Connection failed: {str(e)}",
            title="Connection Test",
            border_style="red"
        ))


@app.command()
def serve_fastapi(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(3333, help="Port to bind to"),
    db_path: str = typer.Option("./mnemo_mcp_db", help="Database directory"),
    collection: str = typer.Option("cursor_memories", help="ChromaDB collection name")
):
    """Start the FastAPI-based MCP server."""
    
    import os
    os.environ["MNEMO_DB_PATH"] = db_path
    os.environ["MNEMO_COLLECTION"] = collection
    
    console.print(Panel(
        f"🚀 Starting Mnemo FastAPI MCP Server\n"
        f"URL: http://{host}:{port}/mcp\n"
        f"Health: http://{host}:{port}/health\n"
        f"Collection: {collection}\n"
        f"Database: {db_path}",
        title="Mnemo FastAPI Server",
        border_style="green"
    ))
    
    from mnemo.mcp.fastapi_server import run_server
    run_server(host=host, port=port)


@app.command()
def serve_streamable(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(3334, help="Port to bind to (default 3334 for streamable)"),
    db_path: str = typer.Option("./mnemo_mcp_db", help="Database directory"),
    collection: str = typer.Option("cursor_memories", help="ChromaDB collection name")
):
    """Start the Streamable FastAPI-based MCP server with SSE support."""
    
    import os
    os.environ["MNEMO_DB_PATH"] = db_path
    os.environ["MNEMO_COLLECTION"] = collection
    
    console.print(Panel(
        f"🚀 Starting Mnemo Streamable MCP Server with SSE\n"
        f"URL: http://{host}:{port}/mcp\n"
        f"SSE: http://{host}:{port}/sse\n"
        f"Health: http://{host}:{port}/health\n"
        f"Collection: {collection}\n"
        f"Database: {db_path}\n"
        f"[yellow]✨ SSE Support Enabled[/yellow]",
        title="Mnemo Streamable Server",
        border_style="cyan"
    ))
    
    from mnemo.mcp.streamable_fastapi_server import run_server
    run_server(host=host, port=port)


@app.command()
def serve_stdio():
    """Start the stdio-based MCP server for use with Cursor."""
    
    import sys
    import json
    import os
    
    db_path = os.getenv("MNEMO_DB_PATH", "./mnemo_mcp_db")
    collection = os.getenv("MNEMO_COLLECTION", "cursor_memories")
    
    console.print(Panel(
        f"🚀 Starting Mnemo STDIO MCP Server\n"
        f"Collection: {collection}\n"
        f"Database: {db_path}\n"
        f"[yellow]Mode: STDIO (for Cursor)[/yellow]",
        title="Mnemo STDIO Server",
        border_style="blue"
    ), file=sys.stderr)
    
    # Import and run the STDIO server
    # For now, we'll use the FastAPI server in STDIO mode
    # TODO: Implement proper STDIO server
    console.print("[red]STDIO mode not yet implemented![/red]", file=sys.stderr)
    console.print("Use the FastAPI server with HTTP transport instead.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    app()