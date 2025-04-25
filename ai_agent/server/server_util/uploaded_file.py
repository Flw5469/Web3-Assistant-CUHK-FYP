def retrieve_from_uploaded(client, emb, query_text, limit=5):
    """
    Retrieve the most relevant text from uploads in Qdrant based on vector similarity.
    
    Args:
        client: Qdrant client instance
        emb: Embedding vector for the query text
        query_text: Original query text string
        collection_name: Name of the Qdrant collection to search
        limit: Number of results to return (default: 1)
        
    Returns:
        String containing the text from the most relevant document
    """
    collection_name="upload_collection"
    try:
        # Search Qdrant using the embedding vector
        search_result = client.search(
            collection_name=collection_name,
            query_vector=emb.embed_query(query_text),
            limit=limit
        )
        
        # Check if we got any results
        if not search_result:
            return f"No documents found matching: '{query_text}'"
        
        # Extract the text from the top result
        top_result = search_result[0]
        
        # Assuming the document text is stored in a field called 'text'
        # Modify this based on your actual document structure
        if 'content' in top_result.payload:
            return top_result.payload['content']
        else:
            return f"Found a document (score: {top_result['score']:.2f}) but couldn't extract text"
    
    except Exception as e:
        return f"Error retrieving from Qdrant: {str(e)}"