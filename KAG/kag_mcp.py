from typing import Any
import httpx
import asyncio
from mcp.server.fastmcp import FastMCP
import json

# Initialize FastMCP server
mcp = FastMCP("kag")

# Constants
BASE_URL = "http://localhost:8887"
DEFAULT_SESSION_ID = 2
DEFAULT_PROJECT_ID = 1
DEFAULT_USER_ID = 111111

async def make_kag_request(method: str, endpoint: str, json_data: dict = None) -> dict[str, Any] | None:
    """Make a request to the KAG API with proper error handling."""
    headers = {
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            if method == "POST":
                response = await client.post(url, json=json_data, headers=headers, timeout=30.0)
            else:
                response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error making KAG request: {str(e)}")
            return None

async def poll_query_status(job_id: str) -> dict[str, Any] | None:
    """Poll the query status until it's finished."""
    while True:
        data = await make_kag_request("GET", f"/v1/datas/query/{job_id}")
        if not data:
            return None
        
        if data["success"] and data["result"]["status"] == "FINISH":
            return data
        
        await asyncio.sleep(1)  # Wait 1 second before polling again

def format_node(node: dict) -> str:
    """Format a node into a readable string."""
    return f"""
Node {node['id']}:
  Title: {node['title']}
  Question: {node['question']}
  Answer: {node['answer'][:200]}...""" if len(node['answer']) > 200 else f"""
  Answer: {node['answer']}"""

@mcp.tool()
async def query_knowledge_base(
    instruction: str,
    type_: str = "NL",
    session_id: int = DEFAULT_SESSION_ID,
    project_id: int = DEFAULT_PROJECT_ID,
    user_id: int = DEFAULT_USER_ID
) -> str:
    """Query the knowledge base with a natural language instruction.

    Args:
        instruction: The natural language query
        type_: Query type (default: "NL" for Natural Language)
        session_id: Session ID (default: 2)
        project_id: Project ID (default: 1)
        user_id: User ID (default: 111111)
    """
    # Submit the query
    payload = {
        "userId": user_id,
        "sessionId": session_id,
        "projectId": project_id,
        "instruction": instruction,
        "document": "",
        "type": type_
    }
    
    submit_response = await make_kag_request("POST", "/v1/datas/asyncSubmit", payload)
    if not submit_response:
        return "Error: Unable to submit query to server."
    
    job_id = submit_response["result"]["id"]
    
    # Poll for results
    result_data = await poll_query_status(job_id)
    if not result_data:
        return "Error: Unable to get query results from server."
    
    try:
        # Parse the result message
        result_message_str = result_data["result"]["resultMessage"]
        result_message = json.loads(result_message_str)
        nodes = result_message["nodes"]
        
        # Get the final answer (node with id "0")
        ai_response_node = next((node for node in nodes if node["id"] == "0"), None)
        if not ai_response_node or not ai_response_node["answer"].strip():
            return "No answer provided by the knowledge base."
        
        # Format the response
        response = f"""
AI Response:
{ai_response_node['answer'].strip()}

Detailed Node List:
{'-'*80}"""
        
        for node in nodes:
            response += format_node(node)
            
        return response
        
    except Exception as e:
        return f"Error processing response: {str(e)}"

if __name__ == "__main__":
    print("Starting MCP KAG Server...")
    print("Use Ctrl+C to stop the server")
    # Initialize and run the server
    mcp.run(transport='stdio') 