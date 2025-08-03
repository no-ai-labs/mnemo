"""Extract code context from Neo4j for AI assistants."""

from typing import Dict, List, Optional, Union
from py2neo import Graph
import json


class Neo4jContextExtractor:
    """Extract various code contexts from Neo4j knowledge graph."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
    
    def get_project_overview(self, project_name: str) -> Dict:
        """Get high-level overview of a project."""
        try:
            # Get project info first
            project = self.graph.nodes.match("Project", name=project_name).first()
            if not project:
                return {'error': f'Project {project_name} not found'}
            
            # Count each type separately to avoid cartesian product
            func_count = self.graph.run("""
                MATCH (f:Function {project: $project})
                RETURN count(f) as count
            """, project=project_name).evaluate() or 0
            
            class_count = self.graph.run("""
                MATCH (c:Class {project: $project})
                RETURN count(c) as count
            """, project=project_name).evaluate() or 0
            
            file_count = self.graph.run("""
                MATCH (f:File {project: $project})
                RETURN count(f) as count
            """, project=project_name).evaluate() or 0
            
            pkg_count = self.graph.run("""
                MATCH (p:Package {project: $project})
                RETURN count(p) as count
            """, project=project_name).evaluate() or 0
            
            dsl_count = self.graph.run("""
                MATCH (d:DSLBlock {project: $project})
                RETURN count(d) as count
            """, project=project_name).evaluate() or 0
            
            stats = {
                'language': project.get('language'),
                'path': project.get('absolute_path'),
                'functions': func_count,
                'classes': class_count,
                'files': file_count,
                'packages': pkg_count,
                'dsl_blocks': dsl_count
            }
            
            # Top-level structure
            packages = self.graph.run("""
                MATCH (pkg:Package {project: $project})
                OPTIONAL MATCH (f:Function {project: $project, package: pkg.name})
                OPTIONAL MATCH (c:Class {project: $project, package: pkg.name})
                RETURN pkg.name as package,
                       count(DISTINCT f) as functions,
                       count(DISTINCT c) as classes
                ORDER BY count(DISTINCT f) + count(DISTINCT c) DESC
                LIMIT 10
            """, project=project_name).data()
            
            return {
                'project': project_name,
                'language': stats['language'],
                'path': stats['path'],
                'stats': {
                    'functions': stats['functions'],
                    'classes': stats['classes'],
                    'files': stats['files'],
                    'packages': stats['packages'],
                    'dsl_blocks': stats['dsl_blocks']
                },
                'top_packages': packages
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_function_context(self, project_name: str, function_name: str, 
                           include_callers: bool = True,
                           include_callees: bool = True) -> Dict:
        """Get detailed context about a specific function."""
        try:
            # Find the function(s)
            functions = self.graph.run("""
                MATCH (f:Function {project: $project, name: $function})
                OPTIONAL MATCH (f)-[:DEFINED_IN]->(file:File)
                RETURN f, file.relative_path as file_path
            """, project=project_name, function=function_name).data()
            
            if not functions:
                return {'error': f'Function {function_name} not found in {project_name}'}
            
            results = []
            for func_data in functions:
                func = func_data['f']
                result = {
                    'name': func['name'],
                    'package': func.get('package', func.get('module')),
                    'file': func_data['file_path'],
                    'language': func.get('language', 'unknown')
                }
                
                # Get callers
                if include_callers:
                    callers = self.graph.run("""
                        MATCH (caller:Function {project: $project})-[:CALLS]->(f:Function {project: $project, name: $function})
                        WHERE caller <> f
                        RETURN DISTINCT caller.name as name, 
                               caller.package as package,
                               caller.module as module
                        LIMIT 20
                    """, project=project_name, function=function_name).data()
                    result['callers'] = callers
                
                # Get callees
                if include_callees:
                    callees = self.graph.run("""
                        MATCH (f:Function {project: $project, name: $function})-[:CALLS]->(callee:Function {project: $project})
                        WHERE f <> callee
                        RETURN DISTINCT callee.name as name,
                               callee.package as package,
                               callee.module as module
                        LIMIT 20
                    """, project=project_name, function=function_name).data()
                    result['callees'] = callees
                
                results.append(result)
            
            return {'functions': results}
        except Exception as e:
            return {'error': str(e)}
    
    def get_class_hierarchy(self, project_name: str, class_name: Optional[str] = None) -> Dict:
        """Get class hierarchy information."""
        try:
            if class_name:
                # Specific class
                classes = self.graph.run("""
                    MATCH (c:Class {project: $project, name: $class})
                    OPTIONAL MATCH (c)-[:INHERITS_FROM]->(parent:Class)
                    OPTIONAL MATCH (child:Class)-[:INHERITS_FROM]->(c)
                    OPTIONAL MATCH (c)-[:DEFINED_IN]->(file:File)
                    RETURN c,
                           collect(DISTINCT parent.name) as parents,
                           collect(DISTINCT child.name) as children,
                           file.relative_path as file_path
                """, project=project_name, **{"class": class_name}).data()
                
                if not classes:
                    return {'error': f'Class {class_name} not found'}
                
                result = []
                for cls_data in classes:
                    cls = cls_data['c']
                    result.append({
                        'name': cls['name'],
                        'package': cls.get('package', cls.get('module')),
                        'file': cls_data['file_path'],
                        'parents': cls_data['parents'],
                        'children': cls_data['children'],
                        'is_interface': cls.get('is_interface', False),
                        'is_enum': cls.get('is_enum', False),
                        'is_data_class': cls.get('is_data_class', False)
                    })
                
                return {'classes': result}
            else:
                # All classes with hierarchy
                hierarchy = self.graph.run("""
                    MATCH (c:Class {project: $project})
                    OPTIONAL MATCH (c)-[:INHERITS_FROM]->(parent:Class {project: $project})
                    RETURN c.name as class,
                           c.package as package,
                           collect(DISTINCT parent.name) as parents
                    ORDER BY c.name
                """, project=project_name).data()
                
                return {'class_hierarchy': hierarchy}
        except Exception as e:
            return {'error': str(e)}
    
    def get_call_graph(self, project_name: str, function_name: Optional[str] = None,
                      depth: int = 2) -> Dict:
        """Get call graph starting from a function or entire project."""
        try:
            if function_name:
                # Call graph from specific function
                query = """
                    MATCH path = (start:Function {project: $project, name: $function})-[:CALLS*1..%d]->(end:Function {project: $project})
                    WITH nodes(path) as functions
                    UNWIND range(0, size(functions)-2) as i
                    WITH functions[i] as caller, functions[i+1] as callee
                    RETURN DISTINCT 
                           caller.name as from,
                           caller.package as from_package,
                           callee.name as to,
                           callee.package as to_package
                    LIMIT 100
                """ % depth
                
                edges = self.graph.run(query, project=project_name, function=function_name).data()
                
                # Also get the starting node
                nodes = {function_name: {'package': None}}
                for edge in edges:
                    nodes[edge['from']] = {'package': edge['from_package']}
                    nodes[edge['to']] = {'package': edge['to_package']}
                
                return {
                    'start_function': function_name,
                    'depth': depth,
                    'nodes': list(nodes.keys()),
                    'edges': edges
                }
            else:
                # Entire project call graph (limited)
                edges = self.graph.run("""
                    MATCH (f1:Function {project: $project})-[:CALLS]->(f2:Function {project: $project})
                    WHERE f1 <> f2
                    RETURN f1.name as from,
                           f1.package as from_package,
                           f2.name as to,
                           f2.package as to_package
                    LIMIT 200
                """, project=project_name).data()
                
                nodes = set()
                for edge in edges:
                    nodes.add(edge['from'])
                    nodes.add(edge['to'])
                
                return {
                    'project': project_name,
                    'node_count': len(nodes),
                    'edge_count': len(edges),
                    'edges': edges[:50]  # Limit for context
                }
        except Exception as e:
            return {'error': str(e)}
    
    def get_package_dependencies(self, project_name: str, package_name: Optional[str] = None) -> Dict:
        """Get package-level dependencies."""
        try:
            if package_name:
                # Dependencies of specific package
                deps = self.graph.run("""
                    MATCH (f1:Function {project: $project, package: $package})-[:CALLS]->(f2:Function {project: $project})
                    WHERE f1.package <> f2.package
                    WITH f2.package as dep_package, count(*) as call_count
                    RETURN dep_package, call_count
                    ORDER BY call_count DESC
                """, project=project_name, package=package_name).data()
                
                # Who depends on this package
                dependents = self.graph.run("""
                    MATCH (f1:Function {project: $project})-[:CALLS]->(f2:Function {project: $project, package: $package})
                    WHERE f1.package <> f2.package
                    WITH f1.package as dependent_package, count(*) as call_count
                    RETURN dependent_package, call_count
                    ORDER BY call_count DESC
                """, project=project_name, package=package_name).data()
                
                return {
                    'package': package_name,
                    'dependencies': deps,
                    'dependents': dependents
                }
            else:
                # All package dependencies
                deps = self.graph.run("""
                    MATCH (f1:Function {project: $project})-[:CALLS]->(f2:Function {project: $project})
                    WHERE f1.package <> f2.package
                    WITH f1.package as from_package, f2.package as to_package, count(*) as calls
                    RETURN from_package, to_package, calls
                    ORDER BY calls DESC
                    LIMIT 50
                """, project=project_name).data()
                
                return {'package_dependencies': deps}
        except Exception as e:
            return {'error': str(e)}
    
    def get_dsl_patterns(self, project_name: str) -> Dict:
        """Get DSL patterns used in the project."""
        try:
            patterns = self.graph.run("""
                MATCH (dsl:DSLBlock {project: $project})
                WITH dsl.type as pattern, count(*) as usage_count
                RETURN pattern, usage_count
                ORDER BY usage_count DESC
            """, project=project_name).data()
            
            # Get examples for each pattern
            examples = {}
            for pattern_data in patterns[:10]:  # Top 10 patterns
                pattern = pattern_data['pattern']
                files = self.graph.run("""
                    MATCH (dsl:DSLBlock {project: $project, type: $pattern})-[:DEFINED_IN]->(f:File)
                    RETURN DISTINCT f.relative_path as file
                    LIMIT 3
                """, project=project_name, pattern=pattern).data()
                examples[pattern] = [f['file'] for f in files]
            
            return {
                'dsl_patterns': patterns,
                'examples': examples
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_circular_dependencies(self, project_name: str) -> Dict:
        """Find circular dependencies in the project."""
        try:
            # Function-level circular dependencies
            func_cycles = self.graph.run("""
                MATCH (f1:Function {project: $project})-[:CALLS]->(f2:Function {project: $project})
                MATCH (f2)-[:CALLS]->(f1)
                WHERE id(f1) < id(f2)
                RETURN f1.name as func1, f2.name as func2,
                       f1.package as package1, f2.package as package2
                LIMIT 20
            """, project=project_name).data()
            
            # Package-level circular dependencies
            pkg_cycles = self.graph.run("""
                MATCH (pkg1:Package {project: $project})<-[:BELONGS_TO]-(f1:Function)-[:CALLS]->(f2:Function)-[:BELONGS_TO]->(pkg2:Package {project: $project})
                MATCH (pkg2)<-[:BELONGS_TO]-(f3:Function)-[:CALLS]->(f4:Function)-[:BELONGS_TO]->(pkg1)
                WHERE pkg1.name < pkg2.name
                RETURN DISTINCT pkg1.name as package1, pkg2.name as package2
                LIMIT 10
            """, project=project_name).data()
            
            return {
                'function_cycles': func_cycles,
                'package_cycles': pkg_cycles
            }
        except Exception as e:
            return {'error': str(e)}
    
    def search_by_pattern(self, project_name: str, pattern: str, 
                         search_type: str = 'function') -> Dict:
        """Search for functions/classes by name pattern."""
        try:
            if search_type == 'function':
                results = self.graph.run("""
                    MATCH (f:Function {project: $project})
                    WHERE f.name CONTAINS $pattern
                    OPTIONAL MATCH (f)-[:DEFINED_IN]->(file:File)
                    RETURN f.name as name,
                           f.package as package,
                           file.relative_path as file
                    ORDER BY f.name
                    LIMIT 50
                """, project=project_name, pattern=pattern).data()
            elif search_type == 'class':
                results = self.graph.run("""
                    MATCH (c:Class {project: $project})
                    WHERE c.name CONTAINS $pattern
                    OPTIONAL MATCH (c)-[:DEFINED_IN]->(file:File)
                    RETURN c.name as name,
                           c.package as package,
                           file.relative_path as file
                    ORDER BY c.name
                    LIMIT 50
                """, project=project_name, pattern=pattern).data()
            else:
                return {'error': 'search_type must be "function" or "class"'}
            
            return {
                'search_type': search_type,
                'pattern': pattern,
                'results': results
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_complexity_hotspots(self, project_name: str, limit: int = 10) -> Dict:
        """Get most complex files and functions."""
        try:
            # Complex files
            files = self.graph.run("""
                MATCH (f:File {project: $project})
                WHERE f.complexity > 100
                RETURN f.relative_path as file,
                       f.complexity as complexity
                ORDER BY f.complexity DESC
                LIMIT $limit
            """, project=project_name, limit=limit).data()
            
            # Functions with many calls
            busy_functions = self.graph.run("""
                MATCH (f:Function {project: $project})
                OPTIONAL MATCH (f)-[:CALLS]->(callee:Function)
                OPTIONAL MATCH (caller:Function)-[:CALLS]->(f)
                WITH f, count(DISTINCT callee) as calls_out, count(DISTINCT caller) as calls_in
                WHERE calls_out + calls_in > 10
                RETURN f.name as function,
                       f.package as package,
                       calls_out,
                       calls_in,
                       calls_out + calls_in as total_connections
                ORDER BY total_connections DESC
                LIMIT $limit
            """, project=project_name, limit=limit).data()
            
            return {
                'complex_files': files,
                'busy_functions': busy_functions
            }
        except Exception as e:
            return {'error': str(e)}
    
    def export_context(self, data: Dict, format: str = 'json') -> str:
        """Export context data in various formats."""
        if format == 'json':
            return json.dumps(data, indent=2)
        elif format == 'markdown':
            return self._to_markdown(data)
        elif format == 'summary':
            return self._to_summary(data)
        else:
            return str(data)
    
    def _to_markdown(self, data: Dict) -> str:
        """Convert context data to markdown format."""
        md = []
        
        if 'project' in data and 'stats' in data:
            md.append(f"# Project: {data['project']}")
            md.append(f"\n**Language**: {data.get('language', 'unknown')}")
            md.append(f"**Path**: `{data.get('path', 'N/A')}`")
            md.append("\n## Statistics")
            for key, value in data['stats'].items():
                md.append(f"- **{key.replace('_', ' ').title()}**: {value}")
        
        if 'functions' in data:
            md.append("\n## Functions")
            for func in data['functions']:
                md.append(f"\n### {func['name']}")
                md.append(f"- **Package**: {func.get('package', 'N/A')}")
                md.append(f"- **File**: `{func.get('file', 'N/A')}`")
                
                if 'callers' in func and func['callers']:
                    md.append("\n**Called by**:")
                    for caller in func['callers'][:5]:
                        md.append(f"- {caller['name']} ({caller.get('package', caller.get('module', 'N/A'))})")
                
                if 'callees' in func and func['callees']:
                    md.append("\n**Calls**:")
                    for callee in func['callees'][:5]:
                        md.append(f"- {callee['name']} ({callee.get('package', callee.get('module', 'N/A'))})")
        
        return '\n'.join(md)
    
    def _to_summary(self, data: Dict) -> str:
        """Convert context data to a brief summary."""
        lines = []
        
        if 'error' in data:
            return f"Error: {data['error']}"
        
        if 'project' in data and 'stats' in data:
            stats = data['stats']
            lines.append(f"Project {data['project']} ({data.get('language', 'unknown')}): "
                        f"{stats['functions']} functions, {stats['classes']} classes, "
                        f"{stats['files']} files")
        
        if 'functions' in data:
            lines.append(f"Found {len(data['functions'])} function(s) matching query")
        
        if 'class_hierarchy' in data:
            lines.append(f"Found {len(data['class_hierarchy'])} classes with hierarchy information")
        
        if 'edges' in data:
            lines.append(f"Call graph with {data.get('node_count', len(data.get('nodes', [])))} nodes "
                        f"and {data.get('edge_count', len(data['edges']))} edges")
        
        return '\n'.join(lines)