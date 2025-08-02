"""Code Guardrails - Detect vibe coding patterns and potential issues."""

import ast
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from py2neo import Graph, Node, Relationship

from mnemo.memory.client import MnemoMemoryClient


class CodeGuardrails:
    """Detect code quality issues and vibe coding patterns."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j", 
                 password: str = "password123"):
        self.graph = Graph(neo4j_uri, auth=(username, password))
        
    def analyze_project_health(self, project_name: str) -> Dict:
        """Comprehensive health check for a project."""
        print(f"[GUARDRAILS] Analyzing project health: {project_name}")
        
        results = {
            'duplicates': self.find_duplicate_implementations(project_name),
            'unused_functions': self.find_unused_functions(project_name),
            'strange_patterns': self.detect_strange_patterns(project_name),
            'potential_risks': self.detect_potential_risks(project_name),
            'consistency_issues': self.check_consistency(project_name),
            'complexity_hotspots': self.find_complexity_hotspots(project_name)
        }
        
        # Calculate health score
        total_issues = sum(len(v) for v in results.values() if isinstance(v, list))
        results['health_score'] = max(0, 100 - (total_issues * 5))  # -5 points per issue
        
        return results
        
    def find_duplicate_implementations(self, project_name: str) -> List[Dict]:
        """Find duplicate or similar function implementations."""
        duplicates = []
        
        # Find functions with same name in different modules
        same_name_funcs = self.graph.run("""
            MATCH (f1:Function {project: $project})
            MATCH (f2:Function {project: $project})
            WHERE f1.name = f2.name 
                  AND f1.module <> f2.module
                  AND id(f1) < id(f2)
            RETURN f1.full_name as func1, f2.full_name as func2, 
                   f1.name as common_name
            LIMIT 20
        """, project=project_name).data()
        
        for dup in same_name_funcs:
            duplicates.append({
                'type': 'same_name',
                'function1': dup['func1'],
                'function2': dup['func2'],
                'name': dup['common_name'],
                'severity': 'medium'
            })
            
        # Find functions with similar call patterns
        similar_patterns = self.graph.run("""
            MATCH (f1:Function {project: $project})-[:CALLS]->(common)
            MATCH (f2:Function {project: $project})-[:CALLS]->(common)
            WHERE f1.module <> f2.module 
                  AND id(f1) < id(f2)
                  AND f1.name <> f2.name
            WITH f1, f2, count(common) as shared_calls
            WHERE shared_calls > 3
            RETURN f1.full_name as func1, f2.full_name as func2, 
                   shared_calls
            ORDER BY shared_calls DESC
            LIMIT 10
        """, project=project_name).data()
        
        for pattern in similar_patterns:
            duplicates.append({
                'type': 'similar_behavior',
                'function1': pattern['func1'],
                'function2': pattern['func2'],
                'shared_calls': pattern['shared_calls'],
                'severity': 'low'
            })
            
        return duplicates
        
    def find_unused_functions(self, project_name: str) -> List[Dict]:
        """Find functions that are never called."""
        unused = []
        
        # Functions with no incoming calls
        dead_code = self.graph.run("""
            MATCH (f:Function {project: $project})
            WHERE NOT ()-[:CALLS]->(f)
                  AND f.name <> '__init__'
                  AND f.name <> '__main__'
                  AND NOT f.name STARTS WITH 'test_'
                  AND NOT f.name STARTS WITH '_'
            OPTIONAL MATCH (f)-[:CALLS]->(callee)
            RETURN f.full_name as function, f.module as module,
                   count(callee) as outgoing_calls
            ORDER BY module
        """, project=project_name).data()
        
        for func in dead_code:
            # Check if it's an entry point
            is_entry_point = (
                'main' in func['function'] or
                'cli' in func['module'] or
                'handler' in func['function'].lower() or
                'route' in func['function'].lower()
            )
            
            if not is_entry_point:
                unused.append({
                    'function': func['function'],
                    'module': func['module'],
                    'outgoing_calls': func['outgoing_calls'],
                    'severity': 'high' if func['outgoing_calls'] > 5 else 'medium'
                })
                
        return unused
        
    def detect_strange_patterns(self, project_name: str) -> List[Dict]:
        """Detect unusual coding patterns."""
        strange_patterns = []
        
        # Circular dependencies
        circular = self.graph.run("""
            MATCH (f1:Function {project: $project})-[:CALLS]->(f2:Function {project: $project}),
                  (f2)-[:CALLS]->(f1)
            RETURN f1.full_name as func1, f2.full_name as func2
            LIMIT 10
        """, project=project_name).data()
        
        for circ in circular:
            strange_patterns.append({
                'type': 'circular_dependency',
                'function1': circ['func1'],
                'function2': circ['func2'],
                'severity': 'high'
            })
            
        # Functions with too many dependencies
        high_coupling = self.graph.run("""
            MATCH (f:Function {project: $project})-[:CALLS]->(callee)
            WITH f, count(DISTINCT callee) as dependencies
            WHERE dependencies > 10
            RETURN f.full_name as function, dependencies
            ORDER BY dependencies DESC
            LIMIT 10
        """, project=project_name).data()
        
        for func in high_coupling:
            strange_patterns.append({
                'type': 'high_coupling',
                'function': func['function'],
                'dependencies': func['dependencies'],
                'severity': 'medium'
            })
            
        # God functions (too many incoming calls)
        god_functions = self.graph.run("""
            MATCH (caller)-[:CALLS]->(f:Function {project: $project})
            WITH f, count(DISTINCT caller) as callers
            WHERE callers > 15
            RETURN f.full_name as function, callers
            ORDER BY callers DESC
            LIMIT 5
        """, project=project_name).data()
        
        for func in god_functions:
            strange_patterns.append({
                'type': 'god_function',
                'function': func['function'],
                'callers': func['callers'],
                'severity': 'high'
            })
            
        return strange_patterns
        
    def detect_potential_risks(self, project_name: str) -> List[Dict]:
        """Detect potential security and quality risks."""
        risks = []
        
        # Check for common risky patterns in function names
        risky_patterns = [
            ('eval', 'code_execution'),
            ('exec', 'code_execution'),
            ('__import__', 'dynamic_import'),
            ('pickle', 'serialization'),
            ('shell', 'shell_execution'),
            ('os.system', 'shell_execution'),
            ('subprocess', 'process_execution')
        ]
        
        for pattern, risk_type in risky_patterns:
            risky_funcs = self.graph.run("""
                MATCH (f:Function {project: $project})
                WHERE toLower(f.name) CONTAINS $pattern
                   OR toLower(f.full_name) CONTAINS $pattern
                RETURN f.full_name as function, f.module as module
                LIMIT 10
            """, project=project_name, pattern=pattern).data()
            
            for func in risky_funcs:
                risks.append({
                    'type': risk_type,
                    'function': func['function'],
                    'module': func['module'],
                    'pattern': pattern,
                    'severity': 'high'
                })
                
        # Functions with no error handling (heuristic)
        no_error_handling = self.graph.run("""
            MATCH (f:Function {project: $project})-[:CALLS]->(callee)
            WHERE NOT (f)-[:CALLS]->(:Function {name: 'Exception'})
                  AND NOT (f)-[:CALLS]->(:Function {name: 'try'})
            WITH f, count(callee) as call_count
            WHERE call_count > 5
            RETURN f.full_name as function, call_count
            LIMIT 10
        """, project=project_name).data()
        
        for func in no_error_handling:
            risks.append({
                'type': 'no_error_handling',
                'function': func['function'],
                'call_count': func['call_count'],
                'severity': 'low'
            })
            
        return risks
        
    def check_consistency(self, project_name: str) -> List[Dict]:
        """Check coding style consistency."""
        issues = []
        
        # Check naming conventions
        naming_stats = self.graph.run("""
            MATCH (f:Function {project: $project})
            WITH f.name as fname
            WITH fname,
                 CASE 
                     WHEN fname =~ '[a-z_]+' THEN 'snake_case'
                     WHEN fname =~ '[a-z][a-zA-Z]*' THEN 'camelCase'
                     WHEN fname =~ '[A-Z][a-zA-Z]*' THEN 'PascalCase'
                     ELSE 'mixed'
                 END as style
            RETURN style, count(*) as count
            ORDER BY count DESC
        """, project=project_name).data()
        
        if len(naming_stats) > 1:
            dominant_style = naming_stats[0]['style']
            total_functions = sum(s['count'] for s in naming_stats)
            
            for style_info in naming_stats[1:]:
                if style_info['count'] > 2:  # More than 2 functions
                    issues.append({
                        'type': 'naming_inconsistency',
                        'expected': dominant_style,
                        'found': style_info['style'],
                        'count': style_info['count'],
                        'percentage': round(style_info['count'] / total_functions * 100, 1),
                        'severity': 'low'
                    })
                    
        # Check module organization
        module_sizes = self.graph.run("""
            MATCH (f:Function {project: $project})
            WITH f.module as module, count(f) as function_count
            RETURN module, function_count
            ORDER BY function_count DESC
        """, project=project_name).data()
        
        avg_size = sum(m['function_count'] for m in module_sizes) / len(module_sizes)
        
        for module in module_sizes:
            if module['function_count'] > avg_size * 3:  # 3x larger than average
                issues.append({
                    'type': 'oversized_module',
                    'module': module['module'],
                    'function_count': module['function_count'],
                    'average': round(avg_size, 1),
                    'severity': 'medium'
                })
                
        return issues
        
    def find_complexity_hotspots(self, project_name: str) -> List[Dict]:
        """Find overly complex functions."""
        hotspots = []
        
        # Functions with high cyclomatic complexity (approximated by call count)
        complex_funcs = self.graph.run("""
            MATCH (f:Function {project: $project})-[:CALLS]->(callee)
            WITH f, count(callee) as complexity
            WHERE complexity > 10
            RETURN f.full_name as function, f.module as module, complexity
            ORDER BY complexity DESC
            LIMIT 10
        """, project=project_name).data()
        
        for func in complex_funcs:
            hotspots.append({
                'function': func['function'],
                'module': func['module'],
                'complexity': func['complexity'],
                'severity': 'high' if func['complexity'] > 20 else 'medium'
            })
            
        return hotspots
        
    def generate_report(self, project_name: str) -> str:
        """Generate a comprehensive guardrails report."""
        results = self.analyze_project_health(project_name)
        
        report = f"""
