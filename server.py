from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict, Any
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import json
import faiss
import asyncio
from uuid import uuid4
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
import pandas as pd
from langchain_core.documents import Document
from langchain_community.graphs import Neo4jGraph
from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv

# Import MCPPlatform
from ai_agent.mcp_platform import MCPPlatform

# Load environment variables from .env file
load_dotenv()

# Setup Neo4j connection from environment variables
graph = Neo4jGraph()

# Initialize OpenAI client from environment variables
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

# Initialize embeddings
emb = OpenAIEmbeddings(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

# Initialize MCP Platform
mcp_platform = MCPPlatform()

# Constants
LIMIT = 2

# Track MCP platform status
mcp_initialized = False
available_mcp_tools = []

async def initialize_mcp():
    """Initialize the MCP platform and connect to all configured servers"""
    global mcp_initialized, available_mcp_tools
    
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

def load_background():
    """Load background knowledge from CSV file into vector store"""
    df = pd.read_csv('context_qa2.csv', encoding="unicode_escape")
    questions = df["Question"].to_list()
    answers = df["Answer"].to_list()
    backgrounds = [Document(page_content=str(question)+"\n"+str(answer)) 
                  for question, answer in zip(questions, answers)] 
    index = faiss.IndexFlatL2(len(emb.embed_query("hello world")))
    vector_store = FAISS(
        embedding_function=emb,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )
    uuids = [str(uuid4()) for _ in range(len(backgrounds))]
    vector_store.add_documents(documents=backgrounds, ids=uuids)
    return vector_store

vector_store = load_background()

def background_retrival(vector_store, query):
    """Retrieve background information from the vector store"""
    results = vector_store.similarity_search(query, k=2)
    return results[0].page_content + "\n" + results[1].page_content

def community_retrival(query: str, result) -> str:
    """Retrieve community information from Neo4j"""
    return graph.query(f"""match (n:__Community__)--(m) where m.id=\"{result[0]["entityName"]}\" return n.summary, n.id""")

def context_and_community_retrival(query: str) -> str:
    """Retrieve combined context and community information"""
    value = emb.embed_query(query)
    result = graph.query(f"""WITH {value} AS queryEmbedding
    MATCH (e:`__Entity__`)
    WITH e, gds.similarity.cosine(e.embedding, queryEmbedding) AS similarity
    WHERE similarity IS NOT NULL
    RETURN e.id AS entityName, similarity, e.description AS description
    ORDER BY similarity DESC
    LIMIT 5""")
    community_result = community_retrival(query, result)
    return f"""
In general: {community_result[0]['n.summary']}
In specific: {result[0]["entityName"]}: \n {result[0]['description']}
"""

def context_retrival(query: str, filter = []) -> Tuple[list, list, list]:
    """Retrieve context from Neo4j with optional filtering"""
    value = emb.embed_query(query)
    print("value is : ", value)
    filter_statement = f", {filter} AS filter_coin_list" if filter else ""
    filter_statement2 = "AND ANY(value IN filter_coin_list WHERE value IN e.coin_name)" if filter else ""

    result = graph.query(f"""WITH {value} AS queryEmbedding{filter_statement}
    MATCH (e:`Document`)
    WITH e, gds.similarity.cosine(e.embedding, queryEmbedding) AS similarity
    WHERE similarity IS NOT NULL {filter_statement2}
    RETURN e.id AS id, similarity, e.text AS text, e.source AS source
    ORDER BY similarity DESC
    LIMIT 5""")
    result = result[:LIMIT]
    neighbour_result = []
    for ele in result:
        print("ele: ", ele)
        query = f"""match (n:Document)--()--(m:Document) where n.id="{ele["id"]}" return m.id AS id, m.text AS text, m.source AS source limit 5"""
        print("query: ", query)
        neighbour_result += graph.query(query)

    result += neighbour_result
    result = result[:LIMIT*2]
    result_string = []
    result_source = []
    result_node = []

    for ele in result:
        if ele['source'] not in result_source:
            result_source.append(ele['source'])
            result_string.append(ele['text'])
            result_node.append(ele['id'])

    return (result_string, result_source, result_node)

def map_model_name(model: str) -> str:
    """Map short model names to full model names"""
    if model == "3.5":
        return "gpt-3.5-turbo"
    elif model == "4o":
        return "gpt-4o"
    return model

def baseline(query, coin_list, model = "3.5") -> Tuple[str, list, list, str]:
    """Baseline query method using context retrieval"""
    (context, source_list, node_list) = context_retrival(query, coin_list)
    formatted_question = f"""You are a professional web3 analyst. Please answer questions for other web3 analyst strictly according to the below context.
############### Context ###########
{context}
################ Question ##########
{query}
################# Answer ###########
"""
    
    print(formatted_question)
    model = map_model_name(model)

    answer = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": formatted_question}
        ],
        timeout=50000)
    result = answer.choices[0].message.content
    total_result = (result, source_list, node_list, formatted_question)
    print(total_result)
    return total_result

