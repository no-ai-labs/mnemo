"""Auto-update call graph when code changes."""

import os
import time
import asyncio
from pathlib import Path
from typing import Set, Dict, Optional
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from mnemo.graph.call_graph_builder import CallGraphBuilder
from mnemo.memory.client import MnemoMemoryClient


class CodeChangeHandler(FileSystemEventHandler):
    """Handle code changes and update call graph."""
    
    def __init__(self, builder: CallGraphBuilder, project_name: str):
        self.builder = builder
        self.project_name = project_name
        self.pending_files: Set[str] = set()
        self.last_update = datetime.now()
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Only process Python files
        if file_path.suffix == '.py':
            print(f"[AUTO-UPDATE] File modified: {file_path}")
            self.pending_files.add(str(file_path))
            
    def process_pending_updates(self):
        """Process all pending file updates."""
        if not self.pending_files:
            return
            
        print(f"[AUTO-UPDATE] Processing {len(self.pending_files)} file changes...")
        
        for file_path in self.pending_files:
            try:
                # Remove old functions from this file
                self.builder.graph.run("""
                    MATCH (f:Function {project: $project, file_path: $file})
                    DETACH DELETE f
                """, project=self.project_name, file=file_path)
                
                # Re-analyze the file
                self.builder._analyze_file(file_path, self.project_name)
                
                print(f"[AUTO-UPDATE] Updated: {file_path}")
                
            except Exception as e:
                print(f"[AUTO-UPDATE] Error updating {file_path}: {e}")
                
        self.pending_files.clear()
        self.last_update = datetime.now()


class CallGraphAutoUpdater:
    """Automatically update call graph on code changes."""
    
    def __init__(self, project_path: str, project_name: str,
                 memory_client: Optional[MnemoMemoryClient] = None):
        self.project_path = Path(project_path)
        self.project_name = project_name
        self.builder = CallGraphBuilder()
        self.memory_client = memory_client
        self.observer = Observer()
        self.handler = CodeChangeHandler(self.builder, project_name)
        
    def start(self):
        """Start watching for file changes."""
        print(f"[AUTO-UPDATE] Starting file watcher for {self.project_path}")
        
        # Initial full analysis
        print(f"[AUTO-UPDATE] Initial analysis...")
        self.builder.build_from_directory(str(self.project_path), self.project_name)
        
        # Setup file watcher
        self.observer.schedule(self.handler, str(self.project_path), recursive=True)
        self.observer.start()
        
        print(f"[AUTO-UPDATE] Watching for changes...")
        
        try:
            while True:
                time.sleep(5)  # Process updates every 5 seconds
                self.handler.process_pending_updates()
                
        except KeyboardInterrupt:
            self.observer.stop()
            print(f"[AUTO-UPDATE] Stopped watching")
            
        self.observer.join()
        
    async def start_async(self):
        """Async version for integration with other services."""
        print(f"[AUTO-UPDATE] Starting async file watcher")
        
        # Initial analysis
        await asyncio.to_thread(
            self.builder.build_from_directory,
            str(self.project_path),
            self.project_name
        )
        
        # Start observer in background
        self.observer.schedule(self.handler, str(self.project_path), recursive=True)
        self.observer.start()
        
        try:
            while True:
                await asyncio.sleep(5)
                await asyncio.to_thread(self.handler.process_pending_updates)
                
                # Save update stats to memory
                if self.memory_client and self.handler.last_update:
                    stats = await self._get_graph_stats()
                    await self._save_update_memory(stats)
                    
        except asyncio.CancelledError:
            self.observer.stop()
            self.observer.join()
            raise
            
    async def _get_graph_stats(self) -> Dict:
        """Get current graph statistics."""
        result = await asyncio.to_thread(
            self.builder.graph.run,
            """
            MATCH (f:Function {project: $project})
            OPTIONAL MATCH (f)-[c:CALLS]->()
            RETURN count(DISTINCT f) as functions, count(c) as calls
            """,
            project=self.project_name
        )
        
        return result.data()[0] if result else {'functions': 0, 'calls': 0}
        
    async def _save_update_memory(self, stats: Dict):
        """Save update statistics to memory."""
        if not self.memory_client:
            return
            
        memory_key = f"call_graph_update_{self.project_name}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        await asyncio.to_thread(
            self.memory_client.remember,
            key=memory_key,
            content=f"Call graph updated: {stats['functions']} functions, {stats['calls']} calls",
            memory_type="fact",
            tags={"call-graph", "auto-update", self.project_name}
        )


def integrate_with_cursor():
    """Integration ideas for Cursor IDE."""
    print("\n=== Cursor Integration Options ===\n")
    
    print("1. MCP Tool Integration:")
    print("   - Add 'update_call_graph' tool to MCP")
    print("   - Trigger on save events via Cursor API")
    
    print("\n2. Background Service:")
    print("   - Run CallGraphAutoUpdater as daemon")
    print("   - Connect via FastAPI endpoints")
    
    print("\n3. Git Hook Integration:")
    print("   - Update on pre-commit")
    print("   - Track changes between commits")
    
    print("\n4. IDE Extension:")
    print("   - Create Cursor extension")
    print("   - Real-time graph visualization")
    
    # Example MCP tool
    print("\nExample MCP tool definition:")
    print("""
    MCPTool(
        name="update_call_graph",
        description="Update call graph for changed files",
        input_schema={
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of changed files"
                }
            }
        }
    )
    """)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        # Start auto-updater
        updater = CallGraphAutoUpdater(".", "mnemo-live")
        updater.start()
    else:
        # Show integration options
        integrate_with_cursor()
        
        print("\nTo start auto-updater:")
        print("  python mnemo/graph/auto_update_graph.py watch")