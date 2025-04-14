import streamlit as st
import streamlit.components.v1 as components
import random
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pandas as pd
# Load environment variables for Neo4j connection
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "staysovryn")

def render_graph(input):
    """Render Neo4j graph visualization using Neovis.js"""
    return components.html(
        f"""
        <html>
<head>
    <title>Neovis.js Simple Example</title>
    <style type="text/css">
        html, body {{
            font: 16pt arial;
        }}

        #viz {{
            width: 700px;
            height: 300px;
            border: 1px solid lightgray;
            font: 22pt arial;
        }}

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

		function draw() {{
			var config = {{
				containerId: "viz",
				neo4j: {{
					serverUrl: "{NEO4J_URI}",
					serverUser: "{NEO4J_USERNAME}",
					serverPassword: "{NEO4J_PASSWORD}"
				}},
				labels: {{
          "__Entity__":{{
            label:"id"
          }},
          "*":{{
            label:"*"          
          }},
				}},
				relationships: {{
					"*": {{
            label:"description",
						value: "id"
					}}
				}},
				initialCypher: "{input}"
			}};

			viz = new NeoVis.default(config);
			viz.render();
			console.log(viz);

		}}
    </script>
</head>
<body onload="draw()">
<div id="viz"></div>

</body>

<script>
	$("#reload").click(function () {{
		var cypher = $("#cypher").val();
		if (cypher.length > 3) {{
			viz.renderWithCypher(cypher);
		}} else {{
			console.log("reload");
			viz.reload();
		}}
	}});

	$("#stabilize").click(function () {{
		viz.stabilize();
	}})
</script>
</html>
        """,
        height=300,
    )

# Function to fetch MCP tools from backend
def fetch_mcp_tools():
    try:
        response = requests.get("http://localhost:8000/api/mcp/tools", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching MCP tools: Status code {response.status_code}")
            return {"initialized": False, "tools": [], "servers": []}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching MCP tools: {str(e)}")
        return {"initialized": False, "tools": [], "servers": []}

# Set up sidebar date range selection
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

# Mode selection
st.sidebar.header("Select Mode")
# Map the display names to the API mode parameter values
mode_dict = {
    "Baseline": "baseline",
    "Enhanced (with background knowledge)": "enhanced",
    "Tool-based Search": "tool_search",
    "Simple Query": "direct",
    "MCP Platform": "mcp"
}

selected_mode = st.sidebar.selectbox(
    "Select framework",
    list(mode_dict.keys())
)
mode = mode_dict[selected_mode]

# Model selection
version = st.sidebar.selectbox("Choose a version:", ["3.5", "4o"])

# MCP Platform options
st.sidebar.header("MCP Platform")
use_mcp = st.sidebar.checkbox("Use MCP Platform Tools", value=False)

# If MCP is enabled, fetch and display available tools
if use_mcp:
    mcp_info = fetch_mcp_tools()
    
    if mcp_info["initialized"]:
        st.sidebar.success(f"MCP Platform is connected with {len(mcp_info['tools'])} tools")
        
        # Group tools by server
        tools_by_server = {}
        for server in mcp_info["servers"]:
            tools_by_server[server] = [
                tool for tool in mcp_info["tools"] 
                if tool.get("server") == server
            ]
        
        # Create an expander to show the tools
        with st.sidebar.expander("Available MCP Tools"):
            for server, tools in tools_by_server.items():
                st.markdown(f"**Server: {server}**")
                for tool in tools:
                    st.markdown(f"- {tool.get('name')}: {tool.get('description')}")
                st.markdown("---")
    else:
        st.sidebar.error("MCP Platform is not initialized")

# Dropzone to input file for Graph Database
file_input = st.sidebar.file_uploader("Upload your input file", type=["csv"], key="uploaded_file")
print("fileinput", file_input)

# Optimized file reading
if file_input is not None:
    iris = pd.read_table(st.session_state["uploaded_file"] , sep=",",  header=0)
else:
    iris = None

print("iris",iris)

st.title("Web3 Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Initialize tools used container
if "tools_used" not in st.session_state:
    st.session_state.tools_used = []

# Display tools used if any
if st.session_state.tools_used:
    with st.expander("MCP Tools Used"):
        for tool in st.session_state.tools_used:
            st.markdown(f"- {tool}")

# React to user input
node_list = []

if prompt := st.chat_input("What would you like to know"):
    print(f"Selected coins: {selected_coins}")
    print(f"Selected mode: {mode}")
    print(f"Use MCP: {use_mcp}")
    
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare the payload including the selected coins and mode
    payload = {
        "prompt": prompt,
        "coin_name": selected_coins,
        "model": version,
        "mode": mode,
        "use_mcp": use_mcp
    }
    
    # Make API call to the consolidated backend endpoint
    try:
        response = requests.post(
            "http://localhost:8000/api/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Extract the response and node list
        response_data = response.json()
        ai_response = response_data["response"]
        node_list = response_data.get("node_list", [])
        mcp_tools_used = response_data.get("mcp_tools_used", [])
        
        # Update tools used if MCP was used
        if mcp_tools_used:
            st.session_state.tools_used = mcp_tools_used
            
            # Display tools used in this response
            with st.expander("MCP Tools Used in This Response"):
                for tool in mcp_tools_used:
                    st.markdown(f"- {tool}")
        
        print(f"Node list: {node_list}")
        print(f"MCP tools used: {mcp_tools_used}")

    except Exception as e:
        ai_response = f"Error: Unable to get response from server. {str(e)}"

    # Render graph if node list is not empty
    if node_list:
        render_graph(f"MATCH (n)-[r]-(m) WHERE n.id IN {node_list} RETURN n,r,m LIMIT 50")
    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(ai_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": ai_response})