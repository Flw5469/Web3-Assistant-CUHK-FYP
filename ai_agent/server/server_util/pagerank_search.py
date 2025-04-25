import logging
from server_util.time_tracker import time_tracker

# Configure logger
logging.basicConfig(
    level=logging.INFO,  # Set to show all INFO level messages and above
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

LIMIT = 2

@time_tracker
def get_entities_by_string(emb, client, entity_input=[], k=None):
    """
    find the top k entity in vector database from vector search.
    Details:
    1. do vector search in entity_collection for each entity_input.
    2. put all the results into a set to remove duplicate
    3. take the top k results after sorting the result by similarity score
    """
    if k==None:
       k = len(entity_input)

    if not entity_input:
        return []
    
    # Collection name defined earlier
    collection_name = "entity_collection"
    
    # Convert entity strings to embeddings
    # Note: You'll need to use the same embedding model as was used for entity_embeddings
    query_embeddings = [emb.embed_query(entity) for entity in entity_input]
    
    # Search results will be stored here
    all_results = []
    
    # Search for each query embedding
    for embedding in query_embeddings:
        search_result = client.search(
            collection_name=collection_name,
            query_vector=embedding,
            limit=k*2  # Get more results initially to account for duplicates
        )
        all_results.extend(search_result)
    
    # Remove duplicates by entity ID
    seen_ids = set()
    unique_results = []
    
    for result in all_results:
        if result.id not in seen_ids:
            seen_ids.add(result.id)
            unique_results.append(result)
    
    # Sort by score in descending order (higher score = better match)
    sorted_results = sorted(unique_results, key=lambda x: x.score, reverse=True)
    
    # Take top k results
    top_k_results = sorted_results[:k]
    
    # Format the results as needed
    formatted_results = []
    for result in top_k_results:
        entity_info = {
            "id": result.id,
            "score": result.score,
            "entity_name": result.payload.get("entity_name"),
            # Include any other metadata from the payload
            "metadata": {k: v for k, v in result.payload.items() if k != "entity_name"}
        }
        formatted_results.append(entity_info)
    
    return formatted_results

@time_tracker
def retrieve_document_by_id(client, collection_name, document_id):
    """
    Retrieve a document from Qdrant collection by its ID
    
    Args:
        client: Qdrant client instance
        collection_name: Name of the collection
        document_id: ID of the document to retrieve
    
    Returns:
        The document if found, None otherwise
    """
    try:
        # Convert document_id to the appropriate type if needed
        # If your IDs are strings but you stored them differently, convert accordingly
        
        # Retrieve the point by ID
        result = client.retrieve(
            collection_name=collection_name,
            ids=[document_id],
            with_vectors=True,  # Include vectors in response
            with_payload=True   # Include payload in response
        )
        
        if result and len(result) > 0:
            return result[0]  # Return the first result
        else:
            logger.info(f"No document found with ID: {document_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving document: {e}")
        return None

# Example usage
@time_tracker
def retrieve_document_wrapper(client, id_list=["772339ddb84a028837b74fa6b55490eb"]):
    result = []
    # Retrieve the document
    for id in id_list:
      retrieved_doc = retrieve_document_by_id(
          client=client,
          collection_name="document_collection",
          document_id=id
      )
    
      # Log results
      if retrieved_doc:
          logger.info(f"Retrieved document ID: {retrieved_doc.id}")
          result.append(retrieved_doc)
    
    return result

@time_tracker
def sort_dict_by_value(d, reverse=True):
    # Sort the dictionary by value and return as a list of tuples (key, value)
    # By default sorts in descending order (highest values first)
    return sorted(d.items(), key=lambda x: x[1], reverse=reverse)

@time_tracker
def get_doc_from_exact_entities(graph, client, emb, id_list=['Cardano Ledger'], k=5):
    """
    run the page rank algorithm with a list of exact ids, like ['Elon Musk', 'Bitcoin'], then return the first k document results
    """

    unprocessed_result = graph.query("""
    MATCH (siteA:__Entity__)
    WHERE siteA.id IN $nodeIds
    CALL gds.pageRank.stream('pagerank', {
        maxIterations: 20,
        dampingFactor: 0.85,
        sourceNodes: [siteA]
    })
    YIELD nodeId, score
    RETURN gds.util.asNode(nodeId).id AS name, score
    ORDER BY score DESC, name ASC
    """, 
    {"nodeIds": id_list})

    unique_scores = {}

    # Iterate through the unprocessed results
    for node in unprocessed_result:
        if node['score'] != 0.0:  # Only include non-zero scores
            name = node['name']
            score = node['score']
            
            # Add score to existing name or create new entry
            if name in unique_scores:
                unique_scores[name] += score
            else:
                unique_scores[name] = score

    # Convert back to list of dictionaries format
    result = [{'name': name, 'score': score} for name, score in unique_scores.items()]
    print(f"results are: {result}")
  
    # Build the Cypher parameter for the ranked nodes
    # Construct the second query using the result from the first query
    node_names = [node["name"] for node in result]
    node_scores_map = {node["name"]: node["score"] for node in result}

    # Now use these directly in the query
    result2 = graph.query(
        """
        MATCH (source:__Entity__)-[r]-(target:Document)
        WHERE source.id IN $nodeNames
        RETURN 
            source.id AS sourceNode, 
            type(r) AS relationship, 
            target.id AS targetDocument,
            target.type AS targetType
        ORDER BY sourceNode ASC
        """,
        {"nodeNames": node_names, }
    )

    result_dict = {item['name']: item['score'] for item in result}
    print("result dicts are: ",result_dict)

    node_dict = {}
    for ele in result2:
        node_dict[ele['targetDocument']] = 0.0

    for ele in result2:
        node_dict[ele['targetDocument']] += result_dict[ele['sourceNode']]
        print(f"target document {ele['targetDocument']} plus {result_dict[ele['sourceNode']]} from {ele['sourceNode']}")

    sorted_items = sort_dict_by_value(node_dict)
    print(sorted_items)
    sorted_items = sorted_items[:min(k, len(sorted_items))]

    logger.info(f"document score from pagerank: {sorted_items}")
    # Run the example
    query_result = []
    if sorted_items:
        sorted_id = [item[0] for item in sorted_items]
        #logger.info(f"sorted_id: {sorted_id}")
        query_result = retrieve_document_wrapper(client, id_list=sorted_id)

    return query_result

from graphdatascience import GraphDataScience
# project graph
gds = GraphDataScience(
    "bolt://localhost:7688", 
    auth=("neo4j", "staysovryn")
)
gds.graph.drop("pagerank")
G, result = gds.graph.project(
    "pagerank",  #  Graph name
    "__Entity__",  #  Node projection
    {
        "_ALL_": {
            "type": "*",
            "orientation": "UNDIRECTED",
            "properties": {"weight": {"property": "*", "aggregation": "COUNT"}},
        }
    },
)

@time_tracker
def pagerank_search(graph, client, emb, model, query=None, k=5):
    # Use LLM to extract entities from the query
    if query:
        # Create a prompt to extract entities
        entity_extraction_prompt = f"""
        Extract the key entities (people, organizations, places, concepts) from the following query.
        Return ONLY a Python list of strings containing these entities. No explanation or other text.
        
        Query: {query}
        """
        
        # Call the LLM to extract entities
        llm_response = model.predict(entity_extraction_prompt)
        
        # Parse the response to get the entities
        # The response should be a Python list format, so we'll evaluate it
        try:
            # Try to extract a Python list from the response
            import re
            list_pattern = r'\[.*?\]'
            list_match = re.search(list_pattern, llm_response, re.DOTALL)
            
            if list_match:
                entity_list_str = list_match.group(0)
                entity_list = eval(entity_list_str)  # Safely evaluate the list string
            else:
                # Fallback: split by commas and clean up
                entity_list = [item.strip().strip('"\'') for item in llm_response.split(',')]
                # Remove any empty strings
                entity_list = [item for item in entity_list if item]
        except:
            # If parsing fails, use a simple split as fallback
            entity_list = [item.strip() for item in llm_response.split('\n') if item.strip()]
    else:
        entity_list = []
    
    # Get entities by string
    entities_list = get_entities_by_string(emb, client, entity_list)
    logger.info("entity list: %s", entities_list)    
    # Extract entity names
    entities_list = [entity['entity_name'] for entity in entities_list]
    
    # Return documents from exact entities
    return get_doc_from_exact_entities(graph, client, emb, entities_list)