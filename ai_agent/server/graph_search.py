from typing import Any, List
from mcp.server.fastmcp import FastMCP
from server_util.pagerank_search import pagerank_search
from server_util.graph_search import graph_search
from server_util.community_search import community_search
from server_util.dictionary_search import find_dictionary_answer
from server_util.uploaded_file import retrieve_from_uploaded

import server_util.models as openai_models
import server_util.uploaded_file
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
import qdrant_client
import os
from langchain_community.graphs import Neo4jGraph
from openai import OpenAI
import json

# Initialize FastMCP server
mcp = FastMCP("pagerank_search")

  
graph = None
vector = None
emb = None
model = None

load_dotenv()

os.environ["NEO4J_URI"] = os.getenv("NEO4J_URI")
os.environ["NEO4J_USERNAME"] = os.getenv("NEO4J_USERNAME") 
os.environ["NEO4J_PASSWORD"] = os.getenv("NEO4J_PASSWORD")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")
#os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL")

graph = Neo4jGraph()
emb = OpenAIEmbeddings(base_url=os.getenv("OPENAI_BASE_URL"))
vector = qdrant_client.QdrantClient(path="./storage.db")

client = openai_models.make_client_from_name("3.5")
model = openai_models.model_object(client, openai_models.get_model_name("3.5"))

import logging
logging.basicConfig(
    level=logging.INFO,  # Set to show all INFO level messages and above
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def get_graph_from_nodes(nodes):
    # Convert the list of node IDs to a string in Neo4j format
    # Use parameter substitution to safely pass the list of nodes
    result = graph.query(
    """
    MATCH (source)
    WHERE source.id IN $nodes
    MATCH (source)-[r]-(target)
    RETURN source.id, type(r), target.id
    """, 
    params={"nodes": nodes})
    return [(ele["source.id"], ele["type(r)"], ele["target.id"]) for ele in result]


@mcp.tool(name="graph_query", description="A graph-based search to query the news graph database, suitable for query with deep concepts")
async def graph_query(query_text: str)->str:#, filter: List[str] = []):
    """
    Perform a search on the Neo4j graph database combined with vector search.
    
    Args:
        query_text: The text to search for in the graph and vector store
        filter: Optional list of filters to apply to the search
    
    Returns:
        Dictionary containing search results with content, sources, and node IDs
    """

    # Perform the search
    result_nodes, result_strings, result_sources = graph_search(graph, vector, emb, query_text)
    graph_string = get_graph_from_nodes(result_nodes)
    # Return results as a dictionary for better JSON serialization
    return {
      "text": "\n---------------------".join(result_strings[:5]),
      "graph":graph_string,
    }



@mcp.tool(name="pagerank_query", description="A pagerank-based search to query the news graph database, suitable for query with a lot of objects.")
async def pagerank_query(query_text: str)->str:#, filter: List[str] = []):
    """
    Perform a pagerank-based search on the Neo4j graph database.
    
    Args:
        query_text: The text to search for in the graph
        filter: Optional list of filters to apply to the search
    
    Returns:
        Dictionary containing search results with content, sources, and node IDs
    """
    
    # pagerank_raw_result = pagerank_search(graph, vector, emb, client, query_text)    
    # result_strings = [ele.payload['content'] for ele in pagerank_raw_result]
    # result_sources = [ele.payload['source'] for ele in pagerank_raw_result]
    # result_nodes = [ele.id for ele in pagerank_raw_result]

    # temp set to graph_search for testing
    # Perform the search
    result_nodes, result_strings, result_sources = graph_search(graph, vector, emb, query_text)
    graph_string = get_graph_from_nodes(result_nodes)
    # Return results as a dictionary for better JSON serialization
    return {
      "text": "\n---------------------".join(result_strings[:5]),
      "graph":graph_string,
    }

@mcp.tool(name="community_query", description="A graph community-based search to query the news graph database, suitable for very general queries")
async def community_query(query_text: str)->str:#, filter: List[str] = []):
    """
    Perform a search on the Neo4j graph database combined with vector search.
    
    Args:
        query_text: The text to search for in the graph and vector store
        filter: Optional list of filters to apply to the search
    
    Returns:
        Dictionary containing search results with content, sources, and node IDs
    """

    # Perform the search
    result_nodes, result_strings, result_sources = community_search(graph, vector, emb, query_text)
    graph_string = get_graph_from_nodes(result_nodes)
    # Return results as a dictionary for better JSON serialization
    return {
      "text": "\n---------------------".join(result_strings[:5]),
      "graph":graph_string,
    }


@mcp.tool(name="expert_dictionary", description="A search to an web3 domain expert dictionary.")
async def expert_dictionary(query_text: str):
    """
    Perform a search to the dictionary object
    
    Args:
        query_text: The text to search for in the graph
    
    Returns:
        string of expert knowledge
    """
    return find_dictionary_answer(query_text)


@mcp.tool(name="uploaded_file_search", description="A search to the recent file the user uploaded.")
async def upload_search(query_text: str):
    """
    Perform a vector search to a simple qdrant database
    
    Args:
        query_text: The text to search for in the graph
    
    Returns:
        string of expert knowledge
    """
    

    return retrieve_from_uploaded(vector, emb, query_text)

# Server initialization code
if __name__ == "__main__":
  mcp.run(transport='stdio')
  #print(pagerank_query("elon musk and bitcoin"))