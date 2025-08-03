"""Unified Kotlin analyzer with adjustable analysis depth."""

from pathlib import Path
import re
from typing import Dict, List, Set, Tuple, Optional
from py2neo import Graph, Node, Relationship
from datetime import datetime
import time
from collections import defaultdict
import hashlib

class UnifiedKotlinAnalyzer:
    """
    Unified Kotlin analyzer with multiple analysis levels:
    - BASIC: Functions, classes, simple metrics
    - MEDIUM: + Call relationships, package dependencies
    - DEEP: + Inheritance, complexity, duplicates
    """
    
    BASIC = 1
    MEDIUM = 2  
    DEEP = 3
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
    def analyze_file(self, file_path: Path, depth: int = BASIC) -> dict:
        """Analyze a single Kotlin file with specified depth."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Remove comments to avoid false positives
            content = self._remove_comments(content)
            
            # Extract package
            package_match = re.search(r'package\s+([\w.]+)', content)
            package_name = package_match.group(1) if package_match else "default"
            
            result = {
                'package': package_name,
                'functions': [],
                'classes': [],
                'imports': [],
                'calls': [],
                'inheritance': [],
                'complexity': 0
            }
            
            # BASIC: Extract functions and classes
            result['functions'] = self._extract_functions(content, depth)
            result['classes'] = self._extract_classes(content, depth)
            
            if depth >= self.MEDIUM:
                # MEDIUM: Extract imports and calls
                result['imports'] = re.findall(r'import\s+([\w.*]+)', content)
                result['calls'] = self._extract_calls(content)
                
            if depth >= self.DEEP:
                # DEEP: Extract inheritance and calculate complexity
                result['inheritance'] = self._extract_inheritance(content)
                result['complexity'] = self._calculate_complexity(content)
                
            return result
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return {
                'package': '', 'functions': [], 'classes': [], 
                'imports': [], 'calls': [], 'inheritance': [], 'complexity': 0
            }
    
    def _remove_comments(self, content: str) -> str:
        """Remove single-line and multi-line comments."""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content
    
    def _extract_functions(self, content: str, depth: int) -> List[Dict]:
        """Extract functions with varying detail based on depth."""
        functions = []
        
        # Enhanced pattern for functions
        pattern = r'(?:(?:public|private|internal|protected|open|override|suspend|inline|tailrec)?\s+)*fun\s+(?:<[\w,\s]+>\s+)?(\w+)\s*\(([^)]*)\)'
        
        for match in re.finditer(pattern, content):
            func_name = match.group(1)
            params = match.group(2)
            
            func_info = {'name': func_name}
            
            if depth >= self.MEDIUM:
                # Parse parameters
                func_info['params'] = self._parse_parameters(params)
                func_info['start_pos'] = match.start()
                
            if depth >= self.DEEP:
                # Extract function body for complexity
                func_body = self._extract_function_body(content, match.end())
                func_info['lines'] = func_body.count('\n') + 1
                func_info['cyclomatic_complexity'] = self._calculate_cyclomatic(func_body)
                
            functions.append(func_info)
            
        return functions
    
    def _extract_classes(self, content: str, depth: int) -> List[Dict]:
        """Extract classes with varying detail based on depth."""
        classes = []
        
        pattern = r'(?:(?:public|private|internal|protected|open|sealed|data|abstract|inner)?\s+)*(class|interface|object|enum\s+class)\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*([^{]+))?'
        
        for match in re.finditer(pattern, content):
            class_type = match.group(1)
            class_name = match.group(2)
            
            class_info = {
                'name': class_name,
                'type': class_type
            }
            
            if depth >= self.MEDIUM:
                inheritance = match.group(3)
                if inheritance:
                    class_info['extends'] = inheritance.strip()
                    
            if depth >= self.DEEP:
                # Extract class body
                class_body = self._extract_class_body(content, match.end())
                class_info['methods'] = len(re.findall(r'fun\s+\w+', class_body))
                class_info['properties'] = len(re.findall(r'(?:val|var)\s+\w+', class_body))
                
            classes.append(class_info)
            
        return classes
    
    def _extract_calls(self, content: str) -> List[Dict]:
        """Extract function calls."""
        calls = []
        
        # Various call patterns
        patterns = [
            (r'(\w+)\s*\(', 'function'),
            (r'(\w+)\.(\w+)\s*\(', 'method'),
            (r'(\w+)\s*\{', 'lambda'),
        ]
        
        keywords = {'if', 'when', 'for', 'while', 'fun', 'return', 'throw', 'try', 'catch', 'class', 'interface'}
        
        for pattern, call_type in patterns:
            for match in re.finditer(pattern, content):
                if call_type == 'method':
                    caller = match.group(1)
                    callee = match.group(2)
                    if callee not in keywords:
                        calls.append({
                            'type': call_type,
                            'caller': caller,
                            'callee': callee
                        })
                else:
                    callee = match.group(1)
                    if callee not in keywords:
                        calls.append({
                            'type': call_type,
                            'callee': callee
                        })
                        
        return calls[:50]  # Limit to prevent memory issues
    
    def _extract_inheritance(self, content: str) -> List[Dict]:
        """Extract inheritance relationships."""
        inheritance = []
        
        # Pattern for class inheritance
        pattern = r'(class|interface)\s+(\w+)(?:<[^>]+>)?\s*:\s*([^{]+)'
        
        for match in re.finditer(pattern, content):
            child = match.group(2)
            parents = match.group(3).strip()
            
            # Split multiple inheritance/implementations
            for parent in re.split(r',\s*', parents):
                parent = parent.strip()
                if parent:
                    inheritance.append({
                        'child': child,
                        'parent': parent.split('(')[0].strip()  # Remove constructor params
                    })
                    
        return inheritance
    
    def _calculate_complexity(self, content: str) -> int:
        """Calculate overall file complexity."""
        # Count decision points
        complexity = 1
        complexity += len(re.findall(r'\bif\b', content))
        complexity += len(re.findall(r'\bwhen\b', content))
        complexity += len(re.findall(r'\bfor\b', content))
        complexity += len(re.findall(r'\bwhile\b', content))
        complexity += len(re.findall(r'\bcatch\b', content))
        complexity += len(re.findall(r'\?\s*:', content))  # Elvis operator
        
        return complexity
    
    def _parse_parameters(self, params: str) -> List[str]:
        """Parse function parameters."""
        if not params.strip():
            return []
        
        # Simple parameter parsing
        params = re.split(r',\s*', params)
        return [p.split(':')[0].strip() for p in params if ':' in p]
    
    def _extract_function_body(self, content: str, start: int) -> str:
        """Extract function body starting from position."""
        brace_count = 0
        in_body = False
        end = start
        
        for i in range(start, min(start + 2000, len(content))):  # Limit search
            if content[i] == '{':
                brace_count += 1
                in_body = True
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0 and in_body:
                    end = i + 1
                    break
                    
        return content[start:end] if end > start else ""
    
    def _extract_class_body(self, content: str, start: int) -> str:
        """Extract class body starting from position."""
        return self._extract_function_body(content, start)  # Same logic
    
    def _calculate_cyclomatic(self, body: str) -> int:
        """Calculate cyclomatic complexity of code block."""
        complexity = 1
        complexity += len(re.findall(r'\bif\b', body))
        complexity += len(re.findall(r'\bwhen\b', body))
        complexity += len(re.findall(r'\bfor\b', body))
        complexity += len(re.findall(r'\bwhile\b', body))
        complexity += len(re.findall(r'\bcatch\b', body))
        
        return complexity
    
    def analyze_project(self, project_path: str, project_name: str, 
                       depth: int = MEDIUM, save_to_neo4j: bool = True) -> Dict:
        """Analyze entire project with specified depth."""
        print(f"🔍 Analyzing {project_name} with depth={depth}...")
        start_time = time.time()
        
        if save_to_neo4j:
            # Clear existing data
            self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                          project=project_name)
        
        project_path = Path(project_path)
        kotlin_files = list(project_path.rglob("*.kt"))
        
        # Filter out build directories
        kotlin_files = [f for f in kotlin_files 
                       if not any(skip in str(f) for skip in ['/build/', '/.gradle/', '/test/'])]
        
        stats = {
            'files': 0,
            'functions': 0,
            'classes': 0,
            'calls': 0,
            'imports': 0,
            'inheritance': 0,
            'avg_complexity': 0,
            'package_dependencies': defaultdict(set),
            'duplicate_functions': defaultdict(list),
            'complex_functions': []
        }
        
        all_complexities = []
        
        # Process files
        for idx, kt_file in enumerate(kotlin_files):
            if idx % 10 == 0:
                print(f"  Processing file {idx}/{len(kotlin_files)}...")
            
            result = self.analyze_file(kt_file, depth)
            relative_path = kt_file.relative_to(project_path)
            
            # Update stats
            stats['files'] += 1
            stats['functions'] += len(result['functions'])
            stats['classes'] += len(result['classes'])
            stats['imports'] += len(result['imports'])
            
            if depth >= self.MEDIUM:
                stats['calls'] += len(result['calls'])
                
                # Track package dependencies
                for imp in result['imports']:
                    if not imp.startswith('java.') and not imp.startswith('kotlin.'):
                        stats['package_dependencies'][result['package']].add(imp)
                        
            if depth >= self.DEEP:
                stats['inheritance'] += len(result['inheritance'])
                all_complexities.append(result['complexity'])
                
                # Track duplicate functions
                for func in result['functions']:
                    stats['duplicate_functions'][func['name']].append({
                        'package': result['package'],
                        'file': str(relative_path)
                    })
                    
                    # Track complex functions
                    if 'cyclomatic_complexity' in func and func['cyclomatic_complexity'] > 10:
                        stats['complex_functions'].append({
                            'name': func['name'],
                            'package': result['package'],
                            'complexity': func['cyclomatic_complexity'],
                            'file': str(relative_path)
                        })
            
            # Save to Neo4j if enabled
            if save_to_neo4j:
                self._save_to_neo4j(result, relative_path, project_name, depth)
        
        # Calculate averages
        if all_complexities:
            stats['avg_complexity'] = sum(all_complexities) / len(all_complexities)
        
        # Convert defaultdicts to regular dicts
        stats['package_dependencies'] = dict(stats['package_dependencies'])
        stats['duplicate_functions'] = {
            name: locations 
            for name, locations in stats['duplicate_functions'].items() 
            if len(locations) > 1
        }
        
        elapsed = time.time() - start_time
        print(f"\n✅ Analysis complete in {elapsed:.1f} seconds")
        
        # Print summary based on depth
        self._print_summary(stats, depth)
        
        return stats
    
    def _save_to_neo4j(self, result: Dict, file_path: Path, project_name: str, depth: int):
        """Save analysis results to Neo4j."""
        # Create package node
        package_node = Node(
            "Package",
            name=result['package'],
            project=project_name
        )
        self.graph.merge(package_node, "Package", "name")
        
        # Create function nodes
        for func in result['functions']:
            func_node = Node(
                "Function",
                name=func['name'],
                full_name=f"{result['package']}.{func['name']}",
                package=result['package'],
                file_path=str(file_path),
                project=project_name,
                language="kotlin"
            )
            
            if depth >= self.DEEP and 'cyclomatic_complexity' in func:
                func_node['complexity'] = func['cyclomatic_complexity']
                func_node['lines'] = func.get('lines', 0)
                
            self.graph.create(func_node)
            
            # Create relationship to package
            rel = Relationship(func_node, "BELONGS_TO", package_node)
            self.graph.create(rel)
        
        # Create class nodes
        for cls in result['classes']:
            class_node = Node(
                "Class",
                name=cls['name'],
                full_name=f"{result['package']}.{cls['name']}",
                package=result['package'],
                file_path=str(file_path),
                project=project_name,
                language="kotlin",
                type=cls['type']
            )
            
            if depth >= self.DEEP:
                class_node['methods'] = cls.get('methods', 0)
                class_node['properties'] = cls.get('properties', 0)
                
            self.graph.create(class_node)
            
            # Create relationship to package
            rel = Relationship(class_node, "BELONGS_TO", package_node)
            self.graph.create(rel)
            
            # Create inheritance relationships
            if depth >= self.MEDIUM and 'extends' in cls:
                parent_name = cls['extends'].split('(')[0].strip()
                parent_node = Node("Class", name=parent_name, project=project_name)
                self.graph.merge(parent_node, "Class", "name")
                
                inherit_rel = Relationship(class_node, "EXTENDS", parent_node)
                self.graph.create(inherit_rel)
    
    def _print_summary(self, stats: Dict, depth: int):
        """Print analysis summary based on depth."""
        print(f"\n📊 Analysis Results:")
        print(f"  Files: {stats['files']}")
        print(f"  Functions: {stats['functions']}")
        print(f"  Classes: {stats['classes']}")
        
        if depth >= self.MEDIUM:
            print(f"  Function Calls: {stats['calls']}")
            print(f"  Imports: {stats['imports']}")
            print(f"  Package Dependencies: {len(stats['package_dependencies'])}")
            
        if depth >= self.DEEP:
            print(f"  Inheritance Relations: {stats['inheritance']}")
            print(f"  Average Complexity: {stats['avg_complexity']:.1f}")
            print(f"  Duplicate Functions: {len(stats['duplicate_functions'])}")
            print(f"  Complex Functions (>10): {len(stats['complex_functions'])}")
            
            if stats['duplicate_functions']:
                print(f"\n⚠️  Top Duplicate Functions:")
                for name, locations in list(stats['duplicate_functions'].items())[:5]:
                    packages = set(loc['package'] for loc in locations)
                    print(f"    - {name}: {len(locations)} occurrences in {len(packages)} packages")
                    
            if stats['complex_functions']:
                print(f"\n🔥 Most Complex Functions:")
                for func in sorted(stats['complex_functions'], 
                                 key=lambda x: x['complexity'], reverse=True)[:5]:
                    print(f"    - {func['name']} (complexity: {func['complexity']}) in {func['package']}")
    
    def find_code_smells(self, project_name: str) -> Dict:
        """Find various code smells in the project."""
        print(f"\n🔍 Finding code smells in {project_name}...")
        
        smells = {
            'god_classes': self._find_god_classes(project_name),
            'long_methods': self._find_long_methods(project_name),
            'circular_dependencies': self._find_circular_dependencies(project_name),
            'unused_code': self._find_unused_code(project_name)
        }
        
        return smells
    
    def _find_god_classes(self, project_name: str) -> List[Dict]:
        """Find classes with too many responsibilities."""
        query = """
        MATCH (c:Class {project: $project})
        WHERE c.methods > 20 OR c.properties > 15
        RETURN c.name as name, c.package as package, 
               c.methods as methods, c.properties as properties
        ORDER BY c.methods DESC
        LIMIT 10
        """
        return self.graph.run(query, project=project_name).data()
    
    def _find_long_methods(self, project_name: str) -> List[Dict]:
        """Find methods that are too long."""
        query = """
        MATCH (f:Function {project: $project})
        WHERE f.lines > 50 OR f.complexity > 15
        RETURN f.name as name, f.package as package,
               f.lines as lines, f.complexity as complexity
        ORDER BY f.complexity DESC
        LIMIT 10
        """
        return self.graph.run(query, project=project_name).data()
    
    def _find_circular_dependencies(self, project_name: str) -> List[Dict]:
        """Find circular package dependencies."""
        # Simplified - just find potential circles
        query = """
        MATCH (p1:Package {project: $project})-[:DEPENDS_ON]->(p2:Package {project: $project})
        MATCH (p2)-[:DEPENDS_ON]->(p1)
        WHERE p1.name < p2.name
        RETURN p1.name as package1, p2.name as package2
        LIMIT 10
        """
        return self.graph.run(query, project=project_name).data()
    
    def _find_unused_code(self, project_name: str) -> List[Dict]:
        """Find potentially unused functions."""
        query = """
        MATCH (f:Function {project: $project})
        WHERE NOT (f)<-[:CALLS]-()
              AND f.name <> 'main'
              AND NOT f.name STARTS WITH 'test'
        RETURN f.name as name, f.package as package, f.file_path as file
        LIMIT 20
        """
        return self.graph.run(query, project=project_name).data()