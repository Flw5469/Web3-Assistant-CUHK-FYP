from crawl2 import main

urls = [
    "https://www.theblock.co/category/web3",
    "https://www.wired.com/tag/web3/",
    "https://www.nftgators.com/web3/#top",
    "https://www.coindesk.com/tag/web3/",
    "https://cryptonews.com/news/bitcoin-news/",
    "https://coingape.com/category/news/bitcoin-news/",
    "https://www.forbes.com/digital-assets/news/?sh=cf3a205f9d5b",
    "https://cointelegraph.com/tags/web3",
    "https://blockworks.co/category/web3",
    "https://www.cointrust.com/",
    "https://blockchainreporter.net/the-ideal-web3-game-must-have-web2-style-gameplay/",
    "https://www.euronews.com/tag/web3",
    "https://cointelegraph.com/news/brazil-crypto-imports-surge-september",
    "https://thepaypers.com/categories/defi-news-and-crypto-news-and-web3-news",
    "https://www.ft.com/crypto",
    "https://www.bloomberg.com/crypto",
    "https://asia.nikkei.com/Spotlight/Cryptocurrencies",
    "https://www.bbc.com/news/topics/cyd7z4rvdm3t",
    "https://cryptonews.com.au/",
    "https://www.barrons.com/topics/cryptocurrencies",
]



from GoogleNews import GoogleNews
googlenews = GoogleNews()
googlenews.search('crypto')
content_urls = []
for i in range(1,10):
  content_urls+=googlenews.page_at(i)




for i,url in enumerate(urls):
  main(url = url, id=i, depth=2)

for i, url in enumerate(content_urls):
  main(url = url['datetime'], id=i+len(urls), depth=1)
