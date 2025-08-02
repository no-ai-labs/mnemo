"""Project context manager for cross-project knowledge transfer."""

import os
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
from py2neo import Graph, Node, Relationship

from mnemo.graph.call_graph_builder import CallGraphBuilder
from mnemo.graph.enhanced_analyzer import EnhancedCodeAnalyzer
from mnemo.memory.client import MnemoMemoryClient


class ProjectContextManager:
    """Manage multiple project contexts in Neo4j."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123",
                 memory_client: Optional[MnemoMemoryClient] = None):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        self.memory_client = memory_client
        self.builder = CallGraphBuilder(neo4j_uri, username, password)
        self.analyzer = EnhancedCodeAnalyzer(self.builder)
        
    def analyze_project(self, project_path: str, project_name: str, 
                       project_type: str = "python",
                       tags: Optional[Set[str]] = None) -> Dict:
        """Analyze a project and store its context."""
        print(f"[CONTEXT] Analyzing project: {project_name} ({project_type})")
        
        analysis_start = datetime.now()
        
        # Create project node
        project_node = Node(
            "Project",
            name=project_name,
            path=project_path,
            type=project_type,
            analyzed_at=analysis_start.isoformat(),
            tags=list(tags) if tags else []
        )
        self.graph.merge(project_node, "Project", "name")
        
        # Build call graph based on project type
        if project_type == "python":
            self._analyze_python_project(project_path, project_name)
        elif project_type == "javascript" or project_type == "typescript":
            self._analyze_js_project(project_path, project_name)
        elif project_type == "java":
            self._analyze_java_project(project_path, project_name)
        
        # Store analysis metadata
        analysis_end = datetime.now()
        duration = (analysis_end - analysis_start).total_seconds()
        
        stats = self._get_project_stats(project_name)
        stats['duration'] = duration
        
        # Save to memory if client available
        if self.memory_client:
            self.memory_client.remember(
                key=f"project_analysis_{project_name}",
                content=f"Analyzed {project_name}: {stats['functions']} functions, "
                       f"{stats['calls']} calls, {stats['files']} files",
                memory_type="fact",
                tags={"project-context", project_name, project_type}
            )
        
        print(f"[CONTEXT] Analysis complete in {duration:.2f}s")
        return stats
        
    def _analyze_python_project(self, project_path: str, project_name: str):
        """Analyze Python project."""
        self.analyzer.build_enhanced_call_graph(project_path, project_name)
        
    def _analyze_js_project(self, project_path: str, project_name: str):
        """Analyze JavaScript/TypeScript project."""
        # TODO: Implement JS/TS analysis
        # - Parse import/export statements
        # - Find React components
        # - Track hooks usage
        print(f"[CONTEXT] JS/TS analysis not yet implemented")
        
    def _analyze_java_project(self, project_path: str, project_name: str):
        """Analyze Java project."""
        # TODO: Implement Java analysis
        # - Parse package imports
        # - Find Spring annotations
        # - Track dependency injection
        print(f"[CONTEXT] Java analysis not yet implemented")
        
    def _get_project_stats(self, project_name: str) -> Dict:
        """Get statistics for a project."""
        result = self.graph.run("""
            MATCH (f:Function {project: $project})
            OPTIONAL MATCH (f)-[c:CALLS]->()
            RETURN 
                count(DISTINCT f) as functions,
                count(c) as calls,
                count(DISTINCT f.file_path) as files
        """, project=project_name).data()[0]
        
        return result
        
    def find_similar_patterns(self, source_project: str, target_project: str,
                            pattern_type: str = "function") -> List[Dict]:
        """Find similar patterns between projects."""
        if pattern_type == "function":
            # Find functions with similar names
            result = self.graph.run("""
                MATCH (f1:Function {project: $source})
                MATCH (f2:Function {project: $target})
                WHERE f1.name = f2.name
                RETURN f1.full_name as source_func, 
                       f2.full_name as target_func,
                       f1.name as name
                LIMIT 20
            """, source=source_project, target=target_project)
            
        elif pattern_type == "structure":
            # Find similar call patterns
            result = self.graph.run("""
                MATCH (f1:Function {project: $source})-[:CALLS]->(c1)
                MATCH (f2:Function {project: $target})-[:CALLS]->(c2)
                WHERE f1.name = f2.name AND c1.name = c2.name
                RETURN f1.full_name as source_func,
                       f2.full_name as target_func,
                       c1.name as common_call
                LIMIT 20
            """, source=source_project, target=target_project)
            
        return list(result)
        
    def get_pattern_from_project(self, project_name: str, pattern_query: str) -> Dict:
        """Get specific pattern from a project."""
        # This would use semantic search to find patterns
        # For now, simple name matching
        
        result = self.graph.run("""
            MATCH (f:Function {project: $project})
            WHERE toLower(f.name) CONTAINS toLower($query)
               OR toLower(f.class_name) CONTAINS toLower($query)
            OPTIONAL MATCH (f)-[:CALLS]->(callee)
            RETURN f, collect(callee) as calls
            LIMIT 5
        """, project=project_name, query=pattern_query)
        
        patterns = []
        for record in result:
            func = record['f']
            patterns.append({
                'function': func['full_name'],
                'file': func['file_path'],
                'line': func['line_number'],
                'calls': [c['full_name'] for c in record['calls']]
            })
            
        return patterns
        
    def compare_projects(self, project1: str, project2: str) -> Dict:
        """Compare two projects."""
        stats1 = self._get_project_stats(project1)
        stats2 = self._get_project_stats(project2)
        
        # Find common patterns
        common_functions = self.graph.run("""
            MATCH (f1:Function {project: $p1})
            MATCH (f2:Function {project: $p2})
            WHERE f1.name = f2.name
            RETURN count(DISTINCT f1.name) as common_count
        """, p1=project1, p2=project2).data()[0]['common_count']
        
        return {
            'project1': {'name': project1, **stats1},
            'project2': {'name': project2, **stats2},
            'common_functions': common_functions,
            'similarity_score': common_functions / max(stats1['functions'], stats2['functions'])
        }
        
    def suggest_implementation(self, description: str, 
                             reference_projects: List[str]) -> List[Dict]:
        """Suggest implementation based on patterns from other projects."""
        suggestions = []
        
        # Extract keywords from description
        keywords = description.lower().split()
        
        for project in reference_projects:
            for keyword in keywords:
                patterns = self.get_pattern_from_project(project, keyword)
                for pattern in patterns:
                    suggestions.append({
                        'from_project': project,
                        'pattern': pattern,
                        'relevance': self._calculate_relevance(description, pattern)
                    })
                    
        # Sort by relevance
        suggestions.sort(key=lambda x: x['relevance'], reverse=True)
        return suggestions[:10]
        
    def _calculate_relevance(self, description: str, pattern: Dict) -> float:
        """Calculate relevance score."""
        # Simple keyword matching for now
        keywords = set(description.lower().split())
        pattern_words = set(pattern['function'].lower().split('.'))
        
        if not pattern_words:
            return 0.0
            
        return len(keywords & pattern_words) / len(keywords)


def demonstrate_cross_project_context():
    """Demonstrate cross-project context usage."""
    print("=== Cross-Project Context Demo ===\n")
    
    print("1. Analyze multiple projects:")
    print("   manager.analyze_project('/path/to/spring-app', 'spring-app', 'java')")
    print("   manager.analyze_project('/path/to/react-app', 'react-app', 'javascript')")
    print("   manager.analyze_project('/path/to/fastapi-app', 'fastapi-app', 'python')")
    
    print("\n2. Find similar patterns:")
    print("   patterns = manager.find_similar_patterns('spring-app', 'fastapi-app')")
    print("   # Returns: Controller patterns that exist in both")
    
    print("\n3. Get specific pattern:")
    print("   auth_pattern = manager.get_pattern_from_project('spring-app', 'authentication')")
    print("   # Returns: Authentication implementation details")
    
    print("\n4. Suggest implementation:")
    print("   suggestions = manager.suggest_implementation(")
    print("       'create REST API endpoint for user registration',")
    print("       ['spring-app', 'fastapi-app']")
    print("   )")
    print("   # Returns: Similar implementations from reference projects")
    
    print("\n5. Compare projects:")
    print("   comparison = manager.compare_projects('project1', 'project2')")
    print("   # Returns: Statistics and similarity score")


if __name__ == "__main__":
    # Test with mnemo itself
    manager = ProjectContextManager()
    stats = manager.analyze_project(".", "mnemo", "python", {"memory", "mcp", "langchain"})
    
    print(f"\nProject stats: {stats}")
    
    # Demo
    print("\n")
    demonstrate_cross_project_context()