# MCP Platform

A unified platform for managing multiple MCP (Model Control Protocol) servers and routing tool calls to the appropriate server.

## Overview

The MCP Platform provides a centralized way to:

1. Connect to multiple MCP servers
2. Maintain a registry of all available tools across servers
3. Route tool calls to the appropriate server
4. Process user queries using an LLM (Large Language Model) and execute tool calls as needed

The platform automatically handles:
- Server connection management
- Tool discovery and mapping
- LLM integration for query processing
- Conversation history tracking
- Error handling and reconnection logic

## Files

- `mcp_platform.py`: The main MCP Platform implementation
- `mcp_example.py`: Example usage script
- `client.py`: The base MCP client used by the platform
- `server_config.json`: Configuration file for available servers

## Usage

### Basic Usage

```python
import asyncio
from mcp_platform import MCPPlatform

async def main():
    # Create the MCP Platform
    platform = MCPPlatform()
    
    # Initialize all servers from config
    await platform.initialize_all_servers()
    
    # Get all available tools
    tools = platform.get_all_tools()
    print(f"Available tools: {tools}")
    
    # Process a user query
    result = await platform.process_query("What's the weather like in New York?")
    print(f"Result: {result}")
    
    # Clean up
    for client in platform.clients.values():
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### Running the Example

```bash
python mcp_example.py
```

This will:
1. Connect to all configured servers
2. List all available tools
3. Enter an interactive mode where you can type queries
4. Process each query and display the conversation and results

### Adding a New Server Manually

```python
await platform.add_server(
    server_name="My Custom Server",
    server_path="./path/to/server.js",
    server_type="node",
    args=["--additional", "arguments"]
)
```

### Server Configuration

The `server_config.json` file should have the following structure:

```json
{
  "servers": [
    {
      "name": "File System Server",
      "path": "./server/file_system_server.js",
      "type": "node",
      "description": "Secure file system access service",
      "args": ["./fileSystemDirectory"]
    },
    {
      "name": "Brave Search Server",
      "path": "server/braveSearch.js",
      "type": "node",
      "description": "Brave Search API service"
    }
  ],
  "default_server": "Weather Server"
}
```

## API Reference

### MCPPlatform Class

#### Constructor

```python
platform = MCPPlatform()
```

#### Methods

- `async initialize_all_servers()`: Connect to all servers in the config
- `async add_server(server_name, server_path, server_type, args=None)`: Add a new server
- `async refresh_all_tools()`: Refresh the list of available tools
- `get_all_tools()`: Get all available tools
- `async call_tool(tool_name, args)`: Call a specific tool
- `async process_query(query, max_iterations=5)`: Process a user query

## Environment Variables

The platform uses the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_BASE_URL`: Base URL for OpenAI API (optional)
- `DEFAULT_MODEL`: Default LLM model to use (defaults to "gpt-3.5-turbo")

## Requirements

- Python 3.8+
- OpenAI Python SDK
- MCP libraries

## Error Handling

The platform includes comprehensive error handling:

- Connection failures
- Tool execution errors
- Server disconnections (with automatic reconnection attempts)
- Configuration errors

All errors are logged using the standard Python logging module.

## Extending the Platform

To add support for additional LLM providers:

1. Modify the `__init__` method to initialize the new provider's client
2. Update the `process_query` method to use the new provider

To add custom tool schemas:

1. Modify the `refresh_all_tools` method to include detailed parameter schemas
2. Update the `process_query` method to format tools appropriately for your LLM provider 