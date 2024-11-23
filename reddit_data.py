import requests
 
# subreddit = 'web3'
# limit = 10
# timeframe = 'month' #hour, day, week, month, year, all
# listing = 'top' # controversial, best, hot, new, random, rising, top
def reddit_data(subreddit = 'web3', limit = 10, timeframe = 'month', listing = 'top'):
  def get_reddit(subreddit,listing,limit,timeframe):
    return get(base_url = f'https://www.reddit.com/r/{subreddit}/{listing}.json?limit={limit}&t={timeframe}')


  def get_comment(subreddit,listing,limit,timeframe,id):
      return get(f'https://www.reddit.com/r/{subreddit}/comments/{id}.json?limit={limit}&t={timeframe}')
  

  def get(base_url):
    try:
        request = requests.get(base_url, headers = {'User-agent': 'yourbot'})
    except:
        print('An Error Occured')
    return request.json()
  
  r = get_reddit(subreddit,listing,limit,timeframe)
  id_list = [ele['data']['id'] for ele in r['data']['children']]
  print(id_list)

  comment_list = [get_comment(subreddit,listing,limit,timeframe,id) for id in id_list]
  content_list = [ele['data']['title']+ele['data']['selftext'] for ele in r['data']['children']]
  post_title_list = [ele['data']['title'] for ele in r['data']['children']]
  post_content_list = [ele['data']['selftext'] for ele in r['data']['children']]
  # Bug: the more_data is not in same JSON format as comment_list_in_post, so later when retrieve text, I need 2 different key
  def extend_comment(id,comment):
    comment_list_in_post = comment[1]['data']['children']
    print("old", comment_list_in_post[-1])
    if comment_list_in_post[-1]['kind']=='more':
      more_data_string = ','.join(comment_list_in_post[-1]['data']['children'])
      more_data = get(f"https://www.reddit.com/api/morechildren?link_id={id}&children={more_data_string}&api_type=json")
      comment_list_in_post = comment_list_in_post[:-1]+more_data['json']['data']['things']
    print("new: ",comment_list_in_post[-1])
    return comment_list_in_post

  modified_id_list = ['t3_'+ele for ele in id_list]
  extended_comment_list = [extend_comment(id,comment) for id,comment in zip(modified_id_list,comment_list)]
  extended_comment_text_list = [[ele2['data']['body'] if 'body' in ele2['data'] else ele2['data']['contentText'] for ele2 in ele1] for ele1 in extended_comment_list]
  import datetime

  def format(content,comment_text):
    text = ""
    for i,ele in enumerate(comment_text):
      text+=f"""Comment {i}: {ele}\n\n"""


    return f"""
  Topic: 
  {content}

  ---------------------------------------------------------------
  The following are the Comments:
  {text}

  """


  def format_comment_only(comment_text):
    text = ""
    for i,ele in enumerate(comment_text):
      text+=f"""Comment {i}: {ele}\n"""
    return text

  def format_post_content_only(post_content):
    return f"""Post: {post_content}\n\n"""


  URL_list = [ele['data']['url'] for ele in r['data']['children']]
  date_list = [ele['data']['created'] for ele in r['data']['children']]


  subreddit_tag = {
    "web3":"Web3",
    "crypto": "Crypto",
    "Cardano" : "Cardano",
    "Bitcoin" : "Bitcoin"
  }

  coin_tag = {
    "bitcoin":"Bitcoin", 
    "Cardano":"Cardano",
    "ethereum":"Ethereum", 
    "Tron":"Tron", 
    "Dogecoin":"Dogecoin",
    "Market" : "Market",
    "Crypto" : "Crypto",
  }

  result = [{
    'URL': url,
    'news_title': post_title,
    'news_content': format_post_content_only(post_content)+format_comment_only(extended_comment_text),
    'date' : str(datetime.datetime.fromtimestamp(date))
  } for url,extended_comment_text, date, post_title, post_content 
      in zip(URL_list,extended_comment_text_list,date_list, post_title_list, post_content_list)]


  for data in result:
    
    coin = []
    for ele in subreddit_tag:
      if subreddit.lower() in ele.lower():
        coin.append(subreddit_tag[subreddit])    
    for ele in coin_tag:
      if (ele.lower() in data['news_title']) or (ele.lower() in data['news_content']):
        if coin_tag[ele] not in coin:
          coin.append(coin_tag[ele])
    data['coins_name'] = coin

    data['news_content'] = data['news_content'].replace("|", " ")
  
  return result