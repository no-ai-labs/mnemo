"""
Test Knowledge Graph Visualization
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mnemo.graph.kg_visualizer import KnowledgeGraphVisualizer
import webbrowser


def main():
    """Test various visualization features"""
    print("=== Testing Knowledge Graph Visualizer ===")
    
    # Initialize visualizer
    viz = KnowledgeGraphVisualizer()
    
    # Check if we have any projects in the graph
    check_query = """
    MATCH (f:Function)
    RETURN DISTINCT f.project as project, count(f) as count
    ORDER BY count DESC
    """
    
    projects = viz.graph.run(check_query).data()
    
    if not projects:
        print("No projects found in the graph database!")
        print("Please run analyze_project first to populate the graph.")
        return
    
    print(f"\nFound {len(projects)} projects in the graph:")
    for p in projects:
        print(f"  - {p['project']}: {p['count']} functions")
    
    # Use the first project for demo
    project_name = projects[0]['project']
    print(f"\nUsing project: {project_name}")
    
    # 1. Basic project visualization
    print("\n1. Creating basic project visualization...")
    project_viz = viz.visualize_project(project_name, "output/project_graph.html")
    
    # 2. Pattern search visualization
    print("\n2. Creating pattern search visualization...")
    # Find a common pattern in the project
    pattern_query = """
    MATCH (f:Function {project: $project})
    WITH split(f.name, '.')[-1] as fname, count(*) as cnt
    WHERE cnt > 1
    RETURN fname
    ORDER BY cnt DESC
    LIMIT 1
    """
    pattern_result = viz.graph.run(pattern_query, project=project_name).data()
    
    if pattern_result:
        pattern = pattern_result[0]['fname']
        print(f"   Searching for pattern: {pattern}")
        pattern_viz = viz.visualize_pattern_search(pattern, project_name, "output/pattern_graph.html")
    
    # 3. Code health visualization
    print("\n3. Creating code health visualization...")
    health_viz = viz.visualize_code_health(project_name, "output/health_graph.html")
    
    # 4. Cross-project visualization (if we have multiple projects)
    if len(projects) > 1:
        project2_name = projects[1]['project']
        print(f"\n4. Creating cross-project visualization between {project_name} and {project2_name}...")
        cross_viz = viz.visualize_cross_project_connections(
            project_name, project2_name, "output/cross_project.html"
        )
    
    # 5. Interactive dashboard
    print("\n5. Creating interactive dashboard...")
    dashboard = viz.create_interactive_dashboard(project_name, "output/dashboard")
    
    # Open dashboard in browser
    print(f"\nOpening dashboard in browser...")
    webbrowser.open(f"file://{os.path.abspath(dashboard)}")
    
    print("\n✅ Visualization test complete!")
    print(f"Check the 'output' directory for generated HTML files.")


if __name__ == "__main__":
    # Create output directory
    os.makedirs("output", exist_ok=True)
    main()