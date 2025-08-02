"""Build call graph from codebase and store in Neo4j."""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from py2neo import Graph, Node, Relationship


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    module: str
    file_path: str
    line_number: int
    class_name: Optional[str] = None
    is_method: bool = False
    params: List[str] = None
    
    @property
    def full_name(self) -> str:
        """Get fully qualified name."""
        if self.class_name:
            return f"{self.module}.{self.class_name}.{self.name}"
        return f"{self.module}.{self.name}"


@dataclass
class CallInfo:
    """Information about a function call."""
    caller: str  # Full name of calling function
    callee: str  # Full name of called function
    line_number: int
    call_type: str  # 'direct', 'method', 'import'


class CallGraphVisitor(ast.NodeVisitor):
    """AST visitor to extract function definitions and calls."""
    
    def __init__(self, module_name: str, file_path: str):
        self.module_name = module_name
        self.file_path = file_path
        self.current_class = None
        self.current_function = None
        self.functions: List[FunctionInfo] = []
        self.calls: List[CallInfo] = []
        self.imports: Dict[str, str] = {}  # alias -> full_module_name
        self.class_bases: Dict[str, List[str]] = {}  # class -> base classes
        self.decorators: List[CallInfo] = []
        
    def visit_Import(self, node: ast.Import):
        """Track imports."""
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.imports[asname] = name
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports."""
        module = node.module or ''
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            if module:
                self.imports[asname] = f"{module}.{name}"
            else:
                self.imports[asname] = name
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Enter class definition."""
        old_class = self.current_class
        self.current_class = node.name
        
        # Add the class itself as a "function" node (for graph purposes)
        class_info = FunctionInfo(
            name=node.name,
            module=self.module_name,
            file_path=self.file_path,
            line_number=node.lineno,
            class_name=None,  # Classes don't belong to other classes
            is_method=False,
            params=[]
        )
        self.functions.append(class_info)
        
        # Track base classes (inheritance)
        bases = []
        for base in node.bases:
            base_name = self._extract_callee(base)
            if base_name:
                bases.append(base_name)
                # Add inheritance as a special call
                call_info = CallInfo(
                    caller=f"{self.module_name}.{node.name}",
                    callee=base_name,
                    line_number=node.lineno,
                    call_type='inherits'
                )
                self.calls.append(call_info)
        
        self.class_bases[node.name] = bases
        
        # Process decorators
        for decorator in node.decorator_list:
            dec_name = self._extract_callee(decorator)
            if dec_name:
                call_info = CallInfo(
                    caller=f"{self.module_name}.{node.name}",
                    callee=dec_name,
                    line_number=decorator.lineno,
                    call_type='decorator'
                )
                self.decorators.append(call_info)
        
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function definition."""
        params = [arg.arg for arg in node.args.args]
        
        func_info = FunctionInfo(
            name=node.name,
            module=self.module_name,
            file_path=self.file_path,
            line_number=node.lineno,
            class_name=self.current_class,
            is_method=self.current_class is not None,
            params=params
        )
        self.functions.append(func_info)
        
        # Track current function for calls
        old_function = self.current_function
        self.current_function = func_info.full_name
        
        # Process decorators
        for decorator in node.decorator_list:
            dec_name = self._extract_callee(decorator)
            if dec_name:
                call_info = CallInfo(
                    caller=self.current_function,
                    callee=dec_name,
                    line_number=decorator.lineno,
                    call_type='decorator'
                )
                self.calls.append(call_info)
        
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_Call(self, node: ast.Call):
        """Track function calls."""
        if not self.current_function:
            self.generic_visit(node)
            return
            
        # Extract called function name
        callee = self._extract_callee(node.func)
        
        if callee:
            call_info = CallInfo(
                caller=self.current_function,
                callee=callee,
                line_number=node.lineno,
                call_type='direct'
            )
            self.calls.append(call_info)
            
        self.generic_visit(node)
    
    def visit_ListComp(self, node):
        """Track calls in list comprehensions."""
        self._visit_comprehension(node)
        
    def visit_DictComp(self, node):
        """Track calls in dict comprehensions."""
        self._visit_comprehension(node)
        
    def visit_SetComp(self, node):
        """Track calls in set comprehensions."""
        self._visit_comprehension(node)
        
    def visit_GeneratorExp(self, node):
        """Track calls in generator expressions."""
        self._visit_comprehension(node)
        
    def _visit_comprehension(self, node):
        """Helper to visit comprehensions."""
        self.generic_visit(node)
    
    def visit_With(self, node):
        """Track context manager calls."""
        if self.current_function:
            for item in node.items:
                if isinstance(item.context_expr, ast.Call):
                    callee = self._extract_callee(item.context_expr.func)
                    if callee:
                        call_info = CallInfo(
                            caller=self.current_function,
                            callee=callee,
                            line_number=node.lineno,
                            call_type='context_manager'
                        )
                        self.calls.append(call_info)
        
        self.generic_visit(node)
        
    def _extract_callee(self, node) -> Optional[str]:
        """Extract the name of the called function."""
        if isinstance(node, ast.Name):
            # Simple function call
            name = node.id
            # Check if it's an imported function
            if name in self.imports:
                return self.imports[name]
            return name
            
        elif isinstance(node, ast.Attribute):
            # Method call or module.function
            value = self._extract_callee(node.value)
            if value:
                return f"{value}.{node.attr}"
            return node.attr
            
        elif isinstance(node, ast.Call):
            # Chained calls like func().method()
            return self._extract_callee(node.func)
            
        elif isinstance(node, ast.Subscript):
            # Subscript like dict[key]
            return self._extract_callee(node.value)
            
        return None
    
    def visit_Assign(self, node):
        """Track assignments that might be function references."""
        if self.current_function:
            # Check if we're assigning a function
            if isinstance(node.value, ast.Call):
                callee = self._extract_callee(node.value.func)
                if callee:
                    call_info = CallInfo(
                        caller=self.current_function,
                        callee=callee,
                        line_number=node.lineno,
                        call_type='assignment'
                    )
                    self.calls.append(call_info)
        
        self.generic_visit(node)
    
    def visit_Return(self, node):
        """Track function calls in return statements."""
        if self.current_function and node.value:
            if isinstance(node.value, ast.Call):
                callee = self._extract_callee(node.value.func)
                if callee:
                    call_info = CallInfo(
                        caller=self.current_function,
                        callee=callee,
                        line_number=node.lineno,
                        call_type='return'
                    )
                    self.calls.append(call_info)
        
        self.generic_visit(node)


class CallGraphBuilder:
    """Build and store call graph in Neo4j."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        self.classes = []  # Track classes separately
        
    def build_from_directory(self, directory: str, project_name: str) -> None:
        """Build call graph from a directory of Python files."""
        print(f"[CALL-GRAPH] Building call graph for: {directory}")
        
        # Clear existing data for this project
        self.graph.run(
            "MATCH (n:Function {project: $project}) DETACH DELETE n",
            project=project_name
        )
        
        all_functions = []
        all_calls = []
        
        # Process all Python files
        for py_file in Path(directory).rglob("*.py"):
            if '__pycache__' in str(py_file):
                continue
                
            module_name = self._get_module_name(py_file, directory)
            functions, calls = self._analyze_file(py_file, module_name)
            all_functions.extend(functions)
            all_calls.extend(calls)
            
        print(f"[CALL-GRAPH] Found {len(all_functions)} functions")
        print(f"[CALL-GRAPH] Found {len(all_calls)} calls")
        
        # Store in Neo4j
        self._store_graph(all_functions, all_calls, project_name)
        
    def _get_module_name(self, file_path: Path, base_dir: str) -> str:
        """Get module name from file path."""
        relative = file_path.relative_to(base_dir)
        parts = list(relative.parts[:-1]) + [relative.stem]
        return '.'.join(parts)
        
    def _analyze_file(self, file_path: Path, module_name: str) -> Tuple[List[FunctionInfo], List[CallInfo]]:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(file_path))
            visitor = CallGraphVisitor(module_name, str(file_path))
            visitor.visit(tree)
            
            # Add decorator calls
            visitor.calls.extend(visitor.decorators)
            
            return visitor.functions, visitor.calls
            
        except Exception as e:
            print(f"[CALL-GRAPH] Error analyzing {file_path}: {e}")
            return [], []
            
    def _store_graph(self, functions: List[FunctionInfo], calls: List[CallInfo], project_name: str) -> None:
        """Store the graph in Neo4j."""
        # Create function nodes
        function_nodes = {}
        
        for func in functions:
            # Determine node type
            if func.class_name is None and not func.is_method:
                # This is either a top-level function or a class
                # Check if it's likely a class (capitalized name)
                node_type = 'Class' if func.name and func.name[0].isupper() else 'Function'
            else:
                node_type = 'Method' if func.is_method else 'Function'
            
            node = Node(
                "Function",  # Keep as Function for queries
                name=func.name,
                full_name=func.full_name,
                module=func.module,
                file_path=func.file_path,
                line_number=func.line_number,
                class_name=func.class_name,
                is_method=func.is_method,
                params=func.params or [],
                project=project_name,
                node_type=node_type  # Add this for visualization
            )
            self.graph.create(node)
            function_nodes[func.full_name] = node
            
        # Create call relationships
        relationship_count = 0
        for call in calls:
            if call.caller in function_nodes:
                caller_node = function_nodes[call.caller]
                
                # Try to find the callee with different strategies
                callee_node = None
                
                # 1. Exact match
                if call.callee in function_nodes:
                    callee_node = function_nodes[call.callee]
                else:
                    # 2. Try to find by name in the same module
                    caller_module = call.caller.rsplit('.', 1)[0]
                    potential_callee = f"{caller_module}.{call.callee}"
                    if potential_callee in function_nodes:
                        callee_node = function_nodes[potential_callee]
                    else:
                        # 3. Try to find by short name anywhere in the project
                        for func_name, node in function_nodes.items():
                            if func_name.endswith(f'.{call.callee}') or func_name == call.callee:
                                callee_node = node
                                break
                
                if callee_node:
                    rel = Relationship(
                        caller_node, "CALLS", callee_node,
                        line_number=call.line_number,
                        call_type=call.call_type
                    )
                    self.graph.create(rel)
                    relationship_count += 1
        
        print(f"[CALL-GRAPH] Created {relationship_count} relationships from {len(calls)} calls")
                
        print(f"[CALL-GRAPH] Stored {len(function_nodes)} functions in Neo4j")
        
    def query_dependents(self, function_name: str) -> List[str]:
        """Find all functions that call the given function."""
        result = self.graph.run(
            "MATCH (caller:Function)-[:CALLS]->(callee:Function {full_name: $name}) "
            "RETURN caller.full_name as caller",
            name=function_name
        )
        return [record['caller'] for record in result]
        
    def query_dependencies(self, function_name: str) -> List[str]:
        """Find all functions called by the given function."""
        result = self.graph.run(
            "MATCH (caller:Function {full_name: $name})-[:CALLS]->(callee:Function) "
            "RETURN callee.full_name as callee",
            name=function_name
        )
        return [record['callee'] for record in result]


if __name__ == "__main__":
    # Test with mnemo codebase
    builder = CallGraphBuilder()
    builder.build_from_directory(".", "mnemo")