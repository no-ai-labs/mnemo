"""Test session tracking functionality."""

import asyncio
from datetime import datetime

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.mcp.auto_tracker import SessionMemoryTracker


async def main():
    """Test session tracking features."""
    
    # Initialize memory system
    vector_store = MnemoVectorStore(
        collection_name="test_session",
        persist_directory="./test_session_db"
    )
    memory_client = MnemoMemoryClient(vector_store)
    
    # Create session tracker
    session_tracker = SessionMemoryTracker(memory_client)
    
    print("Testing session tracking...")
    
    # Simulate chat messages
    test_messages = [
        ("user", "Hello, I need to implement a new feature"),
        ("assistant", "I'll help you with that. What feature do you want to implement?"),
        ("user", "I want to add user authentication"),
        ("assistant", "Great! Let's plan the authentication system"),
        ("user", "We should fix the bug in the login system first"),
        ("assistant", "Good point. Let me check the current implementation"),
        ("user", "Remember to add proper error handling"),
        ("assistant", "I'll make sure to include comprehensive error handling"),
        ("user", "This is just a normal conversation"),
        ("assistant", "Yes, continuing our discussion..."),
    ]
    
    # Add messages to tracker
    for role, content in test_messages:
        print(f"\nAdding message from {role}: {content[:50]}...")
        session_tracker.add_message(role, content)
        await asyncio.sleep(0.1)  # Small delay to simulate real chat
    
    # Get session summary
    summary = session_tracker.get_session_summary()
    print("\n--- Session Summary ---")
    print(f"Session ID: {summary['session_id']}")
    print(f"Total messages: {summary['message_count']}")
    print(f"Important messages: {summary['important_messages']}")
    print(f"Duration: {summary['duration']}")
    
    # Search for saved memories
    print("\n--- Searching for session memories ---")
    
    # Search for important messages
    important_results = memory_client.search(
        query="important message chat",
        tags={"important", "chat"},
        limit=5
    )
    
    print(f"\nFound {len(important_results)} important messages:")
    for result in important_results:
        print(f"\n- Memory ID: {result['memory_id'][:8]}...")
        print(f"  Content: {result['content'][:100]}...")
        print(f"  Tags: {result['tags']}")
    
    # Add more messages to trigger summary
    print("\n\nAdding more messages to trigger summary...")
    for i in range(15):
        session_tracker.add_message(
            "user" if i % 2 == 0 else "assistant",
            f"Message {i+11}: This is a test message for triggering summary"
        )
    
    # Search for session summaries
    summary_results = memory_client.search(
        query="chat session",
        tags={"session", "conversation"},
        limit=3
    )
    
    print(f"\nFound {len(summary_results)} session summaries:")
    for result in summary_results:
        print(f"\n- Memory ID: {result['memory_id'][:8]}...")
        print(f"  Content preview: {result['content'][:150]}...")
    
    print("\n--- Test completed! ---")


if __name__ == "__main__":
    asyncio.run(main())