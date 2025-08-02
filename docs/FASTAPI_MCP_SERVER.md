# FastAPI MCP Server Guide

## 🚀 Why FastAPI for MCP?

The FastAPI-based MCP server provides the best experience for using Mnemo with Cursor:

### Benefits

1. **Persistent State** 🔄
   - Server keeps running in the background
   - Maintains memory connections
   - No need to reinitialize on every request

2. **Better Debugging** 🐛
   - Real-time logs in terminal
   - HTTP endpoints for testing
   - Browser-accessible health checks

3. **Performance** ⚡
   - Faster response times
   - Asynchronous request handling
   - Connection pooling

4. **Stability** 🛡️
   - Production-ready with automatic error recovery
   - Better error handling
   - Automatic recovery

## 📖 Usage Guide

### Starting the Server

```bash
# Option 1: Using CLI command
python -m mnemo.mcp.cli serve-fastapi

# Option 2: Direct module execution
python -m mnemo.mcp.fastapi_server

# Option 3: With custom settings
python -m mnemo.mcp.cli serve-fastapi \
  --host 0.0.0.0 \
  --port 3333 \
  --db-path ./my_memories \
  --collection cursor_memories
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Server host address |
| `--port` | `3333` | Server port |
| `--db-path` | `./mnemo_mcp_db` | Database directory |
| `--collection` | `cursor_memories` | ChromaDB collection name |

### Testing the Server

1. **Health Check**:
   ```bash
   curl http://localhost:3333/health
   # Response: {"status":"ok","service":"mnemo-mcp"}
   ```

2. **MCP Initialize**:
   ```bash
   curl -X POST http://localhost:3333/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}'
   ```

3. **List Tools**:
   ```bash
   curl -X POST http://localhost:3333/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "listTools", "params": {}, "id": 2}'
   ```

## 🔧 Troubleshooting

### Server Won't Start
- Check if port 3333 is already in use: `lsof -i :3333`
- Ensure all dependencies are installed: `pip install fastapi uvicorn`

### Cursor Can't Connect
1. Verify server is running: `curl http://localhost:3333/health`
2. Check Cursor's mcp.json configuration
3. Restart Cursor completely

### Memory Not Persisting
- Check database path permissions
- Ensure ChromaDB is properly initialized
- Look for errors in server logs

## 🛠️ Development

### Running in Development Mode

The server automatically reloads on code changes:

```bash
python -m mnemo.mcp.fastapi_server
# Uvicorn will watch for changes and reload
```

### Custom Endpoints

You can extend the server by adding new endpoints in `fastapi_server.py`:

```python
@app.get("/custom/endpoint")
async def custom_endpoint():
    return {"message": "Custom endpoint"}
```

### Logging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Performance Tips

1. **Use connection pooling** - ChromaDB handles this automatically
2. **Enable caching** - For frequently accessed memories
3. **Monitor memory usage** - Especially with large embeddings
4. **Use appropriate embedding models** - Balance quality vs speed

## 🔐 Security Considerations

For production use:

1. **Add authentication** - Protect your memory endpoints
2. **Use HTTPS** - Encrypt communication
3. **Restrict host binding** - Don't use `0.0.0.0` in production
4. **Environment variables** - Store sensitive config securely

Example with authentication:

```python
from fastapi import Depends, HTTPException, security

api_key = security.APIKeyHeader(name="X-API-Key")

async def verify_api_key(key: str = Depends(api_key)):
    if key != os.getenv("MCP_API_KEY"):
        raise HTTPException(status_code=403)
```

---

For more information, see the [main README](../README.md) or [Cursor guides](./CURSOR_MCP_GUIDE_EN.md).