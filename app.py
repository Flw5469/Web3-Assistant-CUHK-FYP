import streamlit as st
import streamlit.components.v1 as components
import random
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pandas as pd
import json
import re

# Load environment variables for backend connection
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "staysovryn")
BACKEND_URL = os.getenv("BACKEND_URL")

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
        response = requests.get(f"{BACKEND_URL}/api/mcp/tools", timeout=5)
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
with st.sidebar.expander("Select Cryptocurrencies"):
    selected_coins = []
    if st.checkbox("Bitcoin"):
        selected_coins.append("Bitcoin")
    if st.checkbox("Tron"):
        selected_coins.append("Tron")
    if st.checkbox("Web3"):
        selected_coins.append("Web3")
    if st.checkbox("Market"):
        selected_coins.append("Market")
    if st.checkbox("Crypto"):
        selected_coins.append("Crypto")
    if st.checkbox("Cardano"):
        selected_coins.append("Cardano")

# Mode selection
st.sidebar.header("Select Mode")
# Map the display names to the API mode parameter values
mode_dict = {
    "Baseline": "baseline",
    "Enhanced (with background knowledge)": "enhanced",
    "Tool-based Search": "tool_search",
    "Simple Query": "direct",
    "MCP": "mcp"
}

selected_mode = st.sidebar.selectbox(
    "Select framework",
    list(mode_dict.keys())
)
mode = mode_dict[selected_mode]

# Model selection
version = st.sidebar.selectbox("Choose a version:", ["3.5", "4o", "4o-mini"])

# MCP Platform options
st.sidebar.header("MCP Platform")
mcp_info = fetch_mcp_tools()

# Set MCP as default mode if available
if mcp_info["initialized"]:
    st.sidebar.success(f"MCP Platform is connected with {len(mcp_info['tools'])} tools")
    # Default to MCP mode if available
    if selected_mode not in ["MCP"] and "MCP" in mode_dict:
        st.sidebar.info("MCP Platform is available. You can select 'MCP' mode to use it.")
    
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
                st.markdown(f"- {tool.get('name')}")
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

# Initialize intermediate results container
if "intermediate_results" not in st.session_state:
    st.session_state.intermediate_results = []

# Display intermediate results if any
if st.session_state.intermediate_results:
    with st.expander("Tool Execution Details"):
        # Group results by step number for better organization
        step_results = {}
        for result in st.session_state.intermediate_results:
            step_num = result.get('step', 0)
            if step_num not in step_results:
                step_results[step_num] = []
            step_results[step_num].append(result)
        
        # Display results grouped by step
        for step_num in sorted(step_results.keys()):
            step_container = st.container()
            with step_container:
                st.subheader(f"Step {step_num}")
                
                # Process each result in this step
                for result in step_results[step_num]:
                    # Create a container for each result with a border
                    result_container = st.container()
                    with result_container:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**Tool: {result['tool']}**")
                        with col2:
                            if 'timestamp' in result:
                                st.markdown(f"<small>{result['timestamp']}</small>", unsafe_allow_html=True)
                        
                        # Display arguments in a collapsible section if available
                        if 'arguments' in result:
                            with st.expander("Arguments"):
                                st.code(result['arguments'], language="json")
                        
                        # Display result
                        st.markdown("**Result:**")
                        if 'content' in result:
                            content = result['content']
                            # Check if it's a Title/Description format to display nicely
                            if "Title:" in content and "Description:" in content:
                                # Extract title and description for nicer formatting
                                try:
                                    # For Web3 News format
                                    if "Title: Web3 News" in content:
                                        # Extract content within <strong> tags if present
                                        title_match = re.search(r"Title: ([^\n]+)", content)
                                        title = title_match.group(1) if title_match else "Web3 News"
                                        
                                        # Look for strong tags content
                                        strong_content = re.search(r"<strong>(.*?)</strong>", content)
                                        if strong_content:
                                            highlight = strong_content.group(1)
                                            st.markdown(f"### {title}")
                                            st.markdown(f"**{highlight}**")
                                        else:
                                            # Just use the content as is with markdown
                                            st.markdown(content)
                                    else:
                                        st.markdown(content)
                                except Exception as e:
                                    # If extraction fails, display the original content
                                    st.markdown(content)
                        else:
                            st.warning("No content available for this tool result.")
                
                        # Add a visual separator after each step
                        st.markdown("---")

