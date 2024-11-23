from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from typing import List

################################################# Imported functions from notebooks
#################################################
#################################################
#################################################
import faiss
from uuid import uuid4
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
import pandas as pd
from langchain_core.documents import Document
from langchain_community.graphs import Neo4jGraph
from langchain_openai import OpenAIEmbeddings
import os
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "staysovryn"
os.environ["OPENAI_API_KEY"] = "sk-sJAILfYY4hF8aVTM73A26fB09c834c7b8c41D4CeB652Fe95"
graph = Neo4jGraph()
client = OpenAI(api_key = "sk-sJAILfYY4hF8aVTM73A26fB09c834c7b8c41D4CeB652Fe95",base_url="https://openai.ss-gpt.com/v1")

emb = OpenAIEmbeddings(base_url="https://openai.ss-gpt.com/v1")

# baseline
# If no filter then will select all
limit =2
def context_retrival(query:str, filter = []):
  value = emb.embed_query(query)
  filter_statement = f", {filter} AS filter_coin_list" if filter else ""
  filter_statement2 =  "AND ANY(value IN filter_coin_list WHERE value IN e.coin_name)" if filter else ""

  result = graph.query(f"""WITH {value} AS queryEmbedding{filter_statement}
  MATCH (e:`Document`)
  WITH e, gds.similarity.cosine(e.embedding, queryEmbedding) AS similarity
  WHERE similarity IS NOT NULL {filter_statement2}
  RETURN e.id AS id, similarity, e.text AS text, e.source AS source
  ORDER BY similarity DESC
  LIMIT 5""")
  result = result[:limit]
  temp_result = []
  for ele in result:
    print("ele: ",ele)
    query = f"""match (n:Document)--()--(m:Document) where n.id="{ele["id"]}" return m.id AS id, m.text AS text, m.source AS source limit 5"""
    print("query: ",query)
    temp_result+= graph.query(query)

  result+=temp_result

  result = result[:limit*2]
  result_string = []
  result_source = []

  for ele in result:
    if ele['source'] not in result_source:
      result_source.append(ele['source'])
      result_string.append(ele['text'])

  return result_string, result_source

def load_background():
  # Read CSV file into a DataFrame
  df = pd.read_csv('context_qa2.csv',encoding="unicode_escape")
  questions = df["Question"].to_list()
  answers = df["Answer"].to_list()
  backgrounds = [Document(page_content = str(question)+"\n"+str(answer)) for question,answer in zip(questions,answers)] 
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

def background_retrival(vector_store,query):
  results = vector_store.similarity_search(
      query,
      k=2)
  return results[0].page_content+"\n"+results[1].page_content

def baseline(query, filter = [], tool_output = "", tool_source = [], background = ""):
  context, source = context_retrival(query, filter)
  formatted_question = f"""You are a professional web3 analyst. Please answer questions for other web3 analyst strictly according to the below context.
############### Context ###########
{background}
{context}
{tool_output}
################ Question ##########
{query}
################# Answer ###########
"""
  
  print(formatted_question)


  answer = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
      {"role": "user", "content": formatted_question}
    ])
  result = answer.choices[0].message.content
  total_result = (result, formatted_question, tool_source+ source)
  print(total_result)
  return total_result


def enhanced(query, filter = [], tool_output = "", tool_source = []):
  background = background_retrival(vector_store,query)
  return baseline(query,filter, tool_output, tool_source, background)

import requests
def get_current_price(symbol):
    url = f'https://api.binance.com/api/v3/ticker/price'
    params = {'symbol': symbol+"USDT"}
    response = requests.get(url, params=params)
    data = response.json()
    usdt_price = float(data['price'])
    return usdt_price
