import asyncio
import json
import os
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MCPClient:
    """Client for interacting with Model Control Protocol (MCP) servers."""
    
    def __init__(self):
        # Connection state
        self.session = None
        self.exit_stack = AsyncExitStack()
        self.connected = False
        self.tools = []
        self.current_server = None
        self.stdio = None
        self.write = None

    async def connect_to_server(self, server_path: str, server_type: str = None, args: List[str] = None):
        """Connect to an MCP server and retrieve available tools."""
        # Clean up existing connection if any
        if self.connected:
            await self.cleanup()
        
        args = args or []
        
        # Auto-detect server type if not specified
        if server_type is None:
            if server_path.endswith(".py"):
                server_type = "python"
            elif server_path.endswith(".js") or server_path.endswith(".ts"):
                server_type = "node"
            else:
                raise ValueError("Cannot determine server type from file extension")
        
        try:
            # Create a fresh exit stack for this connection
            self.exit_stack = AsyncExitStack()
            
            # Setup connection
            server_params = StdioServerParameters(
                command=server_type, 
                args=[server_path] + args, 
                env=None
            )
            
            # Connect
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            
            # Initialize and get tools
            await self.session.initialize()
            response = await self.session.list_tools()
            self.tools = [{"name": tool.name, "description": tool.description} for tool in response.tools]
            self.connected = True
            
            # Store server info
            self.current_server = {
                "path": server_path,
                "type": server_type,
                "args": args
            }
            
            return self.tools
            
        except Exception as e:
            print(f"Failed to connect to server: {str(e)}")
            # Ensure we clean up partially initialized resources
            await self.cleanup()
            raise ConnectionError(f"Failed to connect to server: {str(e)}")

    async def cleanup(self):
        """Close connection and clean up resources."""
        if not self.connected:
            return
        
        # Reset state first to prevent recursive calls
        self.connected = False
        
        try:
            # Close the session first if it exists
            if self.session:
                # Try to terminate gracefully by sending an exit command
                try:
                    await asyncio.wait_for(self.session.shutdown(), timeout=2.0)
                except (asyncio.TimeoutError, Exception):
                    pass
                self.session = None
            
            # Reset stdio and write
            self.stdio = None
            self.write = None
            
            # Create a new task for exit stack closure to avoid cancel scope issues
            try:
                if self.exit_stack:
                    # Use wait_for to prevent hanging
                    await asyncio.wait_for(self.exit_stack.aclose(), timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception) as e:
                print(f"Non-critical error during exit stack cleanup: {type(e).__name__}")
                # Swallow the error - we've already reset our state
                pass
                
            print("Connection closed successfully")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
        finally:
            # Clear all resources
            self.tools = []
            # Create a new exit stack for future connections
            self.exit_stack = AsyncExitStack()

    async def reconnect(self, server_path: str):
        """Reconnect to a server after connection loss."""
        # Get current server settings if available
        server_type = None
        args = None
        
        if self.current_server:
            server_type = self.current_server.get("type")
            args = self.current_server.get("args")
        
        # Clean up and create new connection
        await self.cleanup()
        
        # Connect to the server with saved parameters
        return await self.connect_to_server(server_path, server_type, args)

    async def check_connection(self):
        """Check if connection is still active."""
        if not self.connected or not self.session:
            return False
        
        try:
            await self.session.list_tools()
            return True
        except Exception as e:
            print(f"Connection check failed: {str(e)}")
            self.connected = False
            return False
            
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]):
        """Execute a tool on the connected server."""
        if not self.connected or not self.session:
            raise ConnectionError("Not connected to a server")
        
        # Check if tool exists
        if not any(tool["name"] == tool_name for tool in self.tools):
            raise ValueError(f"Tool '{tool_name}' not available")
        
        try:
            # Use call_tool instead of execute_tool
            result = await self.session.call_tool(tool_name, args)
            # The result is directly returned, no need to access .result
            return result
        except Exception as e:
            print(f"Tool execution failed: {str(e)}")
            raise RuntimeError(f"Tool execution failed: {str(e)}")

# Singleton instance
_client_instance = None

def get_client():
    """Get or create the singleton MCPClient instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = MCPClient()
    return _client_instance


async def main():
    client = get_client()
    try:
        await client.connect_to_server("server/braveSearch.js", "node")
        print("Connected to server successfully\n")
        print("Available tools:", client.tools)
        print("\n")
        result = await client.execute_tool("brave_web_search", {
            "query": "What is the capital of France?", 
            "count": 10, 
            "offset": 0
        })
        print("Tool execution result:", result)
    except Exception as e:
        print(f"Error during test: {str(e)}")
    finally:
        # Ensure cleanup happens
        print("Cleaning up resources...")
        await client.cleanup()
        print("Cleanup complete.")

if __name__ == "__main__":
    # Run the test function if the file is executed directly
    asyncio.run(main())