# React to user input
if prompt := st.chat_input("What would you like to know?"):
    print(f"Selected model: {version}")
    print(f"Selected mode: {selected_mode} ({mode_dict[selected_mode]})")
    print(f"Using MCP: {selected_mode == 'MCP'}")
    if selected_mode != 'MCP':
        print(f"Selected coins: {selected_coins}")
    
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare the payload
    if selected_mode == "MCP":
        # Use MCP mode
        payload = {
            "prompt": prompt,
            "model": version,
            "use_mcp": True
        }
    else:
        # Use traditional modes (baseline, enhanced, etc.)
        payload = {
            "prompt": prompt,
            "coin_name": selected_coins,
            "model": version,
            "mode": mode,
            "use_mcp": False
        }
    
    # Create a placeholder for the assistant's response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        with response_placeholder.container():
            with st.spinner("Thinking..."):
                # Make API call to the backend endpoint
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/api/chat",
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()  # Raise exception for bad status codes
                    
                    print("response", response)
                    # Extract the response and tool information
                    response_data = response.json()
                    ai_response = response_data["response"]
                    mcp_tools_used = response_data.get("mcp_tools_used", [])
                    
                    # Get node_list if available in the response
                    node_list = response_data.get("node_list", [])
                    
                    # Clear previous intermediate results before adding new ones
                    st.session_state.intermediate_results = []
                    
                    # Update tools used
                    if mcp_tools_used:
                        st.session_state.tools_used = mcp_tools_used
                    
                    # Update intermediate results if available
                    if 'intermediate_results' in response_data and response_data['intermediate_results']:
                        st.session_state.intermediate_results = response_data['intermediate_results']
                        
                except Exception as e:
                    ai_response = f"Error: Unable to get response from server. {str(e)}"
                
                # Replace the spinner with the actual response
                response_placeholder.markdown(ai_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    
    # Render graph if node list is not empty
    if 'node_list' in locals() and node_list:
        try:
            render_graph(f"MATCH (n)-[r]-(m) WHERE n.id IN {node_list} RETURN n,r,m LIMIT 50")
        except Exception as e:
            st.error(f"Error rendering graph: {str(e)}")
            print(f"Graph rendering error: {str(e)}")
    
    # Display tools used in this response
    if 'mcp_tools_used' in locals() and mcp_tools_used:
        with st.expander("MCP Tools Used in This Response"):
            # Simply list the tools used
            for tool in mcp_tools_used:
                st.markdown(f"- {tool}")
    
    # Display intermediate results for this response
    if 'response_data' in locals() and 'intermediate_results' in response_data and response_data['intermediate_results']:
        with st.expander("Tool Execution Results for This Response"):
            # Group results by step number for better organization
            step_results = {}
            for result in response_data['intermediate_results']:
                step_num = result.get('step', 0)
                if step_num not in step_results:
                    step_results[step_num] = []
                step_results[step_num].append(result)
            
            # Display results grouped by step
            for step_num in sorted(step_results.keys()):
                step_container = st.container()
                with step_container:
                    st.subheader(f"Step {step_num}")
                    
                    # Process each result in this step
                    for result in step_results[step_num]:
                        # Create a container for each result with a border
                        result_container = st.container()
                        with result_container:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**Tool: {result['tool']}**")
                            with col2:
                                if 'timestamp' in result:
                                    st.markdown(f"<small>{result['timestamp']}</small>", unsafe_allow_html=True)
                            
                            # Display arguments in a collapsible section if available
                            if 'arguments' in result:
                                with st.expander("Arguments"):
                                    st.code(result['arguments'], language="json")
                            
                            # Display result
                            st.markdown("**Result:**")
                            if 'content' in result:
                                content = result['content']
                                # Check if it's a Title/Description format to display nicely
                                if "Title:" in content and "Description:" in content:
                                    # Extract title and description for nicer formatting
                                    try:
                                        # For Web3 News format
                                        if "Title: Web3 News" in content:
                                            # Extract content within <strong> tags if present
                                            title_match = re.search(r"Title: ([^\n]+)", content)
                                            title = title_match.group(1) if title_match else "Web3 News"
                                            
                                            # Look for strong tags content
                                            strong_content = re.search(r"<strong>(.*?)</strong>", content)
                                            if strong_content:
                                                highlight = strong_content.group(1)
                                                st.markdown(f"### {title}")
                                                st.markdown(f"**{highlight}**")
                                            else:
                                                # Just use the content as is with markdown
                                                st.markdown(content)
                                        else:
                                            st.markdown(content)
                                    except Exception as e:
                                        # If extraction fails, display the original content
                                        st.markdown(content)
                                # Try to detect if content is JSON for better display
                                elif content.strip().startswith('{') or content.strip().startswith('['):
                                    try:
                                        parsed_json = json.loads(content)
                                        st.json(parsed_json)
                                    except:
                                        # If JSON parsing fails, display as text
                                        st.text_area("", content, height=150)
                                else:
                                    # Regular text, display in a text area
                                    st.text_area("", content, height=150)
                            else:
                                st.warning("No content available for this tool result.")
                    
                            # Add a visual separator after each step
                            st.markdown("---")
            
    print(f"MCP tools used: {mcp_tools_used if 'mcp_tools_used' in locals() else []}")