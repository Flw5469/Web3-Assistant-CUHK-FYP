from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from typing import List
from dotenv import load_dotenv
import os

################################################# Imported functions from notebooks
#################################################
#################################################
#################################################
import json
import faiss
from uuid import uuid4
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
import pandas as pd
from langchain_core.documents import Document
from langchain_community.graphs import Neo4jGraph
from langchain_openai import OpenAIEmbeddings
import models
import numpy 
LIMIT =2


load_dotenv()
os.environ["NEO4J_URI"] = os.getenv("NEO4J_URI")
os.environ["NEO4J_USERNAME"] = os.getenv("NEO4J_USERNAME") 
os.environ["NEO4J_PASSWORD"] = os.getenv("NEO4J_PASSWORD")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")
os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL")

graph = Neo4jGraph()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)
emb = OpenAIEmbeddings(base_url=os.getenv("OPENAI_BASE_URL"))

def get_model_value(model_name):
  return (models.model_list[model_name])[2]

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

def community_retrival(query:str, result)->str:
  return graph.query(f"""match (n:__Community__)--(m) where m.id=\"{result[0]["entityName"]}\" return n.summary, n.id""")

# Need to change, since the query now is returning the document node not the entity node.
# NEed to chance since now result 2 and also return source
def context_and_community_retrival(query:str)->str:
  value = emb.embed_query(query)
  result = graph.query(f"""WITH {value} AS queryEmbedding
  MATCH (e:`__Entity__`)
  WITH e, gds.similarity.cosine(e.embedding, queryEmbedding) AS similarity
  WHERE similarity IS NOT NULL
  RETURN e.id AS entityName, similarity, e.description AS description
  ORDER BY similarity DESC
  LIMIT 5""")
  community_result = community_retrival(query,result)
  return f"""
In general: {community_result[0]['n.summary']}
In specific: {result[0]["entityName"]}: \n {result[0]['description']}
"""

# baseline
# If no filter then will select all
def context_retrival(query:str, filter = [], database = "vector") -> tuple[list,list,list]:
  result = []
  result_string = []
  result_source = []
  result_node   = []
  value = emb.embed_query(query)

  if database == "neo4j":
    filter_statement = f", {filter} AS filter_coin_list" if filter else ""
    filter_statement2 =  "AND ANY(value IN filter_coin_list WHERE value IN e.coin_name)" if filter else ""

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
      print("ele: ",ele)
      query = f"""match (n:Document)--()--(m:Document) where n.id="{ele["id"]}" return m.id AS id, m.text AS text, m.source AS source limit 5"""
      print("query: ",query)
      neighbour_result+= graph.query(query)

    result+=neighbour_result
    result = result[:LIMIT]
    for ele in result:
      if ele['source'] not in result_source:
        result_source.append(ele['source'])
        result_string.append(ele['text'])
        result_node.append(ele['id'])

  
  if database == "vector":
    loaded_faiss_index = FAISS.load_local("faiss_index_with_metadata", emb, allow_dangerous_deserialization=True)
    query_result = loaded_faiss_index.similarity_search(query, k=LIMIT)  # Retrieve top-3 matches

    result_source = []
    result_string = []
    result_node = []
    for result in query_result:
      result_string.append(result.page_content)
      result_source.append(result.metadata['source'])


  result = (result_string, result_source, result_node)
  return result
  #return f"""{result[0]['id']}:\n{result[0]['text']}"""

def baseline(query, coin_list, model_name = "3.5", database = "vector") -> tuple[str,list,list, str]:
  (context, source_list, node_list) = context_retrival(query, coin_list, database)
  formatted_question = f"""You are a professional web3 analyst. Please answer questions for other web3 analyst strictly according to the below context.
############### Context ###########
{context}
################ Question ##########
{query}
################# Answer ###########
"""
  
  print(formatted_question)

  client = models.make_client_from_name(model_name)
  answer = client.chat.completions.create(
    model=get_model_value(model_name),
    messages=[
      {"role": "user", "content": formatted_question}
    ],
    timeout=20)
  result = answer.choices[0].message.content
  total_result = (result, source_list, node_list, formatted_question)
  print(total_result)
  return total_result

# Not using rn, chat2 endpoint switched to tool_search_wrapper
def enhanced(query, coin_list, model_name="3.5"):

    """
    Incorporates contextual and background information to form a detailed question for the LLM.
    """
    context, source = context_retrival(query, coin_list)
    background = background_retrival(vector_store, query)
    formatted_question = (
        "You are a professional web3 analyst. Please answer questions for other web3 analyst strictly according to the below context.\n"
        "############### Context ###########\n"
        f"{background}\n\n"
        f"{context}\n"
        "################ Question ##########\n"
        f"{query}\n"
        "################# Answer ###########\n"
    )
    
    client = models.make_client_from_name(model_name)
    answer = client.chat.completions.create(
        model=get_model_value(model_name),
        messages=[{"role": "user", "content": formatted_question}],
        timeout = 20
    )
    result = answer.choices[0].message.content
    return result, formatted_question, source


def get_coin_info(input):
  with open('coins_name.json', 'r') as file:
    # print("coinInput: ",input)
    coin_names = json.load(file)
  for coin in coin_names:
    if coin['coin'].lower() == input.lower():
      return coin
  return "UNKNOWN"

def get_current_price_wrapper(input):
  InputCoin = input['coin_name'].lower()
  coin_details=str(get_coin_info(InputCoin))
  print("coin_details: ",coin_details)
  if coin_details:
    problem = f"Given the information of {coin_details} is most updated"
    return f"""\n ######### Subquestion ############
    {problem}
    ###########################"""
  else:
     return f" The price of {input['coin_name']} now is UNKNOWN. "


