"""Test automatic project tracking functionality."""

import asyncio
import subprocess
import os
from pathlib import Path

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.mcp.auto_tracker import AutoProjectTracker


async def main():
    """Test auto tracking features."""
    
    # Initialize memory system
    vector_store = MnemoVectorStore(
        collection_name="test_tracking",
        persist_directory="./test_tracking_db"
    )
    memory_client = MnemoMemoryClient(vector_store)
    
    # Create auto tracker
    tracker = AutoProjectTracker(memory_client)
    
    print("Starting auto-tracking test...")
    
    # Start tracking with short interval for testing
    await tracker.start_tracking(interval=10)  # 10 seconds for testing
    
    # Make some changes to trigger tracking
    print("\nMaking test changes...")
    
    # Create a test file
    test_file = Path("test_tracking_file.py")
    test_file.write_text("""
# Test file for tracking
def hello():
    print("Hello, tracking!")
""")
    
    # Wait for first tracking cycle
    print("Waiting for tracking cycle...")
    await asyncio.sleep(12)
    
    # Modify the file
    print("Modifying test file...")
    test_file.write_text("""
# Test file for tracking - modified
def hello():
    print("Hello, tracking!")
    
def goodbye():
    print("Goodbye!")
""")
    
    # Make a git commit if in a git repo
    try:
        subprocess.run(["git", "add", str(test_file)], check=False)
        subprocess.run(["git", "commit", "-m", "Test commit for auto-tracking"], check=False)
        print("Created test commit")
    except:
        print("WARNING: Not in a git repository, skipping commit test")
    
    # Wait for another tracking cycle
    await asyncio.sleep(12)
    
    # Search for tracked memories
    print("\nSearching for tracked memories...")
    
    results = memory_client.search(
        query="tracking auto",
        tags={"tracking", "auto"},
        limit=10
    )
    
    print(f"\nFound {len(results)} tracking memories:")
    for result in results:
        print(f"\n- {result['memory_id'][:8]}...")
        print(f"  Content: {result['content'][:100]}...")
        print(f"  Tags: {result['tags']}")
    
    # Stop tracking
    await tracker.stop_tracking()
    
    # Cleanup
    if test_file.exists():
        test_file.unlink()
        print("\nCleaned up test file")
    
    print("\nAuto-tracking test completed!")


if __name__ == "__main__":
    asyncio.run(main())