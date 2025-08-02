"""MCP handlers for different protocol features."""

from typing import Dict, List, Any, Optional
import json
from urllib.parse import urlparse, parse_qs

from mnemo.mcp.types import MCPResource, MCPTool, MCPPrompt, MCPResourceType
from mnemo.memory.client import MnemoMemoryClient


class ResourceHandler:
    """Handler for MCP resource operations."""
    
    def __init__(self, memory_client: MnemoMemoryClient):
        self.memory_client = memory_client
    
    async def list_resources(self) -> List[MCPResource]:
        """List available memory resources."""
        resources = []
        
        # Get current context
        context = self.memory_client.get_context()
        
        # Workspace memories
        if context.get("workspace_path"):
            resources.append(MCPResource(
                id=f"workspace:{context['workspace_path']}",
                name=f"Workspace Memories: {context['workspace_path']}",
                type=MCPResourceType.MEMORY,
                description="All memories for the current workspace",
                uri=f"mnemo://workspace?path={context['workspace_path']}"
            ))
        
        # Project memories
        if context.get("project_name"):
            resources.append(MCPResource(
                id=f"project:{context['project_name']}",
                name=f"Project Memories: {context['project_name']}",
                type=MCPResourceType.MEMORY,
                description="All memories for the current project",
                uri=f"mnemo://project?name={context['project_name']}"
            ))
        
        # Global memories
        resources.append(MCPResource(
            id="global",
            name="Global Memories",
            type=MCPResourceType.MEMORY,
            description="All global memories",
            uri="mnemo://global"
        ))
        
        # Recent memories
        resources.append(MCPResource(
            id="recent",
            name="Recent Memories",
            type=MCPResourceType.MEMORY,
            description="Recently accessed memories",
            uri="mnemo://recent?limit=20"
        ))
        
        return resources
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a specific resource by URI."""
        parsed = urlparse(uri)
        
        if parsed.scheme != "mnemo":
            raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")
        
        query_params = parse_qs(parsed.query)
        
        if parsed.netloc == "workspace":
            # Get workspace memories
            workspace_path = query_params.get("path", [None])[0]
            if workspace_path:
                context = self.memory_client.get_workspace_context(workspace_path)
                return {
                    "type": "workspace_context",
                    "workspace": workspace_path,
                    "memories": context
                }
        
        elif parsed.netloc == "project":
            # Get project memories
            project_name = query_params.get("name", [None])[0]
            if project_name:
                memories = self.memory_client.search(
                    query="",
                    limit=100,
                    similarity_threshold=0.0
                )
                # Filter by project
                project_memories = [
                    m for m in memories 
                    if m.get("project_name") == project_name
                ]
                return {
                    "type": "project_memories",
                    "project": project_name,
                    "memories": project_memories
                }
        
        elif parsed.netloc == "global":
            # Get global memories
            memories = self.memory_client.search(
                query="",
                scopes=["global"],
                limit=100,
                similarity_threshold=0.0
            )
            return {
                "type": "global_memories",
                "memories": memories
            }
        
        elif parsed.netloc == "recent":
            # Get recent memories
            limit = int(query_params.get("limit", [20])[0])
            memories = self.memory_client.search(
                query="",
                limit=limit,
                similarity_threshold=0.0
            )
            # Sort by access time
            memories.sort(
                key=lambda m: m.get("accessed_at", m.get("created_at", "")),
                reverse=True
            )
            return {
                "type": "recent_memories",
                "memories": memories[:limit]
            }
        
        else:
            raise ValueError(f"Unknown resource type: {parsed.netloc}")


class ToolHandler:
    """Handler for MCP tool operations."""
    
    def __init__(self, memory_client: MnemoMemoryClient):
        self.memory_client = memory_client
    
    async def list_tools(self) -> List[MCPTool]:
        """List available memory tools."""
        return [
            MCPTool(
                name="remember",
                description="Store a memory",
                input_schema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Memory key"},
                        "content": {"type": "string", "description": "Memory content"},
                        "memory_type": {
                            "type": "string",
                            "enum": ["fact", "skill", "preference", "code_pattern"],
                            "default": "fact"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Memory tags"
                        }
                    },
                    "required": ["key", "content"]
                }
            ),
            
            MCPTool(
                name="recall",
                description="Recall the most relevant memory",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            ),
            
            MCPTool(
                name="search",
                description="Search memories",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "memory_types": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                }
            ),
            
            MCPTool(
                name="forget",
                description="Delete a memory",
                input_schema={
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string", "description": "Memory ID to delete"}
                    },
                    "required": ["memory_id"]
                }
            ),
            
            MCPTool(
                name="remember_code_pattern",
                description="Store a code pattern",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pattern_name": {"type": "string"},
                        "code": {"type": "string"},
                        "language": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["pattern_name", "code", "language", "description"]
                }
            )
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with given arguments."""
        
        if tool_name == "remember":
            tags = set(arguments.get("tags", []))
            memory_id = self.memory_client.remember(
                key=arguments["key"],
                content=arguments["content"],
                memory_type=arguments.get("memory_type", "fact"),
                tags=tags
            )
            return {"memory_id": memory_id, "success": True}
        
        elif tool_name == "recall":
            content = self.memory_client.recall(arguments["query"])
            return {"content": content, "found": content is not None}
        
        elif tool_name == "search":
            results = self.memory_client.search(
                query=arguments["query"],
                memory_types=arguments.get("memory_types"),
                limit=arguments.get("limit", 10)
            )
            return {"results": results, "count": len(results)}
        
        elif tool_name == "forget":
            success = self.memory_client.forget(arguments["memory_id"])
            return {"success": success}
        
        elif tool_name == "remember_code_pattern":
            memory_id = self.memory_client.remember_code_pattern(
                pattern_name=arguments["pattern_name"],
                code=arguments["code"],
                language=arguments["language"],
                description=arguments["description"]
            )
            return {"memory_id": memory_id, "success": True}
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")


