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


if __name__ == "__main__":
    app()