import asyncio
import json
import os
import sys
import contextlib
import warnings
from typing import Dict, List, Any, Optional, Union
import logging
from openai import AsyncOpenAI
from contextlib import AsyncExitStack

from .client import MCPClient

# Simple logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MCP_Platform")

# Suppress asyncio errors during cleanup
asyncio_logger = logging.getLogger("asyncio")
asyncio_logger.setLevel(logging.CRITICAL)

class MCPPlatform:
    """A unified platform that manages multiple MCP clients and routes tool calls."""
    
    def __init__(self):
        # Core data structures
        self.clients = {}  # server_name -> MCPClient
        self.tool_server_map = {}  # tool_name -> server_name
        self.all_tools = []  # All available tools
        
        # OpenAI client setup
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        
        # DeepSeek client setup if available
        self.deepseek_client = None
        if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_BASE_URL"):
            self.deepseek_client = AsyncOpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url=os.getenv("DEEPSEEK_BASE_URL"),
            )
        
        # Default model
        self.model = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        
        # Load configuration
        self.server_config = self._load_server_config()
        
        # Set asyncio logging to a higher level during platform operations
        # to suppress asyncio-related warnings
        logging.getLogger('asyncio').setLevel(logging.CRITICAL)
        
        self.exit_stack = AsyncExitStack()

    def _load_server_config(self) -> Dict:
        """Load server configuration from server_config.json."""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_config.json")
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            logger.warning(f"Config not found at {config_path}")
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
        
        return {"servers": []}

    def _make_serializable(self, obj):
        """Convert any object to a JSON-serializable format."""
        if obj is None:
            return None
        
        # Handle common types that need special serialization
        if hasattr(obj, '__dict__'):
            return self._make_serializable(obj.__dict__)
        elif hasattr(obj, 'text') and callable(getattr(obj, 'text', None)):
            return obj.text()
        elif hasattr(obj, 'content') and not callable(getattr(obj, 'content', None)):
            return str(obj.content)
            
        # Handle dictionaries - recursively serialize their values
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        
        # Handle lists/tuples - recursively serialize their items
        if isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
            
        # Try direct conversion for basic types
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError, ValueError):
            # If all else fails, convert to string
            return str(obj)

    async def initialize_all_servers(self):
        """Connect to all servers in the configuration."""
        for server in self.server_config.get("servers", []):
            name = server.get("name")
            path = server.get("path")
            type = server.get("type")
            args = server.get("args", [])
            
            if not all([name, path, type]):
                continue
            
            try:
                await self.add_server(name, path, type, args)
                logger.info(f"Initialized server: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize {name}: {str(e)}")

    async def add_server(self, name, path, type, args=None):
        """Add a new server connection."""
        client = MCPClient()
        tools = await client.connect_to_server(path, type, args)
        
        self.clients[name] = client
        
        # Map tools to this server
        for tool in tools:
            self.tool_server_map[tool.get("name")] = name
        
        await self.refresh_all_tools()

    async def refresh_all_tools(self):
        """Update the list of all available tools."""
        self.all_tools = []
        
        for server_name, client in list(self.clients.items()):
            if not await client.check_connection():
                # Skip disconnected servers
                continue
            
            # Add this server's tools to the master list
            for tool in client.tools:
                tool_copy = tool.copy()
                tool_copy["server"] = server_name
                self.all_tools.append(tool_copy)
                self.tool_server_map[tool["name"]] = server_name
        
        return self.all_tools

    def get_all_tools(self):
        """Get all available tools across all servers."""
        return self.all_tools

    async def call_tool(self, tool_name, args):
        """Call a specific tool on the appropriate server."""
        # Find which server has this tool
        server_name = self.tool_server_map.get(tool_name)
        if not server_name:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        # Get the client
        client = self.clients.get(server_name)
        if not client:
            raise ValueError(f"Client for server '{server_name}' not found")
        
        # Verify connection
        if not await client.check_connection():
            raise ConnectionError(f"Server '{server_name}' disconnected")
        
        # Call the tool
        try:
            result = await client.execute_tool(tool_name, args)
            
            # Convert to JSON-serializable format
            serializable_result = self._make_serializable(result)
            return serializable_result
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}': {str(e)}")
            raise
    
    async def process_query(self, query, max_iterations=5):
        """Process a user query with available tools using various LLMs."""
        # Get latest tools
        tools = await self.refresh_all_tools()
        
        # Format tools for LLM
        available_tools = []
        for tool in tools:
            available_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": {"type": "object", "properties": {}}
                }
            })
        
        # Setup initial conversation
        messages = [
            {"role": "system", "content": "You are a helpful assistant with access to various tools."},
            {"role": "user", "content": query}
        ]
        
        conversation_steps = [{"role": "user", "content": query}]
        
        # Process in a loop until no more tool calls or max iterations reached
        for iteration in range(max_iterations):
            # Call the LLM based on the model type
            try:
                if self.model.startswith("deepseek") and self.deepseek_client:
                    # Handle DeepSeek models
                    deepseek_messages = []
                    for msg in messages:
                        if isinstance(msg, dict):
                            # If it's already a dict, make a clean copy with only the required fields
                            clean_msg = {
                                "role": msg["role"],
                                "content": str(msg["content"]) if "content" in msg and msg["content"] is not None else ""
                            }
                            # Handle tool calls for DeepSeek
                            if "tool_calls" in msg:
                                clean_msg["tool_calls"] = msg["tool_calls"]
                            # Handle tool responses
                            if msg["role"] == "tool" and "tool_call_id" in msg:
                                clean_msg["tool_call_id"] = msg["tool_call_id"]
                            deepseek_messages.append(clean_msg)
                        else:
                            # If it's some other object, convert to a simple dict
                            clean_msg = {
                                "role": msg.role,
                                "content": str(msg.content) if hasattr(msg, "content") and msg.content is not None else ""
                            }
                            if hasattr(msg, "tool_call_id"):
                                clean_msg["tool_call_id"] = msg.tool_call_id
                            deepseek_messages.append(clean_msg)
                    
                    response = await self.deepseek_client.chat.completions.create(
                        model=self.model,
                        messages=deepseek_messages,
                        tools=available_tools,
                        tool_choice="auto",
                    )
                else:
                    # Handle OpenAI models
                    response = await self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=available_tools,
                        tool_choice="auto"
                    )
            except Exception as e:
                error_msg = f"Error calling language model: {str(e)}"
                logger.error(error_msg)
                conversation_steps.append({"role": "error", "content": error_msg})
                break
            
            # Process assistant's response
            assistant_message = response.choices[0].message
            
            # Add assistant's content to conversation if it exists
            content = assistant_message.content or ""
            conversation_steps.append({"role": "assistant", "content": content})
            
            # Add clean version to messages for next iteration
            if self.model.startswith("deepseek"):
                clean_msg = {
                    "role": "assistant",
                    "content": content
                }
                if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
                    clean_msg["tool_calls"] = assistant_message.tool_calls
                messages.append(clean_msg)
            else:
                # For OpenAI, ensure we have a clean dictionary
                messages.append({
                    "role": "assistant", 
                    "content": content,
                    "tool_calls": assistant_message.tool_calls if assistant_message.tool_calls else None
                })
            
            # If no tool calls, we're done
            if not assistant_message.tool_calls:
                break
            
            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                
                # Parse arguments - ensure proper JSON
                try:
                    if isinstance(tool_call.function.arguments, str):
                        function_args = json.loads(tool_call.function.arguments)
                    else:
                        function_args = tool_call.function.arguments
                except json.JSONDecodeError:
                    error_msg = f"Invalid JSON in tool arguments: {tool_call.function.arguments}"
                    logger.error(error_msg)
                    conversation_steps.append({"role": "error", "content": error_msg})
                    continue
                
                # Record the tool call in conversation
                conversation_steps.append({
                    "role": "tool",
                    "name": function_name,
                    "args": function_args
                })
                
                try:
                    # Execute the tool call
                    tool_result = await self.call_tool(function_name, function_args)
                    
                    # Add result to conversation
                    conversation_steps.append({
                        "role": "tool_result",
                        "name": function_name,
                        "result": tool_result
                    })
                    
                    # Add tool result to messages for next LLM call
                    # Make sure it's serializable for the response
                    serialized_result = json.dumps(tool_result)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": serialized_result
                    })
                except Exception as e:
                    # Handle tool execution errors
                    error_msg = f"Error executing tool '{function_name}': {str(e)}"
                    logger.error(error_msg)
                    
                    # Add error to conversation
                    conversation_steps.append({
                        "role": "error", 
                        "content": error_msg
                    })
                    
                    # Add error to messages for next LLM call
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": f"Error: {str(e)}"
                    })
        
        # Get final response - the last assistant message
        final_response = next((step["content"] for step in reversed(conversation_steps) 
                            if step["role"] == "assistant"), "No response generated")
        
        return {
            "conversation_steps": conversation_steps,
            "final_response": final_response
        }
        
    async def cleanup(self):
        """Clean up all the clients."""
        if not self.clients:
            return

        # Create a snapshot of clients to clean up
        clients_to_cleanup = list(self.clients.items())
        
        # Clear the clients dictionary first to allow garbage collection
        self.clients.clear()
        self.tool_server_map.clear()
        self.all_tools.clear()
        
        # Clean each client directly instead of using tasks to avoid cancellation issues
        for name, client in clients_to_cleanup:
            try:
                # Directly clean up the client with timeout protection
                await self._cleanup_client(name, client)
            except Exception as e:
                warnings.warn(f"Failed to clean up {name}: {type(e).__name__}")
        
        # Close the exit stack with error handling
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            # This is where the stdio_client async generator error occurs
            warnings.warn(f"Exit stack cleanup issue: {type(e).__name__}")
        
        logger.info("Cleanup completed")

    async def _cleanup_client(self, name, client):
        """Clean up a single client with timeout protection."""
        try:
            # Check if client has the cleanup method (MCPClient class)
            if hasattr(client, 'cleanup') and callable(client.cleanup):
                await asyncio.wait_for(client.cleanup(), timeout=2.0)
            # Check if client has the aclose method
            elif hasattr(client, 'aclose') and callable(client.aclose):
                await asyncio.wait_for(client.aclose(), timeout=2.0)
            # If no cleanup methods available, just log it
            else:
                logger.info(f"No cleanup method found for {name}")
        except asyncio.TimeoutError:
            warnings.warn(f"Cleanup for {name} timed out")
        except Exception as e:
            warnings.warn(f"Error during {name} cleanup: {type(e).__name__}")

async def main():
    platform = MCPPlatform()
    
    try:
        await platform.initialize_all_servers()
        tools = platform.get_all_tools()
        print(f"Available tools: {len(tools)}")
        
        result = await platform.process_query("What's the weather like in New York?")
        print(f"Final response: {result['final_response']}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        await platform.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 