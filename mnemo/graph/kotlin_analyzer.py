"""Kotlin project analyzer for building knowledge graphs."""

import os
import re
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from datetime import datetime
from py2neo import Graph, Node, Relationship

from mnemo.memory.client import MnemoMemoryClient


class KotlinAnalyzer:
    """Analyze Kotlin projects and build knowledge graphs."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
    def analyze_kotlin_project(self, project_path: str, project_name: str) -> Dict:
        """Analyze a Kotlin project and build knowledge graph."""
        print(f"[KOTLIN] Analyzing Kotlin project: {project_name}")
        
        start_time = datetime.now()
        project_path = Path(project_path)
        
        # Clear existing data for this project
        self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                      project=project_name)
        
        # Create project node
        project_node = Node(
            "KotlinProject",
            name=project_name,
            path=str(project_path),
            language="kotlin",
            analyzed_at=start_time.isoformat()
        )
        self.graph.merge(project_node, "KotlinProject", "name")
        
        # Analyze different aspects
        files_analyzed = self._analyze_kotlin_files(project_path, project_name)
        modules_found = self._analyze_gradle_structure(project_path, project_name)
        agents_found = self._analyze_agent_system(project_path, project_name)
        concepts_extracted = self._extract_spice_concepts(project_path, project_name)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        stats = {
            'files': files_analyzed,
            'modules': modules_found,
            'agents': agents_found,
            'concepts': concepts_extracted,
            'duration': duration
        }
        
        print(f"[KOTLIN] Analysis complete: {stats}")
        return stats
        
    def _analyze_kotlin_files(self, project_path: Path, project_name: str) -> int:
        """Analyze Kotlin source files."""
        kotlin_files = list(project_path.rglob("*.kt"))
        
        for kt_file in kotlin_files:
            # Skip build and gradle files
            if any(skip in str(kt_file) for skip in ['/build/', '/.gradle/', '/gradlew']):
                continue
                
            relative_path = kt_file.relative_to(project_path)
            content = kt_file.read_text(encoding='utf-8', errors='ignore')
            
            # Extract package
            package_match = re.search(r'package\s+([\w.]+)', content)
            package_name = package_match.group(1) if package_match else "default"
            
            # Extract imports
            imports = re.findall(r'import\s+([\w.]+)', content)
            
            # Extract classes/interfaces/objects
            classes = re.findall(r'(?:class|interface|object)\s+(\w+)', content)
            
            # Extract functions
            functions = re.findall(r'fun\s+(\w+)', content)
            
            # Create file node
            file_node = Node(
                "KotlinFile",
                name=kt_file.name,
                path=str(relative_path),
                package=package_name,
                project=project_name,
                classes=len(classes),
                functions=len(functions)
            )
            self.graph.create(file_node)
            
            # Create package node
            package_node = Node(
                "Package",
                name=package_name,
                project=project_name
            )
            self.graph.merge(package_node, "Package", "name")
            self.graph.create(Relationship(file_node, "IN_PACKAGE", package_node))
            
            # Create class nodes
            for class_name in classes:
                class_node = Node(
                    "KotlinClass",
                    name=class_name,
                    file=str(relative_path),
                    package=package_name,
                    project=project_name
                )
                self.graph.create(class_node)
                self.graph.create(Relationship(class_node, "DEFINED_IN", file_node))
                
            # Track imports
            for imp in imports:
                if imp.startswith('io.github.spice') or imp.startswith('io.github.noailabs'):
                    import_node = Node(
                        "Import",
                        name=imp,
                        project=project_name
                    )
                    self.graph.merge(import_node, "Import", "name")
                    self.graph.create(Relationship(file_node, "IMPORTS", import_node))
                    
        return len(kotlin_files)
        
    def _analyze_gradle_structure(self, project_path: Path, project_name: str) -> int:
        """Analyze Gradle module structure."""
        modules = []
        
        # Find all build.gradle.kts files
        gradle_files = list(project_path.rglob("build.gradle.kts"))
        
        for gradle_file in gradle_files:
            if gradle_file.parent == project_path:
                continue  # Skip root build file
                
            module_name = gradle_file.parent.name
            modules.append(module_name)
            
            # Create module node
            module_node = Node(
                "Module",
                name=module_name,
                path=str(gradle_file.parent.relative_to(project_path)),
                project=project_name
            )
            self.graph.create(module_node)
            
            # Analyze dependencies
            content = gradle_file.read_text(encoding='utf-8', errors='ignore')
            deps = re.findall(r'implementation\("([^"]+)"\)', content)
            
            for dep in deps:
                if 'spice' in dep or module_name in dep:
                    dep_node = Node(
                        "Dependency",
                        name=dep,
                        project=project_name
                    )
                    self.graph.merge(dep_node, "Dependency", "name")
                    self.graph.create(Relationship(module_node, "DEPENDS_ON", dep_node))
                    
        return len(modules)
        
    def _analyze_agent_system(self, project_path: Path, project_name: str) -> int:
        """Analyze Spice agent system components."""
        agents_found = 0
        
        # Find agent-related files
        for kt_file in project_path.rglob("*.kt"):
            if any(skip in str(kt_file) for skip in ['/build/', '/.gradle/']):
                continue
                
            content = kt_file.read_text(encoding='utf-8', errors='ignore')
            
            # Find agent definitions
            agent_matches = re.findall(
                r'(?:buildAgent|buildOpenAIAgent|buildClaudeAgent)\s*\{([^}]+)\}', 
                content, 
                re.DOTALL
            )
            
            for agent_def in agent_matches:
                # Extract agent properties
                id_match = re.search(r'id\s*=\s*"([^"]+)"', agent_def)
                name_match = re.search(r'name\s*=\s*"([^"]+)"', agent_def)
                
                if id_match:
                    agent_id = id_match.group(1)
                    agent_name = name_match.group(1) if name_match else agent_id
                    
                    agent_node = Node(
                        "SpiceAgent",
                        id=agent_id,
                        name=agent_name,
                        file=kt_file.name,
                        project=project_name
                    )
                    self.graph.create(agent_node)
                    agents_found += 1
                    
            # Find tool definitions
            tool_matches = re.findall(r'tool\("([^"]+)"\)\s*\{', content)
            for tool_name in tool_matches:
                tool_node = Node(
                    "SpiceTool",
                    name=tool_name,
                    file=kt_file.name,
                    project=project_name
                )
                self.graph.create(tool_node)
                
        return agents_found
        
    def _extract_spice_concepts(self, project_path: Path, project_name: str) -> int:
        """Extract Spice framework concepts and patterns."""
        concepts = {
            'Agent': 'Base interface for all intelligent agents',
            'Comm': 'Universal communication unit',
            'Tool': 'Reusable functions agents can execute',
            'Registry': 'Generic thread-safe component registry',
            'SmartCore': 'Next-generation agent system',
            'CommHub': 'Central message routing system',
            'Flow': 'Multi-agent workflow orchestration',
            'VectorStore': 'Vector database integration',
            'SwarmStrategy': 'Multi-agent coordination strategies'
        }
        
        # Create concept nodes
        for concept, description in concepts.items():
            concept_node = Node(
                "SpiceConcept",
                name=concept,
                description=description,
                project=project_name
            )
            self.graph.create(concept_node)
            
        # Find implementations of these concepts
        for kt_file in project_path.rglob("*.kt"):
            if any(skip in str(kt_file) for skip in ['/build/', '/.gradle/']):
                continue
                
            content = kt_file.read_text(encoding='utf-8', errors='ignore')
            
            for concept in concepts:
                # Find classes implementing/extending concepts
                impl_pattern = f'(?:class|interface|object)\\s+(\\w+).*(?::\\s*{concept}|implements\\s+{concept})'
                implementations = re.findall(impl_pattern, content)
                
                for impl_name in implementations:
                    impl_node = Node(
                        "Implementation",
                        name=impl_name,
                        concept=concept,
                        file=kt_file.name,
                        project=project_name
                    )
                    self.graph.create(impl_node)
                    
                    # Link to concept
                    concept_node = self.graph.nodes.match(
                        "SpiceConcept", 
                        name=concept,
                        project=project_name
                    ).first()
                    
                    if concept_node:
                        self.graph.create(
                            Relationship(impl_node, "IMPLEMENTS", concept_node)
                        )
                        
        return len(concepts)
        
    def generate_insights(self, project_name: str) -> Dict:
        """Generate insights from the Kotlin project graph."""
        insights = {}
        
        # Core statistics
        stats = self.graph.run("""
            MATCH (f:KotlinFile {project: $project})
            MATCH (c:KotlinClass {project: $project})
            MATCH (m:Module {project: $project})
            MATCH (a:SpiceAgent {project: $project})
            RETURN 
                count(DISTINCT f) as files,
                count(DISTINCT c) as classes,
                count(DISTINCT m) as modules,
                count(DISTINCT a) as agents
        """, project=project_name).data()[0]
        
        insights['statistics'] = stats
        
        # Package structure
        packages = self.graph.run("""
            MATCH (p:Package {project: $project})<-[:IN_PACKAGE]-(f:KotlinFile)
            RETURN p.name as package, count(f) as files
            ORDER BY files DESC
            LIMIT 10
        """, project=project_name).data()
        
        insights['main_packages'] = packages
        
        # Module dependencies
        module_deps = self.graph.run("""
            MATCH (m:Module {project: $project})-[:DEPENDS_ON]->(d:Dependency)
            WHERE d.name CONTAINS 'spice'
            RETURN m.name as module, collect(d.name) as dependencies
        """, project=project_name).data()
        
        insights['module_dependencies'] = module_deps
        
        # Spice concepts usage
        concept_usage = self.graph.run("""
            MATCH (i:Implementation {project: $project})-[:IMPLEMENTS]->(c:SpiceConcept)
            RETURN c.name as concept, count(i) as implementations
            ORDER BY implementations DESC
        """, project=project_name).data()
        
        insights['concept_implementations'] = concept_usage
        
        return insights


def analyze_spice_project():
    """Analyze the Spice framework."""
    analyzer = KotlinAnalyzer()
    
    print("=== Spice Framework Analysis ===\n")
    
    # Analyze the project
    stats = analyzer.analyze_kotlin_project("/tmp/spice", "spice-framework")
    
    # Generate insights
    insights = analyzer.generate_insights("spice-framework")
    
    print("\n=== Insights ===")
    print(f"\nCore Statistics: {insights['statistics']}")
    
    print("\nMain Packages:")
    for pkg in insights['main_packages'][:5]:
        print(f"  - {pkg['package']}: {pkg['files']} files")
        
    print("\nModule Dependencies:")
    for mod in insights['module_dependencies']:
        print(f"  - {mod['module']}: {len(mod['dependencies'])} Spice dependencies")
        
    print("\nConcept Implementations:")
    for concept in insights['concept_implementations']:
        print(f"  - {concept['concept']}: {concept['implementations']} implementations")
        
    return stats, insights


if __name__ == "__main__":
    analyze_spice_project()