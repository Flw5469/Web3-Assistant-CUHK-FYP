from openai import OpenAI
from interface import model_object, query_result_object

def normal_query(query_text:str, model_obj:model_object) -> query_result_object:
  answer = model_obj.client.chat.completions.create(
    model=model_obj.model_name,
    messages=[
      {"role": "user", "content": query_text}
    ],
    timeout = 20
  )
  print("answer: ", answer)
  result = answer.choices[0].message.content
  return query_result_object([result], [] , [])

