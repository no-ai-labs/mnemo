"""Test cross-project context management."""

from pathlib import Path
from mnemo.graph.project_context_manager import ProjectContextManager
from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient


def main():
    """Test cross-project context features."""
    
    # Initialize with memory client for saving insights
    vector_store = MnemoVectorStore(
        collection_name="project_contexts",
        persist_directory="./project_context_db"
    )
    memory_client = MnemoMemoryClient(vector_store)
    
    manager = ProjectContextManager(memory_client=memory_client)
    
    print("=== Cross-Project Context Analysis ===\n")
    
    # 1. Analyze current project (mnemo)
    print("1. Analyzing mnemo project...")
    mnemo_stats = manager.analyze_project(
        ".", "mnemo", "python", 
        {"memory-system", "mcp", "langchain", "ai-tools"}
    )
    print(f"   - Functions: {mnemo_stats['functions']}")
    print(f"   - Calls: {mnemo_stats['calls']}")
    print(f"   - Files: {mnemo_stats['files']}")
    
    # 2. Demonstrate pattern finding (within same project for now)
    print("\n2. Finding patterns in mnemo...")
    memory_patterns = manager.get_pattern_from_project("mnemo", "memory")
    
    if memory_patterns:
        print(f"   Found {len(memory_patterns)} memory-related patterns:")
        for pattern in memory_patterns[:3]:
            print(f"   - {pattern['function']}")
            if pattern['calls']:
                print(f"     Calls: {', '.join(pattern['calls'][:3])}")
    
    # 3. Demonstrate implementation suggestions
    print("\n3. Getting implementation suggestions...")
    suggestions = manager.suggest_implementation(
        "create function to store user preferences",
        ["mnemo"]
    )
    
    if suggestions:
        print(f"   Found {len(suggestions)} relevant patterns:")
        for sugg in suggestions[:3]:
            print(f"   - From {sugg['from_project']}: {sugg['pattern']['function']}")
            print(f"     Relevance: {sugg['relevance']:.2f}")
    
    # 4. Save insights to memory
    print("\n4. Saving project insights...")
    
    # Save architectural patterns
    memory_client.remember(
        key="mnemo_architecture_patterns",
        content=f"Mnemo uses {mnemo_stats['functions']} functions with {mnemo_stats['calls']} "
                f"call relationships. Key patterns: MCP handlers, memory operations, vector stores.",
        memory_type="fact",
        tags={"architecture", "mnemo", "patterns"}
    )
    
    # Save commonly used patterns
    common_patterns = manager.graph.run("""
        MATCH (f:Function {project: 'mnemo'})<-[:CALLS]-(caller)
        WITH f, count(caller) as usage
        WHERE usage > 2
        RETURN f.name as function, usage
        ORDER BY usage DESC
        LIMIT 5
    """).data()
    
    if common_patterns:
        pattern_summary = ", ".join([f"{p['function']} ({p['usage']} uses)" 
                                   for p in common_patterns])
        memory_client.remember(
            key="mnemo_common_patterns",
            content=f"Most used functions in mnemo: {pattern_summary}",
            memory_type="fact",
            tags={"patterns", "mnemo", "common-functions"}
        )
    
    # 5. Query Neo4j for insights
    print("\n5. Graph insights:")
    
    # Find entry points (functions not called by others)
    entry_points = manager.graph.run("""
        MATCH (f:Function {project: 'mnemo'})
        WHERE NOT ()-[:CALLS]->(f)
          AND (f)-[:CALLS]->()
        RETURN f.full_name as entry_point, f.module
        LIMIT 10
    """).data()
    
    if entry_points:
        print(f"   Entry points (top-level functions):")
        for ep in entry_points[:5]:
            print(f"   - {ep['entry_point']}")
    
    # Find hub functions (called by many, calls many)
    hubs = manager.graph.run("""
        MATCH (caller)-[:CALLS]->(hub:Function {project: 'mnemo'})-[:CALLS]->(callee)
        WITH hub, count(DISTINCT caller) as in_degree, count(DISTINCT callee) as out_degree
        WHERE in_degree > 1 AND out_degree > 1
        RETURN hub.full_name as function, in_degree, out_degree, 
               in_degree * out_degree as hub_score
        ORDER BY hub_score DESC
        LIMIT 5
    """).data()
    
    if hubs:
        print(f"\n   Hub functions (high connectivity):")
        for hub in hubs:
            print(f"   - {hub['function']}")
            print(f"     In: {hub['in_degree']}, Out: {hub['out_degree']}, "
                  f"Score: {hub['hub_score']}")
    
    print("\n=== Analysis Complete ===")
    print("\nNext steps:")
    print("1. Analyze other projects to build cross-project knowledge")
    print("2. Use patterns from one project to guide implementation in another")
    print("3. Find common architectural patterns across projects")
    print("4. Build a knowledge graph of best practices")


if __name__ == "__main__":
    main()