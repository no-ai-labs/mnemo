"""
Knowledge Graph Visualizer for Neo4j using Pyvis
"""
import json
from typing import Dict, List, Optional, Tuple, Any
from pyvis.network import Network
from py2neo import Graph
import tempfile
import webbrowser
import os


class KnowledgeGraphVisualizer:
    """Visualize Neo4j knowledge graphs using Pyvis"""
    
    def __init__(self, graph: Optional[Graph] = None):
        """Initialize visualizer with Neo4j connection"""
        self.graph = graph or Graph("bolt://localhost:7687", auth=("neo4j", "password123"))
    
    def _add_dark_background_to_html(self, file_path: str):
        """Add dark background styling to generated HTML file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Add body style with dark background
        html_content = html_content.replace(
            '<body>',
            '<body style="margin: 0; padding: 0; background-color: #222222; width: 100%; height: 100%;">'
        )
        
        # Also update the HTML tag
        html_content = html_content.replace(
            '<html>',
            '<html style="height: 100%; background-color: #222222;">'
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
    def visualize_project(self, project_name: str, output_file: str = "kg_visualization.html") -> str:
        """
        Visualize a specific project's knowledge graph
        
        Args:
            project_name: Name of the project to visualize
            output_file: Output HTML file path
            
        Returns:
            Path to the generated HTML file
        """
        # Create network
        net = Network(
            height="800px",  # Fixed height to use full screen
            width="100%", 
            bgcolor="#222222",
            font_color="white",
            notebook=False,
            directed=True,
            cdn_resources='in_line'  # Include resources inline to avoid loading issues
        )
        
        # Configure physics for better layout
        net.barnes_hut(
            gravity=-80000,
            central_gravity=0.3,
            spring_length=250,
            spring_strength=0.001,
            damping=0.09
        )
        
        # Disable buttons to avoid configuration issues
        net.show_buttons(filter_=None)
        
        # Get all functions (we'll make it more comprehensive)
        nodes_query = """
        MATCH (f:Function {project: $project})
        OPTIONAL MATCH (f)-[:CALLS]-()
        WITH f, count(*) as degree
        RETURN f.full_name as id, f.name as name, f.module as module, 
               'function' as type, f.file_path as file, f.class_name as class_name,
               f.is_method as is_method, degree
        ORDER BY degree DESC
        LIMIT 200
        """
        
        # Get ALL relationships (both ways)
        rels_query = """
        MATCH (f1:Function {project: $project})-[r:CALLS]->(f2:Function)
        WHERE f1.project = $project AND (f2.project = $project OR f2.project IS NULL)
        RETURN DISTINCT f1.full_name as source, f2.full_name as target, 
               type(r) as type, r.call_type as call_type
        """
        
        # Get data
        nodes = self.graph.run(nodes_query, project=project_name).data()
        relationships = self.graph.run(rels_query, project=project_name).data()
        
        # Filter out None relationships
        relationships = [r for r in relationships if r['source'] and r['target'] and r['type']]
        
        # Add nodes
        added_nodes = set()
        for node in nodes:
            if node['id'] not in added_nodes:
                # Extract full function info for tooltip
                func_name = node['id']
                short_name = node.get('name', func_name.split('.')[-1])
                module = node.get('module', 'Unknown')
                file_path = node.get('file', 'Unknown')
                class_name = node.get('class_name')
                is_method = node.get('is_method', False)
                
                # Create detailed tooltip (plain text for pyvis)
                tooltip = f"Function: {func_name}\n"
                if class_name:
                    tooltip += f"Class: {class_name}\n"
                tooltip += f"Module: {module}\n"
                tooltip += f"File: {file_path}\n"
                tooltip += f"Type: {'Method' if is_method else 'Function'}"
                
                # Size based on connections
                connections = node.get('degree', 0)
                node_size = 20 + min(connections * 3, 50)  # Size between 20-70
                
                # Color based on type and importance
                if is_method and class_name:
                    node_color = "#3498db"  # Blue for methods
                elif connections > 10:
                    node_color = "#e74c3c"  # Red for highly connected
                elif connections > 5:
                    node_color = "#f39c12"  # Orange for moderately connected
                elif short_name == '__init__':
                    node_color = "#9b59b6"  # Purple for constructors
                elif short_name == 'main':
                    node_color = "#e74c3c"  # Red for main functions
                else:
                    node_color = "#00ff41"  # Green for normal nodes
                
                # Add prefix to label for clarity
                if class_name and is_method:
                    label = f"{class_name}.{short_name}"
                else:
                    label = short_name
                
                net.add_node(
                    node['id'],
                    label=label,
                    title=tooltip + f"\nConnections: {connections}",
                    color=node_color,
                    size=node_size,
                    font={'color': 'white', 'size': 12},
                    shape='dot' if not is_method else 'square'
                )
                added_nodes.add(node['id'])
        
        # Add edges
        edge_count = 0
        for rel in relationships:
            if rel['source'] in added_nodes and rel['target'] in added_nodes:
                # Color based on call type
                call_type = rel.get('call_type', 'direct')
                if call_type == 'decorator':
                    edge_color = {'color': '#9b59b6', 'highlight': '#8e44ad'}  # Purple
                    edge_style = True  # dashed
                elif call_type == 'inherits':
                    edge_color = {'color': '#e74c3c', 'highlight': '#c0392b'}  # Red
                    edge_style = False
                elif call_type == 'return':
                    edge_color = {'color': '#3498db', 'highlight': '#2980b9'}  # Blue
                    edge_style = False
                else:
                    edge_color = {'color': '#848484', 'highlight': '#00ff41'}  # Default gray
                    edge_style = False
                
                net.add_edge(
                    rel['source'], 
                    rel['target'], 
                    title=f"{rel['type']} ({call_type})",
                    color=edge_color,
                    arrows='to',
                    width=2,
                    dashes=edge_style
                )
                edge_count += 1
        
        print(f"[KG Visualizer] Added {len(added_nodes)} nodes and {edge_count} edges")
        
        # Generate HTML with custom options
        net.set_options("""
        var options = {
            "nodes": {
                "font": {
                    "color": "white",
                    "size": 14
                }
            },
            "edges": {
                "color": {
                    "color": "#848484",
                    "highlight": "#00ff41"
                },
                "smooth": {
                    "type": "continuous"
                }
            },
            "physics": {
                "enabled": true,
                "barnesHut": {
                    "gravitationalConstant": -80000,
                    "centralGravity": 0.3,
                    "springLength": 250,
                    "springConstant": 0.001,
                    "damping": 0.09
                }
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 200,
                "hideEdgesOnDrag": true
            },
            "configure": {
                "enabled": false
            }
        }
        """)
        
        net.save_graph(output_file)
        
        # Add dark background to the generated HTML
        with open(output_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Add body style with dark background
        html_content = html_content.replace(
            '<body>',
            '<body style="margin: 0; padding: 0; background-color: #222222; width: 100%; height: 100%;">'
        )
        
        # Also update the HTML tag
        html_content = html_content.replace(
            '<html>',
            '<html style="height: 100%; background-color: #222222;">'
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[KG Visualizer] Saved visualization to {output_file}")
        
        return output_file
    
    def visualize_pattern_search(self, pattern: str, project: Optional[str] = None, 
                                output_file: str = "pattern_visualization.html") -> str:
        """
        Visualize functions matching a pattern
        
        Args:
            pattern: Pattern to search for
            project: Specific project (optional)
            output_file: Output HTML file path
            
        Returns:
            Path to the generated HTML file
        """
        net = Network(
            height="800px",  # Fixed height to use full screen
            width="100%", 
            bgcolor="#1a1a1a",
            font_color="white",
            notebook=False,
            directed=True,
            cdn_resources='in_line'
        )
        
        # Configure physics
        net.force_atlas_2based()
        
        # Query for pattern
        if project:
            pattern_query = """
            MATCH (f:Function {project: $project})
            WHERE toLower(f.name) CONTAINS toLower($pattern)
            WITH f LIMIT 50
            OPTIONAL MATCH (f)-[r:CALLS]->(f2:Function)
            RETURN f, r, f2
            """
            params = {"project": project, "pattern": pattern}
        else:
            pattern_query = """
            MATCH (f:Function)
            WHERE toLower(f.name) CONTAINS toLower($pattern)
            WITH f LIMIT 50
            OPTIONAL MATCH (f)-[r:CALLS]->(f2:Function)
            RETURN f, r, f2
            """
            params = {"pattern": pattern}
        
        results = self.graph.run(pattern_query, **params).data()
        
        # Process results
        added_nodes = set()
        for row in results:
            # Add main function
            if row['f'] and row['f']['name'] not in added_nodes:
                f = row['f']
                net.add_node(
                    f['name'],
                    label=f['name'].split('.')[-1],
                    title=f"Function: {f['name']}\nProject: {f.get('project', 'Unknown')}\nFile: {f.get('file', 'Unknown')}",
                    color="#ff6b6b",  # Red for pattern matches
                    size=25
                )
                added_nodes.add(f['name'])
            
            # Add connected function
            if row['f2'] and row['f2']['name'] not in added_nodes:
                f2 = row['f2']
                net.add_node(
                    f2['name'],
                    label=f2['name'].split('.')[-1],
                    title=f"Function: {f2['name']}\nProject: {f2.get('project', 'Unknown')}",
                    color="#4ecdc4",  # Teal for connected nodes
                    size=20
                )
                added_nodes.add(f2['name'])
            
            # Add relationship
            if row['r'] and row['f'] and row['f2']:
                net.add_edge(row['f']['name'], row['f2']['name'], title="CALLS")
        
        # Save and return
        net.save_graph(output_file)
        self._add_dark_background_to_html(output_file)
        print(f"[KG Visualizer] Pattern visualization saved to {output_file}")
        
        return output_file
    
    def visualize_cross_project_connections(self, project1: str, project2: str,
                                          output_file: str = "cross_project.html") -> str:
        """
        Visualize connections between two projects
        
        Args:
            project1: First project name
            project2: Second project name
            output_file: Output HTML file path
            
        Returns:
            Path to the generated HTML file
        """
        net = Network(
            height="750px", 
            width="100%", 
            bgcolor="#0f0f0f",
            font_color="white",
            notebook=False,
            directed=True
        )
        
        # Create network with inline resources
        net = Network(
            height="800px",  # Fixed height to use full screen
            width="100%", 
            bgcolor="#0f0f0f",
            font_color="white",
            notebook=False,
            directed=True,
            cdn_resources='in_line'
        )
        
        # Configure for better separation
        net.repulsion(
            node_distance=420,
            central_gravity=0.33,
            spring_length=110,
            spring_strength=0.10,
            damping=0.95
        )
        
        # Query similar patterns between projects
        query = """
        MATCH (f1:Function {project: $project1})
        MATCH (f2:Function {project: $project2})
        WHERE f1.name <> f2.name 
        AND (
            split(f1.name, '.')[-1] = split(f2.name, '.')[-1]
            OR toLower(f1.name) CONTAINS 'error' AND toLower(f2.name) CONTAINS 'error'
            OR toLower(f1.name) CONTAINS 'auth' AND toLower(f2.name) CONTAINS 'auth'
            OR toLower(f1.name) CONTAINS 'api' AND toLower(f2.name) CONTAINS 'api'
        )
        RETURN f1, f2, split(f1.name, '.')[-1] as common_name
        LIMIT 50
        """
        
        results = self.graph.run(query, project1=project1, project2=project2).data()
        
        # Add nodes and virtual edges
        for row in results:
            f1, f2 = row['f1'], row['f2']
            
            # Add project 1 function
            net.add_node(
                f1['name'],
                label=f1['name'].split('.')[-1],
                title=f"Project: {project1}\nFunction: {f1['name']}",
                color="#e74c3c",  # Red for project 1
                size=25,
                group=project1
            )
            
            # Add project 2 function
            net.add_node(
                f2['name'],
                label=f2['name'].split('.')[-1],
                title=f"Project: {project2}\nFunction: {f2['name']}",
                color="#3498db",  # Blue for project 2
                size=25,
                group=project2
            )
            
            # Add similarity edge
            net.add_edge(
                f1['name'], 
                f2['name'], 
                title=f"Similar: {row['common_name']}",
                color="#95a5a6",
                dashes=True
            )
        
        # Save and return
        net.save_graph(output_file)
        self._add_dark_background_to_html(output_file)
        print(f"[KG Visualizer] Cross-project visualization saved to {output_file}")
        
        return output_file
    
    def visualize_code_health(self, project: str, output_file: str = "code_health.html") -> str:
        """
        Generate a code health report in HTML format
        
        Args:
            project: Project name
            output_file: Output HTML file path
            
        Returns:
            Path to the generated HTML file
        """
        # Gather health metrics
        total_functions = self.graph.run(
            "MATCH (f:Function {project: $project}) RETURN count(f) as count",
            project=project
        ).data()[0]['count']
        
        # Unused functions
        unused_query = """
        MATCH (f:Function {project: $project})
        WHERE NOT (f)<-[:CALLS]-()
        AND f.name <> $project + '.main'
        AND f.name <> '__init__'
        RETURN f.full_name as name, f.module as module, f.node_type as type
        ORDER BY f.module, f.name
        """
        unused = self.graph.run(unused_query, project=project).data()
        
        # Highly connected functions
        hub_query = """
        MATCH (f:Function {project: $project})
        OPTIONAL MATCH (f)-[r:CALLS]-()
        WITH f, count(r) as connections
        WHERE connections > 10
        RETURN f.full_name as name, connections, f.node_type as type
        ORDER BY connections DESC
        LIMIT 10
        """
        hubs = self.graph.run(hub_query, project=project).data()
        
        # Circular dependencies
        circular_query = """
        MATCH path = (f1:Function {project: $project})-[:CALLS*2..5]->(f1)
        WITH path LIMIT 10
        RETURN [n in nodes(path) | n.full_name] as cycle
        """
        circular = self.graph.run(circular_query, project=project).data()
        
        # Isolated functions (no in/out connections)
        isolated_query = """
        MATCH (f:Function {project: $project})
        WHERE NOT (f)-[:CALLS]-()
        RETURN f.full_name as name, f.module as module
        ORDER BY f.module, f.name
        LIMIT 20
        """
        isolated = self.graph.run(isolated_query, project=project).data()
        
        # Generate HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Code Health Report - {project}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #1a1a1a;
                    color: #e0e0e0;
                }}
                h1 {{
                    color: #00ff41;
                    text-align: center;
                }}
                .metric {{
                    background-color: #2c3e50;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    border: 1px solid #34495e;
                }}
                .metric h2 {{
                    color: #3498db;
                    margin-top: 0;
                }}
                .good {{ color: #2ecc71; }}
                .warning {{ color: #f39c12; }}
                .error {{ color: #e74c3c; }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .stat-box {{
                    background-color: #34495e;
                    padding: 15px;
                    border-radius: 5px;
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 2em;
                    font-weight: bold;
                }}
                ul {{
                    list-style-type: none;
                    padding-left: 0;
                }}
                li {{
                    padding: 5px 0;
                    border-bottom: 1px solid #34495e;
                }}
                code {{
                    background-color: #34495e;
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-family: monospace;
                }}
            </style>
        </head>
        <body>
            <h1>Code Health Report - {project}</h1>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{total_functions}</div>
                    <div>Total Functions</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value {'' if len(unused) < 10 else 'warning' if len(unused) < 30 else 'error'}">{len(unused)}</div>
                    <div>Unused Functions</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value {'' if len(circular) == 0 else 'error'}">{len(circular)}</div>
                    <div>Circular Dependencies</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{len(isolated)}</div>
                    <div>Isolated Functions</div>
                </div>
            </div>
            
            <div class="metric">
                <h2>🚨 Circular Dependencies</h2>
                {'<p class="good">No circular dependencies found!</p>' if not circular else ''}
                {'<ul>' + ''.join(f'<li class="error">Cycle: {" → ".join(c["cycle"])}</li>' for c in circular) + '</ul>' if circular else ''}
            </div>
            
            <div class="metric">
                <h2>⚠️ Unused Functions ({len(unused)})</h2>
                <p>Functions that are defined but never called:</p>
                <ul>
                {''.join(f'<li><code>{u["name"]}</code> ({u["type"]})</li>' for u in unused[:20])}
                {'<li>... and more</li>' if len(unused) > 20 else ''}
                </ul>
            </div>
            
            <div class="metric">
                <h2>🌟 Highly Connected Functions</h2>
                <p>Functions with the most connections (potential complexity hotspots):</p>
                <ul>
                {''.join(f'<li><code>{h["name"]}</code> - {h["connections"]} connections ({h["type"]})</li>' for h in hubs)}
                </ul>
            </div>
            
            <div class="metric">
                <h2>🏝️ Isolated Functions</h2>
                <p>Functions with no connections (neither calling nor being called):</p>
                <ul>
                {''.join(f'<li><code>{i["name"]}</code></li>' for i in isolated[:10])}
                {'<li>... and more</li>' if len(isolated) > 10 else ''}
                </ul>
            </div>
            
            <div class="metric">
                <h2>📊 Health Score</h2>
                {self._calculate_health_score_html(total_functions, len(unused), len(circular), len(isolated))}
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[KG Visualizer] Code health report saved to {output_file}")
        return output_file
    
    def _calculate_health_score_html(self, total: int, unused: int, circular: int, isolated: int) -> str:
        """Calculate and format health score"""
        if total == 0:
            return '<p>No functions to analyze</p>'
        
        # Calculate score (0-100)
        unused_ratio = unused / total
        circular_penalty = circular * 10  # Each cycle is bad
        isolated_ratio = isolated / total
        
        score = max(0, 100 - (unused_ratio * 30) - circular_penalty - (isolated_ratio * 20))
        score = int(score)
        
        # Determine status
        if score >= 80:
            status = 'good'
            message = 'Excellent code health!'
        elif score >= 60:
            status = 'warning'
            message = 'Some improvements recommended'
        else:
            status = 'error'
            message = 'Significant refactoring needed'
        
        return f'''
        <div style="text-align: center;">
            <div class="stat-value {status}" style="font-size: 4em;">{score}/100</div>
            <p class="{status}">{message}</p>
            <p>Score calculation: Base 100 - ({int(unused_ratio*30)}% unused) - ({circular_penalty} circular) - ({int(isolated_ratio*20)}% isolated)</p>
        </div>
        '''
    
    def create_interactive_dashboard(self, project: str, output_dir: str = "kg_dashboard") -> str:
        """
        Create a full dashboard with multiple visualizations
        
        Args:
            project: Project name
            output_dir: Output directory for dashboard files
            
        Returns:
            Path to the main dashboard HTML file
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate individual visualizations
        self.visualize_project(project, os.path.join(output_dir, "project_graph.html"))
        self.visualize_code_health(project, os.path.join(output_dir, "code_health.html"))
        
        # Create main dashboard HTML
        dashboard_html = f"""
        <!DOCTYPE html>
        <html style="height: 100%; background-color: #1a1a1a;">
        <head>
            <title>Knowledge Graph Dashboard - {project}</title>
            <style>
                html {{
                    height: 100%;
                    background-color: #1a1a1a;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #1a1a1a;
                    color: white;
                    height: 100%;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                }}
                h1 {{
                    text-align: center;
                    color: #00ff41;
                    margin: 10px 0;
                }}
                .viz-container {{
                    flex: 1;
                    position: relative;
                    overflow: hidden;
                    background-color: #1a1a1a;
                }}
                iframe {{
                    width: 100%;
                    height: 100%;
                    border: none;
                    position: absolute;
                    top: 0;
                    left: 0;
                }}
                .nav-buttons {{
                    text-align: center;
                    margin: 20px 0;
                }}
                button {{
                    background-color: #00ff41;
                    color: black;
                    border: none;
                    padding: 10px 20px;
                    margin: 0 10px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-weight: bold;
                }}
                button:hover {{
                    background-color: #00cc33;
                }}
            </style>
        </head>
        <body>
            <h1>Knowledge Graph Dashboard - {project}</h1>
            
            <div class="nav-buttons">
                <button onclick="showViz('project')">Project Overview</button>
                <button onclick="showViz('health')">Code Health</button>
            </div>
            
            <div id="project-viz" class="viz-container" style="display:flex; flex-direction:column; background-color: #1a1a1a;">
                <h2 style="text-align:center; color: #00ff41; margin: 10px 0;">Project Overview</h2>
                <div style="flex: 1; position: relative; background-color: #1a1a1a;">
                    <iframe src="project_graph.html"></iframe>
                </div>
            </div>
            
            <div id="health-viz" class="viz-container" style="display:none; flex-direction:column; background-color: #1a1a1a;">
                <h2 style="text-align:center; color: #e74c3c; margin: 10px 0;">Code Health Analysis</h2>
                <div style="flex: 1; position: relative; background-color: #1a1a1a;">
                    <iframe src="code_health.html"></iframe>
                </div>
            </div>
            
            <script>
                function showViz(type) {{
                    document.getElementById('project-viz').style.display = type === 'project' ? 'flex' : 'none';
                    document.getElementById('health-viz').style.display = type === 'health' ? 'flex' : 'none';
                }}
            </script>
        </body>
        </html>
        """
        
        dashboard_path = os.path.join(output_dir, "dashboard.html")
        with open(dashboard_path, 'w') as f:
            f.write(dashboard_html)
        
        print(f"[KG Visualizer] Dashboard created at {dashboard_path}")
        return dashboard_path


def demonstrate_visualizer():
    """Demonstrate the KG visualizer with sample visualizations"""
    viz = KnowledgeGraphVisualizer()
    
    print("=== Knowledge Graph Visualizer Demo ===")
    
    # 1. Visualize mnemo project
    print("\n1. Visualizing mnemo project...")
    viz.visualize_project("mnemo-live-test", "mnemo_graph.html")
    
    # 2. Visualize pattern search
    print("\n2. Visualizing 'memory' pattern...")
    viz.visualize_pattern_search("memory", "mnemo-live-test", "memory_pattern.html")
    
    # 3. Create dashboard
    print("\n3. Creating interactive dashboard...")
    dashboard_path = viz.create_interactive_dashboard("mnemo-live-test")
    
    # Open in browser
    print(f"\nOpening dashboard in browser...")
    webbrowser.open(f"file://{os.path.abspath(dashboard_path)}")


if __name__ == "__main__":
    demonstrate_visualizer()