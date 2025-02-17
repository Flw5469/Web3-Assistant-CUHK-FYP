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
import os
from dotenv import load_dotenv
from typing import Optional
from interface import query_result_object, tool

LIMIT =2


load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")
os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL")





# def community_retrival(query:str, result)->str:
#   return graph.query(f"""match (n:__Community__)--(m) where m.id=\"{result[0]["entityName"]}\" return n.summary, n.id""")

# def context_and_community_retrival(query:str, emb:OpenAIEmbeddings)->str:
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

class neo4j_store(tool):

  emb = None
  graph = None

  def init(self, graph, emb):
    self.emb = emb
    self.graph = graph

  def query(self, query_text:str, filter = []) -> query_result_object:
    result = []
    result_string = []
    result_source = []
    result_node   = []
    value = self.emb.embed_query(query_text)

    filter_statement = f", {filter} AS filter_coin_list" if filter else ""
    filter_statement2 =  "AND ANY(value IN filter_coin_list WHERE value IN e.coin_name)" if filter else ""

    result = self.graph.query(f"""WITH {value} AS queryEmbedding{filter_statement}
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
      query_text = f"""match (n:Document)--()--(m:Document) where n.id="{ele["id"]}" return m.id AS id, m.text AS text, m.source AS source limit 5"""
      print("query: ",query_text)
      neighbour_result+= self.graph.query(query_text)

    result+=neighbour_result
    result = result[:LIMIT]
    for ele in result:
      if ele['source'] not in result_source:
        result_source.append(ele['source'])
        result_string.append(ele['text'])
        result_node.append(ele['id'])

    result = query_result_object(result_string, result_source, result_node)
    return result