"""DSL-aware Kotlin analyzer for deep analysis."""

from pathlib import Path
import re
from typing import Dict, List, Set, Tuple, Optional
from py2neo import Graph, Node, Relationship
import time
from collections import defaultdict
import ast

class DSLAwareAnalyzer:
    """
    Kotlin analyzer optimized for DSL-heavy codebases.
    Balances depth with performance.
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
        # Optimized patterns - avoiding catastrophic backtracking
        self.patterns = {
            # Basic elements (fast)
            'package': re.compile(r'package\s+([\w.]+)'),
            'import': re.compile(r'import\s+([\w.*]+)'),
            'simple_function': re.compile(r'fun\s+(\w+)'),
            'simple_class': re.compile(r'(?:class|interface|object)\s+(\w+)'),
            
            # DSL patterns (medium)
            'dsl_block': re.compile(r'(\w+)\s*\{(?:[^{}]|\{[^}]*\})*\}'),
            'property_assign': re.compile(r'(\w+)\s*=\s*([^,\n;]+)'),
            'lambda_block': re.compile(r'\{\s*(\w+(?:\s*,\s*\w+)*)\s*->'),
            'builder_call': re.compile(r'(\w+)\s*\{'),
            
            # Advanced patterns (careful with these)
            'typed_function': re.compile(r'fun\s+(?:<[^>]+>\s+)?(\w+)\s*\(([^)]*)\)\s*:\s*([^\s{]+)'),
            'class_inheritance': re.compile(r'(?:class|interface)\s+(\w+)[^:]*:\s*([^{]+)'),
            
            # Method calls
            'method_call': re.compile(r'\.(\w+)\s*[\(\{]'),
            'constructor_call': re.compile(r'\b([A-Z]\w*)\s*\('),
        }
        
        # DSL keywords to identify DSL-heavy files
        self.dsl_keywords = {
            'spiceAgent', 'buildAgent', 'spiceChain', 'tool', 'step',
            'memory', 'vectorStore', 'llm', 'prompt', 'execute',
            'transform', 'handle', 'behaviors', 'register'
        }
    
    def analyze_file_smart(self, file_path: Path) -> dict:
        """Smart file analysis with DSL awareness."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Quick DSL detection
            is_dsl_heavy = any(keyword in content for keyword in self.dsl_keywords)
            
            # Remove only single-line comments for performance
            content_clean = re.sub(r'//[^\n]*', '', content)
            
            result = {
                'package': '',
                'is_dsl': is_dsl_heavy,
                'functions': [],
                'classes': [],
                'dsl_blocks': [],
                'properties': [],
                'method_calls': [],
                'complexity_score': 0
            }
            
            # Basic extraction (always do these)
            package_match = self.patterns['package'].search(content_clean)
            result['package'] = package_match.group(1) if package_match else "default"
            
            # Simple patterns (fast)
            result['functions'] = self._extract_functions(content_clean, is_dsl_heavy)
            result['classes'] = self._extract_classes(content_clean)
            
            # DSL-specific analysis
            if is_dsl_heavy:
                result['dsl_blocks'] = self._extract_dsl_blocks(content_clean)
                result['properties'] = self._extract_properties(content_clean)
            
            # Calculate complexity
            result['complexity_score'] = self._calculate_complexity(content_clean, result)
            
            return result
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return self._empty_result()
    
    def _extract_functions(self, content: str, is_dsl: bool) -> List[Dict]:
        """Extract functions with DSL awareness."""
        functions = []
        
        if is_dsl:
            # For DSL files, use simple pattern to avoid backtracking
            for match in self.patterns['simple_function'].finditer(content):
                functions.append({
                    'name': match.group(1),
                    'type': 'function'
                })
        else:
            # For non-DSL files, can use more detailed pattern
            for match in self.patterns['typed_function'].finditer(content):
                functions.append({
                    'name': match.group(1),
                    'params': match.group(2),
                    'return_type': match.group(3),
                    'type': 'typed_function'
                })
            
            # Also get simple functions not caught by typed pattern
            simple_funcs = self.patterns['simple_function'].findall(content)
            typed_names = {f['name'] for f in functions}
            
            for func_name in simple_funcs:
                if func_name not in typed_names:
                    functions.append({
                        'name': func_name,
                        'type': 'function'
                    })
        
        return functions
    
    def _extract_classes(self, content: str) -> List[Dict]:
        """Extract classes with inheritance info."""
        classes = []
        
        # First get inheritance info
        inheritance_map = {}
        for match in self.patterns['class_inheritance'].finditer(content):
            class_name = match.group(1)
            extends = match.group(2).strip()
            inheritance_map[class_name] = extends
        
        # Then get all classes
        for match in self.patterns['simple_class'].finditer(content):
            class_name = match.group(1)
            classes.append({
                'name': class_name,
                'extends': inheritance_map.get(class_name, '')
            })
        
        return classes
    
    def _extract_dsl_blocks(self, content: str) -> List[Dict]:
        """Extract DSL builder blocks."""
        blocks = []
        
        # Find builder-style calls
        for match in self.patterns['builder_call'].finditer(content):
            builder_name = match.group(1)
            if builder_name in self.dsl_keywords or builder_name.endswith('Agent') or builder_name.endswith('Chain'):
                blocks.append({
                    'type': builder_name,
                    'position': match.start()
                })
        
        return blocks  # No limit - let's see everything!
    
    def _extract_properties(self, content: str) -> List[Dict]:
        """Extract property assignments in DSL blocks."""
        properties = []
        
        for match in self.patterns['property_assign'].finditer(content):
            prop_name = match.group(1)
            prop_value = match.group(2).strip()
            
            # Skip if it's actually a variable declaration
            if not any(keyword in prop_value for keyword in ['val', 'var', 'fun', 'class']):
                properties.append({
                    'name': prop_name,
                    'value': prop_value[:50]  # Truncate long values
                })
        
        return properties  # No limit!
    
    def _calculate_complexity(self, content: str, result: dict) -> int:
        """Calculate file complexity score."""
        score = 0
        
        # Basic metrics
        score += len(result['functions']) * 2
        score += len(result['classes']) * 3
        
        # DSL complexity
        if result['is_dsl']:
            score += len(result['dsl_blocks']) * 5
            score += len(result['properties'])
        
        # Nesting depth (simplified)
        max_nesting = 0
        current_nesting = 0
        for char in content:
            if char == '{':
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif char == '}':
                current_nesting = max(0, current_nesting - 1)
        
        score += max_nesting * 10
        
        return score
    
    def _empty_result(self) -> dict:
        """Return empty result structure."""
        return {
            'package': '',
            'is_dsl': False,
            'functions': [],
            'classes': [],
            'dsl_blocks': [],
            'properties': [],
            'method_calls': [],
            'complexity_score': 0
        }
    
    def analyze_project_deep(self, project_path: str, project_name: str,
                           focus_on_dsl: bool = True) -> Dict:
        """Deep project analysis with DSL focus."""
        print(f"🔍 Deep DSL-aware analysis of {project_name}...")
        start_time = time.time()
        
        # Clear existing data
        self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                      project=project_name)
        
        project_path = Path(project_path)
        kotlin_files = list(project_path.rglob("*.kt"))
        
        # Filter out build directories
        kotlin_files = [f for f in kotlin_files 
                       if not any(skip in str(f) for skip in ['/build/', '/.gradle/', '/test/'])]
        
        # Categorize files
        dsl_files = []
        regular_files = []
        
        print(f"Categorizing {len(kotlin_files)} files...")
        
        for kt_file in kotlin_files:
            try:
                content = kt_file.read_text(encoding='utf-8', errors='ignore')
                if any(keyword in content for keyword in self.dsl_keywords):
                    dsl_files.append(kt_file)
                else:
                    regular_files.append(kt_file)
            except:
                pass
        
        print(f"Found {len(dsl_files)} DSL files and {len(regular_files)} regular files")
        
        stats = {
            'files': 0,
            'dsl_files': len(dsl_files),
            'functions': 0,
            'classes': 0,
            'dsl_blocks': 0,
            'total_complexity': 0,
            'complex_files': [],
            'dsl_patterns': defaultdict(int),
            'package_dependencies': defaultdict(set)
        }
        
        # Analyze DSL files first (they're more interesting)
        all_results = []
        
        for idx, kt_file in enumerate(dsl_files + regular_files):
            if idx % 10 == 0:
                print(f"  Analyzing file {idx}/{len(kotlin_files)}...")
            
            result = self.analyze_file_smart(kt_file)
            result['file_path'] = str(kt_file.relative_to(project_path))
            all_results.append(result)
            
            # Update stats
            stats['files'] += 1
            stats['functions'] += len(result['functions'])
            stats['classes'] += len(result['classes'])
            stats['dsl_blocks'] += len(result['dsl_blocks'])
            stats['total_complexity'] += result['complexity_score']
            
            # Track complex files
            if result['complexity_score'] > 100:
                stats['complex_files'].append({
                    'file': result['file_path'],
                    'complexity': result['complexity_score'],
                    'is_dsl': result['is_dsl']
                })
            
            # Track DSL patterns
            for block in result['dsl_blocks']:
                stats['dsl_patterns'][block['type']] += 1
            
            # Save to Neo4j
            self._save_analysis_to_neo4j(result, project_name)
        
        # Sort complex files
        stats['complex_files'].sort(key=lambda x: x['complexity'], reverse=True)
        
        elapsed = time.time() - start_time
        print(f"\n✅ Deep analysis complete in {elapsed:.1f}s")
        
        # Print detailed summary
        self._print_deep_summary(stats)
        
        # Find patterns and issues
        patterns = self._find_patterns(all_results, project_name)
        stats['patterns'] = patterns
        
        return stats
    
    def _save_analysis_to_neo4j(self, result: Dict, project_name: str):
        """Save analysis results to Neo4j with relationships."""
        # Create or get package node
        package_results = self.graph.run(
            "MATCH (p:Package {name: $name, project: $project}) RETURN p LIMIT 1",
            name=result['package'], project=project_name
        ).data()
        
        if package_results:
            package_node = package_results[0]['p']
            # Update complexity if higher
            if result['complexity_score'] > package_node.get('complexity', 0):
                package_node['complexity'] = result['complexity_score']
                package_node['is_dsl'] = result['is_dsl']
                self.graph.push(package_node)
        else:
            package_node = Node(
                "Package",
                name=result['package'],
                is_dsl=result['is_dsl'],
                complexity=result['complexity_score'],
                project=project_name
            )
            self.graph.create(package_node)
        
        # Create file node
        file_node = Node(
            "File",
            path=result['file_path'],
            package=result['package'],
            is_dsl=result['is_dsl'],
            complexity=result['complexity_score'],
            project=project_name
        )
        self.graph.create(file_node)
        
        # Link file to package
        rel = Relationship(file_node, "BELONGS_TO", package_node)
        self.graph.create(rel)
        
        # Create function nodes with more detail
        for func in result['functions']:
            func_node = Node(
                "Function",
                name=func['name'],
                type=func.get('type', 'function'),
                return_type=func.get('return_type', ''),
                file_path=result['file_path'],
                package=result['package'],
                project=project_name
            )
            self.graph.create(func_node)
            
            # Link to file
            rel = Relationship(func_node, "DEFINED_IN", file_node)
            self.graph.create(rel)
        
        # Create class nodes
        for cls in result['classes']:
            class_node = Node(
                "Class",
                name=cls['name'],
                extends=cls.get('extends', ''),
                file_path=result['file_path'],
                package=result['package'],
                project=project_name
            )
            self.graph.create(class_node)
            
            # Link to file
            rel = Relationship(class_node, "DEFINED_IN", file_node)
            self.graph.create(rel)
            
            # Create inheritance relationship
            if cls.get('extends'):
                parent_classes = cls['extends'].split(',')
                for parent in parent_classes:
                    parent = parent.strip().split('(')[0]  # Remove constructor params
                    if parent:
                        # Try to find existing parent node first
                        parent_results = self.graph.run(
                            "MATCH (c:Class {name: $name, project: $project}) RETURN c LIMIT 1",
                            name=parent, project=project_name
                        ).data()
                        
                        if parent_results:
                            parent_node = parent_results[0]['c']
                        else:
                            parent_node = Node("Class", name=parent, project=project_name)
                            self.graph.create(parent_node)
                        
                        # Check if relationship already exists
                        existing_rel = self.graph.run(
                            "MATCH (c1:Class {name: $child})-[:EXTENDS]->(c2:Class {name: $parent}) "
                            "WHERE c1.project = $project RETURN count(*) as cnt",
                            child=cls['name'], parent=parent, project=project_name
                        ).data()
                        
                        if not existing_rel or existing_rel[0]['cnt'] == 0:
                            inherit_rel = Relationship(class_node, "EXTENDS", parent_node)
                            self.graph.create(inherit_rel)
        
        # Create DSL block nodes
        for block in result['dsl_blocks']:
            dsl_node = Node(
                "DSLBlock",
                type=block['type'],
                file_path=result['file_path'],
                package=result['package'],
                project=project_name
            )
            self.graph.create(dsl_node)
            
            # Link to file
            rel = Relationship(dsl_node, "DEFINED_IN", file_node)
            self.graph.create(rel)
    
    def _find_patterns(self, all_results: List[Dict], project_name: str) -> Dict:
        """Find interesting patterns in the codebase."""
        patterns = {
            'dsl_heavy_packages': [],
            'inheritance_trees': [],
            'common_patterns': []
        }
        
        # Find DSL-heavy packages
        package_dsl_count = defaultdict(int)
        package_file_count = defaultdict(int)
        
        for result in all_results:
            package = result['package']
            package_file_count[package] += 1
            if result['is_dsl']:
                package_dsl_count[package] += 1
        
        for package, dsl_count in package_dsl_count.items():
            total_files = package_file_count[package]
            if total_files > 0:
                dsl_ratio = dsl_count / total_files
                if dsl_ratio > 0.5:  # More than 50% DSL files
                    patterns['dsl_heavy_packages'].append({
                        'package': package,
                        'dsl_files': dsl_count,
                        'total_files': total_files,
                        'ratio': dsl_ratio
                    })
        
        # Query inheritance trees from Neo4j
        inheritance_query = """
        MATCH (child:Class {project: $project})-[:EXTENDS]->(parent:Class {project: $project})
        RETURN child.name as child, parent.name as parent, child.package as package
        LIMIT 20
        """
        patterns['inheritance_trees'] = self.graph.run(inheritance_query, 
                                                     project=project_name).data()
        
        return patterns
    
    def _print_deep_summary(self, stats: Dict):
        """Print detailed analysis summary."""
        print(f"\n📊 Deep Analysis Results:")
        print(f"  Total Files: {stats['files']}")
        print(f"  DSL Files: {stats['dsl_files']}")
        print(f"  Functions: {stats['functions']}")
        print(f"  Classes: {stats['classes']}")
        print(f"  DSL Blocks: {stats['dsl_blocks']}")
        print(f"  Total Complexity: {stats['total_complexity']}")
        print(f"  Avg Complexity: {stats['total_complexity'] / max(1, stats['files']):.1f}")
        
        if stats['complex_files']:
            print(f"\n🔥 Most Complex Files:")
            for file_info in stats['complex_files'][:5]:
                dsl_marker = "📝" if file_info['is_dsl'] else "📄"
                print(f"  {dsl_marker} {file_info['file']} (complexity: {file_info['complexity']})")
        
        if stats['dsl_patterns']:
            print(f"\n🎯 DSL Pattern Usage:")
            for pattern, count in sorted(stats['dsl_patterns'].items(), 
                                       key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - {pattern}: {count} times")