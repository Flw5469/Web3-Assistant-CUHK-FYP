from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from query_methods.baseline import baseline
from query_methods.normalQuery import normalQuery
from query_methods.tool_search import tool_search_wrapper
import models 
from interface import model_object
from databases.neo4j import neo4j_store
from databases.context import context_store
from langchain_community.graphs import Neo4jGraph
from langchain_openai import OpenAIEmbeddings
import models
import numpy 
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


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
    coin_name: List[str]  # Define coin_name as a list of strings
    model : str
    database : str


class ChatResponse(BaseModel):
    response: str
    node_list : list

load_dotenv()
os.environ["NEO4J_URI"] = os.getenv("NEO4J_URI")
os.environ["NEO4J_USERNAME"] = os.getenv("NEO4J_USERNAME") 
os.environ["NEO4J_PASSWORD"] = os.getenv("NEO4J_PASSWORD")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")
os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL")

graph = Neo4jGraph()
emb = OpenAIEmbeddings(base_url=os.getenv("OPENAI_BASE_URL"))

tool_list = {
    "neo4j":neo4j_store(graph, emb),
    "context":context_store(emb)
}


@app.post("/api/chat1", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(request)
    print(request.prompt)
    print(request.model)

    client = models.make_client_from_name(request.model)
    model_obj = model_object(client, request.model)

    ai_response = baseline(request.prompt, request.coin_name, model_obj, request.database)

    node_list = ai_response[2]
    source = ""
    for ele in ai_response[1]:
        if ele is not None:
            source += f"- [{ele}]({ele})\n"

    if source != "":
       formatted_response = ai_response[0]+f"\n\nSource from the recent news:\n\n"+source
    else:
       formatted_response = ai_response[0]
       node_list = []

    print(formatted_response)

    return ChatResponse(response=formatted_response, node_list = node_list)

@app.post("/api/chat2", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(request)
    print(request.prompt)

    client = models.make_client_from_name(request.model)
    model_obj = model_object(client, request.model)

    ai_response = tool_search_wrapper(request.prompt, request.coin_name, model_obj, request.database)

    node_list = ai_response[2]
    source = ""
    for ele in ai_response[1]:
        if ele is not None:
            source += f"- [{ele}]({ele})\n"

    if source != "":
       formatted_response = ai_response[0]+f"\n\nSource from the recent news:\n\n"+source
    else:
       formatted_response = ai_response[0]
       node_list = []

    print(formatted_response)

    return ChatResponse(response=formatted_response, node_list=node_list)

# @app.post("/api/chat3", response_model=ChatResponse)
# async def chat(request: ChatRequest):
#     print(request)
#     print(request.prompt)
#     ai_response = query.tool_search(request.prompt, request.coin_name)
#     formatted_response = ai_response[0]+f"\n\nSource from the recent news:\n\n"+"\n\n".join(ai_response[2])
#     print(formatted_response)
#     return ChatResponse(response=formatted_response, node_list=node_list)

@app.post("/api/chat3", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(request)
    print(request.prompt)

    client = models.make_client_from_name(request.model)
    model_obj = model_object(client, request.model)

    ai_response = normalQuery(request.prompt, model_obj)
    formatted_response = ai_response[0]#+f"\n\nSource from the recent news:\n\n"+"\n\n".join(ai_response[2])
    print(formatted_response)
    return ChatResponse(response=formatted_response, node_list = [])#, node_list=ai_response[2])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)