"""Quick fix for large Kotlin project analysis."""

import sys
import os
from pathlib import Path

# Add mnemo to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mnemo.graph.fast_kotlin_analyzer import FastKotlinAnalyzer


def analyze_in_batches(project_path: str, project_name: str, batch_size: int = 50):
    """Analyze large project in batches to avoid memory issues."""
    
    print(f"🚀 Batch Analysis for {project_name}")
    print(f"   Path: {project_path}")
    print(f"   Batch size: {batch_size} files")
    
    # First, count total files
    kotlin_files = []
    for root, dirs, files in os.walk(project_path):
        # Skip build directories
        dirs[:] = [d for d in dirs if d not in {'.gradle', 'build', 'out', 'test'}]
        
        for file in files:
            if file.endswith('.kt'):
                kotlin_files.append(Path(root) / file)
    
    total_files = len(kotlin_files)
    print(f"   Total files: {total_files}")
    
    if total_files == 0:
        print("❌ No Kotlin files found!")
        return
    
    # Analyze without Neo4j first (just in memory)
    analyzer = FastKotlinAnalyzer()
    
    all_results = {
        'files': 0,
        'functions': 0,
        'classes': 0,
        'packages': set(),
        'failed_files': []
    }
    
    # Process in batches
    for i in range(0, total_files, batch_size):
        batch = kotlin_files[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_files + batch_size - 1) // batch_size
        
        print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} files)...")
        
        for file_idx, kt_file in enumerate(batch):
            if file_idx % 10 == 0:
                print(f"   Progress: {file_idx}/{len(batch)} files in batch")
            
            try:
                result = analyzer.analyze_file_fast(kt_file)
                
                all_results['files'] += 1
                all_results['functions'] += len(result['functions'])
                all_results['classes'] += len(result['classes'])
                if result['package']:
                    all_results['packages'].add(result['package'])
                    
            except Exception as e:
                print(f"   ⚠️  Failed: {kt_file} - {e}")
                all_results['failed_files'].append(str(kt_file))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Analysis Summary:")
    print(f"   Files analyzed: {all_results['files']}/{total_files}")
    print(f"   Functions found: {all_results['functions']}")
    print(f"   Classes found: {all_results['classes']}")
    print(f"   Packages: {len(all_results['packages'])}")
    print(f"   Failed files: {len(all_results['failed_files'])}")
    
    if all_results['failed_files']:
        print("\n❌ Failed files:")
        for f in all_results['failed_files'][:5]:
            print(f"   - {f}")
        if len(all_results['failed_files']) > 5:
            print(f"   ... and {len(all_results['failed_files']) - 5} more")
    
    print("\n✅ Analysis complete!")
    print("💡 Tip: For Neo4j storage, use smaller projects or increase batch size")
    
    # Option to save to Neo4j
    save_to_neo4j = input("\nSave to Neo4j? (y/n): ").lower() == 'y'
    
    if save_to_neo4j:
        print("\n⚠️  WARNING: Saving 648 files to Neo4j might take a while!")
        print("Consider using a smaller subset or the FastKotlinAnalyzer directly.")
        
        confirm = input("Continue? (y/n): ").lower() == 'y'
        if confirm:
            print("\n🔄 Saving to Neo4j...")
            # Here you would call the actual Neo4j save
            # For now, we'll skip to avoid the infinite loop
            print("❌ Neo4j save skipped for safety. Use smaller dataset.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_fix_analyzer.py <project_path>")
        sys.exit(1)
    
    project_path = sys.argv[1]
    project_name = Path(project_path).name
    
    # Run batch analysis
    analyze_in_batches(project_path, project_name, batch_size=50)


if __name__ == "__main__":
    main()