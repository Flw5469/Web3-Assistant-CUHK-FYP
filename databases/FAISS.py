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
from interface import query_result_object

LIMIT =2


load_dotenv()
os.environ["NEO4J_URI"] = os.getenv("NEO4J_URI")
os.environ["NEO4J_USERNAME"] = os.getenv("NEO4J_USERNAME") 
os.environ["NEO4J_PASSWORD"] = os.getenv("NEO4J_PASSWORD")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")
os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL")

class FAISS_store():
  
  emb:OpenAIEmbeddings
  store: FAISS

  def __init__(self, emb:OpenAIEmbeddings):
    self.emb = emb
    self.store = FAISS.load_local("faiss_index_with_metadata", emb, allow_dangerous_deserialization=True)

  def query(self, query_text:str) -> query_result_object:

    query_result = self.store.similarity_search(query_text, k=LIMIT)

    result_source = []
    result_string = []
    result_node = []
    for result in query_result:
      result_string.append(result.page_content)
      result_source.append(result.metadata['source'])
  
    result = query_result(result_string, result_source, result_node)
    return result