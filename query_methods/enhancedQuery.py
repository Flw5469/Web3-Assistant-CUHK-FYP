# # Not using rn, chat2 endpoint switched to tool_search_wrapper
# def enhanced(query, coin_list, model_name="3.5"):

#     """
#     Incorporates contextual and background information to form a detailed question for the LLM.
#     """
#     context, source = context_retrival(query, coin_list)
#     background = background_retrival(vector_store, query)
#     formatted_question = (
#         "You are a professional web3 analyst. Please answer questions for other web3 analyst strictly according to the below context.\n"
#         "############### Context ###########\n"
#         f"{background}\n\n"
#         f"{context}\n"
#         "################ Question ##########\n"
#         f"{query}\n"
#         "################# Answer ###########\n"
#     )
    
#     client = models.make_client_from_name(model_name)
#     answer = client.chat.completions.create(
#         model=get_model_value(model_name),
#         messages=[{"role": "user", "content": formatted_question}],
#         timeout = 20
#     )
#     result = answer.choices[0].message.content
#     return result, formatted_question, source