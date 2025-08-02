"""Test branch tracking functionality."""

import subprocess
from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.trackers import GitActivityTracker


def main():
    """Test branch tracking."""
    
    # Initialize memory system
    vector_store = MnemoVectorStore(
        collection_name="test_branch",
        persist_directory="./test_branch_db"
    )
    memory_client = MnemoMemoryClient(vector_store)
    
    # Create git tracker
    tracker = GitActivityTracker(memory_client)
    
    print("Testing branch tracking...")
    
    # Track initial branch
    print("\n1. Tracking initial branch state...")
    initial_info = tracker.track_branch_info()
    print(f"   Current branch: {initial_info['current_branch']}")
    
    # Try to find branch switch memories
    print("\n2. Searching for branch memories...")
    results = memory_client.search(
        query="branch switch",
        tags={"git", "branch"},
        limit=5
    )
    
    print(f"\nFound {len(results)} branch-related memories:")
    for result in results:
        print(f"\n- {result['memory_id'][:8]}...")
        print(f"  Content: {result['content']}")
        print(f"  Tags: {result['tags']}")
    
    # Also check current branch memory
    current_branch_memory = memory_client.recall(f"current_branch_{tracker.project_path.name}")
    if current_branch_memory:
        print(f"\nCurrent branch memory: {current_branch_memory}")
    else:
        print("\nNo current branch memory found")
    
    print("\nTo test branch switching:")
    print("   1. Switch to another branch: git checkout main")
    print("   2. Run this script again")
    print("   3. You should see the branch switch recorded!")


if __name__ == "__main__":
    main()