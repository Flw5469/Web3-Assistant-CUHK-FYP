import streamlit as st
import streamlit.components.v1 as components
import random
import requests
from datetime import datetime, timedelta
import models

# col1, col2 = st.columns([3, 1])
# with col2:
def fun(input):
  return  components.html("""
<!doctype html>
<html>
<head>
    <!-- Use CDN for simplicity in this standalone HTML example -->
    <script src="https://unpkg.com/cytoscape/dist/cytoscape.min.js"></script>
    
    <style>
        /* Container styles */
        #cy {
            width: 100%;
            height: 600px;
            display: block;
            background-color: #f5f5f5;
            border: 1px solid #ccc;
        }
        
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
        }
        
        h1 {
            color: #333;
        }
    </style>
</head>
<body>
    <div id="cy"></div>
    
    <script>
        // Wait for DOM to load
        document.addEventListener('DOMContentLoaded', function() {
            
            // Initialize Cytoscape
            var cy = cytoscape({
                container: document.getElementById('cy'),
                
                // Define the elements (nodes and edges)
                elements: [
    // Nodes - Key entities in recent crypto news
    { data: { id: 'elon', label: 'Elon Musk', type: 'person', influence: 'high' } },
    { data: { id: 'doge', label: 'Dogecoin', type: 'cryptocurrency', marketCap: '$18B' } },
    { data: { id: 'btc', label: 'Bitcoin', type: 'cryptocurrency', marketCap: '$1.6T' } },
    { data: { id: 'eth', label: 'Ethereum', type: 'cryptocurrency', marketCap: '$300B' } },
    { data: { id: 'ada', label: 'Cardano', type: 'cryptocurrency', marketCap: '$14B' } },
    { data: { id: 'xrp', label: 'XRP', type: 'cryptocurrency', marketCap: '$35B' } },
    { data: { id: 'tariffs', label: 'China Tariffs', type: 'economic_policy', region: 'Global' } },
    { data: { id: 'sec', label: 'SEC', type: 'regulator', country: 'USA' } },
    { data: { id: 'gensler', label: 'Gary Gensler', type: 'person', role: 'SEC Chair' } },
    { data: { id: 'twitter', label: 'X/Twitter', type: 'company' } },
    { data: { id: 'tesla', label: 'Tesla', type: 'company' } },
    { data: { id: 'etf', label: 'Spot ETFs', type: 'financial_product' } },
    { data: { id: 'election', label: '2024 Election', type: 'political_event' } },
    { data: { id: 'mining', label: 'Crypto Mining', type: 'industry' } },
    { data: { id: 'trump', label: 'Donald Trump', type: 'person', role: 'Former President' } },
    { data: { id: 'blackrock', label: 'BlackRock', type: 'company', industry: 'Finance' } },
    { data: { id: 'jp', label: 'JPMorgan', type: 'company', industry: 'Finance' } },
    { data: { id: 'hoskinson', label: 'Charles Hoskinson', type: 'person', role: 'Cardano Founder' } },
    { data: { id: 'buterin', label: 'Vitalik Buterin', type: 'person', role: 'Ethereum Founder' } },
    { data: { id: 'hack', label: 'Security Breach', type: 'event' } },
    
    // Edges - Relationships from recent news
    { data: { id: 'e1', source: 'elon', target: 'doge', label: 'Twitter promotion', date: '2025-03', sentiment: 'positive' } },
    { data: { id: 'e2', source: 'elon', target: 'twitter', label: 'Owns', date: '2022-present', sentiment: 'neutral' } },
    { data: { id: 'e3', source: 'twitter', target: 'doge', label: 'Payment speculation', date: '2025-04', sentiment: 'positive' } },
    { data: { id: 'e4', source: 'elon', target: 'tesla', label: 'CEO', date: 'Present', sentiment: 'neutral' } },
    { data: { id: 'e5', source: 'tesla', target: 'btc', label: 'Purchased/Sold', date: '2021-2023', sentiment: 'neutral' } },
    { data: { id: 'e6', source: 'tariffs', target: 'mining', label: 'Increased costs', date: '2025-03', sentiment: 'negative' } },
    { data: { id: 'e7', source: 'tariffs', target: 'btc', label: 'Price volatility', date: '2025-03', sentiment: 'negative' } },
    { data: { id: 'e8', source: 'sec', target: 'gensler', label: 'Chaired by', date: 'Present', sentiment: 'neutral' } },
    { data: { id: 'e9', source: 'gensler', target: 'xrp', label: 'Legal settlement', date: '2024-07', sentiment: 'positive' } },
    { data: { id: 'e10', source: 'sec', target: 'eth', label: 'ETF approval', date: '2024-05', sentiment: 'positive' } },
    { data: { id: 'e11', source: 'sec', target: 'btc', label: 'ETF approval', date: '2024-01', sentiment: 'positive' } },
    { data: { id: 'e12', source: 'sec', target: 'ada', label: 'Regulatory scrutiny', date: '2025-02', sentiment: 'negative' } },
    { data: { id: 'e13', source: 'hoskinson', target: 'ada', label: 'Founded', date: '2017', sentiment: 'neutral' } },
    { data: { id: 'e14', source: 'hoskinson', target: 'sec', label: 'Public criticism', date: '2025-02', sentiment: 'negative' } },
    { data: { id: 'e15', source: 'blackrock', target: 'etf', label: 'Manages', date: '2024-Present', sentiment: 'positive' } },
    { data: { id: 'e16', source: 'etf', target: 'btc', label: 'Covers', date: '2024-01', sentiment: 'positive' } },
    { data: { id: 'e17', source: 'etf', target: 'eth', label: 'Covers', date: '2024-05', sentiment: 'positive' } },
    { data: { id: 'e18', source: 'jp', target: 'btc', label: 'Price forecast $150K', date: '2025-03', sentiment: 'positive' } },
    { data: { id: 'e19', source: 'election', target: 'btc', label: 'Price catalyst', date: '2024-11', sentiment: 'positive' } },
    { data: { id: 'e20', source: 'trump', target: 'btc', label: 'Promised "crypto capital"', date: '2024-08', sentiment: 'positive' } },
    { data: { id: 'e21', source: 'buterin', target: 'eth', label: 'Created', date: '2015', sentiment: 'neutral' } },
    { data: { id: 'e22', source: 'hack', target: 'xrp', label: 'Exchange exploit', date: '2025-02', sentiment: 'negative' } },
    { data: { id: 'e23', source: 'trump', target: 'election', label: 'Candidate', date: '2024', sentiment: 'neutral' } },
    { data: { id: 'e24', source: 'elon', target: 'trump', label: 'Endorsed', date: '2024-07', sentiment: 'neutral' } },
    { data: { id: 'e25', source: 'blackrock', target: 'jp', label: 'Market competitors', date: 'Ongoing', sentiment: 'neutral' } }
],
                
                // Define the visual style
                style: [
                    {
                        selector: 'node',
                        style: {
                            'background-color': '#4287f5',
                            'label': 'data(label)',
                            'color': '#fff',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'width': 60,
                            'height': 60,
                            'font-size': 12
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 3,
                            'line-color': '#ccc',
                            'target-arrow-color': '#ccc',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                            'label': 'data(label)',
                            'font-size': 10,
                            'text-rotation': 'autorotate'
                        }
                    }
                ],
                
                // Layout configuration
                layout: {
                    name: 'cose', // force-directed layout
                    padding: 50,
                    randomize: true,
                    nodeRepulsion: 8000,
                    nodeOverlap: 20,
                    idealEdgeLength: 100
                }
            });
            
            // Add some interactions
            cy.on('tap', 'node', function(evt){
                var node = evt.target;
                console.log('Tapped node: ' + node.id());
                
                // Highlight the node and its connections
                cy.elements().style('opacity', 0.3);
                node.style('opacity', 1);
                node.connectedEdges().style('opacity', 1);
                node.connectedEdges().connectedNodes().style('opacity', 1);
                
                // Reset after 3 seconds
                setTimeout(function(){
                    cy.elements().style('opacity', 1);
                }, 3000);
            });
        });
    </script>
</body>
</html>
""",
      height=300,
  )

