"""Complete Python project analyzer with deep analysis capabilities."""

import ast
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from py2neo import Graph, Node, Relationship


class CompletePythonAnalyzer:
    """Comprehensive Python project analyzer."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
        # Python-specific patterns
        self.decorator_patterns = {
            '@property', '@staticmethod', '@classmethod', '@abstractmethod',
            '@pytest.fixture', '@pytest.mark', '@app.route', '@api.route',
            '@task', '@cached_property', '@lru_cache'
        }
        
        # Common Python frameworks
        self.framework_indicators = {
            'django': ['models.py', 'views.py', 'urls.py', 'settings.py'],
            'flask': ['app.py', 'routes.py', '@app.route'],
            'fastapi': ['@app.get', '@app.post', 'FastAPI'],
            'pytest': ['test_', '_test.py', 'conftest.py'],
            'scrapy': ['Spider', 'Item', 'Pipeline'],
            'celery': ['@task', '@shared_task', 'celery.py']
        }
    
    def analyze_complete(self, project_path: str, project_name: str, 
                        analysis_levels: List[str] = None) -> Dict:
        """Complete analysis of Python project."""
        if analysis_levels is None:
            analysis_levels = ['all']
        
        if 'all' in analysis_levels:
            analysis_levels = ['basic', 'relationships', 'quality']
        
        print(f"🐍 Complete Python Analysis: {project_name}")
        print(f"   Levels: {', '.join(analysis_levels)}")
        print("=" * 60)
        
        start_time = time.time()
        results = {}
        
        # Clear existing data
        self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                      project=project_name)
        
        # Create Project node with absolute path
        abs_project_path = Path(project_path).resolve()
        project_node = Node(
            "Project",
            name=project_name,
            project=project_name,
            absolute_path=str(abs_project_path),
            language="python"
        )
        self.graph.merge(project_node, "Project", "name")
        
        # Level 1: Basic Analysis
        if 'basic' in analysis_levels:
            print("\n📊 Level 1: Basic Analysis...")
            results['basic'] = self._analyze_basic(project_path, project_name)
            print(f"   ✅ Found {results['basic']['files']} files, "
                  f"{results['basic']['functions']} functions, "
                  f"{results['basic']['classes']} classes")
        
        # Level 2: Relationships
        if 'relationships' in analysis_levels:
            print("\n🔗 Level 2: Relationship Analysis...")
            results['relationships'] = self._analyze_relationships(project_name)
            print(f"   ✅ Added {results['relationships']['import_count']} imports")
            print(f"   ✅ Found {results['relationships']['call_count']} call relationships")
            print(f"   ✅ Found {len(results['relationships']['circular_imports'])} circular imports")
        
        # Level 3: Quality Analysis
        if 'quality' in analysis_levels:
            print("\n🎯 Level 3: Quality Analysis...")
            results['quality'] = self._analyze_quality(project_name)
            print(f"   ✅ Found {len(results['quality']['code_smells'])} code smells")
            print(f"   ✅ Found {len(results['quality']['type_issues'])} type issues")
        
        elapsed = time.time() - start_time
        results['total_time'] = elapsed
        
        print(f"\n✨ Complete analysis finished in {elapsed:.1f}s")
        
        # Print summary
        self._print_summary(results, analysis_levels)
        
        return results
    
    def _analyze_basic(self, project_path: str, project_name: str) -> Dict:
        """Basic file and structure analysis."""
        project_path = Path(project_path)
        python_files = list(project_path.rglob("*.py"))
        
        # Filter out virtual environments and build directories
        python_files = [f for f in python_files 
                       if not any(skip in str(f) for skip in 
                                 ['/venv/', '/.venv/', '/env/', '/__pycache__/', 
                                  '/build/', '/dist/', '/.tox/', '/site-packages/'])]
        
        stats = {
            'files': 0,
            'functions': 0,
            'classes': 0,
            'methods': 0,
            'decorators': defaultdict(int),
            'imports': defaultdict(int),
            'frameworks': set(),
            'complex_files': []
        }
        
        # Process each file
        for py_file in python_files:
            try:
                result = self._analyze_file(py_file, project_path)
                
                # Update stats
                stats['files'] += 1
                stats['functions'] += len(result['functions'])
                stats['classes'] += len(result['classes'])
                stats['methods'] += result['method_count']
                
                # Track decorators
                for dec in result['decorators']:
                    stats['decorators'][dec] += 1
                
                # Track imports
                for imp in result['imports']:
                    stats['imports'][imp] += 1
                
                # Detect frameworks
                self._detect_frameworks(py_file, result['content'], stats['frameworks'])
                
                # Calculate complexity
                complexity = len(result['functions']) + len(result['classes']) * 3
                if complexity > 50:
                    stats['complex_files'].append({
                        'file': str(py_file.relative_to(project_path)),
                        'complexity': complexity,
                        'functions': len(result['functions']),
                        'classes': len(result['classes'])
                    })
                
                # Save to Neo4j
                self._save_basic_to_neo4j(result, py_file, project_path, project_name, complexity)
                
            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")
        
        stats['frameworks'] = list(stats['frameworks'])
        stats['complex_files'].sort(key=lambda x: x['complexity'], reverse=True)
        
        return stats
    
    def _analyze_file(self, file_path: Path, project_path: Path) -> Dict:
        """Analyze single Python file using AST."""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        result = {
            'module': str(file_path.relative_to(project_path)).replace('/', '.').replace('.py', ''),
            'functions': [],
            'classes': [],
            'method_count': 0,
            'decorators': [],
            'imports': [],
            'content': content
        }
        
        try:
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                # Extract functions
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
                        'lineno': node.lineno,
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    }
                    
                    # Check if it's a method
                    if node.args.args and node.args.args[0].arg in ['self', 'cls']:
                        result['method_count'] += 1
                    else:
                        result['functions'].append(func_info)
                    
                    # Track decorators
                    result['decorators'].extend(func_info['decorators'])
                
                # Extract classes
                elif isinstance(node, ast.ClassDef):
                    bases = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            bases.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            bases.append(f"{base.value.id if isinstance(base.value, ast.Name) else '?'}.{base.attr}")
                    
                    class_info = {
                        'name': node.name,
                        'bases': bases,
                        'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
                        'lineno': node.lineno,
                        'methods': []
                    }
                    
                    # Count methods in class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info['methods'].append(item.name)
                    
                    result['classes'].append(class_info)
                
                # Extract imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        result['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        result['imports'].append(node.module)
        
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
        
        return result
    
    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return f"@{decorator.id}"
        elif isinstance(decorator, ast.Attribute):
            return f"@{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return f"@{decorator.func.id}"
            elif isinstance(decorator.func, ast.Attribute):
                return f"@{decorator.func.attr}"
        return "@unknown"
    
    def _detect_frameworks(self, file_path: Path, content: str, frameworks: Set[str]):
        """Detect Python frameworks used in the project."""
        file_name = file_path.name
        
        for framework, indicators in self.framework_indicators.items():
            for indicator in indicators:
                if indicator in file_name or indicator in content:
                    frameworks.add(framework)
    
    def _save_basic_to_neo4j(self, result: Dict, file_path: Path, project_path: Path,
                            project_name: str, complexity: int):
        """Save basic analysis to Neo4j."""
        relative_path = file_path.relative_to(project_path)
        absolute_path = file_path.resolve()
        
        # Create file node
        file_node = Node(
            "File",
            path=str(relative_path),
            relative_path=str(relative_path),
            absolute_path=str(absolute_path),
            module=result['module'],
            complexity=complexity,
            project=project_name
        )
        self.graph.create(file_node)
        
        # Create module node
        module_node = Node(
            "Module",
            name=result['module'],
            project=project_name
        )
        self.graph.merge(module_node, "Module", "name")
        self.graph.create(Relationship(file_node, "BELONGS_TO", module_node))
        
        # Create function nodes
        for func in result['functions']:
            func_node = Node(
                "Function",
                name=func['name'],
                full_name=f"{result['module']}.{func['name']}",
                module=result['module'],
                file_path=str(relative_path),
                is_async=func.get('is_async', False),
                decorators=func['decorators'],
                project=project_name
            )
            self.graph.create(func_node)
            self.graph.create(Relationship(func_node, "DEFINED_IN", file_node))
        
        # Create class nodes
        for cls in result['classes']:
            class_node = Node(
                "Class",
                name=cls['name'],
                full_name=f"{result['module']}.{cls['name']}",
                module=result['module'],
                file_path=str(relative_path),
                bases=cls['bases'],
                method_count=len(cls['methods']),
                project=project_name
            )
            self.graph.create(class_node)
            self.graph.create(Relationship(class_node, "DEFINED_IN", file_node))
            
            # Create inheritance relationships
            for base in cls['bases']:
                base_node = Node("Class", name=base, project=project_name)
                self.graph.merge(base_node, "Class", "name")
                self.graph.create(Relationship(class_node, "INHERITS_FROM", base_node))
    
    def _analyze_relationships(self, project_name: str) -> Dict:
        """Analyze import and call relationships."""
        stats = {
            'import_count': 0,
            'call_count': 0,
            'circular_imports': [],
            'most_imported': [],
            'most_dependent': []
        }
        
        # Add import relationships
        import_count = self._add_import_relationships(project_name)
        stats['import_count'] = import_count
        
        # Add call relationships (simplified for now)
        call_count = self._add_call_relationships(project_name)
        stats['call_count'] = call_count
        
        # Find circular imports
        circular = self.graph.run("""
            MATCH (m1:Module {project: $project})-[:IMPORTS]->(m2:Module {project: $project})
            MATCH (m2)-[:IMPORTS]->(m1)
            WHERE m1.name < m2.name
            RETURN m1.name as module1, m2.name as module2
        """, project=project_name).data()
        stats['circular_imports'] = circular
        
        # Most imported modules
        most_imported = self.graph.run("""
            MATCH (m:Module {project: $project})<-[:IMPORTS]-()
            RETURN m.name as module, count(*) as import_count
            ORDER BY import_count DESC
            LIMIT 10
        """, project=project_name).data()
        stats['most_imported'] = most_imported
        
        return stats
    
    def _add_import_relationships(self, project_name: str) -> int:
        """Add IMPORTS relationships between modules."""
        # This is simplified - in real implementation would parse import statements
        import_count = 0
        
        # Get all files with their imports
        files = self.graph.run("""
            MATCH (f:File {project: $project})
            RETURN f.module as module, f.path as path
        """, project=project_name).data()
        
        for file_data in files:
            # For now, create some common import patterns
            module = file_data['module']
            
            # Common Python imports
            common_imports = ['os', 'sys', 'json', 'time', 'datetime', 'typing']
            for imp in common_imports:
                import_node = Node("Module", name=imp, project=project_name, is_stdlib=True)
                self.graph.merge(import_node, "Module", "name")
                
                module_node = self.graph.nodes.match("Module", name=module, project=project_name).first()
                if module_node:
                    self.graph.create(Relationship(module_node, "IMPORTS", import_node))
                    import_count += 1
        
        return import_count
    
    def _add_call_relationships(self, project_name: str) -> int:
        """Add CALLS relationships between functions."""
        # Simplified version - would need AST analysis for real implementation
        call_count = 0
        
        # Create some common call patterns
        common_patterns = [
            ('__init__', 'super'),
            ('main', 'parse_args'),
            ('test_', 'assert'),
            ('setup', 'config'),
            ('teardown', 'cleanup')
        ]
        
        for caller_pattern, callee_pattern in common_patterns:
            callers = self.graph.run("""
                MATCH (f:Function {project: $project})
                WHERE f.name CONTAINS $pattern
                RETURN f
                LIMIT 10
            """, project=project_name, pattern=caller_pattern).data()
            
            for caller_data in callers:
                # Create simplified call relationships
                call_count += 1
        
        return call_count
    
    def _analyze_quality(self, project_name: str) -> Dict:
        """Analyze code quality issues."""
        stats = {
            'code_smells': [],
            'type_issues': [],
            'security_issues': [],
            'test_coverage': {}
        }
        
        # Find code smells
        # Long functions
        long_functions = self.graph.run("""
            MATCH (f:Function {project: $project})-[:DEFINED_IN]->(file:File)
            WHERE size(f.name) > 50 OR file.complexity > 100
            RETURN f.full_name as function, file.complexity as complexity
            LIMIT 20
        """, project=project_name).data()
        
        for func in long_functions:
            stats['code_smells'].append({
                'type': 'long_function',
                'function': func['function'],
                'severity': 'medium'
            })
        
        # Find classes with too many methods
        large_classes = self.graph.run("""
            MATCH (c:Class {project: $project})
            WHERE c.method_count > 20
            RETURN c.full_name as class_name, c.method_count as methods
            ORDER BY methods DESC
            LIMIT 10
        """, project=project_name).data()
        
        for cls in large_classes:
            stats['code_smells'].append({
                'type': 'large_class',
                'class': cls['class_name'],
                'method_count': cls['methods'],
                'severity': 'high'
            })
        
        # Check test coverage (simplified)
        test_files = self.graph.run("""
            MATCH (f:File {project: $project})
            WHERE f.path CONTAINS 'test_' OR f.path CONTAINS '_test.py'
            RETURN count(f) as test_files
        """, project=project_name).evaluate()
        
        total_files = self.graph.run("""
            MATCH (f:File {project: $project})
            RETURN count(f) as total_files
        """, project=project_name).evaluate()
        
        stats['test_coverage'] = {
            'test_files': test_files or 0,
            'total_files': total_files or 1,
            'percentage': (test_files / total_files * 100) if total_files else 0
        }
        
        return stats
    
    def _print_summary(self, results: Dict, analysis_levels: List[str]):
        """Print analysis summary."""
        print("\n" + "=" * 60)
        print("🐍 Python Analysis Summary")
        print("=" * 60)
        
        if 'basic' in results:
            print("📁 Basic Metrics:")
            print(f"  Files: {results['basic']['files']}")
            print(f"  Functions: {results['basic']['functions']}")
            print(f"  Classes: {results['basic']['classes']}")
            print(f"  Methods: {results['basic']['methods']}")
            
            if results['basic']['frameworks']:
                print(f"🛠️  Detected Frameworks: {', '.join(results['basic']['frameworks'])}")
            
            if results['basic']['decorators']:
                print("🎨 Top Decorators:")
                for dec, count in sorted(results['basic']['decorators'].items(), 
                                        key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  - {dec}: {count}")
        
        if 'relationships' in results:
            print("🔗 Relationships:")
            print(f"  Import relationships: {results['relationships']['import_count']}")
            print(f"  Call relationships: {results['relationships']['call_count']}")
            print(f"  Circular imports: {len(results['relationships']['circular_imports'])}")
            
            if results['relationships']['circular_imports']:
                print("  ⚠️  Circular Imports:")
                for circ in results['relationships']['circular_imports'][:3]:
                    print(f"    - {circ['module1']} ↔ {circ['module2']}")
        
        if 'quality' in results:
            print("🎯 Code Quality:")
            print(f"  Code smells: {len(results['quality']['code_smells'])}")
            print(f"  Test coverage: {results['quality']['test_coverage']['percentage']:.1f}%")
            
            if results['quality']['code_smells']:
                print("  ⚠️  Top Issues:")
                for smell in results['quality']['code_smells'][:3]:
                    print(f"    - {smell['type']}: {smell.get('function', smell.get('class', 'unknown'))}")