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
    
    def _get_codebase_metrics(self, project_name: str) -> Dict:
        """Get codebase size metrics for percentage calculations."""
        total_functions = self.graph.run("""
            MATCH (f:Function {project: $project})
            RETURN count(f) as count
        """, project=project_name).evaluate() or 1
        
        total_classes = self.graph.run("""
            MATCH (c:Class {project: $project})
            RETURN count(c) as count
        """, project=project_name).evaluate() or 1
        
        total_files = self.graph.run("""
            MATCH (f:File {project: $project})
            RETURN count(f) as count
        """, project=project_name).evaluate() or 1
        
        # Calculate codebase size score (functions + classes * 2 + files)
        codebase_size = total_functions + (total_classes * 2) + total_files
        
        return {
            'total_functions': total_functions,
            'total_classes': total_classes,
            'total_files': total_files,
            'codebase_size': codebase_size
        }
        
    def analyze_project_health(self, project_name: str) -> Dict:
        """Comprehensive health check for a project."""
        print(f"[GUARDRAILS] Analyzing project health: {project_name}")
        
        try:
            # Check if this is a Kotlin project by checking Project node language
            project_node = self.graph.nodes.match("Project", name=project_name).first()
            is_kotlin = False
            
            if project_node and project_node.get('language') == 'kotlin':
                is_kotlin = True
            else:
                # Fallback: Check if functions have package but no module
                is_kotlin = self.graph.run("""
                    MATCH (f:Function {project: $project})
                    WHERE f.package IS NOT NULL AND f.module IS NULL
                    RETURN count(f) > 0 as is_kotlin
                """, project=project_name).evaluate()
            
            if is_kotlin:
                print(f"[GUARDRAILS] Detected Kotlin project, using adapted queries")
                return self._analyze_kotlin_project_health(project_name)
            
            results = {
                'duplicates': self.find_duplicate_implementations(project_name),
                'unused_functions': self.find_unused_functions(project_name),
                'strange_patterns': self.detect_strange_patterns(project_name),
                'potential_risks': self.detect_potential_risks(project_name),
                'consistency_issues': self.check_consistency(project_name),
                'complexity_hotspots': self.find_complexity_hotspots(project_name)
            }
            
            # Get codebase metrics for percentage calculations
            metrics = self._get_codebase_metrics(project_name)
            
            # Calculate issue rates (percentages)
            duplicate_rate = (len(results.get('duplicates', [])) / max(metrics['total_functions'], 1)) * 100
            unused_rate = (len(results.get('unused_functions', [])) / max(metrics['total_functions'], 1)) * 100
            
            # Calculate penalty based on rates
            penalty = 0
            
            # Duplicate rate penalty (max 20 points)
            if duplicate_rate > 50:
                penalty += 20
            elif duplicate_rate > 30:
                penalty += 15
            elif duplicate_rate > 15:
                penalty += 10
            elif duplicate_rate > 5:
                penalty += 5
            
            # Unused code rate penalty (max 15 points)
            if unused_rate > 50:
                penalty += 15
            elif unused_rate > 30:
                penalty += 10
            elif unused_rate > 15:
                penalty += 7
            elif unused_rate > 5:
                penalty += 3
            
            # Other issues (scaled by codebase size)
            issue_density = (len(results.get('strange_patterns', [])) + 
                            len(results.get('consistency_issues', [])) + 
                            len(results.get('complexity_hotspots', []))) / max(metrics['codebase_size'] / 100, 1)
            
            if issue_density > 10:
                penalty += 15
            elif issue_density > 5:
                penalty += 10
            elif issue_density > 2:
                penalty += 5
            
            # Critical risks (always high penalty)
            penalty += len(results.get('potential_risks', [])) * 10
            
            # Calculate final score (no negative scores)
            results['health_score'] = max(0, 100 - penalty)
            
            # Add metrics to results
            results['metrics'] = {
                **metrics,
                'duplicate_rate': round(duplicate_rate, 1),
                'unused_rate': round(unused_rate, 1),
                'issue_density': round(issue_density, 1)
            }
            
        except Exception as e:
            print(f"[GUARDRAILS] Error during analysis: {e}")
            results = {
                'health_score': 0,
                'duplicates': [],
                'unused_functions': [],
                'strange_patterns': [],
                'potential_risks': [],
                'consistency_issues': [],
                'complexity_hotspots': [],
                'error': str(e)
            }
        
        return results
        
    def find_duplicate_implementations(self, project_name: str) -> List[Dict]:
        """Find duplicate or similar function implementations."""
        duplicates = []
        
        # Find functions with same name in different modules
        same_name_funcs = self.graph.run("""
            MATCH (f1:Function {project: $project})
            MATCH (f2:Function {project: $project})
            WHERE f1.name = f2.name 
                  AND ((f1.module IS NOT NULL AND f2.module IS NOT NULL AND f1.module <> f2.module)
                       OR (f1.package IS NOT NULL AND f2.package IS NOT NULL AND f1.package <> f2.package)
                       OR (f1.file_path IS NOT NULL AND f2.file_path IS NOT NULL AND f1.file_path <> f2.file_path))
                  AND id(f1) < id(f2)
            RETURN COALESCE(f1.full_name, f1.package + '.' + f1.name, f1.name) as func1,
                   COALESCE(f2.full_name, f2.package + '.' + f2.name, f2.name) as func2, 
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
            RETURN COALESCE(f.full_name, f.package + '.' + f.name, f.name) as function,
                   COALESCE(f.module, f.package, f.file_path, 'unknown') as module,
                   count(callee) as outgoing_calls
            ORDER BY module
        """, project=project_name).data()
        
        for func in dead_code:
            # Check if it's an entry point
            is_entry_point = (
                'main' in func['function'] or
                (func['module'] and 'cli' in func['module']) or
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
    
    def _analyze_kotlin_project_health(self, project_name: str) -> Dict:
        """Kotlin-specific health check for a project."""
        results = {
            'duplicates': [],
            'unused_functions': [],
            'strange_patterns': [],
            'potential_risks': [],
            'consistency_issues': [],
            'complexity_hotspots': []
        }
        
        try:
            # Find duplicate implementations (Kotlin version)
            duplicates = self.graph.run("""
                MATCH (f1:Function {project: $project})
                MATCH (f2:Function {project: $project})
                WHERE f1.name = f2.name 
                      AND f1.package <> f2.package
                      AND id(f1) < id(f2)
                RETURN f1.name as common_name,
                       f1.package + '.' + f1.name as func1,
                       f2.package + '.' + f2.name as func2
                LIMIT 20
            """, project=project_name).data()
            
            for dup in duplicates:
                results['duplicates'].append({
                    'type': 'same_name',
                    'function1': dup['func1'],
                    'function2': dup['func2'],
                    'name': dup['common_name'],
                    'severity': 'medium'
                })
            
            # Find unused functions (Kotlin version)
            unused = self.graph.run("""
                MATCH (f:Function {project: $project})
                WHERE NOT ()-[:CALLS]->(f)
                      AND f.name <> '__init__'
                      AND f.name <> 'main'
                      AND NOT f.name STARTS WITH 'test'
                RETURN f.package + '.' + f.name as function,
                       f.package as package
                LIMIT 50
            """, project=project_name).data()
            
            for func in unused:
                results['unused_functions'].append({
                    'function': func['function'],
                    'module': func['package'],
                    'severity': 'medium'
                })
            
            # Find complexity hotspots (Kotlin version)
            # For now, we'll use file-level complexity since we don't have method-level complexity
            complex_files = self.graph.run("""
                MATCH (f:File {project: $project})
                WHERE f.complexity > 100
                RETURN f.path as file, f.complexity as complexity
                ORDER BY complexity DESC
                LIMIT 10
            """, project=project_name).data()
            
            for file in complex_files:
                results['complexity_hotspots'].append({
                    'location': file['file'],
                    'complexity': file['complexity'],
                    'severity': 'high' if file['complexity'] > 200 else 'medium'
                })
            
            # Detect DSL pattern issues
            dsl_issues = self.graph.run("""
                MATCH (d:DSLBlock {project: $project})
                WITH d.type as dsl_type, count(d) as usage_count
                WHERE usage_count < 3
                RETURN dsl_type, usage_count
            """, project=project_name).data()
            
            for issue in dsl_issues:
                results['strange_patterns'].append({
                    'type': 'underused_dsl',
                    'pattern': issue['dsl_type'],
                    'usage_count': issue['usage_count'],
                    'severity': 'low'
                })
            
        except Exception as e:
            print(f"[GUARDRAILS] Error in Kotlin analysis: {e}")
        
        # Get codebase metrics for percentage calculations
        metrics = self._get_codebase_metrics(project_name)
        
        # Calculate issue rates (percentages)
        duplicate_rate = (len(results['duplicates']) / max(metrics['total_functions'], 1)) * 100
        unused_rate = (len(results['unused_functions']) / max(metrics['total_functions'], 1)) * 100
        
        # Calculate penalty based on rates
        penalty = 0
        
        # Duplicate rate penalty (max 20 points)
        if duplicate_rate > 50:
            penalty += 20
        elif duplicate_rate > 30:
            penalty += 15
        elif duplicate_rate > 15:
            penalty += 10
        elif duplicate_rate > 5:
            penalty += 5
        
        # Unused code rate penalty (max 15 points)
        if unused_rate > 50:
            penalty += 15
        elif unused_rate > 30:
            penalty += 10
        elif unused_rate > 15:
            penalty += 7
        elif unused_rate > 5:
            penalty += 3
        
        # Other issues (scaled by codebase size)
        issue_density = (len(results['strange_patterns']) + 
                        len(results['consistency_issues']) + 
                        len(results['complexity_hotspots'])) / max(metrics['codebase_size'] / 100, 1)
        
        if issue_density > 10:
            penalty += 15
        elif issue_density > 5:
            penalty += 10
        elif issue_density > 2:
            penalty += 5
        
        # Critical risks (always high penalty)
        penalty += len(results['potential_risks']) * 10
        
        # Calculate final score (no negative scores)
        results['health_score'] = max(0, 100 - penalty)
        
        # Add metrics to results
        results['metrics'] = {
            **metrics,
            'duplicate_rate': round(duplicate_rate, 1),
            'unused_rate': round(unused_rate, 1),
            'issue_density': round(issue_density, 1)
        }
        
        # Add health message based on score
        if results['health_score'] < 30:
            results['health_message'] = f"😱 Critical: Major refactoring needed (Score: {results['health_score']})"
        elif results['health_score'] < 50:
            results['health_message'] = f"⚠️ Warning: Several issues need attention (Score: {results['health_score']})"
        elif results['health_score'] < 70:
            results['health_message'] = f"🤔 Fair: Room for improvement (Score: {results['health_score']})"
        elif results['health_score'] < 85:
            results['health_message'] = f"👍 Good: Pretty decent codebase (Score: {results['health_score']})"
        else:
            results['health_message'] = f"🌟 Excellent: Great code quality! (Score: {results['health_score']})"
        
        return results


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