st.sidebar.header("Select Date Range")
end_date = st.sidebar.date_input(
    "End Date",
    datetime.now()
)
start_date = st.sidebar.date_input(
    "Start Date",
    end_date - timedelta(days=7)  # Default to 7 days before end date
)

# Validate date range
if start_date > end_date:
    st.sidebar.error("Error: Start date must be before end date")


# Adding checkboxes for cryptocurrency selection
st.sidebar.header("Select Cryptocurrencies")
selected_coins = []
if st.sidebar.checkbox("Bitcoin"):
    selected_coins.append("Bitcoin")
if st.sidebar.checkbox("Tron"):
    selected_coins.append("Tron")
if st.sidebar.checkbox("Web3"):
    selected_coins.append("Web3")
if st.sidebar.checkbox("Market"):
    selected_coins.append("Market")
if st.sidebar.checkbox("Crypto"):
    selected_coins.append("Crypto")
if st.sidebar.checkbox("Cardano"):
    selected_coins.append("Cardano")
# Add more checkboxes as needed
# if st.sidebar.checkbox("Ethereum"):
#     selected_coins.append("Ethereum")

chat=""
st.sidebar.header("Select mode")
chat_dict = {
    "baseline":"baseline",
    "enhanced":"tool_search",
    # "tool":"chat3",
    "simple query":"normal_query"
}

model_key_list = models.model_list.keys()
chat = chat_dict[st.sidebar.selectbox("Select frameworks",["baseline","enhanced","tool","simple query"])]
client = st.sidebar.selectbox("Select client :", model_key_list )
database = st.sidebar.selectbox("Select client :", ["neo4j", "vector"])

st.title("Web3 Assistant")
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
# React to user input


node_list = []

if prompt := st.chat_input("What would you like to know"):
    print(selected_coins)
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare the payload including the selected coins
    payload = {
        "prompt": prompt,
        "coin_name": selected_coins,  # Include selected coins in the request
        "model" : client,
        "database" : database,
        "query_type" : chat,
    }
    

    # Make API call to backend server
    try:
        response = requests.post(
            f"http://localhost:8000/api/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()  # Raise exception for bad status codes
        ai_response = response.json()["response"]
        node_list = response.json()["node_list"]
        print(str(node_list))

    except Exception as e:
        ai_response = f"Error: Unable to get response from server. {str(e)}"
    if node_list:
      fun(f"MATCH (n)-[r]-(m) WHERE n.id IN {node_list} RETURN n,r,m LIMIT 50")
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(ai_response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": ai_response})