def normalQuery(query, model_name = "3.5"):
  formatted_question = query
  
  client = models.make_client_from_name(model_name)
  answer = client.chat.completions.create(
    model=get_model_value(model_name),
    messages=[
      {"role": "user", "content": formatted_question}
    ],
    timeout = 20
  )
  print("answer: ", answer)
  result = answer.choices[0].message.content
  total_result = (result, formatted_question)
#   print(total_result)
  return total_result

#subquery is the subquestion from the query breakdown
def tool_search(query, coin_list) -> tuple[str, list, list]:
    """
    Executes context retrieval based on the subquery's type and returns a combined query,
    along with any source and node data.
    """
    subquery_text = query.get("subquestion")
    if subquery_text is None:
        return "", [], []

    query_type = query.get("type")
    retrieved_context = ""
    source_list = []
    node_list = []

    if query_type == "structured_data":
        price = get_current_price_wrapper(query)
        retrieved_context += f"{price}\n"
    elif query_type == "news":
        news_info = context_retrival(subquery_text, coin_list)
        # Join individual news items since news_info[0] is a list.
        news_text = "\n".join(news_info[0]) if isinstance(news_info[0], list) else news_info[0]
        retrieved_context += f"{news_text}\n"
        source_list.extend(news_info[1])
        node_list.extend(news_info[2])
    elif query_type == "general":
        general_info = context_and_community_retrival(subquery_text)
        retrieved_context += f"{general_info}\n"
        # Removed extending source_list and node_list because context_and_community_retrival returns a string.
    elif query_type == "domain_knowledge":
        domain_info = background_retrival(vector_store, subquery_text)
        retrieved_context += f"{domain_info}\n"
    else:
        print("Unexpected subquery_type:", query_type)
    
    print("retrieved_context:", retrieved_context)
    combined_query = subquery_text + retrieved_context
    return combined_query, source_list, node_list

def query_breakdown(question_text):
    """
    Breaks down the input question into subquestions with type classification.
    """
    prompt = (
        "You are a query classifier. Break down the question into subquestions if needed.\n"
        "Classify each subquestion into one of these types:\n"
        "- news (requires recent news/events data)\n"
        "- domain_knowledge (requires technical definitions/concepts)\n"
        "- structured_data (requires current market data/statistics)\n"
        "- general (only when not classified in the above types)\n\n"
        "Return your response in JSON format with the following structure:\n"
        "{\n"
        '  "subquestions": [\n'
        "    {\n"
        '      "subquestion": "the structured representation of the subquestion",\n'
        '      "type": "news|domain_knowledge|structured_data|general",\n'
        '      "explanation": "Brief explanation of why this type was chosen",\n'
        '      "coin_name": "the coin name if it is a coin price question"\n'
        "    }\n"
        "  ]\n"
        "}"
    )
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": question_text},
            ],
            response_format={"type": "json_object"},
        )
        result = completion.choices[0].message.content
        parsed_result = json.loads(result)
        return parsed_result.get("subquestions", [])
    except Exception as e:
        print(f"Error in query breakdown: {str(e)}")
        # Return the original question as a single subquestion if parsing fails.
        return [{"subquestion": question_text, "type": "general"}]

def tool_search_wrapper(original_query, coin_list=None, model="3.5") -> tuple[str, list, list]:
    """
    Integrates query breakdown and tool search to build a combined query processed by a baseline model.
    """
    final_answer = []
    source_list = []
    node_list = []
    
    sub_questions = query_breakdown(original_query)
    print("subQuestionList:", len(sub_questions))

    if not sub_questions:
        # Create a fallback subquestion dictionary if query breakdown fails.
        fallback_dict = {"subquestion": original_query, "type": "general"}
        tool_output, sources, nodes = tool_search(fallback_dict, coin_list)
        final_answer.append(tool_output)
        source_list.extend(sources)
        node_list.extend(nodes)
    else:
        for subq in sub_questions:
            print(subq.get("subquestion"), subq.get("type"))
            tool_output, sources, nodes = tool_search(subq, coin_list)
            final_answer.append(tool_output)
            source_list.extend(sources)
            node_list.extend(nodes)
    
    combined_answer = "\n".join(final_answer)
    complete_query = (
        f"question: {original_query}\n"
        f"answer: {combined_answer}\n"
        "please give a concise answer"
    )

    print("complete query: ",complete_query)
    # This baseline should eventually convert to pure LLM operation.
    baseline_answer = normalQuery(complete_query, model)
    return baseline_answer[0], source_list, node_list

#end of subquery part

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



class ChatRequest(BaseModel):
    prompt: str
    coin_name: List[str]  # Define coin_name as a list of strings
    model : str
    database : str


class ChatResponse(BaseModel):
    response: str
    node_list : list


@app.post("/api/chat1", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(request)
    print(request.prompt)
    print(request.model)
    ai_response = baseline(request.prompt, request.coin_name, request.model, request.database)

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
    ai_response = tool_search_wrapper(request.prompt, request.coin_name, request.model, request.database)

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

@app.post("/api/chat3", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(request)
    print(request.prompt)
    ai_response = tool_search(request.prompt, request.coin_name)
    formatted_response = ai_response[0]+f"\n\nSource from the recent news:\n\n"+"\n\n".join(ai_response[2])
    print(formatted_response)
    return ChatResponse(response=formatted_response, node_list=node_list)

@app.post("/api/chat4", response_model=ChatResponse)
async def chat(request: ChatRequest):
    print(request)
    print(request.prompt)
    ai_response = normalQuery(request.prompt, request.model)
    formatted_response = ai_response[0]#+f"\n\nSource from the recent news:\n\n"+"\n\n".join(ai_response[2])
    print(formatted_response)
    return ChatResponse(response=formatted_response, node_list = [])#, node_list=ai_response[2])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)