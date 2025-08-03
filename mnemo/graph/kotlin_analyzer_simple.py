"""Simple Kotlin analyzer that actually works."""

import os
import re
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from datetime import datetime
from py2neo import Graph, Node, Relationship


class SimpleKotlinAnalyzer:
    """Simple but working Kotlin analyzer."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
    def analyze_kotlin_project(self, project_path: str, project_name: str) -> Dict:
        """Analyze a Kotlin project with simple patterns."""
        print(f"[KOTLIN-SIMPLE] Analyzing project: {project_name}")
        
        start_time = datetime.now()
        project_path = Path(project_path)
        
        # Clear existing data
        self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                      project=project_name)
        
        stats = {
            'files': 0,
            'classes': 0,
            'functions': 0,
            'agents': 0
        }
        
        # Find all Kotlin files
        kotlin_files = list(project_path.rglob("*.kt"))
        
        for kt_file in kotlin_files:
            if any(skip in str(kt_file) for skip in ['/build/', '/.gradle/', '/test/']):
                continue
                
            stats['files'] += 1
            relative_path = kt_file.relative_to(project_path)
            
            try:
                content = kt_file.read_text(encoding='utf-8', errors='ignore')
                
                # Extract package
                package_match = re.search(r'package\s+([\w.]+)', content)
                package_name = package_match.group(1) if package_match else "default"
                
                # Simple class extraction
                class_pattern = r'(?:class|interface|object)\s+(\w+)'
                for match in re.finditer(class_pattern, content):
                    class_name = match.group(1)
                    full_name = f"{package_name}.{class_name}"
                    
                    # Create Function node (for compatibility with search)
                    func_node = Node(
                        "Function",
                        name=class_name,
                        full_name=full_name,
                        file_path=str(relative_path),
                        package=package_name,
                        project=project_name,
                        language="kotlin",
                        type="class"
                    )
                    self.graph.create(func_node)
                    stats['classes'] += 1
                    
                    # Check if it's an Agent
                    if 'Agent' in class_name or ': Agent' in content[match.start():match.end()+100]:
                        stats['agents'] += 1
                
                # Simple function extraction
                function_pattern = r'fun\s+(\w+)'
                for match in re.finditer(function_pattern, content):
                    func_name = match.group(1)
                    full_name = f"{package_name}.{func_name}"
                    
                    # Create Function node
                    func_node = Node(
                        "Function", 
                        name=func_name,
                        full_name=full_name,
                        file_path=str(relative_path),
                        package=package_name,
                        project=project_name,
                        language="kotlin",
                        type="function"
                    )
                    self.graph.create(func_node)
                    stats['functions'] += 1
                    
            except Exception as e:
                print(f"[KOTLIN-SIMPLE] Error processing {kt_file}: {e}")
        
        duration = (datetime.now() - start_time).total_seconds()
        stats['duration'] = duration
        
        print(f"[KOTLIN-SIMPLE] Analysis complete in {duration:.1f}s")
        print(f"[KOTLIN-SIMPLE] Stats: {stats}")
        
        return stats


def analyze_spice_simple():
    """Analyze Spice with simple analyzer."""
    analyzer = SimpleKotlinAnalyzer()
    
    # Check if Spice exists
    spice_path = "/tmp/spice"
    if not Path(spice_path).exists():
        print("Spice project not found at /tmp/spice")
        return
        
    stats = analyzer.analyze_kotlin_project(spice_path, "spice-kotlin")
    
    # Test search
    print("\n[KOTLIN-SIMPLE] Testing search...")
    graph = Graph("bolt://localhost:7687", auth=("neo4j", "password123"))
    
    results = graph.run("""
        MATCH (f:Function {project: 'spice-kotlin'})
        WHERE toLower(f.name) CONTAINS 'agent'
        RETURN f.full_name as name, f.type as type
        LIMIT 10
    """).data()
    
    print(f"Found {len(results)} Agent-related items:")
    for r in results:
        print(f"  - {r['name']} ({r['type']})")
    
    return stats


if __name__ == "__main__":
    analyze_spice_simple()