def enhanced(query, coin_list, model = "3.5") -> Tuple[str, str, list]:
    """Enhanced query method using both context and background retrieval"""
    context, source = context_retrival(query, coin_list)
    background = background_retrival(vector_store, query)
    formatted_question = f"""You are a professional web3 analyst. Please answer questions for other web3 analyst strictly according to the below context.
############### Context ###########
{background}

{context}
################ Question ##########
{query}
################# Answer ###########
"""
    
    model = map_model_name(model)

    answer = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": formatted_question}
        ])
    result = answer.choices[0].message.content
    return (result, formatted_question, source)

def get_coin_info(input):
    """Get information about a specific coin from JSON file"""
    with open('coins_name.json', 'r') as file:
        coin_names = json.load(file)
    for coin in coin_names:
        if coin['coin'].lower() == input.lower():
            return coin
    return "UNKNOWN"

def get_current_price_wrapper(input):
    """Wrapper to get current price information for a coin"""
    InputCoin = input['coin_name'].lower()
    coin_details = str(get_coin_info(InputCoin))
    print("coin_details: ", coin_details)
    if coin_details:
        problem = f"Given the information of {coin_details} is most updated"
        return f"""\n ######### Subquestion ############
        {problem}
        ###########################"""
    else:
        return f" The price of {input['coin_name']} now is UNKNOWN. "

def normalQuery(query, model = "3.5") -> Tuple[str, str]:
    """Simple query directly to the LLM without additional context"""
    model = map_model_name(model)
    
    answer = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": query}
        ])
    result = answer.choices[0].message.content
    return (result, query)

def tool_search(query, coin_list) -> Tuple[str, list, list]:
    """Search using different tools based on query type"""
    subquery = query.get("subquestion")
    if not subquery:
        return ("", [], [])
    
    subquery_type = query.get("type")
    retrieved_context = ""
    source_list = []
    node_list = []

    if subquery_type == "structured_data":
        price = get_current_price_wrapper(query)
        retrieved_context += str(price) + "\n"
    elif subquery_type == "news":
        news_info = context_retrival(subquery, coin_list)
        retrieved_context += str(news_info[0]) + "\n"
        source_list += news_info[1]
        node_list += news_info[2]
    elif subquery_type == "general":
        general_info = context_and_community_retrival(subquery)
        retrieved_context += str(general_info) + "\n"
    elif subquery_type == "domain_knowledge":
        domain_info = background_retrival(vector_store, subquery)
        retrieved_context += str(domain_info) + "\n"
    else:
        print("Unexpected subquery_type", subquery_type)
    
    print("retrieved_context: ", retrieved_context)
    combined_query = subquery + retrieved_context
    return (combined_query, source_list, node_list)

def query_breakdown(input):
    """Break down a query into subquestions by type"""
    prompt = """You are a query classifier. Break down the question into subquestions if needed.
    Classify each subquestion into one of these types:
    - news (requires recent news/events data)
    - domain_knowledge (requires technical definitions/concepts) 
    - structured_data (requires current market data/statistics)
    - general (only when not classified in the above types)
    
    Return your response in JSON format with the following structure:
    {
      "subquestions": [
        {
          "subquestion": "the structured representation of the subquestion",
          "type": "news|domain_knowledge|structured_data|general",
          "explanation": "Brief explanation of why this type was chosen",
          "coin_name": "the coin name if it is a coin price question"
        }
      ]
    }"""
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": input}
            ],
            response_format={"type": "json_object"}
        )
        
        result = completion.choices[0].message.content
        parsed_result = json.loads(result)
        return parsed_result.get("subquestions", [])
        
    except Exception as e:
        print(f"Error in query breakdown: {str(e)}")
        # Return the original query as a single subquestion if parsing fails
        return [{
            "subquestion": input,
            "type": "general"
        }]

