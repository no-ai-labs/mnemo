"""Batch analyzer for handling large projects without timeout."""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from mnemo.memory.client import MnemoMemoryClient


class BatchProjectAnalyzer:
    """Analyze large projects in batches to avoid timeouts."""
    
    def __init__(self, memory_client: Optional[MnemoMemoryClient] = None):
        self.memory_client = memory_client
        self.batch_size = 50  # Files per batch
        self.progress_callback = None
        
    async def analyze_project_async(
        self, 
        project_path: str, 
        project_name: str,
        language: str = "python",
        progress_callback=None
    ) -> Dict[str, Any]:
        """Analyze project in batches with progress reporting."""
        self.progress_callback = progress_callback
        
        start_time = datetime.now()
        project_path = Path(project_path)
        
        # Collect all files to analyze
        files = self._collect_files(project_path, language)
        total_files = len(files)
        
        print(f"[BATCH] Found {total_files} files to analyze")
        
        # Process in batches
        results = {
            'files': 0,
            'functions': 0,
            'classes': 0,
            'calls': 0,
            'errors': [],
            'batches_processed': 0
        }
        
        for i in range(0, total_files, self.batch_size):
            batch = files[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            # Report progress
            progress = (i / total_files) * 100
            await self._report_progress(
                f"Processing batch {batch_num} ({i}/{total_files} files)",
                progress
            )
            
            # Process batch
            try:
                batch_result = await self._process_batch(
                    batch, project_name, language
                )
                
                # Aggregate results
                results['files'] += batch_result.get('files', 0)
                results['functions'] += batch_result.get('functions', 0)
                results['classes'] += batch_result.get('classes', 0)
                results['calls'] += batch_result.get('calls', 0)
                results['batches_processed'] += 1
                
                # Save intermediate results to memory
                if self.memory_client and i % (self.batch_size * 5) == 0:
                    await self._save_intermediate_results(
                        project_name, results, progress
                    )
                    
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                results['errors'].append({
                    'batch': batch_num,
                    'error': str(e)
                })
                print(f"[BATCH] Error in batch {batch_num}: {e}")
        
        # Final results
        duration = (datetime.now() - start_time).total_seconds()
        results['duration'] = duration
        results['total_files'] = total_files
        
        # Save final results
        if self.memory_client:
            await self._save_final_results(project_name, results)
        
        await self._report_progress("Analysis complete!", 100)
        
        return results
    
    def _collect_files(self, project_path: Path, language: str) -> List[Path]:
        """Collect all files to analyze based on language."""
        extensions = {
            'python': ['.py'],
            'kotlin': ['.kt', '.kts'],
            'javascript': ['.js', '.jsx'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java']
        }
        
        file_extensions = extensions.get(language, ['.py'])
        files = []
        
        # Skip common directories
        skip_dirs = {
            'node_modules', 'venv', 'env', '.git', '__pycache__',
            'build', 'dist', 'target', '.gradle', '.idea'
        }
        
        for root, dirs, filenames in os.walk(project_path):
            # Remove skip directories from dirs to prevent walking into them
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for filename in filenames:
                if any(filename.endswith(ext) for ext in file_extensions):
                    files.append(Path(root) / filename)
        
        return files
    
    async def _process_batch(
        self, 
        files: List[Path], 
        project_name: str,
        language: str
    ) -> Dict[str, Any]:
        """Process a batch of files."""
        result = {
            'files': len(files),
            'functions': 0,
            'classes': 0,
            'calls': 0
        }
        
        if language == "kotlin":
            # Use regex for Kotlin analysis
            import re
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Count functions and classes using regex
                    function_pattern = r'(?:fun|suspend fun)\s+(\w+)\s*\('
                    class_pattern = r'(?:class|interface|object|data class|sealed class)\s+(\w+)'
                    
                    functions = re.findall(function_pattern, content)
                    classes = re.findall(class_pattern, content)
                    
                    result['functions'] += len(functions)
                    result['classes'] += len(classes)
                    
                except Exception as e:
                    print(f"[BATCH] Error processing {file_path}: {e}")
                    
        elif language == "python":
            # Use AST for Python analysis
            import ast
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            result['functions'] += 1
                        elif isinstance(node, ast.ClassDef):
                            result['classes'] += 1
                        elif isinstance(node, ast.Call):
                            result['calls'] += 1
                            
                except Exception as e:
                    print(f"[BATCH] Error processing {file_path}: {e}")
        
        return result
    
    async def _report_progress(self, message: str, percentage: float):
        """Report progress to callback or console."""
        if self.progress_callback:
            # Check if callback is async
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(message, percentage)
            else:
                self.progress_callback(message, percentage)
        else:
            print(f"[BATCH] {message} ({percentage:.1f}%)")
    
    async def _save_intermediate_results(
        self, 
        project_name: str, 
        results: Dict,
        progress: float
    ):
        """Save intermediate results to memory."""
        if not self.memory_client:
            return
            
        self.memory_client.remember(
            key=f"project_analysis_{project_name}_progress",
            content=json.dumps({
                'progress': progress,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }),
            memory_type="fact",
            tags={project_name, "analysis-progress"}
        )
    
    async def _save_final_results(
        self, 
        project_name: str, 
        results: Dict
    ):
        """Save final analysis results."""
        if not self.memory_client:
            return
            
        self.memory_client.remember(
            key=f"project_analysis_{project_name}",
            content=f"Analyzed {project_name}: {results['functions']} functions, "
                   f"{results['classes']} classes, {results['files']} files in "
                   f"{results['duration']:.2f}s",
            memory_type="fact",
            tags={project_name, "project-analysis", "complete"}
        )
        
        # Also save detailed results
        self.memory_client.remember(
            key=f"project_analysis_{project_name}_details",
            content=json.dumps(results),
            memory_type="fact",
            tags={project_name, "analysis-details"}
        )