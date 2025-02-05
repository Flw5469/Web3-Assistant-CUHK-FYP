from openai import OpenAI

model_list = {
  "3.5":("sk-sJAILfYY4hF8aVTM73A26fB09c834c7b8c41D4CeB652Fe95", "https://openai.ss-gpt.com/v1", "gpt-3.5-turbo"),
  "4o":("sk-sJAILfYY4hF8aVTM73A26fB09c834c7b8c41D4CeB652Fe95", "https://openai.ss-gpt.com/v1", "gpt-4o"),
  "deepseek":("abc", "http://58.176.61.54:11434/v1", "deepseek-r1:7b"),
}

def make_client(dict_value:tuple):
  return OpenAI(api_key = dict_value[0],base_url=dict_value[1])

def make_client_from_name(model_name):
  return make_client(model_list[model_name])

# client = make_client(model_list['deepseek'])

# answer = client.chat.completions.create(
#   model="gpt-3.5-turbo",
#   messages=[
#     {"role": "user", "content": "why are people gay?"}
#   ])

# print(answer)