coin_names = {
  'bitcoin': 'BTC',
  'ethereum': 'ETH',
  'binance coin': 'BNB',
  'ripple': 'XRP',
  'solana': 'SOL',
  'cardano': 'ADA',
  'dogecoin': 'DOGE',
  'polygon': 'MATIC',
  'polkadot':"DOT",
  'avalanche': 'AVAX'
}
def get_current_price_wrapper(input):
  if input['coin_name'].lower() in coin_names:
    return f"""\n ######### Context ############
The price of {input['coin_name']} now is : {str(get_current_price(coin_names[input['coin_name'].lower()]))}
###########################""", ["https://api.binance.com"]
  else:
     return f" The price of {input['coin_name']} now is UNKNOWN. ", ["https://api.binance.com"]
  
from openai import OpenAI
import openai
from pydantic import BaseModel
import json

client = OpenAI(api_key = "sk-sJAILfYY4hF8aVTM73A26fB09c834c7b8c41D4CeB652Fe95",base_url="https://openai.ss-gpt.com/v1")

class coin(BaseModel):
  coin_name:str

def query_with_tools(input):
  tools = [openai.pydantic_function_tool(coin)]
  print("query_with_tools: ", input)
  completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
      {"role": "assistant", "content": """You are an Web3 assistant who can answer call tools to get context. Please call tools only if the context is missing and you need to retrieve the required information to answer questions. Otherwise output the answer directly."""},
      {"role": "user", "content": input}
    ],
    tools=tools
    #response_format={ "type": "json_object" },
  )
  print("Completion: ",completion)
  return completion

def tool_search(query, filter=[]):
  completion = query_with_tools(query)
  print(completion)
  answer = completion.choices[0].message.content

  tool_output = ""
  tool_source = []
  if completion.choices[0].message.tool_calls!=None:
    function_name = completion.choices[0].message.tool_calls[0].function.name
    function_args = completion.choices[0].message.tool_calls[0].function.arguments

    print("The argument: ")
    print(completion.choices[0].message.tool_calls[0].function.arguments) 
    data = json.loads(function_args)
    if data:
      print("received data!")
      if (function_name=="coin"):
        tool_output, tool_source = get_current_price_wrapper(data)
        
  answer = enhanced(query,[],tool_output, tool_source)
  print("Question: ",query)
  print("Answer: ",answer)
  return answer



#################################################
#################################################
###################################################



app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = OpenAI(
    api_key="sk-sJAILfYY4hF8aVTM73A26fB09c834c7b8c41D4CeB652Fe95",
    base_url="https://openai.ss-gpt.com/v1"
)

class ChatRequest(BaseModel):
    prompt: str
    coin_name: List[str]  # Define coin_name as a list of strings


class ChatResponse(BaseModel):
    response: str

# @app.post("/api/chat", response_model=ChatResponse)
# async def chat(request: ChatRequest):
#     print(request)
#     try:
#         completion = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "user", "content": request.prompt}
#             ]
#         )
        
#         # Extract the response from the completion
#         ai_response = completion.choices[0].message.content
        
#         return ChatResponse(response=ai_response)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat1", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(request)
    print(request.prompt)
    ai_response = baseline(request.prompt, request.coin_name)
    formatted_response = ai_response[0]+f"\n\nSource from the recent news:\n\n"+"\n\n".join(ai_response[2])
    print(formatted_response)
    return ChatResponse(response=formatted_response)

@app.post("/api/chat2", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(request)
    print(request.prompt)
    ai_response = enhanced(request.prompt, request.coin_name)
    formatted_response = ai_response[0]+f"\n\nSource from the recent news:\n\n"+"\n\n".join(ai_response[2])
    print(formatted_response)
    return ChatResponse(response=formatted_response)

@app.post("/api/chat3", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(request)
    print(request.prompt)
    ai_response = tool_search(request.prompt, request.coin_name)
    formatted_response = ai_response[0]+f"\n\nSource from the recent news:\n\n"+"\n\n".join(ai_response[2])
    print(formatted_response)
    return ChatResponse(response=formatted_response)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
