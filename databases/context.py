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
from interface import tool

def load_background(emb:OpenAIEmbeddings) -> FAISS:
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


class context_store(tool):

  emb:OpenAIEmbeddings
  store:FAISS

  def init(self, emb, store = None):
    self.emb = emb
    self.store = load_background(emb)

  def background_retrival(self,query_text:str) -> str:
    results = self.store.similarity_search(
        query_text,
        k=2)
    return results[0].page_content+"\n"+results[1].page_content