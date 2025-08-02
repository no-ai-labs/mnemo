"""JavaScript/TypeScript project analyzer for building knowledge graphs."""

import os
import re
import json
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from datetime import datetime
from py2neo import Graph, Node, Relationship


class JSTypeScriptAnalyzer:
    """Analyze JavaScript/TypeScript projects and build knowledge graphs."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
    def analyze_frontend_project(self, project_path: str, project_name: str) -> Dict:
        """Analyze a JavaScript/TypeScript frontend project."""
        print(f"[JS/TS] Analyzing frontend project: {project_name}")
        
        start_time = datetime.now()
        project_path = Path(project_path)
        
        # Clear existing data for this project
        self.graph.run("MATCH (n {project: $project}) DETACH DELETE n", 
                      project=project_name)
        
        # Create project node
        project_node = Node(
            "FrontendProject",
            name=project_name,
            path=str(project_path),
            analyzed_at=start_time.isoformat()
        )
        self.graph.merge(project_node, "FrontendProject", "name")
        
        # Analyze package.json
        framework_info = self._analyze_package_json(project_path, project_name)
        
        # Analyze different aspects
        files_analyzed = self._analyze_js_ts_files(project_path, project_name)
        components_found = self._analyze_vue_components(project_path, project_name)
        stores_found = self._analyze_state_management(project_path, project_name)
        routes_found = self._analyze_routes(project_path, project_name)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        stats = {
            'files': files_analyzed,
            'framework': framework_info.get('framework', 'unknown'),
            'components': components_found,
            'stores': stores_found,
            'routes': routes_found,
            'duration': duration
        }
        
        print(f"[JS/TS] Analysis complete: {stats}")
        return stats
        
    def _analyze_package_json(self, project_path: Path, project_name: str) -> Dict:
        """Analyze package.json for dependencies and framework info."""
        package_json_path = project_path / "package.json"
        framework_info = {}
        
        if package_json_path.exists():
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                
            # Detect framework
            deps = {**package_data.get('dependencies', {}), 
                   **package_data.get('devDependencies', {})}
            
            if 'vue' in deps:
                framework_info['framework'] = 'Vue'
                framework_info['version'] = deps.get('vue', 'unknown')
            elif 'react' in deps:
                framework_info['framework'] = 'React'
                framework_info['version'] = deps.get('react', 'unknown')
            elif '@angular/core' in deps:
                framework_info['framework'] = 'Angular'
                framework_info['version'] = deps.get('@angular/core', 'unknown')
                
            # Create framework node
            if 'framework' in framework_info:
                framework_node = Node(
                    "Framework",
                    name=framework_info['framework'],
                    version=framework_info['version'],
                    project=project_name
                )
                self.graph.create(framework_node)
            
            # Analyze key dependencies
            key_deps = {
                'UI Libraries': ['@tiptap/core', 'vuetify', 'element-plus', 'tailwindcss'],
                'State Management': ['vuex', 'pinia', 'redux', 'mobx'],
                'Build Tools': ['vite', 'webpack', 'parcel', 'rollup'],
                'Testing': ['jest', 'vitest', '@testing-library/vue', 'cypress'],
                'Charts': ['chart.js', 'd3', 'echarts'],
                'Flow/Graph': ['vue-flow', '@vue-flow/core', 'react-flow-renderer']
            }
            
            for category, libs in key_deps.items():
                for lib in libs:
                    if lib in deps:
                        dep_node = Node(
                            "Dependency",
                            name=lib,
                            category=category,
                            version=deps[lib],
                            project=project_name
                        )
                        self.graph.create(dep_node)
                        
        return framework_info
        
    def _analyze_js_ts_files(self, project_path: Path, project_name: str) -> int:
        """Analyze JavaScript and TypeScript files."""
        js_files = list(project_path.glob("**/*.js"))
        ts_files = list(project_path.glob("**/*.ts"))
        jsx_files = list(project_path.glob("**/*.jsx"))
        tsx_files = list(project_path.glob("**/*.tsx"))
        js_ts_files = js_files + ts_files + jsx_files + tsx_files
        
        count = 0
        for file_path in js_ts_files:
            # Skip node_modules and build directories
            if any(skip in str(file_path) for skip in ['node_modules', 'dist', 'build', '.next']):
                continue
                
            count += 1
            relative_path = file_path.relative_to(project_path)
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Extract imports
            imports = self._extract_imports(content)
            
            # Extract exports
            exports = self._extract_exports(content)
            
            # Create file node
            file_node = Node(
                "JSFile",
                name=file_path.name,
                path=str(relative_path),
                type=file_path.suffix[1:],  # js, ts, jsx, tsx
                imports_count=len(imports),
                exports_count=len(exports),
                project=project_name
            )
            self.graph.create(file_node)
            
            # Track imports
            for imp in imports:
                if not imp.startswith('.') and not imp.startswith('@/'):
                    # External import
                    import_node = Node(
                        "Import",
                        name=imp,
                        type="external",
                        project=project_name
                    )
                    self.graph.merge(import_node, "Import", "name")
                    self.graph.create(Relationship(file_node, "IMPORTS", import_node))
                    
        return count
        
    def _analyze_vue_components(self, project_path: Path, project_name: str) -> int:
        """Analyze Vue components."""
        vue_files = list(project_path.glob("**/*.vue"))
        component_count = 0
        
        for vue_file in vue_files:
            if 'node_modules' in str(vue_file):
                continue
                
            component_count += 1
            relative_path = vue_file.relative_to(project_path)
            content = vue_file.read_text(encoding='utf-8', errors='ignore')
            
            # Extract component name
            name_match = re.search(r'name:\s*[\'"]([^\'"\s]+)[\'"]', content)
            component_name = name_match.group(1) if name_match else vue_file.stem
            
            # Check for specific patterns
            has_template = '<template>' in content
            has_script = '<script' in content
            has_style = '<style' in content
            uses_composition_api = 'setup()' in content or '<script setup>' in content
            
            # Extract props
            props = re.findall(r'props:\s*\{([^}]+)\}', content, re.DOTALL)
            prop_count = len(re.findall(r'(\w+):\s*\{', props[0])) if props else 0
            
            # Create component node
            component_node = Node(
                "VueComponent",
                name=component_name,
                file=str(relative_path),
                has_template=has_template,
                has_script=has_script,
                has_style=has_style,
                uses_composition_api=uses_composition_api,
                props_count=prop_count,
                project=project_name
            )
            self.graph.create(component_node)
            
            # For Mentat specific nodes
            if 'Block' in component_name or 'Node' in component_name:
                node_type = None
                if 'DataBlock' in component_name:
                    node_type = "DataBlock"
                elif 'PromptBlock' in component_name:
                    node_type = "PromptBlock"
                elif 'AgentBlock' in component_name:
                    node_type = "AgentBlock"
                elif 'ActionNode' in component_name:
                    node_type = "ActionNode"
                elif 'ResultBlock' in component_name:
                    node_type = "ResultBlock"
                    
                if node_type:
                    mentat_node = Node(
                        "MentatNode",
                        type=node_type,
                        component=component_name,
                        project=project_name
                    )
                    self.graph.create(mentat_node)
                    self.graph.create(Relationship(mentat_node, "IMPLEMENTED_BY", component_node))
                    
        return component_count
        
    def _analyze_state_management(self, project_path: Path, project_name: str) -> int:
        """Analyze state management (stores, composables)."""
        store_count = 0
        
        # Look for common store patterns
        store_patterns = [
            "**/stores/**/*.js",
            "**/stores/**/*.ts",
            "**/store/**/*.js",
            "**/store/**/*.ts",
            "**/composables/**/*.js",
            "**/composables/**/*.ts"
        ]
        
        for pattern in store_patterns:
            for store_file in project_path.glob(pattern):
                if 'node_modules' in str(store_file):
                    continue
                    
                store_count += 1
                content = store_file.read_text(encoding='utf-8', errors='ignore')
                
                # Detect store type
                store_type = "unknown"
                if 'defineStore' in content:
                    store_type = "pinia"
                elif 'createStore' in content:
                    store_type = "vuex"
                elif 'useState' in content or 'useReducer' in content:
                    store_type = "react-hooks"
                    
                store_node = Node(
                    "Store",
                    name=store_file.stem,
                    type=store_type,
                    file=str(store_file.relative_to(project_path)),
                    project=project_name
                )
                self.graph.create(store_node)
                
        return store_count
        
    def _analyze_routes(self, project_path: Path, project_name: str) -> int:
        """Analyze routing configuration."""
        route_count = 0
        
        # Look for router files
        router_patterns = [
            "**/router/**/*.js",
            "**/router/**/*.ts",
            "**/routes/**/*.js",
            "**/routes/**/*.ts"
        ]
        
        for pattern in router_patterns:
            for router_file in project_path.glob(pattern):
                if 'node_modules' in str(router_file):
                    continue
                    
                content = router_file.read_text(encoding='utf-8', errors='ignore')
                
                # Extract route definitions
                routes = re.findall(r'path:\s*[\'"]([^\'"\s]+)[\'"]', content)
                
                for route_path in routes:
                    route_count += 1
                    route_node = Node(
                        "Route",
                        path=route_path,
                        file=str(router_file.relative_to(project_path)),
                        project=project_name
                    )
                    self.graph.create(route_node)
                    
        return route_count
        
    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements."""
        imports = []
        
        # ES6 imports
        es6_imports = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"\s]+)[\'"]', content)
        imports.extend(es6_imports)
        
        # CommonJS requires
        cjs_imports = re.findall(r'require\([\'"]([^\'"\s]+)[\'"]\)', content)
        imports.extend(cjs_imports)
        
        return list(set(imports))
        
    def _extract_exports(self, content: str) -> List[str]:
        """Extract export statements."""
        exports = []
        
        # Named exports
        named_exports = re.findall(r'export\s+(?:const|let|var|function|class)\s+(\w+)', content)
        exports.extend(named_exports)
        
        # Default export
        if 'export default' in content:
            exports.append('default')
            
        return list(set(exports))
        
    def generate_frontend_insights(self, project_name: str) -> Dict:
        """Generate insights from frontend project analysis."""
        insights = {}
        
        # Framework and dependencies
        framework = self.graph.run("""
            MATCH (f:Framework {project: $project})
            RETURN f.name as name, f.version as version
        """, project=project_name).data()
        
        if framework:
            insights['framework'] = framework[0]
            
        # Component statistics
        component_stats = self.graph.run("""
            MATCH (c:VueComponent {project: $project})
            RETURN 
                count(c) as total_components,
                sum(CASE WHEN c.uses_composition_api THEN 1 ELSE 0 END) as composition_api_count,
                avg(c.props_count) as avg_props_per_component
        """, project=project_name).data()[0]
        
        insights['components'] = component_stats
        
        # Mentat specific nodes
        mentat_nodes = self.graph.run("""
            MATCH (m:MentatNode {project: $project})
            RETURN m.type as node_type, count(m) as count
            ORDER BY count DESC
        """, project=project_name).data()
        
        insights['mentat_nodes'] = mentat_nodes
        
        # Dependencies by category
        deps_by_category = self.graph.run("""
            MATCH (d:Dependency {project: $project})
            RETURN d.category as category, collect(d.name) as dependencies
            ORDER BY size(dependencies) DESC
        """, project=project_name).data()
        
        insights['dependencies'] = deps_by_category
        
        return insights