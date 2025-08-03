"""Complete Kotlin analyzer with all deep analysis features."""

from pathlib import Path
import re
from typing import Dict, List, Optional
from py2neo import Graph, Node, Relationship
import time
from collections import defaultdict
import difflib

class CompleteKotlinAnalyzer:
    """
    Complete Kotlin analyzer combining:
    - Fast DSL-aware analysis
    - Function call relationships
    - Package dependencies
    - Code similarity detection
    - Code quality metrics
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
        # Pre-compiled patterns for performance
        self.patterns = {
            'package': re.compile(r'package\s+([\w.]+)'),
            'import': re.compile(r'import\s+([\w.*]+)'),
            'function': re.compile(r'fun\s+(?:<[^>]+>\s+)?(\w+)\s*\(([^)]*)\)'),
            'class': re.compile(r'(?:class|interface|object)\s+(\w+)'),
            'dsl_block': re.compile(r'(\w+)\s*\{'),
            'call': re.compile(r'(\w+)\s*\('),
            'method_call': re.compile(r'\.(\w+)\s*[\(\{]')
        }
        
        self.dsl_keywords = {
            'spiceAgent', 'buildAgent', 'spiceChain', 'tool', 'step',
            'memory', 'vectorStore', 'llm', 'prompt', 'execute',
            'transform', 'handle', 'behaviors', 'register'
        }
        
        self.keywords_to_skip = {
            'if', 'when', 'for', 'while', 'fun', 'return', 'throw', 
            'try', 'catch', 'class', 'interface', 'object', 'val', 'var'
        }
    
    def analyze_complete(self, project_path: str, project_name: str,
                        analysis_levels: List[str] = None) -> Dict:
        """
        Complete analysis with configurable levels.
        
        Levels:
        - 'basic': Files, functions, classes, DSL patterns
        - 'relationships': + Call relationships, dependencies
        - 'quality': + Code clones, similarity, complexity
        - 'all': Everything
        """
        if analysis_levels is None:
            analysis_levels = ['all']
        
        if 'all' in analysis_levels:
            analysis_levels = ['basic', 'relationships', 'quality']
        
        print(f"🚀 Complete Kotlin Analysis: {project_name}")
        print(f"   Levels: {', '.join(analysis_levels)}")
        print("=" * 60)
        
        start_time = time.time()
        results = {}
        
        # Clear existing data
        self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                      project=project_name)
        
        # Create Project node with absolute path
        from pathlib import Path
        abs_project_path = Path(project_path).resolve()
        project_node = Node(
            "Project",
            name=project_name,
            project=project_name,
            absolute_path=str(abs_project_path),
            language="kotlin"
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
            print(f"   ✅ Added {results['relationships']['call_count']} call relationships")
            print(f"   ✅ Found {len(results['relationships']['circular_deps'])} circular dependencies")
        
        # Level 3: Quality Analysis
        if 'quality' in analysis_levels:
            print("\n🎯 Level 3: Quality Analysis...")
            results['quality'] = self._analyze_quality(project_name)
            print(f"   ✅ Found {len(results['quality']['similar_functions'])} similar functions")
            print(f"   ✅ Found {len(results['quality']['code_smells'])} code smells")
        
        elapsed = time.time() - start_time
        results['total_time'] = elapsed
        
        print(f"\n✨ Complete analysis finished in {elapsed:.1f}s")
        
        # Print summary
        self._print_summary(results, analysis_levels)
        
        return results
    
    def _analyze_basic(self, project_path: str, project_name: str) -> Dict:
        """Basic file and structure analysis."""
        project_path = Path(project_path)
        kotlin_files = list(project_path.rglob("*.kt"))
        
        # Filter out build directories
        kotlin_files = [f for f in kotlin_files 
                       if not any(skip in str(f) for skip in ['/build/', '/.gradle/', '/test/'])]
        
        stats = {
            'files': 0,
            'functions': 0,
            'classes': 0,
            'dsl_blocks': 0,
            'packages': set(),
            'dsl_patterns': defaultdict(int),
            'complex_files': []
        }
        
        # Process each file
        for kt_file in kotlin_files:
            result = self._analyze_file(kt_file)
            
            # Update stats
            stats['files'] += 1
            stats['functions'] += len(result['functions'])
            stats['classes'] += len(result['classes'])
            stats['dsl_blocks'] += len(result['dsl_blocks'])
            stats['packages'].add(result['package'])
            
            # Track DSL patterns
            for block in result['dsl_blocks']:
                stats['dsl_patterns'][block['type']] += 1
            
            # Calculate complexity
            complexity = self._calculate_complexity(result)
            if complexity > 100:
                stats['complex_files'].append({
                    'file': str(kt_file.relative_to(project_path)),
                    'complexity': complexity
                })
            
            # Save to Neo4j
            self._save_basic_to_neo4j(result, kt_file, project_path,
                                     project_name, complexity)
        
        stats['packages'] = len(stats['packages'])
        stats['complex_files'].sort(key=lambda x: x['complexity'], reverse=True)
        
        return stats
    
    def _analyze_file(self, file_path: Path) -> Dict:
        """Analyze single file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Remove single-line comments
            content = re.sub(r'//[^\n]*', '', content)
            
            # Extract package
            package_match = self.patterns['package'].search(content)
            package_name = package_match.group(1) if package_match else "default"
            
            # Check if DSL-heavy
            is_dsl = any(keyword in content for keyword in self.dsl_keywords)
            
            # Extract components
            functions = []
            for match in self.patterns['function'].finditer(content):
                functions.append({
                    'name': match.group(1),
                    'params': match.group(2)
                })
            
            classes = self.patterns['class'].findall(content)
            
            # Extract DSL blocks
            dsl_blocks = []
            if is_dsl:
                for match in self.patterns['dsl_block'].finditer(content):
                    block_name = match.group(1)
                    if block_name in self.dsl_keywords or block_name.endswith('Agent'):
                        dsl_blocks.append({
                            'type': block_name,
                            'position': match.start()
                        })
            
            # Extract calls
            calls = self.patterns['call'].findall(content)
            calls = [c for c in calls if c not in self.keywords_to_skip][:50]
            
            return {
                'package': package_name,
                'is_dsl': is_dsl,
                'functions': functions,
                'classes': classes,
                'dsl_blocks': dsl_blocks,
                'calls': calls
            }
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return {
                'package': '', 'is_dsl': False, 'functions': [], 
                'classes': [], 'dsl_blocks': [], 'calls': []
            }
    
    def _analyze_relationships(self, project_name: str) -> Dict:
        """Analyze call relationships and dependencies."""
        stats = {
            'call_count': 0,
            'package_deps': [],
            'circular_deps': [],
            'most_called': [],
            'most_calling': []
        }
        
        # Add call relationships
        call_count = self._add_call_relationships(project_name)
        stats['call_count'] = call_count
        
        # Analyze package dependencies
        self._create_package_dependencies(project_name)
        
        # Find circular dependencies
        circular = self.graph.run("""
            MATCH (p1:Package {project: $project})-[:DEPENDS_ON]->(p2:Package {project: $project})
            MATCH (p2)-[:DEPENDS_ON]->(p1)
            WHERE p1.name < p2.name
            RETURN p1.name as pkg1, p2.name as pkg2
        """, project=project_name).data()
        stats['circular_deps'] = circular
        
        # Most called functions
        most_called = self.graph.run("""
            MATCH (f:Function {project: $project})<-[:CALLS]-()
            RETURN f.name as function, count(*) as call_count
            ORDER BY call_count DESC
            LIMIT 10
        """, project=project_name).data()
        stats['most_called'] = most_called
        
        # Functions making most calls
        most_calling = self.graph.run("""
            MATCH (f:Function {project: $project})-[:CALLS]->()
            RETURN f.name as function, count(*) as calls_out
            ORDER BY calls_out DESC
            LIMIT 10
        """, project=project_name).data()
        stats['most_calling'] = most_calling
        
        return stats
    
    def _analyze_quality(self, project_name: str) -> Dict:
        """Analyze code quality and find issues."""
        stats = {
            'similar_functions': [],
            'code_clones': [],
            'code_smells': [],
            'god_classes': []
        }
        
        # Find similar functions
        similar = self._find_similar_functions(project_name)
        stats['similar_functions'] = similar
        
        # Find code clones
        clones = self._find_code_clones(project_name)
        stats['code_clones'] = clones
        
        # Find code smells
        smells = self._find_code_smells(project_name)
        stats['code_smells'] = smells
        
        # Find god classes
        god_classes = self.graph.run("""
            MATCH (c:Class {project: $project})-[:DEFINED_IN]->(f:File)
            MATCH (f)<-[:DEFINED_IN]-(func:Function)
            WITH c, count(func) as method_count
            WHERE method_count > 15
            RETURN c.name as class_name, method_count
            ORDER BY method_count DESC
            LIMIT 10
        """, project=project_name).data()
        stats['god_classes'] = god_classes
        
        return stats
    
    def _save_basic_to_neo4j(self, result: Dict, file_path: Path, project_path: Path,
                            project_name: str, complexity: int):
        """Save basic analysis to Neo4j."""
        # Calculate paths
        relative_path = file_path.relative_to(project_path)
        absolute_path = file_path.resolve()
        
        # Create or get package node
        package_node = Node(
            "Package",
            name=result['package'],
            project=project_name
        )
        self.graph.merge(package_node, "Package", "name")
        
        # Create file node with both paths
        file_node = Node(
            "File",
            path=str(relative_path),  # Keep for backward compatibility
            relative_path=str(relative_path),
            absolute_path=str(absolute_path),
            package=result['package'],
            is_dsl=result['is_dsl'],
            complexity=complexity,
            project=project_name
        )
        self.graph.create(file_node)
        
        # Link file to package
        self.graph.create(Relationship(file_node, "BELONGS_TO", package_node))
        
        # Create function nodes
        for func in result['functions']:
            func_node = Node(
                "Function",
                name=func['name'],
                package=result['package'],
                file_path=str(relative_path),
                language="kotlin",
                project=project_name
            )
            self.graph.create(func_node)
            self.graph.create(Relationship(func_node, "DEFINED_IN", file_node))
        
        # Create class nodes
        for class_name in result['classes']:
            class_node = Node(
                "Class",
                name=class_name,
                package=result['package'],
                file_path=str(relative_path),
                language="kotlin",
                project=project_name
            )
            self.graph.create(class_node)
            self.graph.create(Relationship(class_node, "DEFINED_IN", file_node))
        
        # Create DSL block nodes
        for block in result['dsl_blocks']:
            dsl_node = Node(
                "DSLBlock",
                type=block['type'],
                file_path=str(relative_path),
                package=result['package'],
                language="kotlin",
                project=project_name
            )
            self.graph.create(dsl_node)
            self.graph.create(Relationship(dsl_node, "DEFINED_IN", file_node))
    
    def _calculate_complexity(self, result: Dict) -> int:
        """Calculate file complexity."""
        score = 0
        score += len(result['functions']) * 2
        score += len(result['classes']) * 3
        score += len(result['dsl_blocks']) * 5
        score += len(result['calls'])
        return score
    
    def _add_call_relationships(self, project_name: str) -> int:
        """Add CALLS relationships between functions using actual code analysis."""
        from mnemo.graph.kotlin_call_analyzer import KotlinCallAnalyzer
        
        # Get project root from Project node
        project_node = self.graph.nodes.match("Project", name=project_name).first()
        if not project_node or 'absolute_path' not in project_node:
            print(f"Warning: No project node found for {project_name}")
            return 0
        
        project_root = Path(project_node['absolute_path'])
        if not project_root.exists():
            print(f"Warning: Project path does not exist: {project_root}")
            return 0
        
        # Analyze actual function calls
        analyzer = KotlinCallAnalyzer()
        call_map, total_calls = analyzer.analyze_project_calls(str(project_root))
        
        call_count = 0
        
        # Create relationships in Neo4j
        for caller_full, callees in call_map.items():
            # Parse caller info
            if ':' in caller_full:
                caller_file, caller_name = caller_full.rsplit(':', 1)
                
                # Find caller function node
                caller_nodes = self.graph.nodes.match("Function", 
                                                    name=caller_name, 
                                                    project=project_name).all()
                
                for caller_node in caller_nodes:
                    # Check if file matches
                    if caller_file in caller_node.get('file_path', ''):
                        # Find callee nodes
                        for callee_name in callees:
                            callee_nodes = self.graph.nodes.match("Function",
                                                                name=callee_name,
                                                                project=project_name).all()
                            
                            for callee_node in callee_nodes:
                                # Create relationship
                                rel = Relationship(caller_node, "CALLS", callee_node)
                                self.graph.merge(rel)
                                call_count += 1
        
        print(f"Created {call_count} call relationships from {total_calls} detected calls")
        return call_count
    
    def _create_package_dependencies(self, project_name: str):
        """Create DEPENDS_ON relationships between packages."""
        # Based on function calls
        self.graph.run("""
            MATCH (f1:Function {project: $project})-[:CALLS]->(f2:Function {project: $project})
            WHERE f1.package <> f2.package
            WITH f1.package as from_pkg, f2.package as to_pkg, count(*) as calls
            MATCH (p1:Package {name: from_pkg, project: $project})
            MATCH (p2:Package {name: to_pkg, project: $project})
            MERGE (p1)-[r:DEPENDS_ON]->(p2)
            SET r.call_count = calls
        """, project=project_name)
    
    def _find_similar_functions(self, project_name: str) -> List[Dict]:
        """Find similar function names."""
        functions = self.graph.run("""
            MATCH (f:Function {project: $project})
            RETURN f.name as name, f.package as package
        """, project=project_name).data()
        
        similar = []
        for i, func1 in enumerate(functions):
            for func2 in functions[i+1:]:
                if func1['package'] != func2['package']:
                    ratio = difflib.SequenceMatcher(None, 
                                                  func1['name'], 
                                                  func2['name']).ratio()
                    if ratio > 0.8:
                        similar.append({
                            'func1': func1['name'],
                            'pkg1': func1['package'],
                            'func2': func2['name'],
                            'pkg2': func2['package'],
                            'similarity': ratio
                        })
        
        return sorted(similar, key=lambda x: x['similarity'], reverse=True)[:10]
    
    def _find_code_clones(self, project_name: str) -> List[Dict]:
        """Find potential code clones."""
        # Find functions with same name in different packages
        clones = self.graph.run("""
            MATCH (f1:Function {project: $project})
            MATCH (f2:Function {project: $project})
            WHERE f1.name = f2.name 
                  AND f1.package <> f2.package
                  AND id(f1) < id(f2)
            RETURN f1.name as function, 
                   collect(DISTINCT f1.package)[0] as pkg1,
                   collect(DISTINCT f2.package)[0] as pkg2
            LIMIT 10
        """, project=project_name).data()
        
        return clones
    
    def _find_code_smells(self, project_name: str) -> List[Dict]:
        """Find various code smells."""
        smells = []
        
        # Long parameter lists
        long_params = self.graph.run("""
            MATCH (f:Function {project: $project})
            WHERE size(split(f.params, ',')) > 5
            RETURN f.name as function, f.package as package,
                   size(split(f.params, ',')) as param_count
            LIMIT 5
        """, project=project_name).data()
        
        for item in long_params:
            smells.append({
                'type': 'long_parameter_list',
                'function': item['function'],
                'package': item['package'],
                'detail': f"{item['param_count']} parameters"
            })
        
        return smells
    
    def _print_summary(self, results: Dict, levels: List[str]):
        """Print analysis summary."""
        print("\n" + "=" * 60)
        print("📊 Analysis Summary")
        print("=" * 60)
        
        if 'basic' in levels and 'basic' in results:
            basic = results['basic']
            print(f"\n📁 Basic Metrics:")
            print(f"  Files: {basic['files']}")
            print(f"  Functions: {basic['functions']}")
            print(f"  Classes: {basic['classes']}")
            print(f"  DSL Blocks: {basic['dsl_blocks']}")
            print(f"  Packages: {basic['packages']}")
            
            if basic['dsl_patterns']:
                print(f"\n🎯 Top DSL Patterns:")
                for pattern, count in sorted(basic['dsl_patterns'].items(), 
                                           key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  - {pattern}: {count}")
        
        if 'relationships' in levels and 'relationships' in results:
            rels = results['relationships']
            print(f"\n🔗 Relationships:")
            print(f"  Call relationships: {rels['call_count']}")
            print(f"  Circular dependencies: {len(rels['circular_deps'])}")
            
            if rels['circular_deps']:
                print(f"\n  ⚠️  Circular Dependencies:")
                for dep in rels['circular_deps'][:3]:
                    print(f"    - {dep['pkg1']} ↔ {dep['pkg2']}")
        
        if 'quality' in levels and 'quality' in results:
            quality = results['quality']
            print(f"\n🎯 Code Quality:")
            print(f"  Similar functions: {len(quality['similar_functions'])}")
            print(f"  Code clones: {len(quality['code_clones'])}")
            print(f"  Code smells: {len(quality['code_smells'])}")
            print(f"  God classes: {len(quality['god_classes'])}")
            
            if quality['god_classes']:
                print(f"\n  📦 God Classes:")
                for gc in quality['god_classes'][:3]:
                    print(f"    - {gc['class_name']}: {gc['method_count']} methods")