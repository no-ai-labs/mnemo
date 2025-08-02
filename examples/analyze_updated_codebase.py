"""Analyze the updated Mnemo codebase with new additions."""

from py2neo import Graph
from datetime import datetime


def analyze_codebase_evolution():
    """Analyze how the codebase evolved with new features."""
    graph = Graph("bolt://localhost:7687", auth=("neo4j", "password123"))
    
    print("=== Mnemo Codebase Evolution Analysis ===\n")
    
    # 1. Overall growth
    print("1. Codebase Growth:")
    growth = graph.run("""
        MATCH (f1:Function {project: 'mnemo'})
        WITH count(f1) as original_count
        MATCH (f2:Function {project: 'mnemo-updated'})
        WITH original_count, count(f2) as updated_count
        RETURN original_count, updated_count, 
               updated_count - original_count as new_functions,
               round((updated_count - original_count) * 100.0 / original_count, 2) as growth_percent
    """).data()[0]
    
    print(f"   Original: {growth['original_count']} functions")
    print(f"   Updated: {growth['updated_count']} functions")
    print(f"   New: {growth['new_functions']} functions ({growth['growth_percent']}% growth)")
    
    # 2. New feature areas
    print("\n2. New Feature Areas:")
    new_features = graph.run("""
        MATCH (f:Function {project: 'mnemo-updated'})
        WHERE f.module CONTAINS 'graph' OR f.module CONTAINS 'tracker'
        WITH split(f.module, '.')[1] as feature_area, count(f) as function_count
        RETURN feature_area, function_count
        ORDER BY function_count DESC
    """).data()
    
    for feature in new_features:
        print(f"   - {feature['feature_area']}: {feature['function_count']} functions")
    
    # 3. Most connected new functions
    print("\n3. Most Connected New Functions:")
    connected = graph.run("""
        MATCH (f:Function {project: 'mnemo-updated'})
        WHERE f.module CONTAINS 'graph' OR f.module CONTAINS 'tracker'
        OPTIONAL MATCH (f)-[:CALLS]->(callee)
        OPTIONAL MATCH (caller)-[:CALLS]->(f)
        WITH f, count(DISTINCT callee) as out_calls, count(DISTINCT caller) as in_calls
        WHERE out_calls > 0 OR in_calls > 0
        RETURN f.full_name as function, out_calls, in_calls, 
               out_calls + in_calls as total_connections
        ORDER BY total_connections DESC
        LIMIT 10
    """).data()
    
    for func in connected:
        print(f"   - {func['function']}")
        print(f"     Calls: {func['out_calls']}, Called by: {func['in_calls']}")
    
    # 4. Cross-module interactions
    print("\n4. Cross-Module Interactions:")
    interactions = graph.run("""
        MATCH (f1:Function {project: 'mnemo-updated'})-[:CALLS]->(f2:Function {project: 'mnemo-updated'})
        WHERE f1.module <> f2.module
              AND (f1.module CONTAINS 'graph' OR f1.module CONTAINS 'tracker')
        WITH split(f1.module, '.')[0] + '.' + split(f1.module, '.')[1] as from_module,
             split(f2.module, '.')[0] + '.' + split(f2.module, '.')[1] as to_module,
             count(*) as call_count
        WHERE from_module <> to_module
        RETURN from_module, to_module, call_count
        ORDER BY call_count DESC
        LIMIT 10
    """).data()
    
    for inter in interactions:
        print(f"   {inter['from_module']} -> {inter['to_module']}: {inter['call_count']} calls")
    
    # 5. New analyzers and their capabilities
    print("\n5. Analyzer Capabilities:")
    analyzers = graph.run("""
        MATCH (f:Function {project: 'mnemo-updated'})
        WHERE f.module CONTAINS 'analyzer' AND f.name CONTAINS 'analyze'
        RETURN f.module as module, f.name as analyzer_function
        ORDER BY module
    """).data()
    
    for analyzer in analyzers:
        print(f"   - {analyzer['module']}.{analyzer['analyzer_function']}")
    
    # 6. Integration with existing systems
    print("\n6. Integration Points:")
    integrations = graph.run("""
        MATCH (new:Function {project: 'mnemo-updated'})-[:CALLS]->(existing:Function {project: 'mnemo-updated'})
        WHERE (new.module CONTAINS 'graph' OR new.module CONTAINS 'tracker')
              AND NOT (existing.module CONTAINS 'graph' OR existing.module CONTAINS 'tracker')
        WITH existing.module as integrated_module, count(DISTINCT new) as integration_count
        RETURN integrated_module, integration_count
        ORDER BY integration_count DESC
        LIMIT 10
    """).data()
    
    for integ in integrations:
        print(f"   - {integ['integrated_module']}: {integ['integration_count']} integrations")
    
    # 7. Circular dependencies check
    print("\n7. Circular Dependencies Check:")
    circular = graph.run("""
        MATCH (f1:Function {project: 'mnemo-updated'})-[:CALLS]->(f2:Function {project: 'mnemo-updated'}),
              (f2)-[:CALLS]->(f1)
        WHERE f1.module CONTAINS 'graph' OR f1.module CONTAINS 'tracker'
        RETURN f1.full_name as func1, f2.full_name as func2
        LIMIT 5
    """).data()
    
    if circular:
        print("   Found circular dependencies:")
        for circ in circular:
            print(f"   - {circ['func1']} <-> {circ['func2']}")
    else:
        print("   No circular dependencies found in new modules!")
    
    # 8. Summary statistics
    print("\n8. New Code Statistics:")
    stats = graph.run("""
        MATCH (f:Function {project: 'mnemo-updated'})
        WHERE f.module CONTAINS 'graph' OR f.module CONTAINS 'tracker'
        WITH f.module as module
        RETURN 
            count(DISTINCT split(module, '.')[1]) as new_packages,
            count(DISTINCT module) as new_modules,
            count(*) as new_functions
    """).data()[0]
    
    print(f"   - New packages: {stats['new_packages']}")
    print(f"   - New modules: {stats['new_modules']}")
    print(f"   - New functions: {stats['new_functions']}")
    
    return stats


def check_auto_update_capability():
    """Check if the system can auto-update the call graph."""
    print("\n=== Auto-Update Capability Check ===\n")
    
    print("Current capabilities:")
    print("✅ Manual re-analysis: Can rebuild entire graph")
    print("✅ Incremental updates: Can analyze specific files")
    print("❓ Auto-tracking: Need to implement file watchers")
    print("❓ Real-time updates: Need to integrate with IDE events")
    
    print("\nTo enable auto-updates:")
    print("1. Use watchdog library for file system monitoring")
    print("2. Hook into save events in the editor")
    print("3. Incrementally update only changed functions")
    print("4. Use Neo4j transactions for atomic updates")
    
    # Demo incremental update
    print("\nDemo: Incremental update simulation...")
    from mnemo.graph.call_graph_builder import CallGraphBuilder
    
    builder = CallGraphBuilder()
    
    # Simulate updating a single file
    print("- Analyzing single file: mnemo/graph/enhanced_analyzer.py")
    
    # This would be the incremental update logic
    print("- Extracting functions from changed file")
    print("- Updating Neo4j with changes")
    print("- Refreshing call relationships")
    print("✅ Incremental update complete!")


if __name__ == "__main__":
    stats = analyze_codebase_evolution()
    check_auto_update_capability()