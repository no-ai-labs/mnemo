"""Explore Mentat project knowledge graph in detail."""

from py2neo import Graph


def explore_mentat_details():
    """Explore detailed Mentat project structure."""
    graph = Graph("bolt://localhost:7687", auth=("neo4j", "password123"))
    
    print("=== Mentat Project Deep Dive ===\n")
    
    # 1. Frontend Components
    print("1. Vue Components Found:")
    vue_components = graph.run("""
        MATCH (c:VueComponent {project: 'mentat'})
        RETURN c.name as name, c.file as file, c.props_count as props,
               c.uses_composition_api as composition_api
        ORDER BY c.name
    """).data()
    
    for comp in vue_components[:10]:
        print(f"   - {comp['name']} ({comp['file']})")
        print(f"     Props: {comp['props']}, Composition API: {comp['composition_api']}")
    
    if len(vue_components) > 10:
        print(f"   ... and {len(vue_components) - 10} more components")
    
    # 2. Backend Structure
    print("\n2. Backend Kotlin Files:")
    kotlin_files = graph.run("""
        MATCH (f:KotlinFile {project: 'mentat'})
        RETURN f.name as name, f.path as path, f.classes as class_count
        ORDER BY f.classes DESC
    """).data()
    
    for file in kotlin_files:
        print(f"   - {file['name']} ({file['class_count']} classes)")
    
    # 3. Dependencies
    print("\n3. Key Frontend Dependencies:")
    frontend_deps = graph.run("""
        MATCH (d:Dependency {project: 'mentat'})
        WHERE d.category IN ['UI Libraries', 'Charts', 'Flow/Graph']
        RETURN d.name as name, d.version as version, d.category as category
        ORDER BY d.category, d.name
    """).data()
    
    for dep in frontend_deps:
        print(f"   - {dep['name']} ({dep['version']}) - {dep['category']}")
    
    # 4. File Statistics
    print("\n4. File Type Distribution:")
    file_stats = graph.run("""
        MATCH (f:JSFile {project: 'mentat'})
        RETURN f.type as type, count(f) as count
        ORDER BY count DESC
    """).data()
    
    for stat in file_stats:
        print(f"   - .{stat['type']} files: {stat['count']}")
    
    # 5. Store/State Management
    print("\n5. State Management:")
    stores = graph.run("""
        MATCH (s:Store {project: 'mentat'})
        RETURN s.name as name, s.type as type, s.file as file
    """).data()
    
    for store in stores:
        print(f"   - {store['name']} ({store['type']}) in {store['file']}")
    
    # 6. Spice Concepts in Backend
    print("\n6. Spice Framework Concepts:")
    spice_concepts = graph.run("""
        MATCH (c:SpiceConcept {project: 'mentat'})
        RETURN c.name as concept, c.description as description
        ORDER BY c.name
    """).data()
    
    for concept in spice_concepts:
        print(f"   - {concept['concept']}: {concept['description']}")
    
    # 7. Import Analysis
    print("\n7. Most Used Imports:")
    imports = graph.run("""
        MATCH (f:JSFile {project: 'mentat'})-[:IMPORTS]->(i:Import)
        WITH i.name as import, count(f) as usage
        ORDER BY usage DESC
        LIMIT 10
        RETURN import, usage
    """).data()
    
    for imp in imports:
        print(f"   - {imp['import']}: used in {imp['usage']} files")
    
    # 8. Project Summary
    print("\n8. Overall Project Summary:")
    summary = graph.run("""
        MATCH (n {project: 'mentat'})
        RETURN 
            count(DISTINCT CASE WHEN 'VueComponent' IN labels(n) THEN n END) as vue_count,
            count(DISTINCT CASE WHEN 'JSFile' IN labels(n) THEN n END) as js_files,
            count(DISTINCT CASE WHEN 'KotlinFile' IN labels(n) THEN n END) as kotlin_files,
            count(DISTINCT CASE WHEN 'KotlinClass' IN labels(n) THEN n END) as kotlin_classes,
            count(DISTINCT CASE WHEN 'Dependency' IN labels(n) THEN n END) as dependencies
    """).data()[0]
    
    print(f"   - Vue Components: {summary['vue_count']}")
    print(f"   - JavaScript/TypeScript Files: {summary['js_files']}")
    print(f"   - Kotlin Files: {summary['kotlin_files']}")
    print(f"   - Kotlin Classes: {summary['kotlin_classes']}")
    print(f"   - Dependencies: {summary['dependencies']}")
    
    # 9. Architecture Patterns
    print("\n9. Architecture Patterns:")
    
    # Find TipTap usage
    tiptap_usage = graph.run("""
        MATCH (d:Dependency {project: 'mentat'})
        WHERE d.name CONTAINS 'tiptap'
        RETURN d.name as lib, d.version as version
    """).data()
    
    if tiptap_usage:
        print("   - TipTap Integration:")
        for lib in tiptap_usage:
            print(f"     {lib['lib']} ({lib['version']})")
    
    # Find Vue Flow usage
    flow_usage = graph.run("""
        MATCH (d:Dependency {project: 'mentat'})
        WHERE d.name CONTAINS 'flow'
        RETURN d.name as lib, d.version as version
    """).data()
    
    if flow_usage:
        print("   - Flow/Graph Libraries:")
        for lib in flow_usage:
            print(f"     {lib['lib']} ({lib['version']})")
    
    # 10. Mentat Specific Features
    print("\n10. Mentat-Specific Features:")
    
    # Look for block components
    block_components = graph.run("""
        MATCH (c:VueComponent {project: 'mentat'})
        WHERE c.name CONTAINS 'Block' OR c.name CONTAINS 'Node'
        RETURN c.name as component, c.file as file
        ORDER BY c.name
    """).data()
    
    if block_components:
        print("   Block/Node Components:")
        for comp in block_components:
            print(f"   - {comp['component']} ({comp['file']})")
    else:
        print("   No block components found in current analysis")
    
    return summary


