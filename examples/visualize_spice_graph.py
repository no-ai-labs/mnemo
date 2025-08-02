"""Visualize and query the Spice framework knowledge graph."""

from py2neo import Graph
from mnemo.graph.kotlin_analyzer import KotlinAnalyzer


def explore_spice_architecture():
    """Explore Spice framework architecture through Neo4j queries."""
    graph = Graph("bolt://localhost:7687", auth=("neo4j", "password123"))
    
    print("=== Spice Framework Knowledge Graph ===\n")
    
    # 1. Core Architecture
    print("1. Core Architecture Components:")
    core_components = graph.run("""
        MATCH (c:SpiceConcept {project: 'spice-framework'})
        RETURN c.name as component, c.description as description
        ORDER BY c.name
    """).data()
    
    for comp in core_components:
        print(f"   - {comp['component']}: {comp['description']}")
    
    # 2. Agent System Analysis
    print("\n2. Agent System:")
    agent_types = graph.run("""
        MATCH (a:SpiceAgent {project: 'spice-framework'})
        RETURN DISTINCT a.name as agent_name, a.file as defined_in
        LIMIT 10
    """).data()
    
    print(f"   Found {len(agent_types)} agent definitions")
    for agent in agent_types[:5]:
        print(f"   - {agent['agent_name']} (in {agent['defined_in']})")
    
    # 3. Module Structure
    print("\n3. Module Structure:")
    modules = graph.run("""
        MATCH (m:Module {project: 'spice-framework'})
        OPTIONAL MATCH (m)-[:DEPENDS_ON]->(d:Dependency)
        RETURN m.name as module, count(d) as dependencies
        ORDER BY dependencies DESC
    """).data()
    
    for mod in modules:
        print(f"   - {mod['module']}: {mod['dependencies']} dependencies")
    
    # 4. Package Hierarchy
    print("\n4. Main Package Structure:")
    package_hierarchy = graph.run("""
        MATCH (p:Package {project: 'spice-framework'})<-[:IN_PACKAGE]-(f:KotlinFile)
        WITH p.name as package, count(f) as file_count
        ORDER BY file_count DESC
        LIMIT 5
        RETURN package, file_count
    """).data()
    
    for pkg in package_hierarchy:
        print(f"   - {pkg['package']}: {pkg['file_count']} files")
    
    # 5. Implementation Patterns
    print("\n5. Key Implementation Patterns:")
    implementations = graph.run("""
        MATCH (i:Implementation {project: 'spice-framework'})-[:IMPLEMENTS]->(c:SpiceConcept)
        RETURN c.name as concept, collect(DISTINCT i.name) as implementations
        ORDER BY size(implementations) DESC
    """).data()
    
    for impl in implementations:
        if impl['implementations']:
            print(f"   - {impl['concept']}: {', '.join(impl['implementations'][:3])}")
            if len(impl['implementations']) > 3:
                print(f"     ... and {len(impl['implementations']) - 3} more")
    
    # 6. File Dependencies (through imports)
    print("\n6. Core Import Dependencies:")
    imports = graph.run("""
        MATCH (f:KotlinFile {project: 'spice-framework'})-[:IMPORTS]->(i:Import)
        WHERE i.name STARTS WITH 'io.github.spice' OR i.name STARTS WITH 'io.github.noailabs'
        WITH i.name as import, count(f) as usage_count
        ORDER BY usage_count DESC
        LIMIT 10
        RETURN import, usage_count
    """).data()
    
    for imp in imports:
        print(f"   - {imp['import']}: used in {imp['usage_count']} files")
    
    # 7. Agent Tools
    print("\n7. Spice Tools:")
    tools = graph.run("""
        MATCH (t:SpiceTool {project: 'spice-framework'})
        RETURN DISTINCT t.name as tool_name, t.file as defined_in
        LIMIT 10
    """).data()
    
    for tool in tools:
        print(f"   - Tool '{tool['tool_name']}' in {tool['defined_in']}")
    
    # 8. Architectural Insights
    print("\n8. Architectural Insights:")
    
    # Find central classes (high connectivity)
    central_classes = graph.run("""
        MATCH (c:KotlinClass {project: 'spice-framework'})
        OPTIONAL MATCH (c)-[r]-()
        WITH c, count(r) as connections
        WHERE connections > 0
        RETURN c.name as class_name, c.package as package, connections
        ORDER BY connections DESC
        LIMIT 5
    """).data()
    
    print("   Central Classes (high connectivity):")
    for cls in central_classes:
        print(f"   - {cls['class_name']} ({cls['package']}): {cls['connections']} connections")
    
    # 9. Design Patterns in Spice
    print("\n9. Design Patterns Detected:")
    patterns = {
        'Registry Pattern': graph.run("""
            MATCH (n {project: 'spice-framework'})
            WHERE n.name CONTAINS 'Registry'
            RETURN count(n) as count
        """).evaluate(),
        'Builder Pattern': graph.run("""
            MATCH (n {project: 'spice-framework'})
            WHERE n.name CONTAINS 'Builder' OR n.name CONTAINS 'build'
            RETURN count(n) as count
        """).evaluate(),
        'Strategy Pattern': graph.run("""
            MATCH (n {project: 'spice-framework'})
            WHERE n.name CONTAINS 'Strategy'
            RETURN count(n) as count
        """).evaluate()
    }
    
    for pattern, count in patterns.items():
        print(f"   - {pattern}: {count} occurrences")
    
    # 10. Summary
    print("\n10. Framework Summary:")
    summary = graph.run("""
        MATCH (n {project: 'spice-framework'})
        RETURN 
            sum(CASE WHEN 'KotlinFile' IN labels(n) THEN 1 ELSE 0 END) as total_files,
            sum(CASE WHEN 'KotlinClass' IN labels(n) THEN 1 ELSE 0 END) as total_classes,
            sum(CASE WHEN 'SpiceAgent' IN labels(n) THEN 1 ELSE 0 END) as total_agents,
            sum(CASE WHEN 'SpiceTool' IN labels(n) THEN 1 ELSE 0 END) as total_tools,
            sum(CASE WHEN 'Module' IN labels(n) THEN 1 ELSE 0 END) as total_modules
    """).data()[0]
    
    print(f"   - Total Kotlin Files: {summary['total_files']}")
    print(f"   - Total Classes: {summary['total_classes']}")
    print(f"   - Total Agents: {summary['total_agents']}")
    print(f"   - Total Tools: {summary['total_tools']}")
    print(f"   - Total Modules: {summary['total_modules']}")
    
    return summary