def tool_search_wrapper(input, coin_list = None, model = "3.5") -> Tuple[str, list, list]:
    """Wrapper for tool search that breaks down queries and combines results"""
    final_answer = []
    source_list = []
    node_list = []
    
    subQuestionList = query_breakdown(input)
    print("subQuestionList: ", len(subQuestionList))

    if len(subQuestionList) == 0:
        return (input, [], [])
    
    for subq in subQuestionList:
        print(subq.get("subquestion"), subq.get("type"))
        toolsComplete = tool_search(subq, coin_list)
        final_answer.append(toolsComplete[0])
        source_list += toolsComplete[1]
        node_list += toolsComplete[2]

    combined_answer = "\n".join(final_answer)
    complete_query = f"""question:{input} \n answer: {combined_answer}
    please give a concise answer"""
    
    baseline_answer = normalQuery(complete_query, model)
    return (baseline_answer[0], source_list, node_list)

# Initialize FastAPI app
app = FastAPI()

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
    coin_name: List[str]
    model: str = "3.5"
    mode: str = "baseline"  # 'baseline', 'tool_search', 'direct', 'enhanced', 'mcp'
    use_mcp: bool = False

class ChatResponse(BaseModel):
    response: str
    node_list: Optional[list] = None
    mcp_tools_used: Optional[List[str]] = None

class MCPToolsResponse(BaseModel):
    initialized: bool
    tools: List[Dict[str, Any]]
    servers: List[str]

@app.get("/api/mcp/tools", response_model=MCPToolsResponse)
async def get_mcp_tools():
    """Get available MCP tools and server status"""
    global mcp_initialized, available_mcp_tools
    
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

async def process_with_mcp(prompt: str, model: str) -> Tuple[str, List[str]]:
    """Process a query using MCP Platform"""
    global mcp_initialized, mcp_platform
    
    # Initialize MCP if not already initialized
    if not mcp_initialized:
        await initialize_mcp()
    
    if not mcp_initialized:
        return "MCP Platform is not initialized. Please check server logs.", []
    
    try:
        # Set the model to use
        mcp_platform.model = map_model_name(model)
        
        # Process query through MCP
        result = await mcp_platform.process_query(prompt)
        
        # Track the tools used in this conversation
        tools_used = []
        for step in result.get("conversation_steps", []):
            if step.get("role") == "tool" and "name" in step:
                tools_used.append(step["name"])
        
        return result.get("final_response", "No response generated"), tools_used
    except Exception as e:
        print(f"Error processing with MCP: {str(e)}")
        return f"Error processing with MCP: {str(e)}", []

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Single API endpoint for all chat modes"""
    print(f"Processing request - Mode: {request.mode}, Model: {request.model}, Prompt: {request.prompt}, Use MCP: {request.use_mcp}")
    
    try:
        # Use MCP Platform if requested and available
        if request.use_mcp:
            response, tools_used = await process_with_mcp(request.prompt, request.model)
            return ChatResponse(response=response, node_list=[], mcp_tools_used=tools_used)
        
        # Traditional processing modes
        if request.mode == "baseline":
            ai_response = baseline(request.prompt, request.coin_name, request.model)
            source = "".join([str(ele) for ele in ai_response[1] if ele is not None])
            response = ai_response[0] + f"\n\nSource from the recent news:\n\n" + source
            return ChatResponse(response=response, node_list=ai_response[2])
            
        elif request.mode == "tool_search":
            ai_response = tool_search_wrapper(request.prompt, request.coin_name, request.model)
            source = "".join([str(ele) for ele in ai_response[1] if ele is not None])
            response = ai_response[0] + f"\n\nSource from the recent news:\n\n" + source
            return ChatResponse(response=response, node_list=ai_response[2])
            
        elif request.mode == "direct":
            ai_response = normalQuery(request.prompt, request.model)
            return ChatResponse(response=ai_response[0])
            
        elif request.mode == "enhanced":
            ai_response = enhanced(request.prompt, request.coin_name, request.model)
            return ChatResponse(response=ai_response[0], node_list=[])
        
        elif request.mode == "mcp":
            response, tools_used = await process_with_mcp(request.prompt, request.model)
            return ChatResponse(response=response, node_list=[], mcp_tools_used=tools_used)
            
        else:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Cleanup function to shut down MCP platform when server stops
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when FastAPI server is shutting down"""
    global mcp_platform
    try:
        await mcp_platform.cleanup()
        print("MCP Platform resources cleaned up")
    except Exception as e:
        print(f"Error during MCP cleanup: {str(e)}")

if __name__ == "__main__":
    # Initialize MCP platform in the background
    asyncio.create_task(initialize_mcp())
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)
