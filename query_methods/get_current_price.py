import json
from interface import query_result_object

def _get_coin_info(input:str) -> str:
  with open('coins_name.json', 'r') as file:
    # print("coinInput: ",input)
    coin_names = json.load(file)
  for coin in coin_names:
    if coin['coin'].lower() == input.lower():
      return coin
  return "UNKNOWN"


def _get_current_price(input:str) -> str:
  InputCoin = input['coin_name'].lower()
  coin_details=str(_get_coin_info(InputCoin))
  print("coin_details: ",coin_details)
  if coin_details:
    problem = f"Given the information of {coin_details} is most updated"
    return f"""\n ######### Subquestion ############
    {problem}
    ###########################"""
  else:
     return f" The price of {input['coin_name']} now is UNKNOWN. "
  
def get_current_price_wrapper(input:str) -> query_result_object:
  return query_result_object([_get_current_price(input)] , [],[])