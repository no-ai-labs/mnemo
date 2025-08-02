"""Enhanced code analyzer using Cursor's search capabilities."""

import re
from typing import List, Dict, Tuple, Set
from pathlib import Path
from mnemo.graph.call_graph_builder import CallGraphBuilder, FunctionInfo, CallInfo


class EnhancedCodeAnalyzer:
    """Analyze code using multiple strategies."""
    
    def __init__(self, graph_builder: CallGraphBuilder):
        self.graph_builder = graph_builder
        self.import_map = {}  # module -> imported items
        
    def analyze_imports_in_project(self, project_path: str) -> Dict[str, Dict[str, str]]:
        """Build a map of all imports in the project."""
        imports = {}
        
        for py_file in Path(project_path).rglob("*.py"):
            if '__pycache__' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                file_imports = self._extract_imports(content)
                if file_imports:
                    module = self._path_to_module(py_file, project_path)
                    imports[module] = file_imports
                    
            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")
                
        return imports
        
    def _extract_imports(self, content: str) -> Dict[str, str]:
        """Extract import statements from file content."""
        imports = {}
        
        # Pattern for: from X import Y, Z
        from_import_pattern = re.compile(
            r'from\s+([\w\.]+)\s+import\s+([^#\n]+)'
        )
        
        # Pattern for: import X as Y
        import_pattern = re.compile(
            r'import\s+([\w\.]+)(?:\s+as\s+(\w+))?'
        )
        
        for match in from_import_pattern.finditer(content):
            module = match.group(1)
            items = match.group(2)
            
            # Parse imported items
            for item in items.split(','):
                item = item.strip()
                if ' as ' in item:
                    orig, alias = item.split(' as ')
                    imports[alias.strip()] = f"{module}.{orig.strip()}"
                else:
                    imports[item] = f"{module}.{item}"
                    
        for match in import_pattern.finditer(content):
            module = match.group(1)
            alias = match.group(2)
            if alias:
                imports[alias] = module
            else:
                imports[module] = module
                
        return imports
        
    def _path_to_module(self, file_path: Path, base_dir: str) -> str:
        """Convert file path to module name."""
        relative = file_path.relative_to(base_dir)
        parts = list(relative.parts[:-1]) + [relative.stem]
        return '.'.join(parts)
        
    def find_function_calls_pattern(self, function_name: str, project_path: str) -> List[Tuple[str, int]]:
        """Find where a function is called using pattern matching."""
        calls = []
        pattern = re.compile(rf'\b{function_name}\s*\(')
        
        for py_file in Path(project_path).rglob("*.py"):
            if '__pycache__' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines, 1):
                    if pattern.search(line):
                        module = self._path_to_module(py_file, project_path)
                        calls.append((module, i))
                        
            except Exception:
                pass
                
        return calls
        
    def build_enhanced_call_graph(self, project_path: str, project_name: str):
        """Build enhanced call graph with cross-file analysis."""
        print("[ENHANCED] Building enhanced call graph...")
        
        # First, build basic graph with AST
        self.graph_builder.build_from_directory(project_path, project_name)
        
        # Then enhance with import analysis
        imports = self.analyze_imports_in_project(project_path)
        
        # Add cross-file relationships
        self._add_cross_file_calls(imports, project_name)
        
        print("[ENHANCED] Enhanced graph building complete!")
        
    def _add_cross_file_calls(self, imports: Dict[str, Dict[str, str]], project_name: str):
        """Add cross-file call relationships based on imports."""
        # This is where we would connect imported functions to their definitions
        # For now, just count the imports
        import_count = sum(len(imp) for imp in imports.values())
        print(f"[ENHANCED] Found {import_count} import statements across {len(imports)} files")
        
    def analyze_function_usage(self, function_name: str, project_path: str) -> Dict:
        """Comprehensive analysis of a function's usage."""
        usage = {
            "direct_calls": [],
            "imported_in": [],
            "method_calls": [],
            "dynamic_calls": []
        }
        
        # Find direct calls
        calls = self.find_function_calls_pattern(function_name, project_path)
        usage["direct_calls"] = calls
        
        # Find imports
        for py_file in Path(project_path).rglob("*.py"):
            if '__pycache__' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if f"import {function_name}" in content or f"from .* import .*{function_name}" in content:
                    module = self._path_to_module(py_file, project_path)
                    usage["imported_in"].append(module)
                    
            except Exception:
                pass
                
        return usage


def demonstrate_cursor_search_integration():
    """
    Show how to use Cursor's search tools for call graph building:
    
    1. codebase_search examples:
       - "Where is function X defined?"
       - "Find all functions that handle memory operations"
       - "Where are database connections made?"
       
    2. grep_search patterns:
       - Function calls: r"function_name\s*\("
       - Method calls: r"\.method_name\s*\("
       - Class instantiation: r"ClassName\s*\("
       - Decorators: r"@decorator_name"
       
    3. Combining searches:
       - First use codebase_search to find relevant files
       - Then use grep_search for exact patterns
       - Finally use read_file for AST parsing
    """
    
    print("=== Cursor Search Integration Demo ===")
    print("\n1. Finding function definitions:")
    print('   codebase_search("function definitions in mnemo")')
    
    print("\n2. Finding function calls:")
    print('   grep_search(r"remember\\s*\\(", "*.py")')
    
    print("\n3. Finding imports:")
    print('   grep_search(r"from .* import|import ", "*.py")')
    
    print("\n4. Finding class inheritance:")
    print('   grep_search(r"class \\w+\\(.*\\):", "*.py")')
    
    print("\n5. Finding decorators:")
    print('   grep_search(r"@\\w+", "*.py")')
    

if __name__ == "__main__":
    # Test enhanced analyzer
    from mnemo.graph.call_graph_builder import CallGraphBuilder
    
    builder = CallGraphBuilder()
    analyzer = EnhancedCodeAnalyzer(builder)
    
    # Analyze mnemo project
    analyzer.build_enhanced_call_graph(".", "mnemo")
    
    # Test function usage analysis
    print("\n=== Analyzing remember function usage ===")
    usage = analyzer.analyze_function_usage("remember", ".")
    print(f"Direct calls: {len(usage['direct_calls'])}")
    print(f"Imported in: {len(usage['imported_in'])} files")
    
    # Show demo
    print("\n")
    demonstrate_cursor_search_integration()