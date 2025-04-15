import streamlit as st
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
        "use_mcp": False  # Disable MCP tools by default
    }
    
    # Make API call to the backend endpoint
    try:
        with st.spinner("Thinking..."):
            response = requests.post(
                "http://localhost:8000/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            # Extract the response
            response_data = response.json()
            ai_response = response_data["response"]
        
    except Exception as e:
        ai_response = f"Error: Unable to get response from server. {str(e)}"
    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(ai_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": ai_response})