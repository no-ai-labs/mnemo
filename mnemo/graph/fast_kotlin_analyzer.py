"""Fast Kotlin analyzer with optimized regex patterns."""

from pathlib import Path
import re
from typing import Dict, List, Optional
from py2neo import Graph, Node, Relationship
import time

class FastKotlinAnalyzer:
    """
    Optimized Kotlin analyzer focusing on speed.
    Uses simplified regex patterns to avoid catastrophic backtracking.
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
        # Pre-compile optimized patterns
        self.patterns = {
            'package': re.compile(r'package\s+([\w.]+)'),
            'import': re.compile(r'import\s+([\w.*]+)'),
            # Simplified function pattern - avoid nested quantifiers
            'function': re.compile(r'fun\s+(?:<[^>]+>\s+)?(\w+)\s*\([^)]*\)'),
            # Simplified class pattern
            'class': re.compile(r'(?:class|interface|object)\s+(\w+)'),
            # Simple call pattern
            'call': re.compile(r'(\w+)\s*\('),
            # Method call pattern
            'method_call': re.compile(r'(\w+)\.(\w+)\s*\(')
        }
        
        # Keywords to exclude from calls
        self.keywords = {
            'if', 'when', 'for', 'while', 'fun', 'return', 'throw', 
            'try', 'catch', 'class', 'interface', 'object', 'val', 'var',
            'println', 'print', 'require', 'check', 'assert'
        }
    
    def analyze_file_fast(self, file_path: Path) -> dict:
        """Analyze file with optimized patterns."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Quick comment removal (simpler pattern)
            # Only remove single-line comments for speed
            content = re.sub(r'//[^\n]*', '', content)
            
            # Extract basic info
            package_match = self.patterns['package'].search(content)
            package_name = package_match.group(1) if package_match else "default"
            
            # Find functions (simplified)
            functions = self.patterns['function'].findall(content)
            
            # Find classes (simplified)
            classes = self.patterns['class'].findall(content)
            
            # Find calls (limited)
            calls = self.patterns['call'].findall(content)[:30]  # Limit
            calls = [c for c in calls if c not in self.keywords]
            
            return {
                'package': package_name,
                'functions': functions,
                'classes': classes,
                'calls': calls,
                'imports': self.patterns['import'].findall(content)[:20]  # Limit
            }
            
        except Exception as e:
            print(f"Error in {file_path}: {e}")
            return {
                'package': '', 'functions': [], 'classes': [], 
                'calls': [], 'imports': []
            }
    
    def analyze_project_fast(self, project_path: str, project_name: str,
                           save_to_neo4j: bool = True) -> Dict:
        """Fast project analysis."""
        print(f"⚡ Fast analysis of {project_name}...")
        start_time = time.time()
        
        if save_to_neo4j:
            # Clear existing data
            self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                          project=project_name)
        
        project_path = Path(project_path)
        kotlin_files = []
        
        # Faster file discovery using os.walk
        import os
        for root, dirs, files in os.walk(project_path):
            # Skip build directories
            dirs[:] = [d for d in dirs if d not in {'.gradle', 'build', 'out'}]
            
            for file in files:
                if file.endswith('.kt'):
                    kotlin_files.append(Path(root) / file)
        
        print(f"Found {len(kotlin_files)} Kotlin files")
        
        stats = {
            'files': 0,
            'functions': 0,
            'classes': 0,
            'calls': 0,
            'packages': set(),
            'function_list': [],
            'class_list': []
        }
        
        # Process files
        for idx, kt_file in enumerate(kotlin_files):
            if idx % 20 == 0:
                print(f"  Progress: {idx}/{len(kotlin_files)} files...")
            
            result = self.analyze_file_fast(kt_file)
            
            # Update stats
            stats['files'] += 1
            stats['functions'] += len(result['functions'])
            stats['classes'] += len(result['classes'])
            stats['calls'] += len(result['calls'])
            stats['packages'].add(result['package'])
            
            # Track for duplicates
            for func in result['functions']:
                stats['function_list'].append({
                    'name': func,
                    'package': result['package'],
                    'file': kt_file.name
                })
            
            for cls in result['classes']:
                stats['class_list'].append({
                    'name': cls,
                    'package': result['package'],
                    'file': kt_file.name
                })
            
            # Save to Neo4j (batch for speed)
            if save_to_neo4j and idx % 10 == 0:
                self._batch_save_to_neo4j(stats['function_list'][-10:], 
                                        stats['class_list'][-10:], 
                                        project_name)
        
        # Final batch save
        if save_to_neo4j:
            remaining_funcs = len(stats['function_list']) % 10
            remaining_classes = len(stats['class_list']) % 10
            if remaining_funcs > 0:
                self._batch_save_to_neo4j(stats['function_list'][-remaining_funcs:], 
                                        [], project_name)
            if remaining_classes > 0:
                self._batch_save_to_neo4j([], 
                                        stats['class_list'][-remaining_classes:], 
                                        project_name)
        
        # Find duplicates
        stats['duplicate_functions'] = self._find_duplicates(stats['function_list'])
        stats['duplicate_classes'] = self._find_duplicates(stats['class_list'])
        
        elapsed = time.time() - start_time
        
        # Clean up lists from stats
        del stats['function_list']
        del stats['class_list']
        stats['packages'] = len(stats['packages'])
        
        print(f"\n✅ Fast analysis complete in {elapsed:.1f}s")
        self._print_summary(stats)
        
        return stats
    
    def _batch_save_to_neo4j(self, functions: List[Dict], classes: List[Dict], 
                           project_name: str):
        """Batch save to Neo4j for better performance."""
        # Create function nodes
        for func in functions:
            func_node = Node(
                "Function",
                name=func['name'],
                package=func['package'],
                file=func['file'],
                project=project_name
            )
            self.graph.create(func_node)
        
        # Create class nodes  
        for cls in classes:
            class_node = Node(
                "Class",
                name=cls['name'],
                package=cls['package'],
                file=cls['file'],
                project=project_name
            )
            self.graph.create(class_node)
    
    def _find_duplicates(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Find duplicate items."""
        from collections import defaultdict
        
        duplicates = defaultdict(list)
        for item in items:
            duplicates[item['name']].append({
                'package': item['package'],
                'file': item['file']
            })
        
        # Keep only actual duplicates
        return {name: locs for name, locs in duplicates.items() if len(locs) > 1}
    
    def _print_summary(self, stats: Dict):
        """Print analysis summary."""
        print(f"\n📊 Analysis Results:")
        print(f"  Files: {stats['files']}")
        print(f"  Packages: {stats['packages']}")
        print(f"  Functions: {stats['functions']}")
        print(f"  Classes: {stats['classes']}")
        print(f"  Function Calls: {stats['calls']}")
        
        if stats['duplicate_functions']:
            print(f"\n⚠️  Duplicate Functions: {len(stats['duplicate_functions'])}")
            for name, locs in list(stats['duplicate_functions'].items())[:5]:
                packages = set(loc['package'] for loc in locs)
                print(f"    - {name}: {len(locs)} times in {len(packages)} packages")
        
        if stats['duplicate_classes']:
            print(f"\n⚠️  Duplicate Classes: {len(stats['duplicate_classes'])}")
            for name, locs in list(stats['duplicate_classes'].items())[:5]:
                packages = set(loc['package'] for loc in locs)
                print(f"    - {name}: {len(locs)} times in {len(packages)} packages")
    
    def find_code_issues(self, project_name: str) -> Dict:
        """Quick code issue detection."""
        print(f"\n🔍 Finding code issues in {project_name}...")
        
        issues = {}
        
        # Find duplicate functions across packages
        duplicate_query = """
        MATCH (f1:Function {project: $project})
        MATCH (f2:Function {project: $project})
        WHERE f1.name = f2.name 
              AND f1.package <> f2.package
              AND id(f1) < id(f2)
        RETURN f1.name as name, 
               collect(DISTINCT f1.package) + collect(DISTINCT f2.package) as packages
        LIMIT 10
        """
        issues['duplicate_functions'] = self.graph.run(duplicate_query, 
                                                     project=project_name).data()
        
        # Find potential god classes (by name pattern)
        god_class_query = """
        MATCH (c:Class {project: $project})
        WHERE c.name CONTAINS 'Manager' 
           OR c.name CONTAINS 'Helper'
           OR c.name CONTAINS 'Util'
           OR c.name CONTAINS 'Service'
        RETURN c.name as name, c.package as package
        LIMIT 10
        """
        issues['potential_god_classes'] = self.graph.run(god_class_query, 
                                                       project=project_name).data()
        
        return issues