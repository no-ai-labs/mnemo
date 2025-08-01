"""
Mnemo: LangChain-powered Universal Memory System for AI Assistants

A modern memory system built on LangChain with optional LangGraph support
for complex workflows. Designed to work seamlessly with AI assistants
like Cursor via MCP integration.
"""

__version__ = "0.2.0"
__author__ = "DevHub Team"

from mnemo.memory.store import MnemoVectorStore
from mnemo.memory.client import MnemoMemoryClient
from mnemo.chains.memory import MemoryChain
from mnemo.tools.memory import MemoryTool

__all__ = [
    "MnemoVectorStore",
    "MnemoMemoryClient",
    "MemoryChain",
    "MemoryTool",
]