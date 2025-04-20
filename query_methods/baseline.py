from query_methods.normal_query import normal_query
from interface import tool, model_object, query_result_object

def baseline(query_text:str, coin_list:list, model:model_object, tool:tool) -> query_result_object:

  response:query_result_object = tool.query(query_text)
  formatted_question = f"""You are a professional web3 analyst. Please answer questions for other web3 analyst strictly according to the below context.
############### Context ###########
{response.string}
################ Question ##########
{query_text}
################# Answer ###########
"""
  
  print(formatted_question)

  answer = normal_query(formatted_question, model)
  total_result = query_result_object(answer.string, response.source, response.node )#,formatted_question)
  print(total_result)
  return total_result