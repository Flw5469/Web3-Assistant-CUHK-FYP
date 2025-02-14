from openai import OpenAI
from query_methods.baseline import baseline
from query_methods.get_current_price import get_current_price_wrapper
from query_methods.normalQuery import normalQuery
from interface import model_object, query_result_object, tool
import json


def tool_search(query, coin_list, tool_dict:dict[tool]) -> query_result_object:
    """
    Executes context retrieval based on the subquery's type and returns a combined query,
    along with any source and node data.
    """
    subquery_text = query.get("subquestion")
    if subquery_text is None:
        return [], [], []

    query_type = query.get("type")
    result_object = query_result_object([],[],[])

    if query_type == "structured_data":
        price = get_current_price_wrapper(query)
        result_object.string[0] += f"{price}\n"

    elif query_type == "news":
        news_info = tool_dict['neo4j'](subquery_text, coin_list)
        # Join individual news items since news_info[0] is a list.
        result_object += news_info

    elif query_type == "general":
        general_info = normalQuery(subquery_text)
        result_object.string[0] += f"{general_info}\n"
        # Removed extending source_list and node_list because context_and_community_retrival returns a string.

    elif query_type == "domain_knowledge":
        domain_info = tool_dict['context'](subquery_text)
        result_object.string[0] += f"{domain_info}\n"
        
    else:
        print("Unexpected subquery_type:", query_type)
    
    result_object.string[0] = subquery_text + result_object.string[0]
    return result_object

def query_breakdown(question_text, model:model_object):
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
        completion = model.client.chat.completions.create(
            model=model.model_name,
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

def tool_search_wrapper(original_query,model:model_object, coin_list=None) -> query_result_object:
    """
    Integrates query breakdown and tool search to build a combined query processed by a baseline model.
    """
    
    result_object = query_result_object([],[],[])

    
    sub_questions = query_breakdown(original_query, model)
    print("subQuestionList:", len(sub_questions))

    if not sub_questions:
        # Create a fallback subquestion dictionary if query breakdown fails.
        fallback_dict = {"subquestion": original_query, "type": "general"}
        result_object += tool_search(fallback_dict, coin_list)
        
    else:
        for subq in sub_questions:
            print(subq.get("subquestion"), subq.get("type"))
            result_object += tool_search(subq, coin_list)
    
    combined_answer = "\n".join(result_object.string)

    complete_query = (
        f"question: {original_query}\n"
        f"answer: {combined_answer}\n"
        "please give a concise answer"
    )

    print("complete query: ",complete_query)

    # This baseline should eventually convert to pure LLM operation.
    result_object.string = normalQuery(complete_query, model).string

    return result_object