def find_spice_patterns_for_mentat():
    """Find patterns in Spice that could be useful for Mentat."""
    graph = Graph("bolt://localhost:7687", auth=("neo4j", "password123"))
    
    print("\n=== Patterns for Mentat ===\n")
    
    # 1. Agent Communication Pattern
    print("1. Agent Communication Pattern:")
    comm_pattern = graph.run("""
        MATCH (c:SpiceConcept {name: 'Comm', project: 'spice-framework'})
        MATCH (ch:SpiceConcept {name: 'CommHub', project: 'spice-framework'})
        RETURN c.description as comm_desc, ch.description as hub_desc
    """).data()
    
    if comm_pattern:
        print(f"   - Comm: {comm_pattern[0]['comm_desc']}")
        print(f"   - CommHub: {comm_pattern[0]['hub_desc']}")
    
    # 2. Multi-Agent Orchestration
    print("\n2. Multi-Agent Orchestration:")
    orchestration = graph.run("""
        MATCH (f:SpiceConcept {name: 'Flow', project: 'spice-framework'})
        MATCH (s:SpiceConcept {name: 'SwarmStrategy', project: 'spice-framework'})
        RETURN f.description as flow_desc, s.description as swarm_desc
    """).data()
    
    if orchestration:
        print(f"   - Flow: {orchestration[0]['flow_desc']}")
        print(f"   - SwarmStrategy: {orchestration[0]['swarm_desc']}")
    
    # 3. Registry System
    print("\n3. Registry System Pattern:")
    registry_impls = graph.run("""
        MATCH (i:Implementation {project: 'spice-framework'})-[:IMPLEMENTS]->(c:SpiceConcept {name: 'Registry'})
        RETURN i.name as implementation, i.file as file
    """).data()
    
    for reg in registry_impls:
        print(f"   - {reg['implementation']} (in {reg['file']})")
    
    print("\n4. Agent Builder Pattern:")
    builders = graph.run("""
        MATCH (a:SpiceAgent {project: 'spice-framework'})
        RETURN DISTINCT a.file as file
        LIMIT 5
    """).data()
    
    print(f"   Agent builders found in {len(builders)} files")
    
    # Key insights for Mentat
    print("\n=== Key Insights for Mentat ===")
    print("1. Spice uses a Registry pattern for managing agents, tools, and flows")
    print("2. Communication is handled through 'Comm' objects routed via 'CommHub'")
    print("3. Multi-agent coordination uses Flow and SwarmStrategy patterns")
    print("4. Strong DSL support with builder patterns (buildAgent, buildFlow, etc.)")
    print("5. Type-safe, coroutine-first architecture in Kotlin")
    print("6. Modular structure: core, DSL samples, Spring Boot integration")


if __name__ == "__main__":
    # First explore the architecture
    summary = explore_spice_architecture()
    
    # Then find patterns useful for Mentat
    find_spice_patterns_for_mentat()