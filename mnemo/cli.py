"""Command line interface for Mnemo (LangChain version)."""

import os
from typing import Optional, Set
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient

app = typer.Typer(help="Mnemo - LangChain-powered Universal Memory System")
console = Console()


def get_memory_client(
    collection_name: Optional[str] = None,
    persist_directory: Optional[str] = None
) -> MnemoMemoryClient:
    """Get a configured memory client."""
    
    # Use defaults if not specified
    collection_name = collection_name or "mnemo_memories"
    persist_directory = persist_directory or "./mnemo_db"
    
    # Create vector store and client
    vector_store = MnemoVectorStore(
        collection_name=collection_name,
        persist_directory=persist_directory
    )
    
    return MnemoMemoryClient(vector_store)


@app.command()
def remember(
    key: str = typer.Argument(..., help="Memory key"),
    content: str = typer.Argument(..., help="Content to remember"),
    memory_type: str = typer.Option("fact", help="Type of memory"),
    scope: str = typer.Option("workspace", help="Memory scope"),
    priority: str = typer.Option("medium", help="Memory priority"),
    tags: Optional[str] = typer.Option(None, help="Comma-separated tags"),
    workspace: Optional[str] = typer.Option(None, help="Workspace path"),
    project: Optional[str] = typer.Option(None, help="Project name"),
    expires_in: Optional[int] = typer.Option(None, help="Expires in seconds"),
    collection: Optional[str] = typer.Option(None, help="Collection name"),
    db_dir: Optional[str] = typer.Option(None, help="Database directory")
):
    """Remember something."""
    
    try:
        client = get_memory_client(collection, db_dir)
        
        if workspace:
            client.set_context(workspace_path=workspace)
        if project:
            client.set_context(project_name=project)
        
        tag_set = set(tags.split(",")) if tags else None
        
        memory_id = client.remember(
            key=key,
            content=content,
            memory_type=memory_type,
            scope=scope,
            priority=priority,
            tags=tag_set,
            expires_in_seconds=expires_in
        )
        
        console.print(Panel(
            f"✅ Remembered: {key}\n"
            f"ID: {memory_id}\n"
            f"Type: {memory_type}\n"
            f"Scope: {scope}",
            title="Memory Stored",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(Panel(
            f"❌ Error storing memory: {str(e)}",
            title="Error",
            border_style="red"
        ))


@app.command()
def recall(
    query: str = typer.Argument(..., help="Query to recall"),
    collection: Optional[str] = typer.Option(None, help="Collection name"),
    db_dir: Optional[str] = typer.Option(None, help="Database directory")
):
    """Recall the most relevant memory for a query."""
    
    try:
        client = get_memory_client(collection, db_dir)
        content = client.recall(query)
        
        if content is not None:
            console.print(Panel(
                f"Query: {query}\n"
                f"Content: {content}",
                title="Memory Recalled",
                border_style="blue"
            ))
        else:
            console.print(Panel(
                f"❌ No relevant memory found for: {query}",
                title="Memory Not Found",
                border_style="red"
            ))
            
    except Exception as e:
        console.print(Panel(
            f"❌ Error recalling memory: {str(e)}",
            title="Error",
            border_style="red"
        ))


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    memory_types: Optional[str] = typer.Option(None, help="Comma-separated memory types"),
    tags: Optional[str] = typer.Option(None, help="Comma-separated tags"),
    limit: int = typer.Option(10, help="Maximum results"),
    threshold: float = typer.Option(0.7, help="Similarity threshold"),
    workspace: Optional[str] = typer.Option(None, help="Workspace path"),
    project: Optional[str] = typer.Option(None, help="Project name"),
    collection: Optional[str] = typer.Option(None, help="Collection name"),
    db_dir: Optional[str] = typer.Option(None, help="Database directory")
):
    """Search memories."""
    
    try:
        client = get_memory_client(collection, db_dir)
        
        if workspace:
            client.set_context(workspace_path=workspace)
        if project:
            client.set_context(project_name=project)
        
        type_list = memory_types.split(",") if memory_types else None
        tag_set = set(tags.split(",")) if tags else None
        
        results = client.search(
            query=query,
            memory_types=type_list,
            tags=tag_set,
            limit=limit,
            similarity_threshold=threshold
        )
        
        if results:
            table = Table(title=f"Search Results for: {query}")
            table.add_column("Type", style="cyan")
            table.add_column("Content", style="white", max_width=60)
            table.add_column("Tags", style="yellow")
            table.add_column("Score", style="green")
            table.add_column("Created", style="magenta")
            
            for memory in results:
                content_preview = memory["content"][:100] + "..." if len(memory["content"]) > 100 else memory["content"]
                tags_str = ", ".join(memory["tags"]) if memory["tags"] else ""
                
                table.add_row(
                    memory["type"],
                    content_preview,
                    tags_str,
                    f"{memory['similarity_score']:.3f}",
                    memory["created_at"][:10]
                )
            
            console.print(table)
        else:
            console.print(Panel(
                f"❌ No memories found matching: {query}",
                title="No Results",
                border_style="red"
            ))
            
    except Exception as e:
        console.print(Panel(
            f"❌ Error searching memories: {str(e)}",
            title="Error",
            border_style="red"
        ))


@app.command()
def stats(
    collection: Optional[str] = typer.Option(None, help="Collection name"),
    db_dir: Optional[str] = typer.Option(None, help="Database directory")
):
    """Show memory statistics."""
    
    try:
        client = get_memory_client(collection, db_dir)
        stats_data = client.get_stats()
        
        table = Table(title="Memory Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Memories", str(stats_data.get("total_count", 0)))
        table.add_row("Backend", stats_data.get("backend", "unknown"))
        table.add_row("Collection", stats_data.get("collection_name", "unknown"))
        
        if "type_counts" in stats_data:
            for memory_type, count in stats_data["type_counts"].items():
                table.add_row(f"  {memory_type.title()} memories", str(count))
        
        if "scope_counts" in stats_data:
            for scope, count in stats_data["scope_counts"].items():
                table.add_row(f"  {scope.title()} scope", str(count))
        
        console.print(table)
        
    except Exception as e:
        console.print(Panel(
            f"❌ Error getting stats: {str(e)}",
            title="Error",
            border_style="red"
        ))


@app.command()
def workspace_context(
    workspace_path: str = typer.Argument(..., help="Workspace path"),
    collection: Optional[str] = typer.Option(None, help="Collection name"),
    db_dir: Optional[str] = typer.Option(None, help="Database directory")
):
    """Get all context for a workspace."""
    
    try:
        client = get_memory_client(collection, db_dir)
        context = client.get_workspace_context(workspace_path)
        
        console.print(Panel(
            f"📁 Workspace Context for: {workspace_path}",
            title="Workspace Context",
            border_style="blue"
        ))
        
        for category, memories in context.items():
            if memories:
                console.print(f"\n🔧 {category.title()}: {len(memories)} items")
                for memory in memories[:3]:  # Show first 3
                    content_preview = memory["content"][:80] + "..." if len(memory["content"]) > 80 else memory["content"]
                    console.print(f"  • {content_preview}")
                if len(memories) > 3:
                    console.print(f"  ... and {len(memories) - 3} more")
        
    except Exception as e:
        console.print(Panel(
            f"❌ Error getting workspace context: {str(e)}",
            title="Error",
            border_style="red"
        ))


@app.command()
def code_pattern(
    pattern_name: str = typer.Argument(..., help="Pattern name"),
    code: str = typer.Argument(..., help="Code content"),
    language: str = typer.Argument(..., help="Programming language"),
    description: str = typer.Argument(..., help="Pattern description"),
    tags: Optional[str] = typer.Option(None, help="Comma-separated tags"),
    collection: Optional[str] = typer.Option(None, help="Collection name"),
    db_dir: Optional[str] = typer.Option(None, help="Database directory")
):
    """Store a code pattern."""
    
    try:
        client = get_memory_client(collection, db_dir)
        
        tag_set = set(tags.split(",")) if tags else None
        
        memory_id = client.remember_code_pattern(
            pattern_name=pattern_name,
            code=code,
            language=language,
            description=description,
            tags=tag_set
        )
        
        console.print(Panel(
            f"✅ Code pattern stored: {pattern_name}\n"
            f"ID: {memory_id}\n"
            f"Language: {language}",
            title="Code Pattern Stored",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(Panel(
            f"❌ Error storing code pattern: {str(e)}",
            title="Error",
            border_style="red"
        ))


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()