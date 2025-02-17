from openai import OpenAI

class query_result_object:
  string = []
  source = []
  node   = []

  def init(self, string, source, node):
    self.string = string
    self.source = source
    self.node = node

  def __add__(self, other:'query_result_object'):
    self.string += other.string
    self.source += other.source
    self.node   += other.node

# query is must-have, other (eg community search for graph db) is extra
class tool:
  # databases are only initalized / connected in main, only an reference of the object will be passed inside here.
  def init():
    pass
  
  def query(query_text:str) -> query_result_object:
    pass

class model_object:
  client : OpenAI
  model_name : str
  def init(self, client, model_name):
    self.client = client
    self.model_name = model_name