from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict, Any
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import json
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from datetime import datetime
import re

# Import MCPPlatform
try:
    from ai_agent.mcp_platform import MCPPlatform
    mcp_available = True
except ImportError as e:
    print(f"Warning: MCP Platform not available: {e}")
    mcp_available = False

# Load environment variables from .env file
load_dotenv()

# Initialize global variables for resources
mcp_platform = None
mcp_initialized = False
available_mcp_tools = []
client = None

# Define lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize resources when the app starts
    await startup_event()
    yield
    # Clean up resources when the app shuts down
    await shutdown_event()

# Initialize OpenAI client from environment variables
def setup_openai():
    global client
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )

async def startup_event():
    """Initialize resources when the application starts up"""
    global mcp_platform
    
    # Setup OpenAI
    setup_openai()
    
    # Initialize MCP Platform if available
    if mcp_available:
        try:
            mcp_platform = MCPPlatform()
            print("MCP Platform initialized successfully")
            await initialize_mcp()
        except Exception as e:
            print(f"Error initializing MCP Platform: {e}")

async def shutdown_event():
    """Clean up resources when FastAPI server is shutting down"""
    global mcp_platform, mcp_available
    
    if mcp_available and mcp_platform is not None:
        try:
            await mcp_platform.cleanup()
            print("MCP Platform resources cleaned up")
        except Exception as e:
            print(f"Error during MCP cleanup: {str(e)}")

async def initialize_mcp():
    """Initialize the MCP platform and connect to all configured servers"""
    global mcp_initialized, available_mcp_tools, mcp_platform, mcp_available
    
    if not mcp_available or mcp_platform is None:
        print("MCP Platform is not available")
        return False
    
    try:
        await mcp_platform.initialize_all_servers()
        available_mcp_tools = mcp_platform.get_all_tools()
        mcp_initialized = True
        print(f"MCP Platform initialized with {len(available_mcp_tools)} tools")
        return True
    except Exception as e:
        print(f"Failed to initialize MCP Platform: {str(e)}")
        mcp_initialized = False
        return False

def map_model_name(model: str) -> str:
    """Map short model names to full model names"""
    if model == "3.5":
        return "gpt-3.5-turbo"
    elif model == "4o-mini":
        return "gpt-4o-mini"
    elif model == "4o":
        return "gpt-4o"
    return model

def log_tool_usage(step_number, tool_name, arguments, result_preview):
    """Log tool usage with formatted output for easy identification in logs"""
    log_header = f"===== TOOL USAGE [{step_number}] =====".ljust(80, '=')
    log_footer = "=" * 80
    
    print(log_header)
    print(f"Tool: {tool_name}")
    print(f"Arguments: {arguments}")
    print(log_footer)

def log_tool_result(step_number, tool_name, result_preview):
    """Log tool result with formatted output for easy identification in logs"""
    log_header = f"===== TOOL RESULT [{step_number}] =====".ljust(80, '=')
    log_footer = "=" * 80
    
    print(log_header)
    print(f"Tool: {tool_name}")
    print(f"Result Preview: {result_preview}")
    print(log_footer)

# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    prompt: str
    model: str = "3.5"
    use_mcp: bool = True

class ChatResponse(BaseModel):
    response: str
    node_list: Optional[list] = None
    mcp_tools_used: Optional[List[str]] = None
    intermediate_results: Optional[List[Dict]] = None

class MCPToolsResponse(BaseModel):
    initialized: bool
    tools: List[Dict[str, Any]]
    servers: List[str]

