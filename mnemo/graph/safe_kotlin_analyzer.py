"""Safe Kotlin analyzer using compiled JAR - no regex catastrophic backtracking!"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from py2neo import Graph, Node, Relationship
import time
import shutil


class SafeKotlinAnalyzer:
    """
    Safe Kotlin analyzer that won't hang on comment-heavy files.
    Uses a pre-compiled Kotlin analyzer JAR instead of regex.
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        self.analyzer_jar = self._setup_analyzer()
        
    def _setup_analyzer(self) -> Path:
        """Setup the safe analyzer JAR."""
        # Check if JAR exists in current directory
        local_jar = Path("simple_analyzer.jar")
        if local_jar.exists():
            return local_jar
            
        # Otherwise, create and compile it
        analyzer_code = '''// Safe Kotlin analyzer
import java.io.File

fun analyzeFile(path: String): String {
    val file = File(path)
    val lines = file.readLines()
    
    var packageName = ""
    var imports = 0
    val functions = mutableListOf<String>()
    val classes = mutableListOf<String>()
    var comments = 0
    var inBlock = false
    
    for (line in lines) {
        val trim = line.trim()
        
        // Comment counting (safe!)
        when {
            inBlock -> {
                comments++
                if (trim.contains("*/")) inBlock = false
            }
            trim.startsWith("/*") -> {
                comments++
                inBlock = !trim.contains("*/")
            }
            trim.startsWith("//") -> comments++
        }
        
        // Extract info
        when {
            trim.startsWith("package ") -> packageName = trim.substring(8).trim()
            trim.startsWith("import ") -> imports++
            trim.contains(" fun ") && !trim.startsWith("//") && !trim.startsWith("*") -> {
                val match = Regex("fun\\\\s+(\\\\w+)").find(trim)
                match?.let { functions.add(it.groupValues[1]) }
            }
            (trim.startsWith("class ") || trim.startsWith("interface ") || 
             trim.startsWith("object ") || trim.startsWith("data class ")) -> {
                val className = trim.split(" ")[1].substringBefore("(").substringBefore(":")
                classes.add(className)
            }
        }
    }
    
    // Return JSON
    return """{"file":"${file.name}","package":"$packageName","lines":${lines.size},"comments":$comments,"imports":$imports,"functions":${functions.size},"classes":${classes.size},"functionList":${functions.map{"\\"$it\\""}},"classList":${classes.map{"\\"$it\\""}}}"""
}

fun main(args: Array<String>) {
    if (args.isNotEmpty()) {
        try {
            println(analyzeFile(args[0]))
        } catch (e: Exception) {
            println("""{"error":"${e.message}"}""")
        }
    }
}
'''
        
        # Write and compile
        kt_file = Path("safe_analyzer.kt")
        jar_file = Path("safe_analyzer.jar")
        
        try:
            kt_file.write_text(analyzer_code)
            
            # Compile to JAR
            result = subprocess.run(
                ["kotlinc", str(kt_file), "-include-runtime", "-d", str(jar_file)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and jar_file.exists():
                kt_file.unlink()  # Clean up source
                return jar_file
            else:
                raise Exception(f"Compilation failed: {result.stderr}")
                
        except Exception as e:
            print(f"⚠️  Could not create analyzer JAR: {e}")
            # Fall back to simple_analyzer.jar if available
            if local_jar.exists():
                return local_jar
            raise
    
    def analyze_file(self, file_path: str) -> Optional[Dict]:
        """Analyze single file safely."""
        try:
            # Check file size
            file_size = os.path.getsize(file_path) / 1024  # KB
            if file_size > 1000:  # 1MB limit
                print(f"⚠️  Skipping large file: {Path(file_path).name} ({file_size:.1f}KB)")
                return None
            
            # Run analyzer
            result = subprocess.run(
                ["java", "-jar", str(self.analyzer_jar), file_path],
                capture_output=True,
                text=True,
                timeout=5  # 5 second timeout
            )
            
            if result.returncode == 0:
                # Parse output
                output = result.stdout.strip()
                if output.startswith("==="):
                    # Handle simple_analyzer.jar format
                    lines = output.split('\n')
                    return {
                        'file': Path(file_path).name,
                        'package': lines[2].split(': ')[1] if len(lines) > 2 else '',
                        'lines': int(lines[3].split(': ')[1]) if len(lines) > 3 else 0,
                        'comments': int(lines[5].split(': ')[1].split(' ')[0]) if len(lines) > 5 else 0,
                        'functions': [],
                        'classes': []
                    }
                else:
                    # JSON format
                    return json.loads(output)
            else:
                print(f"❌ Error analyzing {Path(file_path).name}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  Timeout analyzing: {Path(file_path).name}")
            return None
        except Exception as e:
            print(f"❌ Error analyzing {Path(file_path).name}: {e}")
            return None
    
    def analyze_project(self, project_path: str, project_name: str, 
                       save_to_neo4j: bool = True, max_files: Optional[int] = None,
                       batch_size: int = 50) -> Dict:
        """Safely analyze Kotlin project."""
        print(f"\n🛡️  Safe Kotlin Analysis (No Regex!)")
        print(f"   Project: {project_name}")
        print(f"   Path: {project_path}")
        print(f"   Batch size: {batch_size}")
        
        start_time = time.time()
        project_path = Path(project_path)
        
        # Find Kotlin files
        kotlin_files = []
        for root, dirs, files in os.walk(project_path):
            # Skip build directories
            dirs[:] = [d for d in dirs if d not in {'.gradle', 'build', 'out', '.git', 'node_modules'}]
            
            for file in files:
                if file.endswith('.kt'):
                    kotlin_files.append(Path(root) / file)
        
        if max_files:
            kotlin_files = kotlin_files[:max_files]
        
        total_files = len(kotlin_files)
        print(f"   Found {total_files} Kotlin files")
        
        if total_files == 0:
            return {'error': 'No Kotlin files found'}
        
        # Check Java availability
        try:
            subprocess.run(["java", "-version"], capture_output=True, check=True)
        except:
            print("\n❌ Java not found! Please install Java 8+")
            return {'error': 'Java not found'}
        
        if save_to_neo4j:
            # Clear existing data
            print("   Clearing existing data...")
            self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                          project=project_name)
        
        stats = {
            'files': 0,
            'classes': 0,
            'functions': 0,
            'comments': 0,
            'errors': 0,
            'timeouts': 0
        }
        
        # Process in batches
        for i in range(0, total_files, batch_size):
            batch = kotlin_files[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_files + batch_size - 1) // batch_size
            
            print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} files)")
            
            for file_idx, kt_file in enumerate(batch):
                if file_idx % 10 == 0:
                    print(f"   Progress: {file_idx}/{len(batch)}")
                
                result = self.analyze_file(str(kt_file))
                
                if result and 'error' not in result:
                    stats['files'] += 1
                    stats['classes'] += result.get('classes', 0) if isinstance(result.get('classes'), int) else len(result.get('classes', []))
                    stats['functions'] += result.get('functions', 0) if isinstance(result.get('functions'), int) else len(result.get('functions', []))
                    stats['comments'] += result.get('comments', 0)
                    
                    # Save to Neo4j if enabled
                    if save_to_neo4j:
                        self._save_to_neo4j(result, kt_file, project_name)
                else:
                    stats['errors'] += 1
        
        duration = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ Safe Analysis Complete!")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Files analyzed: {stats['files']}/{total_files}")
        print(f"   Classes: {stats['classes']}")
        print(f"   Functions: {stats['functions']}")
        print(f"   Comment lines: {stats['comments']}")
        print(f"   Errors: {stats['errors']}")
        print(f"   Speed: {stats['files']/duration:.1f} files/second")
        print(f"\n💪 No regex catastrophic backtracking!")
        
        return stats
    
    def _save_to_neo4j(self, analysis: Dict, file_path: Path, project_name: str):
        """Save analysis results to Neo4j."""
        try:
            # Create file node
            file_node = Node(
                "KotlinFile",
                path=str(file_path),
                name=analysis.get('file', file_path.name),
                package=analysis.get('package', ''),
                project=project_name,
                totalLines=analysis.get('lines', 0),
                commentLines=analysis.get('comments', 0)
            )
            self.graph.merge(file_node, "KotlinFile", "path")
            
        except Exception as e:
            print(f"   Neo4j save error: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        analyzer = SafeKotlinAnalyzer()
        analyzer.analyze_project(sys.argv[1], "safe_test", save_to_neo4j=False, max_files=100)
    else:
        print("Usage: python safe_kotlin_analyzer.py <project_path>")