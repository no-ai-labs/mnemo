"""Kotlin project analyzer for building knowledge graphs."""

import os
import re
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from datetime import datetime
from py2neo import Graph, Node, Relationship

from mnemo.memory.client import MnemoMemoryClient


class KotlinAnalyzer:
    """Analyze Kotlin projects and build knowledge graphs."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
    def analyze_kotlin_project(self, project_path: str, project_name: str) -> Dict:
        """Analyze a Kotlin project and build knowledge graph."""
        print(f"[KOTLIN] Analyzing Kotlin project: {project_name}")
        
        start_time = datetime.now()
        project_path = Path(project_path)
        
        # Clear existing data for this project
        self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                      project=project_name)
        
        # Create project node
        project_node = Node(
            "KotlinProject",
            name=project_name,
            path=str(project_path),
            language="kotlin",
            analyzed_at=start_time.isoformat()
        )
        self.graph.merge(project_node, "KotlinProject", "name")
        
        # Analyze different aspects
        files_analyzed = self._analyze_kotlin_files(project_path, project_name)
        modules_found = self._analyze_gradle_structure(project_path, project_name)
        agents_found = self._analyze_agent_system(project_path, project_name)
        concepts_extracted = self._extract_spice_concepts(project_path, project_name)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        stats = {
            'files': files_analyzed,
            'modules': modules_found,
            'agents': agents_found,
            'concepts': concepts_extracted,
            'duration': duration
        }
        
        print(f"[KOTLIN] Analysis complete: {stats}")
        return stats
        
    def _analyze_kotlin_files(self, project_path: Path, project_name: str) -> int:
        """Analyze Kotlin source files with enhanced patterns."""
        kotlin_files = list(project_path.rglob("*.kt"))
        total_functions = 0
        total_calls = 0
        
        for kt_file in kotlin_files:
            # Skip build and gradle files
            if any(skip in str(kt_file) for skip in ['/build/', '/.gradle/', '/gradlew', '/test/', '/generated/']):
                continue
                
            relative_path = kt_file.relative_to(project_path)
            content = kt_file.read_text(encoding='utf-8', errors='ignore')
            
            # Remove comments to avoid false positives
            content = self._remove_comments(content)
            
            # Extract package
            package_match = re.search(r'package\s+([\w.]+)', content)
            package_name = package_match.group(1) if package_match else "default"
            
            # Extract imports
            imports = re.findall(r'import\s+([\w.*]+)', content)
            
            # Enhanced class/interface/object extraction
            class_info = self._extract_classes(content)
            
            # Enhanced function extraction
            function_info = self._extract_functions(content, package_name, relative_path)
            
            # Extract function calls
            call_info = self._extract_function_calls(content, package_name, relative_path)
            
            total_functions += len(function_info)
            total_calls += len(call_info)
            
            # Create file node
            file_node = Node(
                "KotlinFile",
                name=kt_file.name,
                path=str(relative_path),
                package=package_name,
                project=project_name,
                classes=len(class_info),
                functions=len(function_info)
            )
            self.graph.create(file_node)
            
            # Create package node
            package_node = Node(
                "Package",
                name=package_name,
                project=project_name
            )
            self.graph.merge(package_node, "Package", "name")
            self.graph.create(Relationship(file_node, "IN_PACKAGE", package_node))
            
            # Create class nodes with enhanced info
            for cls in class_info:
                class_node = Node(
                    "KotlinClass",
                    name=cls['name'],
                    full_name=f"{package_name}.{cls['name']}",
                    file=str(relative_path),
                    package=package_name,
                    type=cls['type'],
                    inheritance=cls.get('inheritance', ''),
                    project=project_name
                )
                self.graph.create(class_node)
                self.graph.create(Relationship(class_node, "DEFINED_IN", file_node))
            
            # Create function nodes
            for func in function_info:
                func_node = Node(
                    "KotlinFunction",
                    name=func['name'],
                    full_name=func['full_name'],
                    file=str(relative_path),
                    package=package_name,
                    return_type=func.get('return_type', 'Unit'),
                    type=func.get('type', 'function'),
                    class_name=func.get('class_name'),
                    project=project_name
                )
                self.graph.create(func_node)
                self.graph.create(Relationship(func_node, "DEFINED_IN", file_node))
            
            # Create call relationships
            for call in call_info:
                # Try to find the target function
                target_func = self._resolve_function_call(call, package_name, imports, project_name)
                if target_func:
                    caller_func = self._find_containing_function(call['line'], function_info)
                    if caller_func:
                        caller_node = self.graph.nodes.match(
                            "KotlinFunction",
                            full_name=caller_func['full_name'],
                            project=project_name
                        ).first()
                        
                        if caller_node:
                            self.graph.create(Relationship(
                                caller_node,
                                "CALLS",
                                target_func,
                                call_type=call['type']
                            ))
                
            # Track imports
            for imp in imports:
                if imp.startswith('io.github.spice') or imp.startswith('io.github.noailabs'):
                    import_node = Node(
                        "Import",
                        name=imp,
                        project=project_name
                    )
                    self.graph.merge(import_node, "Import", "name")
                    self.graph.create(Relationship(file_node, "IMPORTS", import_node))
                    
        print(f"[KOTLIN] Analyzed {len(kotlin_files)} files, found {total_functions} functions and {total_calls} calls")
        return len(kotlin_files)
    
    def _remove_comments(self, content: str) -> str:
        """Remove single-line and multi-line comments."""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content
    
    def _extract_classes(self, content: str) -> List[Dict]:
        """Extract classes with enhanced patterns."""
        class_pattern = r'(?:(?:public|private|internal|protected|open|sealed|data|abstract|inner)?\s+)*(?:class|interface|object|enum\s+class)\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*([^{]+))?'
        classes = []
        
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            inheritance = match.group(2).strip() if match.group(2) else ""
            class_type = 'class'
            if 'interface' in match.group(0):
                class_type = 'interface'
            elif 'object' in match.group(0):
                class_type = 'object'
            elif 'enum' in match.group(0):
                class_type = 'enum'
                
            classes.append({
                'name': class_name,
                'inheritance': inheritance,
                'type': class_type
            })
        
        return classes
    
    def _extract_functions(self, content: str, package: str, file_path) -> List[Dict]:
        """Extract functions with enhanced patterns."""
        functions = []
        lines = content.split('\n')
        
        # Pattern for regular and extension functions
        func_pattern = r'(?:(?:public|private|internal|protected|open|override|suspend|inline|tailrec)?\s+)*fun\s+(?:<[^>]+>\s+)?(?:([^\s.]+)\.)?([\w]+)\s*\([^)]*\)(?:\s*:\s*([^\s{]+))?'
        
        # Find the class context for each function
        class_context = self._build_class_context(content)
        
        for i, line in enumerate(lines):
            match = re.search(func_pattern, line)
            if match:
                receiver = match.group(1)
                func_name = match.group(2)
                return_type = match.group(3) or 'Unit'
                
                # Determine if this function is inside a class
                containing_class = self._find_containing_class(i, class_context)
                
                if receiver:  # Extension function
                    full_name = f"{package}.{receiver}.{func_name}"
                    func_type = 'extension'
                elif containing_class:
                    full_name = f"{package}.{containing_class}.{func_name}"
                    func_type = 'method'
                else:
                    full_name = f"{package}.{func_name}"
                    func_type = 'function'
                
                functions.append({
                    'name': func_name,
                    'full_name': full_name,
                    'return_type': return_type,
                    'type': func_type,
                    'class_name': containing_class,
                    'receiver': receiver,
                    'line': i + 1
                })
        
        return functions
    
    def _extract_function_calls(self, content: str, package: str, file_path) -> List[Dict]:
        """Extract function calls with context."""
        calls = []
        lines = content.split('\n')
        
        # Various call patterns
        patterns = [
            # Regular function calls: functionName(...)
            (r'(?<!fun\s)(?<!override\s)(?<!\.)(\w+)\s*\(', 'function_call'),
            # Method calls: object.method(...)
            (r'(\w+)\.(\w+)\s*\(', 'method_call'),
            # Constructor calls: ClassName(...)
            (r'\b([A-Z]\w*)\s*\(', 'constructor_call'),
            # Safe calls: object?.method(...)
            (r'(\w+)\?\.(\w+)\s*\(', 'safe_call'),
            # Scope functions: let, run, apply, also, with
            (r'\.(let|run|apply|also|with)\s*\{', 'scope_function'),
        ]
        
        for i, line in enumerate(lines):
            for pattern, call_type in patterns:
                for match in re.finditer(pattern, line):
                    if call_type in ['method_call', 'safe_call']:
                        calls.append({
                            'caller': match.group(1),
                            'callee': match.group(2),
                            'type': call_type,
                            'line': i + 1
                        })
                    else:
                        calls.append({
                            'callee': match.group(1),
                            'type': call_type,
                            'line': i + 1
                        })
        
        return calls
    
    def _build_class_context(self, content: str) -> List[Tuple[int, int, str]]:
        """Build a map of class boundaries in the file."""
        lines = content.split('\n')
        class_stack = []
        class_boundaries = []
        
        class_start_pattern = r'(?:class|interface|object)\s+(\w+)'
        
        brace_count = 0
        current_class = None
        class_start_line = 0
        
        for i, line in enumerate(lines):
            # Check for class start
            match = re.search(class_start_pattern, line)
            if match and '{' in line:
                current_class = match.group(1)
                class_start_line = i
                brace_count = 1
                continue
            
            if current_class:
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0:
                    class_boundaries.append((class_start_line, i, current_class))
                    current_class = None
        
        return class_boundaries
    
    def _find_containing_class(self, line_num: int, class_boundaries: List[Tuple[int, int, str]]) -> Optional[str]:
        """Find which class contains a given line number."""
        for start, end, class_name in class_boundaries:
            if start <= line_num <= end:
                return class_name
        return None
    
    def _find_containing_function(self, line_num: int, functions: List[Dict]) -> Optional[Dict]:
        """Find which function contains a given line number."""
        # Simple heuristic: find the closest function above the line
        closest_func = None
        closest_distance = float('inf')
        
        for func in functions:
            func_line = func.get('line', 0)
            if func_line < line_num:
                distance = line_num - func_line
                if distance < closest_distance:
                    closest_distance = distance
                    closest_func = func
        
        # Only return if reasonably close (within 50 lines)
        if closest_func and closest_distance < 50:
            return closest_func
        return None
    
    def _resolve_function_call(self, call: Dict, current_package: str, imports: List[str], project_name: str) -> Optional:
        """Try to resolve a function call to its definition."""
        callee = call['callee']
        
        # Try to find in current package
        possible_targets = [
            f"{current_package}.{callee}",
            callee
        ]
        
        # Check imports
        for imp in imports:
            if imp.endswith(f'.{callee}'):
                possible_targets.insert(0, imp)
            elif imp.endswith('*'):
                base = imp[:-1]  # Remove the *
                possible_targets.append(f"{base}{callee}")
        
        # Try to find the function node
        for target in possible_targets:
            func_node = self.graph.nodes.match(
                "KotlinFunction",
                project=project_name
            ).where(f"_.full_name = '{target}' OR _.name = '{callee}'").first()
            
            if func_node:
                return func_node
        
        return None
        
    def _analyze_gradle_structure(self, project_path: Path, project_name: str) -> int:
        """Analyze Gradle module structure."""
        modules = []
        
        # Find all build.gradle.kts files
        gradle_files = list(project_path.rglob("build.gradle.kts"))
        
        for gradle_file in gradle_files:
            if gradle_file.parent == project_path:
                continue  # Skip root build file
                
            module_name = gradle_file.parent.name
            modules.append(module_name)
            
            # Create module node
            module_node = Node(
                "Module",
                name=module_name,
                path=str(gradle_file.parent.relative_to(project_path)),
                project=project_name
            )
            self.graph.create(module_node)
            
            # Analyze dependencies
            content = gradle_file.read_text(encoding='utf-8', errors='ignore')
            deps = re.findall(r'implementation\("([^"]+)"\)', content)
            
            for dep in deps:
                if 'spice' in dep or module_name in dep:
                    dep_node = Node(
                        "Dependency",
                        name=dep,
                        project=project_name
                    )
                    self.graph.merge(dep_node, "Dependency", "name")
                    self.graph.create(Relationship(module_node, "DEPENDS_ON", dep_node))
                    
        return len(modules)
        
    def _analyze_agent_system(self, project_path: Path, project_name: str) -> int:
        """Analyze Spice agent system components."""
        agents_found = 0
        
        # Find agent-related files
        for kt_file in project_path.rglob("*.kt"):
            if any(skip in str(kt_file) for skip in ['/build/', '/.gradle/']):
                continue
                
            content = kt_file.read_text(encoding='utf-8', errors='ignore')
            
            # Find agent definitions
            agent_matches = re.findall(
                r'(?:buildAgent|buildOpenAIAgent|buildClaudeAgent)\s*\{([^}]+)\}', 
                content, 
                re.DOTALL
            )
            
            for agent_def in agent_matches:
                # Extract agent properties
                id_match = re.search(r'id\s*=\s*"([^"]+)"', agent_def)
                name_match = re.search(r'name\s*=\s*"([^"]+)"', agent_def)
                
                if id_match:
                    agent_id = id_match.group(1)
                    agent_name = name_match.group(1) if name_match else agent_id
                    
                    agent_node = Node(
                        "SpiceAgent",
                        id=agent_id,
                        name=agent_name,
                        file=kt_file.name,
                        project=project_name
                    )
                    self.graph.create(agent_node)
                    agents_found += 1
                    
            # Find tool definitions
            tool_matches = re.findall(r'tool\("([^"]+)"\)\s*\{', content)
            for tool_name in tool_matches:
                tool_node = Node(
                    "SpiceTool",
                    name=tool_name,
                    file=kt_file.name,
                    project=project_name
                )
                self.graph.create(tool_node)
                
        return agents_found
        
    def _extract_spice_concepts(self, project_path: Path, project_name: str) -> int:
        """Extract Spice framework concepts and patterns."""
        concepts = {
            'Agent': 'Base interface for all intelligent agents',
            'Comm': 'Universal communication unit',
            'Tool': 'Reusable functions agents can execute',
            'Registry': 'Generic thread-safe component registry',
            'SmartCore': 'Next-generation agent system',
            'CommHub': 'Central message routing system',
            'Flow': 'Multi-agent workflow orchestration',
            'VectorStore': 'Vector database integration',
            'SwarmStrategy': 'Multi-agent coordination strategies'
        }
        
        # Create concept nodes
        for concept, description in concepts.items():
            concept_node = Node(
                "SpiceConcept",
                name=concept,
                description=description,
                project=project_name
            )
            self.graph.create(concept_node)
            
        # Find implementations of these concepts
        for kt_file in project_path.rglob("*.kt"):
            if any(skip in str(kt_file) for skip in ['/build/', '/.gradle/']):
                continue
                
            content = kt_file.read_text(encoding='utf-8', errors='ignore')
            
            for concept in concepts:
                # Find classes implementing/extending concepts
                impl_pattern = f'(?:class|interface|object)\\s+(\\w+).*(?::\\s*{concept}|implements\\s+{concept})'
                implementations = re.findall(impl_pattern, content)
                
                for impl_name in implementations:
                    impl_node = Node(
                        "Implementation",
                        name=impl_name,
                        concept=concept,
                        file=kt_file.name,
                        project=project_name
                    )
                    self.graph.create(impl_node)
                    
                    # Link to concept
                    concept_node = self.graph.nodes.match(
                        "SpiceConcept", 
                        name=concept,
                        project=project_name
                    ).first()
                    
                    if concept_node:
                        self.graph.create(
                            Relationship(impl_node, "IMPLEMENTS", concept_node)
                        )
                        
        return len(concepts)
        
    def generate_insights(self, project_name: str) -> Dict:
        """Generate insights from the Kotlin project graph."""
        insights = {}
        
        # Core statistics
        stats = self.graph.run("""
            MATCH (f:KotlinFile {project: $project})
            MATCH (c:KotlinClass {project: $project})
            MATCH (m:Module {project: $project})
            MATCH (a:SpiceAgent {project: $project})
            RETURN 
                count(DISTINCT f) as files,
                count(DISTINCT c) as classes,
                count(DISTINCT m) as modules,
                count(DISTINCT a) as agents
        """, project=project_name).data()[0]
        
        insights['statistics'] = stats
        
        # Package structure
        packages = self.graph.run("""
            MATCH (p:Package {project: $project})<-[:IN_PACKAGE]-(f:KotlinFile)
            RETURN p.name as package, count(f) as files
            ORDER BY files DESC
            LIMIT 10
        """, project=project_name).data()
        
        insights['main_packages'] = packages
        
        # Module dependencies
        module_deps = self.graph.run("""
            MATCH (m:Module {project: $project})-[:DEPENDS_ON]->(d:Dependency)
            WHERE d.name CONTAINS 'spice'
            RETURN m.name as module, collect(d.name) as dependencies
        """, project=project_name).data()
        
        insights['module_dependencies'] = module_deps
        
        # Spice concepts usage
        concept_usage = self.graph.run("""
            MATCH (i:Implementation {project: $project})-[:IMPLEMENTS]->(c:SpiceConcept)
            RETURN c.name as concept, count(i) as implementations
            ORDER BY implementations DESC
        """, project=project_name).data()
        
        insights['concept_implementations'] = concept_usage
        
        return insights


def analyze_spice_project():
    """Analyze the Spice framework."""
    analyzer = KotlinAnalyzer()
    
    print("=== Spice Framework Analysis ===\n")
    
    # Analyze the project
    stats = analyzer.analyze_kotlin_project("/tmp/spice", "spice-framework")
    
    # Generate insights
    insights = analyzer.generate_insights("spice-framework")
    
    print("\n=== Insights ===")
    print(f"\nCore Statistics: {insights['statistics']}")
    
    print("\nMain Packages:")
    for pkg in insights['main_packages'][:5]:
        print(f"  - {pkg['package']}: {pkg['files']} files")
        
    print("\nModule Dependencies:")
    for mod in insights['module_dependencies']:
        print(f"  - {mod['module']}: {len(mod['dependencies'])} Spice dependencies")
        
    print("\nConcept Implementations:")
    for concept in insights['concept_implementations']:
        print(f"  - {concept['concept']}: {concept['implementations']} implementations")
        
    return stats, insights


if __name__ == "__main__":
    analyze_spice_project()