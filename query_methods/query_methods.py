# Ignorable

# import json
# import faiss
# from uuid import uuid4
# from langchain_community.docstore.in_memory import InMemoryDocstore
# from langchain_community.vectorstores import FAISS
# import pandas as pd
# from langchain_core.documents import Document
# from langchain_community.graphs import Neo4jGraph
# from langchain_openai import OpenAIEmbeddings
# import models
# import numpy 
# import os
# from dotenv import load_dotenv
# from typing import Optional


# LIMIT =2


# load_dotenv()
# os.environ["NEO4J_URI"] = os.getenv("NEO4J_URI")
# os.environ["NEO4J_USERNAME"] = os.getenv("NEO4J_USERNAME") 
# os.environ["NEO4J_PASSWORD"] = os.getenv("NEO4J_PASSWORD")
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
# os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")
# os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL")

# graph = Neo4jGraph()
# client = OpenAI(
#     api_key=os.getenv("OPENAI_API_KEY"),
#     base_url=os.getenv("OPENAI_BASE_URL")
# )
# emb = OpenAIEmbeddings(base_url=os.getenv("OPENAI_BASE_URL"))

# def get_model_value(model_name):
#   return (models.model_list[model_name])[2]

# def load_background():
#   # Read CSV file into a DataFrame
#   df = pd.read_csv('context_qa2.csv',encoding="unicode_escape")
#   questions = df["Question"].to_list()
#   answers = df["Answer"].to_list()
#   backgrounds = [Document(page_content = str(question)+"\n"+str(answer)) for question,answer in zip(questions,answers)] 
#   index = faiss.IndexFlatL2(len(emb.embed_query("hello world")))
#   vector_store = FAISS(
#       embedding_function=emb,
#       index=index,
#       docstore=InMemoryDocstore(),
#       index_to_docstore_id={},
#   )
#   uuids = [str(uuid4()) for _ in range(len(backgrounds))]
#   vector_store.add_documents(documents=backgrounds, ids=uuids)
#   return vector_store

# vector_store = load_background()

# def background_retrival(vector_store,query):
#   results = vector_store.similarity_search(
#       query,
#       k=2)
#   return results[0].page_content+"\n"+results[1].page_content

# def community_retrival(query:str, result)->str:
#   return graph.query(f"""match (n:__Community__)--(m) where m.id=\"{result[0]["entityName"]}\" return n.summary, n.id""")

# # Need to change, since the query now is returning the document node not the entity node.
# # NEed to chance since now result 2 and also return source
# def context_and_community_retrival(query:str)->str:
#   value = emb.embed_query(query)
#   result = graph.query(f"""WITH {value} AS queryEmbedding
#   MATCH (e:`__Entity__`)
#   WITH e, gds.similarity.cosine(e.embedding, queryEmbedding) AS similarity
#   WHERE similarity IS NOT NULL
#   RETURN e.id AS entityName, similarity, e.description AS description
#   ORDER BY similarity DESC
#   LIMIT 5""")
#   community_result = community_retrival(query,result)
#   return f"""
# In general: {community_result[0]['n.summary']}
# In specific: {result[0]["entityName"]}: \n {result[0]['description']}
# """

# # baseline
# # If no filter then will select all
# def context_retrival(query:str, filter = [], database = "vector") -> tuple[list,list,list]:
#   result = []
#   result_string = []
#   result_source = []
#   result_node   = []
#   value = emb.embed_query(query)

#   if database == "neo4j":
#     filter_statement = f", {filter} AS filter_coin_list" if filter else ""
#     filter_statement2 =  "AND ANY(value IN filter_coin_list WHERE value IN e.coin_name)" if filter else ""

#     result = graph.query(f"""WITH {value} AS queryEmbedding{filter_statement}
#     MATCH (e:`Document`)
#     WITH e, gds.similarity.cosine(e.embedding, queryEmbedding) AS similarity
#     WHERE similarity IS NOT NULL {filter_statement2}
#     RETURN e.id AS id, similarity, e.text AS text, e.source AS source
#     ORDER BY similarity DESC
#     LIMIT 5""")
#     result = result[:LIMIT]
#     neighbour_result = []
#     for ele in result:
#       print("ele: ",ele)
#       query = f"""match (n:Document)--()--(m:Document) where n.id="{ele["id"]}" return m.id AS id, m.text AS text, m.source AS source limit 5"""
#       print("query: ",query)
#       neighbour_result+= graph.query(query)

#     result+=neighbour_result
#     result = result[:LIMIT]
#     for ele in result:
#       if ele['source'] not in result_source:
#         result_source.append(ele['source'])
#         result_string.append(ele['text'])
#         result_node.append(ele['id'])

  
#   if database == "vector":
#     loaded_faiss_index = FAISS.load_local("faiss_index_with_metadata", emb, allow_dangerous_deserialization=True)
#     query_result = loaded_faiss_index.similarity_search(query, k=LIMIT)  # Retrieve top-3 matches

#     result_source = []
#     result_string = []
#     result_node = []
#     for result in query_result:
#       result_string.append(result.page_content)
#       result_source.append(result.metadata['source'])


#   result = (result_string, result_source, result_node)
#   return result
#   #return f"""{result[0]['id']}:\n{result[0]['text']}"""











# #subquery is the subquestion from the query breakdown
