import streamlit as st
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pandas as pd
import streamlit.components.v1 as components
import json
import ast

def convert_to_graph_format(data):
    nodes = []
    edges = []
    node_ids = {}
    import re

    # Remove any unnecessary escape characters

    data = ast.literal_eval(data)
    print(f"data: {data}")

    # First, create nodes from unique entities in the third position
    for item in data:
        document_id, relation, entity = item
        
        # If we haven't seen this entity before, create a node for it
        if entity not in node_ids:
            node_id = entity.lower().replace(' ', '_')
            node_ids[entity] = node_id
            
            # Create node
            nodes.append({
                'data': {
                    'id': node_id,
                    'label': entity,
                    'type': 'entity'
                }
            })
    
    # Also create nodes for document IDs (first position)
    unique_docs = set(item[0] for item in data)
    for doc_id in unique_docs:
        short_id = doc_id[:8]  # Use first 8 chars for brevity
        node_ids[doc_id] = short_id
        
        nodes.append({
            'data': {
                'id': short_id,
                'label': f'Document {short_id}',
                'type': 'document'
            }
        })
    
    # Create edges between documents and entities
    for i, item in enumerate(data):
        document_id, relation, entity = item
        
        source_id = node_ids[document_id[:8]]
        target_id = node_ids[entity[:8]]
        
        # Create edge
        edges.append({
            'data': {
                'id': f'e{i+1}',
                'source': source_id,
                'target': target_id,
                'label': relation,
                'sentiment': 'neutral'  # Default sentiment
            }
        })
    
    return nodes+edges


def fun(graph_string):
  if not graph_string:
    return  # Return early if no graph data is provided
  
  # Process the graph string and display the visualisation
  try:
    graph_result = convert_to_graph_format(graph_string)

    html = """
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
                elements: """ + str(graph_result) + """,
                
                // Define the visual style
                style: [
                    {
                        selector: 'node',
                        style: {
                            'background-color': '#4287f5',
                            'label': 'data(label)',
                            'color': '#000',
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
"""
    print(html)
    return components.html(html,
        height=300,
    )
  except Exception as e:
    print(f"Error processing graph: {str(e)}")
    return None




# Load environment variables for Neo4j connection
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL")

st.title("Web3 Assistant")

# Initialize chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Simplified sidebar with just essential options
with st.sidebar:
    st.header("Options")
    # Model selection
    version = st.selectbox("Choose a version:", ["3.5", "4o"])
    
    # Lazy-loaded cryptocurrency selection expander
    with st.expander("Select Cryptocurrencies"):
        selected_coins = []
        if st.checkbox("Bitcoin"):
            selected_coins.append("Bitcoin")
        if st.checkbox("Ethereum"):
            selected_coins.append("Ethereum")
        if st.checkbox("Web3"):
            selected_coins.append("Web3")
    
    # Simplified mode selection
    mode = st.selectbox(
        "Select framework",
        ["baseline", "enhanced", "direct"]
    )

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
    
st.sidebar.header("MCP Platform")
use_mcp = st.sidebar.checkbox("Use MCP Platform Tools", value=False)

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
                    st.markdown(f"- {tool.get('name')}")
                st.markdown("---")
    else:
        st.sidebar.error("MCP Platform is not initialized")

# React to user input
if prompt := st.chat_input("What would you like to know"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare the payload with minimal required data
    payload = {
        "prompt": prompt,
        "coin_name": selected_coins,
        "model": version,
        "mode": mode,
        "use_mcp": use_mcp,  # Disable MCP tools by default
        "excluded_tool_list": []
    }
    
    # Make API call to the backend endpoint
    try:
        with st.spinner("Thinking..."):
            response = requests.post(
                "http://localhost:8000/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60  # Add timeout to avoid hanging indefinitely
            )
            
            # Extract the response
            if response.status_code == 200:
                response_data = response.json()
                print(response_data)
                ai_response = response_data.get("response", "No response received from the server.")
            else:
                response_data = {}
                ai_response = f"Error: The server returned status code {response.status_code}."
        
    except requests.exceptions.Timeout:
        response_data = {}
        ai_response = "Error: The request timed out. Please try again later."
    except requests.exceptions.ConnectionError:
        response_data = {}
        ai_response = "Error: Could not connect to the server. Please check if the backend is running."
    except Exception as e:
        response_data = {}
        ai_response = f"Error: An unexpected error occurred. {str(e)}"
    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        if 'graph_string' in response_data:
            try:
                fun(response_data['graph_string'])
            except Exception as e:
                st.error(f"Failed to display graph: {str(e)}")
        st.markdown(ai_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": ai_response})