def find_mentat_patterns():
    """Find patterns that show Mentat's architecture."""
    graph = Graph("bolt://localhost:7687", auth=("neo4j", "password123"))
    
    print("\n=== Mentat Architecture Patterns ===\n")
    
    # 1. Frontend-Backend Communication
    print("1. API Communication Pattern:")
    
    # Check for API-related files
    api_files = graph.run("""
        MATCH (f {project: 'mentat'})
        WHERE (f:JSFile OR f:KotlinFile) AND 
              (f.path CONTAINS 'api' OR f.path CONTAINS 'service')
        RETURN f.name as file, labels(f)[0] as type, f.path as path
    """).data()
    
    for api in api_files:
        print(f"   - {api['file']} ({api['type']})")
    
    # 2. Component Architecture
    print("\n2. Component Architecture:")
    
    component_stats = graph.run("""
        MATCH (c:VueComponent {project: 'mentat'})
        WITH 
            sum(CASE WHEN c.has_template THEN 1 ELSE 0 END) as with_template,
            sum(CASE WHEN c.has_script THEN 1 ELSE 0 END) as with_script,
            sum(CASE WHEN c.has_style THEN 1 ELSE 0 END) as with_style,
            sum(CASE WHEN c.uses_composition_api THEN 1 ELSE 0 END) as composition_api,
            count(c) as total
        RETURN with_template, with_script, with_style, composition_api, total
    """).data()[0]
    
    if component_stats['total'] > 0:
        print(f"   - Total Components: {component_stats['total']}")
        print(f"   - Using Composition API: {component_stats['composition_api']}")
        print(f"   - With Template: {component_stats['with_template']}")
        print(f"   - With Script: {component_stats['with_script']}")
        print(f"   - With Style: {component_stats['with_style']}")
    
    # 3. Data Flow Pattern
    print("\n3. Data Flow Pattern:")
    
    # Check for stores and state management
    stores = graph.run("""
        MATCH (s:Store {project: 'mentat'})
        RETURN s.name as store, s.type as type
    """).data()
    
    if stores:
        print("   State Management:")
        for store in stores:
            print(f"   - {store['store']} ({store['type']})")
    
    # 4. Build Configuration
    print("\n4. Build Configuration:")
    
    build_deps = graph.run("""
        MATCH (d:Dependency {project: 'mentat'})
        WHERE d.category = 'Build Tools'
        RETURN d.name as tool, d.version as version
    """).data()
    
    for tool in build_deps:
        print(f"   - {tool['tool']} ({tool['version']})")
    
    print("\n=== Key Insights ===")
    print("- Mentat combines Vue 3 frontend with Spring Boot + Spice backend")
    print("- Uses TipTap for rich text editing in block-based editor")
    print("- Visual workflow powered by Vue Flow")
    print("- Node types: DataBlock, PromptBlock, AgentBlock, ActionNode, ResultBlock")
    print("- Architecture: Message-based Agent system with visual graph editor")


if __name__ == "__main__":
    summary = explore_mentat_details()
    find_mentat_patterns()