"""Types for MCP implementation."""

from typing import Dict, List, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


class MCPResourceType(Enum):
    """Types of resources exposed via MCP."""
    MEMORY = "memory"
    CONTEXT = "context"
    KNOWLEDGE = "knowledge"


class MCPResource(BaseModel):
    """Resource exposed via MCP."""
    id: str
    name: str
    type: MCPResourceType
    description: str
    uri: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPTool(BaseModel):
    """Tool exposed via MCP."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None


class MCPPrompt(BaseModel):
    """Prompt template exposed via MCP."""
    name: str
    description: str
    arguments: List[str]
    template: str


class MCPRequest(BaseModel):
    """MCP JSON-RPC request."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Union[str, int, None] = None


class MCPResponse(BaseModel):
    """MCP JSON-RPC response."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Union[str, int, None] = None


class MCPError(BaseModel):
    """MCP error."""
    code: int
    message: str
    data: Optional[Any] = None