import logging
from server_util.time_tracker import time_tracker

# Setup logger
logging.basicConfig(
    level=logging.INFO,  # Set to show all INFO level messages and above
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@time_tracker
def search_documents(client, query_vector, k=5):
    """
    Search for similar entities using a query vector
    
    Parameters:
        query_vector: The embedding vector to search with
        limit: Maximum number of results to return
    
    Returns:
        List of search results with scores and payload data
    """
    search_results = client.search(
        collection_name="document_collection",
        query_vector=query_vector,
        limit=k
    )
    
    return search_results

@time_tracker
def get_doc_from_query_string(client, emb, query_string="what coin is elon musk buying?", k=5):
    doc_list = search_documents(client, emb.embed_query(query_string))[:k]
    # logger.info(doc_list)
    return [content.payload['content'] for content in doc_list], [content.id for content in doc_list], [content.payload['source'] for content in doc_list]
    # entities_list = [entity['entity_name'] for entity in entities_list]
    # logger.info(f"lists are : {entities_list}")
    # query_result = get_doc_from_exact_entities(entities_list)
    # return query_result

@time_tracker
def graph_search(graph, client, emb, query:str, k=5):
    # Get each node's id from vector search
    string_list, id_list, source_list = get_doc_from_query_string(client, emb, query)
    # do cut of first k results
    string_list = string_list[:k]
    id_list = id_list[:k]
    source_list = source_list[:k]

    new_string_list = [ele for ele in string_list]
    new_id_list = [ele for ele in id_list]

    # Get neighbour for each node
    for id in id_list:
        logger.info(f"ele: {id}")
        query_text = f"""match (n:Document)--()--(m:Document) where n.id="{id}" return m.id AS id, m.text AS text, m.source AS source limit {k}"""
        logger.info(f"query: {query_text}")
        current_result = graph.query(query_text)
        if (current_result):
            for ele in current_result:
                new_string_list.append(ele['text'])
                new_id_list.append(ele['id'])
                source_list.append(ele['source'])
                
    new_id_list = new_id_list
    new_string_list = new_string_list[:k]
    source_list = source_list[:k]

    logger.info(f"query result is: {new_id_list}, {new_id_list}")
    # Do the cut of first k nodes here
    return new_id_list, new_string_list, source_list