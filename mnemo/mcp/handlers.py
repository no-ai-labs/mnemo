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
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "success": {"type": "boolean"}
                    }
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
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "found": {"type": "boolean"}
                    }
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
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "count": {"type": "integer"}
                    }
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
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"}
                    }
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
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "success": {"type": "boolean"}
                    }
                }
            ),
            MCPTool(
                name="session_status",
                title="Get Session Status",
                description="Get current chat session tracking status",
                input_schema={
                    "type": "object",
                    "properties": {}
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "message_count": {"type": "integer"},
                        "important_messages": {"type": "integer"},
                        "duration": {"type": "string"}
                    }
                }
            ),
            
            # Code Intelligence Tools
            MCPTool(
                name="analyze_project",
                title="Analyze Project Code",
                description="Analyze a project and build its code knowledge graph",
                input_schema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Path to the project directory"},
                        "project_name": {"type": "string", "description": "Name for the project in the graph"},
                        "language": {
                            "type": "string",
                            "enum": ["python", "kotlin", "javascript", "typescript"],
                            "description": "Primary language of the project"
                        }
                    },
                    "required": ["project_path", "project_name"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "functions": {"type": "integer"},
                        "calls": {"type": "integer"},
                        "files": {"type": "integer"},
                        "success": {"type": "boolean"}
                    }
                }
            ),
            
            MCPTool(
                name="find_pattern",
                title="Find Code Pattern",
                description="Find similar code patterns from analyzed projects",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Pattern to search for (e.g., 'authentication', 'error handling')"},
                        "project": {"type": "string", "description": "Specific project to search in (optional)"}
                    },
                    "required": ["pattern"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "patterns": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "function": {"type": "string"},
                                    "file": {"type": "string"},
                                    "project": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            ),
            
            MCPTool(
                name="compare_projects",
                title="Compare Projects",
                description="Compare code patterns between two projects",
                input_schema={
                    "type": "object",
                    "properties": {
                        "project1": {"type": "string", "description": "First project name"},
                        "project2": {"type": "string", "description": "Second project name"}
                    },
                    "required": ["project1", "project2"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "similarity_score": {"type": "number"},
                        "common_patterns": {"type": "integer"},
                        "project1_stats": {"type": "object"},
                        "project2_stats": {"type": "object"}
                    }
                }
            ),
            
            MCPTool(
                name="check_guardrails",
                title="Check Code Guardrails",
                description="Analyze code quality and detect vibe coding patterns",
                input_schema={
                    "type": "object",
                    "properties": {
                        "project": {"type": "string", "description": "Project name to analyze"},
                        "checks": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["duplicates", "unused", "patterns", "risks", "consistency", "complexity", "all"]
                            },
                            "description": "Specific checks to run (default: all)"
                        }
                    },
                    "required": ["project"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "health_score": {"type": "integer"},
                        "total_issues": {"type": "integer"},
                        "critical_issues": {"type": "integer"},
                        "recommendations": {"type": "array", "items": {"type": "string"}},
                        "details": {"type": "object"}
                    }
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
            result = {"memory_id": memory_id, "success": True}
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result)
                    }
                ],
                "structuredContent": result
            }
        
        elif tool_name == "recall":
            content = self.memory_client.recall(arguments["query"])
            result = {"content": content, "found": content is not None}
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result)
                    }
                ],
                "structuredContent": result
            }
        
        elif tool_name == "search":
            results = self.memory_client.search(
                query=arguments["query"],
                memory_types=arguments.get("memory_types"),
                limit=arguments.get("limit", 10)
            )
            result = {"results": results, "count": len(results)}
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result)
                    }
                ],
                "structuredContent": result
            }
        
        elif tool_name == "forget":
            success = self.memory_client.forget(arguments["memory_id"])
            result = {"success": success}
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result)
                    }
                ],
                "structuredContent": result
            }
        
        elif tool_name == "remember_code_pattern":
            memory_id = self.memory_client.remember_code_pattern(
                pattern_name=arguments["pattern_name"],
                code=arguments["code"],
                language=arguments["language"],
                description=arguments["description"]
            )
            result = {"memory_id": memory_id, "success": True}
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result)
                    }
                ],
                "structuredContent": result
            }
        
        elif tool_name == "session_status":
            # Import here to avoid circular dependency
            from mnemo.mcp.fastapi_server import session_tracker
            
            if session_tracker:
                summary = session_tracker.get_session_summary()
                result = summary
            else:
                result = {
                    "session_id": "none",
                    "message_count": 0,
                    "important_messages": 0,
                    "duration": "0:00:00"
                }
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result)
                    }
                ],
                "structuredContent": result
                            }
                
        elif tool_name == "analyze_project":
            project_path = arguments.get("project_path")
            project_name = arguments.get("project_name")
            language = arguments.get("language", "python")
            
            try:
                # Import analyzers
                if language == "python":
                    from mnemo.graph.call_graph_builder import CallGraphBuilder
                    builder = CallGraphBuilder()
                    builder.build_from_directory(project_path, project_name)
                    
                    # Get stats
                    stats = builder.graph.run("""
                        MATCH (f:Function {project: $project})
                        OPTIONAL MATCH (f)-[c:CALLS]->()
                        RETURN count(DISTINCT f) as functions, 
                               count(c) as calls,
                               count(DISTINCT f.file_path) as files
                    """, project=project_name).data()[0]
                    
                elif language == "kotlin":
                    from mnemo.graph.kotlin_analyzer_simple import SimpleKotlinAnalyzer
                    analyzer = SimpleKotlinAnalyzer()
                    result = analyzer.analyze_kotlin_project(project_path, project_name)
                    stats = {
                        'functions': result.get('functions', 0),
                        'calls': result.get('calls', 0),
                        'files': result.get('files', 0)
                    }
                    
                elif language in ["javascript", "typescript"]:
                    from mnemo.graph.js_ts_analyzer import JSTypeScriptAnalyzer
                    analyzer = JSTypeScriptAnalyzer()
                    result = analyzer.analyze_frontend_project(project_path, project_name)
                    stats = {
                        'functions': result.get('components', 0),
                        'calls': 0,
                        'files': result.get('files', 0)
                    }
                else:
                    stats = {'functions': 0, 'calls': 0, 'files': 0}
                
                result = {**stats, 'success': True}
                
            except Exception as e:
                result = {
                    'functions': 0,
                    'calls': 0,
                    'files': 0,
                    'success': False,
                    'error': str(e)
                }
                
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Analyzed {project_name}: {stats['functions']} functions, {stats['calls']} calls, {stats['files']} files"
                    }
                ],
                "structuredContent": result
            }
            
        elif tool_name == "find_pattern":
            pattern = arguments.get("pattern")
            project = arguments.get("project")
            
            try:
                from mnemo.graph.project_context_manager import ProjectContextManager
                manager = ProjectContextManager()
                
                patterns = []
                if project:
                    found = manager.get_pattern_from_project(project, pattern)
                    for p in found:
                        patterns.append({
                            'function': p['function'],
                            'file': p['file'],
                            'project': project
                        })
                else:
                    # Search all projects
                    from py2neo import Graph
                    graph = Graph("bolt://localhost:7687", auth=("neo4j", "password123"))
                    results = graph.run("""
                        MATCH (f)
                        WHERE (f:Function OR f:KotlinFunction OR f:KotlinClass)
                          AND (toLower(f.name) CONTAINS toLower($pattern)
                           OR toLower(f.full_name) CONTAINS toLower($pattern))
                        RETURN f.full_name as function, f.file_path as file, f.project as project
                        LIMIT 20
                    """, pattern=pattern).data()
                    
                    patterns = [{'function': r['function'], 'file': r['file'], 'project': r['project']} 
                               for r in results]
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(patterns)} patterns matching '{pattern}'"
                        }
                    ],
                    "structuredContent": {"patterns": patterns}
                }
                
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error finding patterns: {str(e)}"
                        }
                    ],
                    "structuredContent": {"patterns": []}
                }
                
        elif tool_name == "compare_projects":
            project1 = arguments.get("project1")
            project2 = arguments.get("project2")
            
            try:
                from mnemo.graph.project_context_manager import ProjectContextManager
                manager = ProjectContextManager()
                
                comparison = manager.compare_projects(project1, project2)
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Comparison: {project1} vs {project2} - Similarity: {comparison['similarity_score']:.2%}"
                        }
                    ],
                    "structuredContent": comparison
                }
                
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error comparing projects: {str(e)}"
                        }
                    ],
                    "structuredContent": {
                        "similarity_score": 0,
                        "common_patterns": 0,
                        "project1_stats": {},
                        "project2_stats": {}
                    }
                }
                
        elif tool_name == "check_guardrails":
            project = arguments.get("project")
            checks = arguments.get("checks", ["all"])
            
            try:
                from mnemo.graph.code_guardrails import CodeGuardrails
                guardrails = CodeGuardrails()
                
                if "all" in checks:
                    results = guardrails.analyze_project_health(project)
                else:
                    results = {
                        'health_score': 100,
                        'duplicates': [],
                        'unused_functions': [],
                        'strange_patterns': [],
                        'potential_risks': [],
                        'consistency_issues': [],
                        'complexity_hotspots': []
                    }
                    
                    if "duplicates" in checks:
                        results['duplicates'] = guardrails.find_duplicate_implementations(project)
                    if "unused" in checks:
                        results['unused_functions'] = guardrails.find_unused_functions(project)
                    if "patterns" in checks:
                        results['strange_patterns'] = guardrails.detect_strange_patterns(project)
                    if "risks" in checks:
                        results['potential_risks'] = guardrails.detect_potential_risks(project)
                    if "consistency" in checks:
                        results['consistency_issues'] = guardrails.check_consistency(project)
                    if "complexity" in checks:
                        results['complexity_hotspots'] = guardrails.find_complexity_hotspots(project)
                    
                    # Recalculate health score
                    total_issues = sum(len(v) for v in results.values() if isinstance(v, list))
                    results['health_score'] = max(0, 100 - (total_issues * 5))
                
                # Count critical issues
                critical_issues = 0
                for issues in results.values():
                    if isinstance(issues, list):
                        critical_issues += sum(1 for issue in issues 
                                             if isinstance(issue, dict) and issue.get('severity') == 'high')
                
                # Generate recommendations
                recommendations = []
                if results['health_score'] < 60:
                    recommendations.append("Critical: Major refactoring needed")
                if len(results.get('duplicates', [])) > 10:
                    recommendations.append("Consolidate duplicate implementations")
                if len(results.get('unused_functions', [])) > 20:
                    recommendations.append("Remove dead code")
                if critical_issues > 5:
                    recommendations.append("Address high-severity issues immediately")
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Health Score: {results['health_score']}/100 ({len(recommendations)} recommendations)"
                        }
                    ],
                    "structuredContent": {
                        "health_score": results['health_score'],
                        "total_issues": sum(len(v) for v in results.values() if isinstance(v, list)),
                        "critical_issues": critical_issues,
                        "recommendations": recommendations,
                        "details": results
                    }
                }
                
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error checking guardrails: {str(e)}"
                        }
                    ],
                    "structuredContent": {
                        "health_score": 0,
                        "total_issues": 0,
                        "critical_issues": 0,
                        "recommendations": ["Error occurred"],
                        "details": {}
                    }
                }
        
        elif tool_name == "visualize_graph":
            project = arguments.get("project")
            viz_type = arguments.get("visualization_type", "dashboard")
            pattern = arguments.get("pattern")
            output_dir = arguments.get("output_dir", "kg_output")
            
            try:
                from mnemo.graph.kg_visualizer import KnowledgeGraphVisualizer
                import os
                
                # Create output directory
                os.makedirs(output_dir, exist_ok=True)
                
                viz = KnowledgeGraphVisualizer()
                
                if viz_type == "project":
                    file_path = viz.visualize_project(project, os.path.join(output_dir, "project_graph.html"))
                elif viz_type == "pattern" and pattern:
                    file_path = viz.visualize_pattern_search(pattern, project, os.path.join(output_dir, "pattern_graph.html"))
                elif viz_type == "health":
                    file_path = viz.visualize_code_health(project, os.path.join(output_dir, "health_graph.html"))
                elif viz_type == "dashboard":
                    file_path = viz.create_interactive_dashboard(project, os.path.join(output_dir, "dashboard"))
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "Invalid visualization type or missing pattern"
                            }
                        ],
                        "structuredContent": {
                            "file_path": "",
                            "visualization_type": viz_type,
                            "success": False,
                            "message": "Invalid parameters"
                        }
                    }
                
                abs_path = os.path.abspath(file_path)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Visualization created successfully!\nType: {viz_type}\nFile: {abs_path}\nOpen in browser: file://{abs_path}"
                        }
                    ],
                    "structuredContent": {
                        "file_path": abs_path,
                        "visualization_type": viz_type,
                        "success": True,
                        "message": f"Visualization saved to {abs_path}"
                    }
                }
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error creating visualization: {str(e)}"
                        }
                    ],
                    "structuredContent": {
                        "file_path": "",
                        "visualization_type": viz_type,
                        "success": False,
                        "message": str(e)
                    }
                }
                
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
                arguments=[
                    {
                        "name": "query",
                        "description": "The user's query or question",
                        "required": True
                    },
                    {
                        "name": "context",
                        "description": "Additional context for the response",
                        "required": False
                    }
                ],
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
                arguments=[
                    {
                        "name": "task",
                        "description": "The coding task to accomplish",
                        "required": True
                    },
                    {
                        "name": "language",
                        "description": "The programming language to use",
                        "required": True
                    }
                ],
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
                arguments=[
                    {
                        "name": "topic",
                        "description": "The topic to synthesize knowledge about",
                        "required": True
                    }
                ],
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