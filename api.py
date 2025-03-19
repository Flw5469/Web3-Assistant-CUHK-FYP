from mcp.server.fastmcp import FastMCP
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# Initialize the FastMCP server
server = FastMCP("RAG server")

# (Optional) Enable CORS middleware if needed.
# Uncomment the following code block if you want to allow CORS.
# server.app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, replace with your frontend URL
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Initialize the OpenAI client (dummy implementation here; replace with your actual client and credentials)
from openai import OpenAI  # Ensure that you have an appropriate OpenAI package installed
client = OpenAI(
    api_key="sk-sJAILfYY4hF8aVTM73A26fB09c834c7b8c41D4CeB652Fe95",
    base_url="https://openai.ss-gpt.com/v1"
)

# Define Pydantic models for the request and response data
class ChatRequest(BaseModel):
    prompt: str
    coin_name: List[str]  # Define coin_name as a list of strings
    model: str

class ChatResponse(BaseModel):
    response: str
    node_list: List

# Dummy implementations for helper functions.
# Replace these with your actual implementations.
def baseline(prompt: str, coin_name: List[str], model: str):
    # Return a tuple: (response, list_of_sources, node_list)
    return ("Baseline response", ["Source A", "Source B"], ["Node1", "Node2"])

def tool_search_wrapper(prompt: str, coin_name: List[str], model: str):
    return ("Tool search wrapper response", ["Source C", "Source D"], ["Node3", "Node4"])

def tool_search(prompt: str, coin_name: List[str]):
    return ("Tool search response", None, ["Node5", "Node6", "Node7"])

def normalQuery(prompt: str, model: str):
    return ("Normal query response",)

# Define your endpoints using the MCP server tools

@server.tool("/api/chat1", response_model=ChatResponse)
async def chat1(request: ChatRequest):
    print("Request from chat1 endpoint:", request)
    print("Prompt:", request.prompt)
    print("Model:", request.model)
    ai_response = baseline(request.prompt, request.coin_name, request.model)
    
    source = ""
    for ele in ai_response[1]:
        if ele is not None:
            source += ele
    
    formatted_response = (
        ai_response[0] +
        "\n\nSource from the recent news:\n\n" +
        source
    )
    print("Formatted response:", formatted_response)
    return ChatResponse(response=formatted_response, node_list=ai_response[2])

@server.tool("/api/chat2", response_model=ChatResponse)
async def chat2(request: ChatRequest):
    print("Request from chat2 endpoint:", request)
    print("Prompt:", request.prompt)
    ai_response = tool_search_wrapper(request.prompt, request.coin_name, request.model)
    
    source = ""
    for ele in ai_response[1]:
        if ele is not None:
            source += ele
    
    formatted_response = (
        ai_response[0] +
        "\n\nSource from the recent news:\n\n" +
        source
    )
    print("Formatted response:", formatted_response)
    return ChatResponse(response=formatted_response, node_list=ai_response[2])

@server.tool("/api/chat3", response_model=ChatResponse)
async def chat3(request: ChatRequest):
    print("Request from chat3 endpoint:", request)
    print("Prompt:", request.prompt)
    ai_response = tool_search(request.prompt, request.coin_name)
    
    formatted_response = (
        ai_response[0] +
        "\n\nSource from the recent news:\n\n" +
        "\n\n".join(ai_response[2])
    )
    print("Formatted response:", formatted_response)
    return ChatResponse(response=formatted_response, node_list=ai_response[2])

@server.tool("/api/chat4", response_model=ChatResponse)
async def chat4(request: ChatRequest):
    print("Request from chat4 endpoint:", request)
    print("Prompt:", request.prompt)
    ai_response = normalQuery(request.prompt, request.model)
    
    formatted_response = ai_response[0]
    print("Formatted response:", formatted_response)
    return ChatResponse(response=formatted_response, node_list=[])

if __name__ == "__main__":
    server.run()