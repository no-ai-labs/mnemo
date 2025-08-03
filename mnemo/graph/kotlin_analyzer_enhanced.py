"""Enhanced Kotlin analyzer with better regex patterns and call tracking."""

import os
import re
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from datetime import datetime
from py2neo import Graph, Node, Relationship


class EnhancedKotlinAnalyzer:
    """Enhanced Kotlin analyzer with better pattern matching and call tracking."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
    def analyze_kotlin_file(self, file_path: Path, project_name: str) -> Dict:
        """Analyze a single Kotlin file with enhanced patterns."""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # Remove comments to avoid false positives
        content = self._remove_comments(content)
        
        # Extract package
        package_match = re.search(r'package\s+([\w.]+)', content)
        package_name = package_match.group(1) if package_match else "default"
        
        # Extract imports
        imports = re.findall(r'import\s+([\w.*]+)', content)
        
        # Enhanced class/interface/object extraction with inheritance
        class_pattern = r'(?:(?:public|private|internal|protected|open|sealed|data|abstract|inner)?\s+)*(?:class|interface|object|enum\s+class)\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*([^{]+))?'
        classes = []
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            inheritance = match.group(2).strip() if match.group(2) else ""
            classes.append({
                'name': class_name,
                'inheritance': inheritance,
                'type': 'class' if 'class' in match.group(0) else 'interface' if 'interface' in match.group(0) else 'object'
            })
        
        # Enhanced function extraction with better patterns
        functions = self._extract_functions(content)
        
        # Extract function calls
        calls = self._extract_function_calls(content)
        
        # Extract property declarations
        properties = self._extract_properties(content)
        
        return {
            'package': package_name,
            'imports': imports,
            'classes': classes,
            'functions': functions,
            'calls': calls,
            'properties': properties,
            'file': str(file_path)
        }
    
    def _remove_comments(self, content: str) -> str:
        """Remove single-line and multi-line comments."""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content
    
    def _extract_functions(self, content: str) -> List[Dict]:
        """Extract functions with detailed information."""
        functions = []
        
        # Function patterns including extension functions
        patterns = [
            # Regular functions
            r'(?:(?:public|private|internal|protected|open|override|suspend|inline|tailrec)?\s+)*fun\s+(?:<[^>]+>\s+)?(\w+)\s*\([^)]*\)(?:\s*:\s*([^\s{]+))?',
            # Extension functions
            r'(?:(?:public|private|internal|protected|open|override|suspend|inline)?\s+)*fun\s+(?:<[^>]+>\s+)?([^\s.]+)\.(\w+)\s*\([^)]*\)(?:\s*:\s*([^\s{]+))?',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                if len(match.groups()) == 2:  # Regular function
                    functions.append({
                        'name': match.group(1),
                        'return_type': match.group(2) or 'Unit',
                        'type': 'function'
                    })
                else:  # Extension function
                    functions.append({
                        'name': match.group(2),
                        'receiver': match.group(1),
                        'return_type': match.group(3) or 'Unit',
                        'type': 'extension'
                    })
        
        return functions
    
    def _extract_function_calls(self, content: str) -> List[Dict]:
        """Extract function calls and method invocations."""
        calls = []
        
        # Different call patterns
        patterns = [
            # Regular function calls: functionName(...)
            (r'(?<!fun\s)(?<!override\s)(?<!\.)\b(\w+)\s*\(', 'function_call'),
            # Method calls: object.method(...)
            (r'(\w+)\.(\w+)\s*\(', 'method_call'),
            # Constructor calls: ClassName(...)
            (r'\b([A-Z]\w*)\s*\(', 'constructor_call'),
            # Infix calls: a to b
            (r'(\w+)\s+(to|until|downTo|step|and|or|xor|shl|shr|ushr)\s+(\w+)', 'infix_call'),
            # Lambda invocations: { ... }()
            (r'\}\s*\(\)', 'lambda_call'),
            # invoke() calls
            (r'(\w+)\.invoke\s*\(', 'invoke_call'),
        ]
        
        for pattern, call_type in patterns:
            for match in re.finditer(pattern, content):
                if call_type == 'method_call':
                    calls.append({
                        'caller': match.group(1),
                        'callee': match.group(2),
                        'type': call_type
                    })
                elif call_type == 'infix_call':
                    calls.append({
                        'caller': match.group(1),
                        'callee': match.group(2),  # operator
                        'argument': match.group(3),
                        'type': call_type
                    })
                else:
                    calls.append({
                        'callee': match.group(1),
                        'type': call_type
                    })
        
        return calls
    
    def _extract_properties(self, content: str) -> List[Dict]:
        """Extract property declarations."""
        properties = []
        
        # Property patterns
        patterns = [
            # val/var declarations
            r'(?:(?:public|private|internal|protected|open|override)?\s+)*(?:val|var)\s+(\w+)\s*:\s*([^\s=]+)',
            # Property with getter/setter
            r'(?:(?:public|private|internal|protected|open|override)?\s+)*(?:val|var)\s+(\w+)(?:\s*:\s*([^\s{]+))?\s*(?:get|set)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                properties.append({
                    'name': match.group(1),
                    'type': match.group(2) if len(match.groups()) > 1 else 'Any'
                })
        
        return properties
    
    def build_call_graph(self, project_path: str, project_name: str) -> Dict:
        """Build an enhanced call graph for Kotlin project."""
        print(f"[KOTLIN] Building enhanced call graph for: {project_name}")
        
        project_path = Path(project_path)
        
        # Clear existing data
        self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                      project=project_name)
        
        # Create project node
        project_node = Node(
            "KotlinProject",
            name=project_name,
            path=str(project_path),
            language="kotlin"
        )
        self.graph.merge(project_node, "KotlinProject", "name")
        
        # Analyze all Kotlin files
        kotlin_files = list(project_path.rglob("*.kt"))
        all_functions = {}
        all_classes = {}
        all_calls = []
        
        for kt_file in kotlin_files:
            if any(skip in str(kt_file) for skip in ['/build/', '/.gradle/', '/test/']):
                continue
            
            analysis = self.analyze_kotlin_file(kt_file, project_name)
            
            # Store functions with their file context
            for func in analysis['functions']:
                func_key = f"{analysis['package']}.{func['name']}"
                func['package'] = analysis['package']
                func['file'] = str(kt_file.relative_to(project_path))
                all_functions[func_key] = func
            
            # Store classes
            for cls in analysis['classes']:
                cls_key = f"{analysis['package']}.{cls['name']}"
                cls['package'] = analysis['package']
                cls['file'] = str(kt_file.relative_to(project_path))
                all_classes[cls_key] = cls
            
            # Store calls with context
            for call in analysis['calls']:
                call['file'] = str(kt_file.relative_to(project_path))
                call['package'] = analysis['package']
                all_calls.append(call)
        
        # Create nodes and relationships
        stats = self._create_graph_elements(project_name, all_functions, all_classes, all_calls)
        
        print(f"[KOTLIN] Enhanced analysis complete: {stats}")
        return stats
    
    def _create_graph_elements(self, project_name: str, functions: Dict, 
                              classes: Dict, calls: List) -> Dict:
        """Create graph nodes and relationships."""
        # Create function nodes
        for func_key, func_info in functions.items():
            func_node = Node(
                "KotlinFunction",
                name=func_key,
                short_name=func_info['name'],
                return_type=func_info.get('return_type', 'Unit'),
                type=func_info.get('type', 'function'),
                file=func_info['file'],
                package=func_info['package'],
                project=project_name
            )
            self.graph.create(func_node)
        
        # Create class nodes
        for cls_key, cls_info in classes.items():
            cls_node = Node(
                "KotlinClass",
                name=cls_key,
                short_name=cls_info['name'],
                type=cls_info['type'],
                inheritance=cls_info.get('inheritance', ''),
                file=cls_info['file'],
                package=cls_info['package'],
                project=project_name
            )
            self.graph.create(cls_node)
        
        # Create call relationships
        call_count = 0
        for call in calls:
            # Try to resolve the callee
            callee_name = call['callee']
            possible_callees = [
                f"{call['package']}.{callee_name}",  # Same package
                callee_name,  # Simple name
            ]
            
            # Find matching function node
            for possible_callee in possible_callees:
                callee_node = self.graph.nodes.match(
                    "KotlinFunction",
                    project=project_name
                ).where(f"_.name = '{possible_callee}' OR _.short_name = '{callee_name}'").first()
                
                if callee_node:
                    # Create CALLS relationship
                    # For now, create from file to function
                    # In a more advanced version, we'd track the calling function
                    rel = Relationship(
                        Node("CallSite", file=call['file'], project=project_name),
                        "CALLS",
                        callee_node,
                        call_type=call['type']
                    )
                    self.graph.create(rel)
                    call_count += 1
                    break
        
        return {
            'functions': len(functions),
            'classes': len(classes),
            'calls': call_count,
            'total_call_sites': len(calls)
        }


def test_enhanced_analyzer():
    """Test the enhanced Kotlin analyzer."""
    analyzer = EnhancedKotlinAnalyzer()
    
    # Test with sample Kotlin code
    sample_code = '''
    package com.example.spice
    
    import io.github.spice.api.*
    
    class MyAgent : BaseAgent() {
        override fun process(message: String): String {
            val result = analyzeMessage(message)
            return formatResponse(result)
        }
        
        private fun analyzeMessage(msg: String): Analysis {
            val tokens = msg.split(" ")
            return Analysis(tokens.size)
        }
        
        fun formatResponse(analysis: Analysis): String {
            return "Processed ${analysis.count} tokens"
        }
    }
    
    fun main() {
        val agent = MyAgent()
        agent.process("Hello world")
    }
    '''
    
    # Analyze sample
    from pathlib import Path
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.kt', delete=False) as f:
        f.write(sample_code)
        temp_path = Path(f.name)
    
    result = analyzer.analyze_kotlin_file(temp_path, "test-project")
    
    print("Analysis Result:")
    print(f"Functions found: {len(result['functions'])}")
    print(f"Classes found: {len(result['classes'])}")
    print(f"Function calls found: {len(result['calls'])}")
    
    # Clean up
    temp_path.unlink()
    
    return result


if __name__ == "__main__":
    test_enhanced_analyzer()