"""Test call graph queries."""

from mnemo.graph.call_graph_builder import CallGraphBuilder


def main():
    """Test various call graph queries."""
    
    # Connect to Neo4j
    builder = CallGraphBuilder()
    
    print("=== Call Graph Analysis for Mnemo ===\n")
    
    # Test 1: Find who calls remember function
    print("1. Who calls MnemoMemoryClient.remember?")
    callers = builder.query_dependents("mnemo.memory.client.MnemoMemoryClient.remember")
    for caller in callers[:10]:  # Show first 10
        print(f"   - {caller}")
    
    # Test 2: What does remember call?
    print("\n2. What does remember function call?")
    dependencies = builder.query_dependencies("mnemo.memory.client.MnemoMemoryClient.remember")
    for dep in dependencies[:10]:
        print(f"   - {dep}")
    
    # Test 3: Find most called functions
    print("\n3. Most called functions (top 10):")
    result = builder.graph.run("""
        MATCH (callee:Function)<-[:CALLS]-(caller)
        WITH callee, count(caller) as call_count
        RETURN callee.full_name as function, call_count
        ORDER BY call_count DESC
        LIMIT 10
    """)
    for record in result:
        print(f"   - {record['function']}: {record['call_count']} calls")
    
    # Test 4: Find functions with most dependencies
    print("\n4. Functions with most dependencies (top 10):")
    result = builder.graph.run("""
        MATCH (caller:Function)-[:CALLS]->(callee)
        WITH caller, count(callee) as dep_count
        RETURN caller.full_name as function, dep_count
        ORDER BY dep_count DESC
        LIMIT 10
    """)
    for record in result:
        print(f"   - {record['function']}: calls {record['dep_count']} functions")
    
    # Test 5: Find circular dependencies
    print("\n5. Checking for circular dependencies:")
    result = builder.graph.run("""
        MATCH path = (f1:Function)-[:CALLS*2..5]->(f1)
        RETURN DISTINCT f1.full_name as function, length(path) as cycle_length
        LIMIT 5
    """)
    cycles = list(result)
    if cycles:
        for record in cycles:
            print(f"   - Cycle found: {record['function']} (length: {record['cycle_length']})")
    else:
        print("   - No circular dependencies found!")
    
    # Test 6: Find isolated functions (no calls in or out)
    print("\n6. Isolated functions (no dependencies):")
    result = builder.graph.run("""
        MATCH (f:Function)
        WHERE NOT (f)-[:CALLS]-() AND NOT ()-[:CALLS]-(f)
        RETURN f.full_name as function
        LIMIT 10
    """)
    for record in result:
        print(f"   - {record['function']}")
    
    # Test 7: Analyze MCP handlers
    print("\n7. MCP Handler analysis:")
    result = builder.graph.run("""
        MATCH (f:Function)
        WHERE f.module CONTAINS 'mcp.handlers'
        OPTIONAL MATCH (f)-[:CALLS]->(callee)
        RETURN f.full_name as handler, collect(callee.full_name) as calls
    """)
    for record in result:
        print(f"   - {record['handler']}")
        if record['calls']:
            for call in record['calls'][:5]:
                print(f"     → {call}")
    
    print("\n=== Analysis Complete ===")
    print(f"Visit http://localhost:7474 to explore the graph visually!")
    print(f"Login: neo4j / password123")


if __name__ == "__main__":
    main()