# Code Guardrails Report: {project_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Health Score: {results['health_score']}/100

## Summary
- Duplicate Implementations: {len(results['duplicates'])}
- Unused Functions: {len(results['unused_functions'])}
- Strange Patterns: {len(results['strange_patterns'])}
- Potential Risks: {len(results['potential_risks'])}
- Consistency Issues: {len(results['consistency_issues'])}
- Complexity Hotspots: {len(results['complexity_hotspots'])}

## Detailed Findings

### 1. Duplicate Implementations
"""
        
        for dup in results['duplicates'][:5]:
            report += f"- **{dup['type']}**: {dup.get('function1', '')} vs {dup.get('function2', '')}\n"
            
        if results['unused_functions']:
            report += "\n### 2. Unused Functions (Potential Dead Code)\n"
            for func in results['unused_functions'][:10]:
                report += f"- {func['function']} ({func['severity']})\n"
                
        if results['strange_patterns']:
            report += "\n### 3. Strange Patterns\n"
            for pattern in results['strange_patterns'][:5]:
                report += f"- **{pattern['type']}**: {pattern.get('function', pattern.get('function1', ''))}\n"
                
        if results['potential_risks']:
            report += "\n### 4. Potential Risks\n"
            for risk in results['potential_risks'][:5]:
                report += f"- **{risk['type']}**: {risk['function']} (pattern: {risk.get('pattern', 'N/A')})\n"
                
        report += "\n## Recommendations\n"
        
        if results['health_score'] < 60:
            report += "- ⚠️ **Critical**: Major refactoring needed\n"
        elif results['health_score'] < 80:
            report += "- ⚡ **Moderate**: Address high-severity issues\n"
        else:
            report += "- ✅ **Good**: Minor improvements recommended\n"
            
        return report


def demonstrate_guardrails():
    """Demonstrate code guardrails features."""
    guardrails = CodeGuardrails()
    
    print("=== Code Guardrails Demo ===\n")
    
    # Analyze current project
    print("Analyzing mnemo-updated project...")
    report = guardrails.generate_report("mnemo-updated")
    
    print(report)
    
    # Save report
    with open("guardrails_report.md", "w") as f:
        f.write(report)
    print("\nReport saved to guardrails_report.md")


if __name__ == "__main__":
    demonstrate_guardrails()