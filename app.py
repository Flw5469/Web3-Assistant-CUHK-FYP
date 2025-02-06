import streamlit as st
import streamlit.components.v1 as components
import random
import requests
from datetime import datetime, timedelta



# col1, col2 = st.columns([3, 1])
# with col2:
def fun(input):
  return  components.html(
      """
      <html>
<head>
    <title>Neovis.js Simple Example</title>
    <style type="text/css">
        html, body {
            font: 16pt arial;
        }

        #viz {
            width: 700px;
            height: 300px;
            border: 1px solid lightgray;
            font: 22pt arial;
        }

    </style>

    <!-- FIXME: load from dist -->
    <script src="https://unpkg.com/neovis.js@2.0.2"></script>


    <script
            src="https://code.jquery.com/jquery-3.2.1.min.js"
            integrity="sha256-hwg4gsxgFZhOsEEamdOYGBf13FyQuiTwlAQgxVSNgt4="
            crossorigin="anonymous"></script>

    <script type="text/javascript">
		// define config car
		// instantiate nodevis object
		// draw

		var viz;

		function draw() {
			var config = {
				containerId: "viz",
				neo4j: {
					serverUrl: "bolt://localhost:7687",
					serverUser: "neo4j",
					serverPassword: "staysovryn"
				},
				labels: {
// 					"Document": {
//						label: "id",
// 					},
          "__Entity__":{
            label:"id"
          },
          "*":{
            label:"*"          
          },
				},
				relationships: {
					"*": {
            label:"description",
						value: "id"
					}
				},
				initialCypher: """+f"""\"{input}\""""+"""
			};

			viz = new NeoVis.default(config);
			viz.render();
			console.log(viz);

		}
    </script>
</head>
<body onload="draw()">
<div id="viz"></div>

</body>

<script>
	$("#reload").click(function () {

		var cypher = $("#cypher").val();

		if (cypher.length > 3) {
			viz.renderWithCypher(cypher);
		} else {
			console.log("reload");
			viz.reload();

		}

	});

	$("#stabilize").click(function () {
		viz.stabilize();
	})

</script>
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
    "baseline":"chat1",
    "enhanced":"chat2",
    "tool":"chat3",
    "simple query":"chat4"
}

chat = chat_dict[st.sidebar.selectbox("Select frameworks",["baseline","enhanced","tool","simple query"])]
version = st.sidebar.selectbox("Choose a version:", ["3.5", "4o"])
client = st.sidebar.selectbox("Select client :", ["Ollama", "OpenRouter"])

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
        "model" : version
    }
    

    # Make API call to backend server
    try:
        response = requests.post(
            f"http://localhost:8000/api/{chat}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()  # Raise exception for bad status codes
        ai_response = response.json()["response"]
        node_list = response.json()["node_list"]
        print(str(node_list))

    except Exception as e:
        ai_response = f"Error: Unable to get response from server. {str(e)}"

    fun(f"MATCH (n)-[r]-(m) WHERE n.id IN {node_list} RETURN n,r,m LIMIT 50")
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(ai_response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": ai_response})