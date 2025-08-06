"""Debug script for Kotlin analyzer infinite loop issue."""

import os
import sys
import time
import psutil
import threading
from pathlib import Path

# Add mnemo to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mnemo.graph.unified_kotlin_analyzer import UnifiedKotlinAnalyzer
from mnemo.graph.fast_kotlin_analyzer import FastKotlinAnalyzer
from mnemo.graph.complete_kotlin_analyzer import CompleteKotlinAnalyzer


class AnalyzerDebugger:
    def __init__(self):
        self.start_time = time.time()
        self.files_processed = 0
        self.last_file = None
        self.memory_usage = []
        self.monitoring = True
        
    def monitor_resources(self):
        """Monitor CPU and memory usage."""
        process = psutil.Process()
        
        while self.monitoring:
            cpu_percent = process.cpu_percent(interval=1)
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            self.memory_usage.append({
                'time': time.time() - self.start_time,
                'cpu': cpu_percent,
                'memory_mb': memory_mb,
                'files': self.files_processed,
                'current_file': self.last_file
            })
            
            # Print status every 10 seconds
            if len(self.memory_usage) % 10 == 0:
                print(f"\n[{time.time() - self.start_time:.1f}s] Status:")
                print(f"  Files: {self.files_processed}")
                print(f"  CPU: {cpu_percent:.1f}%")
                print(f"  Memory: {memory_mb:.1f} MB")
                print(f"  Current: {self.last_file}")
                
            time.sleep(1)
    
    def analyze_with_monitoring(self, analyzer_class, project_path, project_name):
        """Run analyzer with resource monitoring."""
        print(f"\n{'='*60}")
        print(f"Testing {analyzer_class.__name__}")
        print(f"Project: {project_path}")
        print(f"{'='*60}")
        
        # Count files first
        kotlin_files = list(Path(project_path).rglob("*.kt"))
        # Filter out build directories
        kotlin_files = [f for f in kotlin_files 
                       if not any(skip in str(f) for skip in ['/build/', '/.gradle/', '/test/'])]
        
        print(f"Total Kotlin files: {len(kotlin_files)}")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_resources, daemon=True)
        monitor_thread.start()
        
        try:
            # Patch the analyzer to track progress
            original_analyze_file = None
            analyzer = analyzer_class()
            
            # Try to find and patch the file processing method
            if hasattr(analyzer, '_analyze_file'):
                original_analyze_file = analyzer._analyze_file
                
                def tracked_analyze_file(file_path):
                    self.files_processed += 1
                    self.last_file = str(file_path)
                    return original_analyze_file(file_path)
                
                analyzer._analyze_file = tracked_analyze_file
            
            # Run analysis with timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Analysis timed out!")
            
            # Set timeout to 5 minutes
            if sys.platform != "win32":
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(300)  # 5 minutes
            
            result = analyzer.analyze_project(project_path, project_name, 
                                            depth=1, save_to_neo4j=False)
            
            if sys.platform != "win32":
                signal.alarm(0)  # Cancel alarm
                
            print(f"\n✅ Analysis completed successfully!")
            print(f"   Duration: {time.time() - self.start_time:.1f}s")
            print(f"   Files processed: {self.files_processed}")
            
        except TimeoutError:
            print(f"\n❌ TIMEOUT! Analysis stuck after {time.time() - self.start_time:.1f}s")
            print(f"   Last file: {self.last_file}")
            print(f"   Files processed: {self.files_processed}/{len(kotlin_files)}")
            
        except Exception as e:
            print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
            print(f"   Last file: {self.last_file}")
            print(f"   Files processed: {self.files_processed}")
            import traceback
            traceback.print_exc()
            
        finally:
            self.monitoring = False
            
        # Print memory stats
        if self.memory_usage:
            max_memory = max(m['memory_mb'] for m in self.memory_usage)
            print(f"\n📊 Resource Usage:")
            print(f"   Peak memory: {max_memory:.1f} MB")
            print(f"   Files/second: {self.files_processed / (time.time() - self.start_time):.2f}")


def debug_file_processing(project_path: str):
    """Debug individual file processing."""
    print("\n🔍 Debugging individual file processing...")
    
    kotlin_files = list(Path(project_path).rglob("*.kt"))[:10]  # Just first 10
    
    for idx, kt_file in enumerate(kotlin_files):
        print(f"\n[{idx+1}/10] Processing: {kt_file}")
        start = time.time()
        
        try:
            content = kt_file.read_text(encoding='utf-8', errors='ignore')
            lines = len(content.splitlines())
            
            # Check for problematic patterns
            if "import" in content:
                imports = len([l for l in content.splitlines() if l.strip().startswith("import")])
            else:
                imports = 0
                
            functions = len([l for l in content.splitlines() if "fun " in l])
            
            print(f"   Lines: {lines}, Imports: {imports}, Functions: {functions}")
            print(f"   Time: {time.time() - start:.3f}s")
            
            # Check for circular patterns
            if content.count("companion object") > 5:
                print("   ⚠️  Many companion objects")
            if content.count("inline fun") > 10:
                print("   ⚠️  Many inline functions")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")


def main():
    """Main debug function."""
    if len(sys.argv) < 2:
        print("Usage: python debug_kotlin_analyzer.py <project_path>")
        sys.exit(1)
    
    project_path = sys.argv[1]
    project_name = Path(project_path).name
    
    print(f"🐞 Kotlin Analyzer Debugger")
    print(f"Project: {project_path}")
    
    # First, check basic file access
    debug_file_processing(project_path)
    
    # Then test analyzers
    debugger = AnalyzerDebugger()
    
    # Test different analyzers
    analyzers_to_test = [
        FastKotlinAnalyzer,
        UnifiedKotlinAnalyzer,
        # CompleteKotlinAnalyzer  # This might be the slowest
    ]
    
    for analyzer_class in analyzers_to_test:
        debugger.files_processed = 0
        debugger.last_file = None
        debugger.memory_usage = []
        debugger.start_time = time.time()
        
        debugger.analyze_with_monitoring(analyzer_class, project_path, project_name)
        
        # Give some breathing room between tests
        time.sleep(2)
    
    print("\n✅ Debug session completed!")


if __name__ == "__main__":
    main()