async def process_with_mcp(prompt: str, model: str) -> Tuple[str, List[str], List[Dict]]:
    """Process a query using MCP Platform"""
    global mcp_initialized, mcp_platform, mcp_available
    
    # Check if MCP is available at all
    if not mcp_available or mcp_platform is None:
        return "MCP Platform is not available on this server.", [], []
    
    # Initialize MCP if not already initialized
    if not mcp_initialized:
        success = await initialize_mcp()
        if not success:
            return "Failed to initialize MCP Platform. Please check server logs.", [], []
    
    try:
        # Set the model to use
        mcp_platform.model = map_model_name(model)
        
        # Process query through MCP
        result = await mcp_platform.process_query(prompt)
        
        # Debug log the conversation steps
        print("\n===== CONVERSATION STEPS STRUCTURE =====")
        for i, step in enumerate(result.get("conversation_steps", [])):
            print(f"Step {i+1}: Role = {step.get('role')}")
            if step.get('role') == 'tool':
                print(f"  Tool name: {step.get('name')}")
            elif step.get('role') == 'tool_result':
                result_data = step.get('result', {})
                print(f"  Result type: {type(result_data)}")
                if isinstance(result_data, dict):
                    print(f"  Result keys: {list(result_data.keys())}")
        print("======================================\n")
        
        # Track the tools used in this conversation
        tools_used = []
        intermediate_results = []
        step_counter = 0
        
        for step in result.get("conversation_steps", []):
            if step.get("role") == "tool" and "name" in step:
                step_counter += 1
                tools_used.append(step["name"])
                
                # Capture tool arguments
                args_str = "None"
                if "arguments" in step:
                    try:
                        args_str = json.dumps(step["arguments"], indent=2)
                    except Exception as e:
                        args_str = f"Error parsing arguments: {str(e)}"
                
                # Log the tool usage
                log_tool_usage(step_counter, step["name"], args_str, "")
            
            # Handle tool result step separately
            elif step.get("role") == "tool_result" and "result" in step:
                result_data = step.get("result", {})
                content_str = "No content available"
                
                # Try to extract content based on various possible structures
                try:
                    # Case 1: result.content is a list of dicts with 'text' field
                    if isinstance(result_data, dict) and 'content' in result_data:
                        if isinstance(result_data['content'], list):
                            text_parts = []
                            for item in result_data['content']:
                                if isinstance(item, dict) and 'text' in item:
                                    text_parts.append(item['text'])
                            if text_parts:
                                content_str = "\n".join(text_parts)
                        # Case 2: result.content.text direct path
                        elif isinstance(result_data['content'], dict) and 'text' in result_data['content']:
                            content_str = result_data['content']['text']
                        # Case 3: result.content as string
                        elif isinstance(result_data['content'], str):
                            content_str = result_data['content']
                    # Case 4: result has direct text field
                    elif isinstance(result_data, dict) and 'text' in result_data:
                        content_str = result_data['text']
                    # Case 5: result is string
                    elif isinstance(result_data, str):
                        content_str = result_data
                    # Case 6: other dict format - convert to JSON
                    elif isinstance(result_data, dict):
                        content_str = json.dumps(result_data, indent=2)
                    # Case 7: fallback
                    else:
                        content_str = str(result_data)
                        
                    # Final cleanup - unescape common escape sequences
                    content_str = content_str.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\'", "'")
                    
                    # If the content is very long, truncate it to 5000 bytes
                    if len(content_str) > 5000:
                        content_str = content_str[:5000] + "... (truncated)"
                except Exception as e:
                    content_str = f"Error extracting content: {str(e)}"
                
                # Create a detailed tool result object
                tool_name = step.get("name", "unknown_tool")
                # Try to get the tool name from the previous step if not in current step
                if tool_name == "unknown_tool" and step_counter > 0:
                    tool_name = tools_used[-1] if tools_used else "unknown_tool"
                
                # Improved universal content extraction for all tools
                if isinstance(content_str, str):
                    # First attempt to extract TextContent pattern which is common across many tools
                    text_content_match = re.search(r"TextContent\(type=['\"]text['\"],\s*text=['\"](.*?)['\"](,|\))", content_str, re.DOTALL)
                    if text_content_match:
                        content_str = text_content_match.group(1)
                    else:
                        # Try to match meta=None content=[TextContent(type='text', text='ACTUAL_CONTENT'
                        meta_content_match = re.search(r"meta=None content=\[TextContent\(type=['\"]text['\"],\s*text=['\"](.*?)['\"](,|\))", content_str, re.DOTALL)
                        if meta_content_match:
                            content_str = meta_content_match.group(1)
                    
                    # Clean up any remaining escape characters
                    content_str = content_str.replace('\\n', '\n').replace('\\\\', '\\').replace('\\"', '"').replace("\\'", "'")
                    
                    # Remove any remaining annotations or isError markers
                    content_str = re.sub(r',\s*annotations=.*?(False|True)', '', content_str)
                    content_str = re.sub(r',\s*isError=(False|True)', '', content_str)
                
                tool_result = {
                    "tool": tool_name,
                    "step": step_counter,
                    "timestamp": datetime.now().isoformat(),
                    "content": content_str[:5000]  # Limit to 5000 bytes
                }
                
                # Add arguments if available from previous step
                if args_str != "None":
                    tool_result["arguments"] = args_str[:1000]  # Limit args to 1000 chars
                
                intermediate_results.append(tool_result)
                
                # Log the tool result
                result_preview = tool_result['content'][:200] + "..." if len(tool_result['content']) > 200 else tool_result['content']
                log_tool_result(step_counter, tool_name, result_preview)
        
        return result.get("final_response", "No response generated"), tools_used, intermediate_results
    except Exception as e:
        print(f"Error processing with MCP: {str(e)}")
        return f"Error processing with MCP: {str(e)}", [], []

@app.get("/api/mcp/tools", response_model=MCPToolsResponse)
async def get_mcp_tools():
    """Get available MCP tools and server status"""
    # Check if MCP is available
    if not mcp_available or mcp_platform is None:
        return MCPToolsResponse(
            initialized=False,
            tools=[],
            servers=[]
        )
    
    # Initialize MCP if not already initialized
    if not mcp_initialized:
        await initialize_mcp()
    
    # Get unique server names
    servers = list(set(tool.get("server", "") for tool in available_mcp_tools if "server" in tool))
    
    return MCPToolsResponse(
        initialized=mcp_initialized,
        tools=available_mcp_tools,
        servers=servers
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Single API endpoint for all chat modes"""
    print(f"Processing request - Model: {request.model}, Prompt: {request.prompt}")
    
    try:
        # Process with MCP Platform
        response, tools_used, intermediate_results = await process_with_mcp(request.prompt, request.model)
        return ChatResponse(
            response=response, 
            node_list=[], 
            mcp_tools_used=tools_used, 
            intermediate_results=intermediate_results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Use uvicorn programmatically
    uvicorn.run(app, host="0.0.0.0", port=8000)
