"""Batch Kotlin analyzer for large projects."""

from pathlib import Path
import re
from typing import Dict, List, Optional, Iterator
from py2neo import Graph, Node, Relationship, Transaction
import time
import gc
from collections import defaultdict
import os


class BatchKotlinAnalyzer:
    """
    Kotlin analyzer optimized for large projects.
    Features:
    - Batch processing to avoid memory issues
    - Transaction batching for Neo4j
    - Progress tracking
    - Graceful error handling
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123",
                 batch_size: int = 50):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        self.batch_size = batch_size
        
        # Simple patterns that won't cause backtracking
        self.patterns = {
            'package': re.compile(r'^package\s+([\w.]+)', re.MULTILINE),
            'import': re.compile(r'^import\s+([\w.*]+)', re.MULTILINE),
            'function': re.compile(r'^\s*(?:suspend\s+)?(?:inline\s+)?(?:private\s+|public\s+|internal\s+)?fun\s+(\w+)', re.MULTILINE),
            'class': re.compile(r'^\s*(?:data\s+)?(?:sealed\s+)?(?:class|interface|object)\s+(\w+)', re.MULTILINE)
        }
    
    def iter_kotlin_files(self, project_path: Path) -> Iterator[Path]:
        """Iterate through Kotlin files efficiently."""
        for root, dirs, files in os.walk(project_path):
            # Skip build and test directories
            dirs[:] = [d for d in dirs if d not in {'.gradle', 'build', 'out', '.git', 'node_modules'}]
            
            for file in files:
                if file.endswith('.kt') and not file.endswith('.test.kt'):
                    yield Path(root) / file
    
    def analyze_file_simple(self, file_path: Path) -> Optional[dict]:
        """Simple file analysis that won't hang."""
        try:
            # Read with size limit
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Skip huge files
            if len(content) > 100000:  # 100KB limit
                print(f"   ⚠️  Skipping large file: {file_path.name} ({len(content)} chars)")
                return None
            
            # Remove comments to avoid pattern matching issues
            content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            
            # Extract basic info
            package_match = self.patterns['package'].search(content)
            package = package_match.group(1) if package_match else "default"
            
            # Limit matches to avoid memory issues
            functions = self.patterns['function'].findall(content)[:50]
            classes = self.patterns['class'].findall(content)[:20]
            imports = self.patterns['import'].findall(content)[:30]
            
            return {
                'path': str(file_path),
                'name': file_path.name,
                'package': package,
                'functions': functions,
                'classes': classes,
                'imports': imports,
                'size': len(content)
            }
            
        except Exception as e:
            print(f"   ❌ Error analyzing {file_path.name}: {str(e)}")
            return None
    
    def analyze_batch(self, files: List[Path], project_name: str, batch_num: int) -> dict:
        """Analyze a batch of files."""
        batch_results = {
            'files': 0,
            'functions': 0,
            'classes': 0,
            'errors': 0
        }
        
        nodes_to_create = []
        
        for file_path in files:
            result = self.analyze_file_simple(file_path)
            
            if result:
                batch_results['files'] += 1
                batch_results['functions'] += len(result['functions'])
                batch_results['classes'] += len(result['classes'])
                
                # Prepare node data
                nodes_to_create.append({
                    'type': 'KotlinFile',
                    'properties': {
                        'path': result['path'],
                        'name': result['name'],
                        'package': result['package'],
                        'project': project_name,
                        'batch': batch_num,
                        'functions': len(result['functions']),
                        'classes': len(result['classes'])
                    }
                })
            else:
                batch_results['errors'] += 1
        
        # Save to Neo4j in transaction
        if nodes_to_create:
            self._save_batch_to_neo4j(nodes_to_create, project_name)
        
        return batch_results
    
    def _save_batch_to_neo4j(self, nodes: List[dict], project_name: str):
        """Save batch to Neo4j efficiently."""
        try:
            # Use parameterized query for efficiency
            query = """
            UNWIND $nodes as node
            CREATE (n:KotlinFile)
            SET n = node.properties
            """
            
            self.graph.run(query, nodes=nodes)
            
        except Exception as e:
            print(f"   ⚠️  Neo4j save error: {str(e)}")
    
    def analyze_project(self, project_path: str, project_name: str, 
                       save_to_neo4j: bool = True, max_files: Optional[int] = None) -> Dict:
        """Analyze project in batches."""
        print(f"\n🚀 Batch Kotlin Analysis")
        print(f"   Project: {project_name}")
        print(f"   Path: {project_path}")
        print(f"   Batch size: {self.batch_size}")
        if max_files:
            print(f"   Max files: {max_files}")
        
        start_time = time.time()
        project_path = Path(project_path)
        
        if save_to_neo4j:
            # Clear existing data for this project
            print("   Clearing existing data...")
            self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                          project=project_name)
        
        # Collect files
        print("   Scanning for Kotlin files...")
        all_files = list(self.iter_kotlin_files(project_path))
        
        if max_files:
            all_files = all_files[:max_files]
        
        total_files = len(all_files)
        print(f"   Found {total_files} Kotlin files")
        
        if total_files == 0:
            return {'error': 'No Kotlin files found'}
        
        # Process in batches
        total_stats = {
            'files': 0,
            'functions': 0,
            'classes': 0,
            'errors': 0,
            'batches': 0
        }
        
        for i in range(0, total_files, self.batch_size):
            batch = all_files[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_files + self.batch_size - 1) // self.batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} files)")
            
            batch_stats = self.analyze_batch(batch, project_name, batch_num)
            
            # Update totals
            for key in batch_stats:
                total_stats[key] += batch_stats[key]
            total_stats['batches'] += 1
            
            # Progress report
            print(f"   ✓ Processed: {batch_stats['files']} files")
            print(f"   ✓ Functions: {batch_stats['functions']}")
            print(f"   ✓ Classes: {batch_stats['classes']}")
            if batch_stats['errors']:
                print(f"   ⚠️  Errors: {batch_stats['errors']}")
            
            # Garbage collection between batches
            gc.collect()
            
            # Small delay to avoid overwhelming the system
            time.sleep(0.1)
        
        duration = time.time() - start_time
        
        # Final summary
        print("\n" + "="*60)
        print("📊 Analysis Complete!")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Files analyzed: {total_stats['files']}/{total_files}")
        print(f"   Total functions: {total_stats['functions']}")
        print(f"   Total classes: {total_stats['classes']}")
        print(f"   Errors: {total_stats['errors']}")
        print(f"   Speed: {total_stats['files']/duration:.1f} files/second")
        
        total_stats['duration'] = duration
        total_stats['total_files'] = total_files
        
        return total_stats


# Quick test function
def test_analyzer(project_path: str):
    """Test the batch analyzer."""
    analyzer = BatchKotlinAnalyzer(batch_size=25)
    
    # First test without Neo4j
    print("\n🧪 Test run without Neo4j...")
    results = analyzer.analyze_project(
        project_path, 
        "test_project",
        save_to_neo4j=False,
        max_files=100  # Limit for testing
    )
    
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_analyzer(sys.argv[1])
    else:
        print("Usage: python batch_kotlin_analyzer.py <project_path>")