"""LangChain tools for memory operations."""

from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from mnemo.memory.client import MnemoMemoryClient


class MemoryStoreInput(BaseModel):
    """Input for memory store tool."""
    key: str = Field(description="Unique key for the memory")
    content: str = Field(description="Content to store in memory")
    memory_type: str = Field(default="fact", description="Type of memory (fact, skill, preference, etc.)")
    tags: Optional[str] = Field(default=None, description="Comma-separated tags")


class MemorySearchInput(BaseModel):
    """Input for memory search tool."""
    query: str = Field(description="Search query for finding relevant memories")
    memory_types: Optional[str] = Field(default=None, description="Comma-separated memory types to search")
    limit: int = Field(default=5, description="Maximum number of results")


class MemoryStoreTool(BaseTool):
    """Tool for storing memories."""
    
    name: str = "store_memory"
    description: str = "Store information in long-term memory for future reference"
    args_schema: Type[BaseModel] = MemoryStoreInput
    
    memory_client: MnemoMemoryClient
    
    def __init__(self, memory_client: MnemoMemoryClient, **kwargs):
        super().__init__(**kwargs)
        self.memory_client = memory_client
    
    def _run(
        self,
        key: str,
        content: str,
        memory_type: str = "fact",
        tags: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Store a memory and return the memory ID."""
        
        # Parse tags
        tag_set = set(tags.split(",")) if tags else None
        
        # Store memory
        memory_id = self.memory_client.remember(
            key=key,
            content=content,
            memory_type=memory_type,
            tags=tag_set
        )
        
        return f"Memory stored successfully with ID: {memory_id}"
    
    async def _arun(self, **kwargs: Any) -> str:
        """Async version of _run."""
        return self._run(**kwargs)


class MemorySearchTool(BaseTool):
    """Tool for searching memories."""
    
    name: str = "search_memory"
    description: str = "Search for relevant information in long-term memory"
    args_schema: Type[BaseModel] = MemorySearchInput
    
    memory_client: MnemoMemoryClient
    
    def __init__(self, memory_client: MnemoMemoryClient, **kwargs):
        super().__init__(**kwargs)
        self.memory_client = memory_client
    
    def _run(
        self,
        query: str,
        memory_types: Optional[str] = None,
        limit: int = 5,
        **kwargs: Any
    ) -> str:
        """Search memories and return formatted results."""
        
        # Parse memory types
        type_list = memory_types.split(",") if memory_types else None
        
        # Search memories
        results = self.memory_client.search(
            query=query,
            memory_types=type_list,
            limit=limit
        )
        
        if not results:
            return "No relevant memories found."
        
        # Format results
        formatted_results = []
        for i, memory in enumerate(results, 1):
            result_text = f"""
{i}. [{memory['type']}] {memory['content'][:200]}{'...' if len(memory['content']) > 200 else ''}
   Tags: {', '.join(memory['tags']) if memory['tags'] else 'None'}
   Created: {memory['created_at'][:10]}
   Similarity: {memory['similarity_score']:.3f}
"""
            formatted_results.append(result_text.strip())
        
        return f"Found {len(results)} relevant memories:\n\n" + "\n\n".join(formatted_results)
    
    async def _arun(self, **kwargs: Any) -> str:
        """Async version of _run."""
        return self._run(**kwargs)


class MemoryTool(BaseTool):
    """
    Combined memory tool that can both store and search memories.
    
    This is a unified tool that can handle both memory operations
    based on the input provided.
    """
    
    name: str = "memory"
    description: str = """
    Interact with long-term memory system. Can store or search for information.
    
    To store: Provide 'action=store', 'key', 'content', and optionally 'memory_type' and 'tags'
    To search: Provide 'action=search', 'query', and optionally 'memory_types' and 'limit'
    """
    
    memory_client: MnemoMemoryClient
    
    def __init__(self, memory_client: MnemoMemoryClient, **kwargs):
        super().__init__(**kwargs)
        self.memory_client = memory_client
    
    def _run(self, tool_input: str, **kwargs: Any) -> str:
        """Parse input and execute appropriate memory operation."""
        
        try:
            # Simple parsing of the input
            if "action=store" in tool_input:
                return self._handle_store(tool_input)
            elif "action=search" in tool_input:
                return self._handle_search(tool_input)
            else:
                # Default to search if no action specified
                return self._handle_search(f"query={tool_input}")
        
        except Exception as e:
            return f"Error processing memory operation: {str(e)}"
    
    def _handle_store(self, input_str: str) -> str:
        """Handle memory storage."""
        
        # Extract parameters (simple parsing)
        params = {}
        for param in input_str.split(","):
            if "=" in param:
                key, value = param.split("=", 1)
                params[key.strip()] = value.strip()
        
        required_params = ["key", "content"]
        for param in required_params:
            if param not in params:
                return f"Missing required parameter: {param}"
        
        # Store memory
        tags = set(params.get("tags", "").split(",")) if params.get("tags") else None
        
        memory_id = self.memory_client.remember(
            key=params["key"],
            content=params["content"],
            memory_type=params.get("memory_type", "fact"),
            tags=tags
        )
        
        return f"Memory stored successfully with ID: {memory_id}"
    
    def _handle_search(self, input_str: str) -> str:
        """Handle memory search."""
        
        # Extract query
        if "query=" in input_str:
            query_part = input_str.split("query=")[1].split(",")[0]
            query = query_part.strip()
        else:
            query = input_str.strip()
        
        # Extract other parameters
        params = {}
        for param in input_str.split(","):
            if "=" in param:
                key, value = param.split("=", 1)
                params[key.strip()] = value.strip()
        
        # Search memories
        memory_types = params.get("memory_types", "").split(",") if params.get("memory_types") else None
        limit = int(params.get("limit", 5))
        
        results = self.memory_client.search(
            query=query,
            memory_types=memory_types,
            limit=limit
        )
        
        if not results:
            return "No relevant memories found."
        
        # Format results
        formatted_results = []
        for i, memory in enumerate(results, 1):
            result_text = f"{i}. [{memory['type']}] {memory['content'][:150]}{'...' if len(memory['content']) > 150 else ''}"
            formatted_results.append(result_text)
        
        return f"Found {len(results)} memories:\n" + "\n".join(formatted_results)
    
    async def _arun(self, tool_input: str, **kwargs: Any) -> str:
        """Async version of _run."""
        return self._run(tool_input, **kwargs)