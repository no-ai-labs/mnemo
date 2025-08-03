"""Enhanced Kotlin call relationship analyzer."""
import re
from typing import Dict, List, Tuple, Set
from pathlib import Path
from collections import defaultdict

class KotlinCallAnalyzer:
    """Analyzes actual function calls in Kotlin code."""
    
    def __init__(self):
        # Pattern to find function declarations
        self.func_pattern = re.compile(
            r'(?:fun|suspend\s+fun)\s+(\w+)\s*\([^)]*\)[^{]*\{',
            re.MULTILINE | re.DOTALL
        )
        
        # Pattern to find function calls
        self.call_pattern = re.compile(
            r'(\w+)\s*\(',
            re.MULTILINE
        )
        
        # Keywords to skip
        self.keywords = {
            'if', 'when', 'while', 'for', 'try', 'catch', 
            'return', 'throw', 'super', 'this', 'println',
            'print', 'require', 'check', 'assert', 'error'
        }
        
    def analyze_calls(self, file_path: Path) -> Dict[str, List[str]]:
        """Analyze function calls in a single file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Remove comments
            content = re.sub(r'//[^\n]*', '', content)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            
            # Find all function definitions with their body
            functions = {}
            for match in self.func_pattern.finditer(content):
                func_name = match.group(1)
                start = match.end()
                
                # Find matching closing brace
                brace_count = 1
                end = start
                while brace_count > 0 and end < len(content):
                    if content[end] == '{':
                        brace_count += 1
                    elif content[end] == '}':
                        brace_count -= 1
                    end += 1
                
                # Extract function body
                body = content[start:end-1]
                functions[func_name] = body
            
            # Analyze calls in each function
            call_map = defaultdict(list)
            for func_name, body in functions.items():
                # Find all potential function calls
                for call_match in self.call_pattern.finditer(body):
                    called_func = call_match.group(1)
                    
                    # Skip keywords and already recorded calls
                    if (called_func not in self.keywords and 
                        called_func not in call_map[func_name] and
                        called_func != func_name):  # No self-recursion for now
                        call_map[func_name].append(called_func)
            
            return dict(call_map)
            
        except Exception as e:
            print(f"Error analyzing calls in {file_path}: {e}")
            return {}
    
    def analyze_project_calls(self, project_path: str) -> Tuple[Dict[str, List[str]], int]:
        """Analyze all function calls in a project."""
        project_path = Path(project_path)
        kotlin_files = list(project_path.rglob("*.kt"))
        
        # Filter out build directories
        kotlin_files = [f for f in kotlin_files 
                       if not any(skip in str(f) for skip in ['/build/', '/.gradle/', '/test/'])]
        
        all_calls = {}
        total_calls = 0
        
        for kt_file in kotlin_files:
            file_calls = self.analyze_calls(kt_file)
            
            # Add file context to function names
            relative_path = kt_file.relative_to(project_path)
            for func, calls in file_calls.items():
                full_func_name = f"{relative_path}:{func}"
                all_calls[full_func_name] = calls
                total_calls += len(calls)
        
        return all_calls, total_calls