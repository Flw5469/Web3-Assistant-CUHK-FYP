print("import time")
import time
start_time = time.time()
print("import langchain")
from langchain_openai import ChatOpenAI
langchain_time = time.time()

class model_object:
  client : ChatOpenAI
  model_name : str
  def __init__(self, client, model_name):
    self.client = client
    self.model_name = model_name

model_list = {
  "3.5":("sk-sJAILfYY4hF8aVTM73A26fB09c834c7b8c41D4CeB652Fe95", "https://openai.ss-gpt.com/v1", "gpt-3.5-turbo"),
  "4o":("sk-sJAILfYY4hF8aVTM73A26fB09c834c7b8c41D4CeB652Fe95", "https://openai.ss-gpt.com/v1", "gpt-4o-2024-11-20"),
  "deepseek":("abc", "http://58.176.61.54:11434/v1", "deepseek-r1:7b"),
}

def make_client(dict_value:tuple):
  return ChatOpenAI(api_key = dict_value[0],base_url=dict_value[1], model_name = dict_value[2])

def make_client_from_name(model_name):
  return make_client(model_list[model_name])

def get_model_name(model_name_key):
  return model_list[model_name_key][2]

# client = make_client(model_list['deepseek'])

# answer = client.chat.completions.create(
#   model="gpt-3.5-turbo",
#   messages=[
#     {"role": "user", "content": "why are people gay?"}
#   ])

# print(answer)


if __name__ == "__main__":
    # Start the timer

    run_time = time.time()
    print("started")
    # Create the model client
    model_obj = make_client_from_name("4o")
    client_creation_time = time.time()
    print("created")
    # Make the prediction
    ans = model_obj.predict("1. How is the weather? 2. What model are you and when did you get release?")
    prediction_time = time.time()

    # Print the results and timing information
    print(f"Answer: {ans}")
    print("\nTiming Information:")
    print(f"Import took: {(run_time - start_time):.3f} seconds")
    print(f"Client creation took: {(client_creation_time - run_time):.3f} seconds")
    print(f"Prediction took: {(prediction_time - client_creation_time):.3f} seconds")
    print(f"Total execution time: {(prediction_time - start_time):.3f} seconds")