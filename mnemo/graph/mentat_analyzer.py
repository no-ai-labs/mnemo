"""Mentat project analyzer combining frontend and backend analysis."""

import os
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime
from py2neo import Graph, Node, Relationship

from mnemo.graph.kotlin_analyzer import KotlinAnalyzer
from mnemo.graph.js_ts_analyzer import JSTypeScriptAnalyzer
from mnemo.memory.client import MnemoMemoryClient
from mnemo.memory.store import MnemoVectorStore


class MentatAnalyzer:
    """Analyze the complete Mentat project (frontend + backend)."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123",
                 memory_client: Optional[MnemoMemoryClient] = None):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        self.kotlin_analyzer = KotlinAnalyzer(neo4j_uri, username, password)
        self.js_ts_analyzer = JSTypeScriptAnalyzer(neo4j_uri, username, password)
        self.memory_client = memory_client
        
    def analyze_mentat_project(self, project_path: str) -> Dict:
        """Analyze the complete Mentat project."""
        print(f"[MENTAT] Starting full project analysis...")
        
        start_time = datetime.now()
        project_path = Path(project_path)
        
        # Clear existing Mentat data
        self.graph.run("MATCH (n {project: 'mentat'}) DETACH DELETE n")
        
        # Create main project node
        project_node = Node(
            "Project",
            name="mentat",
            type="fullstack",
            description="AI-Powered Graph Editor",
            analyzed_at=start_time.isoformat()
        )
        self.graph.merge(project_node, "Project", "name")
        
        results = {}
        
        # Analyze frontend
        frontend_path = project_path / "frontend"
        if frontend_path.exists():
            print("[MENTAT] Analyzing frontend...")
            frontend_stats = self.js_ts_analyzer.analyze_frontend_project(
                str(frontend_path), "mentat"
            )
            results['frontend'] = frontend_stats
            
            # Create frontend subproject node
            frontend_node = Node(
                "Subproject",
                name="mentat-frontend",
                type="frontend",
                framework=frontend_stats.get('framework', 'Vue'),
                project="mentat"
            )
            self.graph.create(frontend_node)
            self.graph.create(Relationship(frontend_node, "PART_OF", project_node))
        
        # Analyze backend
        backend_path = project_path / "backend"
        if backend_path.exists():
            print("[MENTAT] Analyzing backend...")
            backend_stats = self.kotlin_analyzer.analyze_kotlin_project(
                str(backend_path), "mentat"
            )
            results['backend'] = backend_stats
            
            # Create backend subproject node
            backend_node = Node(
                "Subproject",
                name="mentat-backend",
                type="backend",
                framework="Spring Boot + Spice",
                project="mentat"
            )
            self.graph.create(backend_node)
            self.graph.create(Relationship(backend_node, "PART_OF", project_node))
        
        # Analyze architecture connections
        self._analyze_architecture_connections()
        
        # Generate insights
        insights = self._generate_mentat_insights()
        results['insights'] = insights
        
        duration = (datetime.now() - start_time).total_seconds()
        results['duration'] = duration
        
        # Save to memory if client available
        if self.memory_client:
            self._save_mentat_insights(results)
        
        print(f"[MENTAT] Analysis complete in {duration:.2f}s")
        return results
        
    def _analyze_architecture_connections(self):
        """Analyze connections between frontend and backend."""
        # Find API endpoints in backend
        api_endpoints = self.graph.run("""
            MATCH (f:KotlinFile {project: 'mentat'})
            WHERE f.content CONTAINS '@RestController' OR f.content CONTAINS '@GetMapping'
            RETURN f.name as file, f.path as path
        """).data()
        
        # Find API calls in frontend
        api_calls = self.graph.run("""
            MATCH (f:JSFile {project: 'mentat'})
            WHERE f.content CONTAINS 'fetch(' OR f.content CONTAINS 'axios'
            RETURN f.name as file, f.path as path
        """).data()
        
        # Create API connection nodes
        if api_endpoints and api_calls:
            api_node = Node(
                "Architecture",
                type="API_Layer",
                backend_endpoints=len(api_endpoints),
                frontend_calls=len(api_calls),
                project="mentat"
            )
            self.graph.create(api_node)
            
    def _generate_mentat_insights(self) -> Dict:
        """Generate comprehensive insights about Mentat."""
        insights = {}
        
        # Overall architecture
        overall = self.graph.run("""
            MATCH (n {project: 'mentat'})
            RETURN 
                sum(CASE WHEN 'VueComponent' IN labels(n) THEN 1 ELSE 0 END) as vue_components,
                sum(CASE WHEN 'KotlinClass' IN labels(n) THEN 1 ELSE 0 END) as kotlin_classes,
                sum(CASE WHEN 'MentatNode' IN labels(n) THEN 1 ELSE 0 END) as mentat_nodes,
                sum(CASE WHEN 'JSFile' IN labels(n) THEN 1 ELSE 0 END) as js_files,
                sum(CASE WHEN 'KotlinFile' IN labels(n) THEN 1 ELSE 0 END) as kotlin_files
        """).data()[0]
        
        insights['architecture'] = overall
        
        # Frontend insights
        frontend_insights = self.js_ts_analyzer.generate_frontend_insights("mentat")
        insights['frontend'] = frontend_insights
        
        # Mentat-specific nodes
        mentat_nodes = self.graph.run("""
            MATCH (m:MentatNode {project: 'mentat'})
            RETURN m.type as type, count(m) as count
            ORDER BY count DESC
        """).data()
        
        insights['node_types'] = mentat_nodes
        
        # Dependencies analysis
        key_deps = self.graph.run("""
            MATCH (d:Dependency {project: 'mentat'})
            WHERE d.name IN ['@tiptap/core', 'vue-flow', 'chart.js', 'marked', 'tailwindcss']
            RETURN d.name as dependency, d.version as version
        """).data()
        
        insights['key_dependencies'] = key_deps
        
        # Spice integration
        spice_usage = self.graph.run("""
            MATCH (i:Import {project: 'mentat'})
            WHERE i.name CONTAINS 'spice'
            RETURN count(DISTINCT i) as spice_imports
        """).evaluate()
        
        insights['spice_integration'] = {
            'imports': spice_usage or 0,
            'framework': 'Spice 0.1.2'
        }
        
        return insights
        
    def _save_mentat_insights(self, results: Dict):
        """Save Mentat insights to memory."""
        # Architecture overview
        arch = results['insights']['architecture']
        self.memory_client.remember(
            key="mentat_architecture",
            content=f"Mentat has {arch['vue_components']} Vue components, "
                   f"{arch['kotlin_classes']} Kotlin classes, "
                   f"{arch['mentat_nodes']} specialized node types. "
                   f"Frontend: Vue 3 + TipTap, Backend: Spring Boot + Spice",
            memory_type="fact",
            tags={"mentat", "architecture", "fullstack"}
        )
        
        # Node types
        node_types = results['insights'].get('node_types', [])
        if node_types:
            node_summary = ", ".join([f"{n['type']} ({n['count']})" for n in node_types])
            self.memory_client.remember(
                key="mentat_node_types",
                content=f"Mentat implements these node types: {node_summary}. "
                       f"Each represents different aspects of the AI workflow graph.",
                memory_type="fact",
                tags={"mentat", "nodes", "workflow"}
            )
        
        # Key features
        key_deps = results['insights'].get('key_dependencies', [])
        if key_deps:
            deps_summary = ", ".join([d['dependency'] for d in key_deps])
            self.memory_client.remember(
                key="mentat_features",
                content=f"Mentat uses: {deps_summary}. "
                       f"TipTap for rich text editing, Vue Flow for visual workflows, "
                       f"Chart.js for data visualization, Tailwind CSS for styling.",
                memory_type="fact",
                tags={"mentat", "features", "dependencies"}
            )


def analyze_mentat():
    """Run Mentat analysis."""
    # Initialize with memory
    vector_store = MnemoVectorStore(
        collection_name="mentat_analysis",
        persist_directory="./mentat_analysis_db"
    )
    memory_client = MnemoMemoryClient(vector_store)
    
    analyzer = MentatAnalyzer(memory_client=memory_client)
    
    print("=== Mentat Project Analysis ===\n")
    
    results = analyzer.analyze_mentat_project("/tmp/mentat")
    
    print("\n=== Analysis Results ===")
    
    if 'frontend' in results:
        print(f"\nFrontend: {results['frontend']}")
        
    if 'backend' in results:
        print(f"\nBackend: {results['backend']}")
        
    insights = results.get('insights', {})
    
    print("\n=== Architecture Overview ===")
    arch = insights.get('architecture', {})
    print(f"- Vue Components: {arch.get('vue_components', 0)}")
    print(f"- Kotlin Classes: {arch.get('kotlin_classes', 0)}")
    print(f"- Mentat Node Types: {arch.get('mentat_nodes', 0)}")
    
    print("\n=== Node Types ===")
    for node in insights.get('node_types', []):
        print(f"- {node['type']}: {node['count']}")
        
    print("\n=== Key Dependencies ===")
    for dep in insights.get('key_dependencies', []):
        print(f"- {dep['dependency']} ({dep['version']})")
        
    print("\n=== Spice Integration ===")
    spice = insights.get('spice_integration', {})
    print(f"- Framework: {spice.get('framework')}")
    print(f"- Import count: {spice.get('imports', 0)}")
    
    return results


if __name__ == "__main__":
    analyze_mentat()