class PromptHandler:
    """Handler for MCP prompt operations."""
    
    def __init__(self, memory_client: MnemoMemoryClient):
        self.memory_client = memory_client
    
    async def list_prompts(self) -> List[MCPPrompt]:
        """List available prompt templates."""
        return [
            MCPPrompt(
                name="memory_enhanced_response",
                description="Generate a response using relevant memories",
                arguments=["query", "context"],
                template="""Based on the following memories and context, provide a helpful response:

Relevant Memories:
{memories}

Context: {context}

Query: {query}

Response:"""
            ),
            
            MCPPrompt(
                name="code_generation_with_patterns",
                description="Generate code using stored patterns",
                arguments=["task", "language"],
                template="""Generate code for the following task using these patterns as reference:

Code Patterns:
{patterns}

Task: {task}
Language: {language}

Generated Code:"""
            ),
            
            MCPPrompt(
                name="knowledge_synthesis",
                description="Synthesize knowledge from multiple memories",
                arguments=["topic"],
                template="""Synthesize the following memories about {topic}:

Memories:
{memories}

Synthesis:"""
            )
        ]
    
    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> str:
        """Get a filled prompt template."""
        
        if prompt_name == "memory_enhanced_response":
            # Search for relevant memories
            query = arguments.get("query", "")
            memories = self.memory_client.search(query, limit=5)
            
            # Format memories
            memory_text = "\n".join([
                f"- [{m['type']}] {m['content']}"
                for m in memories
            ])
            
            return f"""Based on the following memories and context, provide a helpful response:

Relevant Memories:
{memory_text}

Context: {arguments.get('context', 'No specific context')}

Query: {query}

Response:"""
        
        elif prompt_name == "code_generation_with_patterns":
            # Search for code patterns
            task = arguments.get("task", "")
            language = arguments.get("language", "")
            
            patterns = self.memory_client.search(
                query=f"{task} {language}",
                memory_types=["code_pattern"],
                limit=3
            )
            
            # Format patterns
            pattern_text = "\n\n".join([
                f"Pattern: {p['content']}"
                for p in patterns
            ])
            
            return f"""Generate code for the following task using these patterns as reference:

Code Patterns:
{pattern_text}

Task: {task}
Language: {language}

Generated Code:"""
        
        elif prompt_name == "knowledge_synthesis":
            # Search for topic-related memories
            topic = arguments.get("topic", "")
            memories = self.memory_client.search(topic, limit=10)
            
            # Format memories by type
            memory_text = "\n".join([
                f"- [{m['type']}] {m['content']}"
                for m in memories
            ])
            
            return f"""Synthesize the following memories about {topic}:

Memories:
{memory_text}

Synthesis:"""
        
        else:
            raise ValueError(f"Unknown prompt: {prompt_name}")