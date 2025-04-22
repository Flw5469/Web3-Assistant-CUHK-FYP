import gradio as gr
import random
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pandas as pd
import json
import re
import html

# Load environment variables for backend connection
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "staysovryn")
BACKEND_URL = os.getenv("BACKEND_URL")

# Initialize global variables
chat_history = []
tools_used = []
intermediate_results = []
uploaded_file_info = None
mcp_tool_options = []
crypto_options = []

def render_graph(input):
    """Generate Neo4j graph visualization HTML using Neovis.js"""
    html_content = f"""
    <html>
    <head>
        <title>Neovis.js Simple Example</title>
        <style type="text/css">
            html, body {{
                font: 16pt arial;
            }}

            #viz {{
                width: 100%;
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
    """
    return html_content

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

# Format intermediate results for display
def format_intermediate_results(results):
    if not results:
        return ""
    
    html_output = ""
    
    # Group results by step number
    step_results = {}
    for result in results:
        step_num = result.get('step', 0)
        if step_num not in step_results:
            step_results[step_num] = []
        step_results[step_num].append(result)
    
    # Generate HTML for each step
    for step_num in sorted(step_results.keys()):
        html_output += f"<h3>Step {step_num}</h3>"
        
        for result in step_results[step_num]:
            tool_name = result.get('tool', 'Unknown Tool')
            timestamp = result.get('timestamp', '')
            content = result.get('content', 'No content available')
            arguments = result.get('arguments', '')
            
            # Create a container for the result
            html_output += '<div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 15px;">'
            
            # Tool name and timestamp in a flex container
            html_output += '<div style="display: flex; justify-content: space-between; margin-bottom: 10px;">'
            html_output += f'<div><strong>Tool: {html.escape(tool_name)}</strong></div>'
            if timestamp:
                html_output += f'<div><small>{html.escape(timestamp)}</small></div>'
            html_output += '</div>'
            
            # Arguments if available
            if arguments:
                html_output += '<details style="margin-bottom: 10px;">'
                html_output += '<summary style="cursor: pointer; padding: 5px;">Arguments</summary>'
                html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto;">{html.escape(arguments)}</pre>'
                html_output += '</details>'
            
            # Display content
            html_output += '<div><strong>Result:</strong></div>'
            
            # Check content type for formatting
            if content.strip().startswith('{') or content.strip().startswith('['):
                try:
                    # Try to format as JSON
                    parsed_json = json.loads(content)
                    formatted_json = json.dumps(parsed_json, indent=2)
                    html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(formatted_json)}</pre>'
                except:
                    # Fall back to plain text
                    html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(content)}</pre>'
            else:
                # Regular text
                html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(content)}</pre>'
            
            html_output += '</div>'
            
        # Add a separator between steps
        html_output += '<hr style="margin: 20px 0;">'
    
    return html_output

# Process user query and get AI response
def process_query(prompt, model, mode, selected_coins, filtered_tools=None, uploaded_file=None):
    global chat_history, tools_used, intermediate_results, uploaded_file_info
    
    try:
        # Add user message to chat history
        chat_history.append({"role": "user", "content": prompt})
        
        # Get file content from global state if available
        file_content = None
        file_name = None
        if hasattr(globals(), 'uploaded_file_info') and uploaded_file_info:
            file_content = uploaded_file_info.get('file_content')
            file_name = uploaded_file_info.get('file_name')
        
        # Prepare the payload based on mode
        if mode == "MCP":
            # Use MCP mode
            payload = {
                "prompt": prompt,
                "model": model,
                "use_mcp": True,
                "file_content": file_content,
                "file_name": file_name,
                "filter_tools": filtered_tools if filtered_tools and len(filtered_tools) > 0 else None
            }
            
            print(f"Sending payload with filter_tools: {filtered_tools if filtered_tools and len(filtered_tools) > 0 else None}")
        else:
            # Use traditional modes (baseline, enhanced, etc.)
            payload = {
                "prompt": prompt,
                "coin_name": selected_coins,
                "model": model,
                "mode": mode,
                "use_mcp": False,
                "file_content": file_content,
                "file_name": file_name
            }
        
        # Make API call to the backend endpoint
        response = requests.post(
            f"{BACKEND_URL}/api/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Extract the response and tool information
        response_data = response.json()
        ai_response = response_data["response"]
        mcp_tools_used = response_data.get("mcp_tools_used", [])
        
        # Update tools used
        tools_used = mcp_tools_used
        
        # Update intermediate results if available
        if 'intermediate_results' in response_data and response_data['intermediate_results']:
            intermediate_results = response_data['intermediate_results']
        
        # Get node_list if available in the response
        node_list = response_data.get("node_list", [])
        
        # Render graph if node list is not empty
        graph_html = ""
        if node_list:
            try:
                graph_html = render_graph(f"MATCH (n)-[r]-(m) WHERE n.id IN {node_list} RETURN n,r,m LIMIT 50")
            except Exception as e:
                print(f"Graph rendering error: {str(e)}")
        
        # Add assistant response to chat history
        chat_history.append({"role": "assistant", "content": ai_response})
        
        # Format the intermediate results for display
        formatted_results = format_intermediate_results(intermediate_results)
        
        # Format tools used for display
        tools_used_html = ""
        if tools_used:
            tools_used_html = "<ul>" + "".join([f"<li>{tool}</li>" for tool in tools_used]) + "</ul>"
        
        return chat_history, formatted_results, tools_used_html, graph_html
        
    except Exception as e:
        error_message = f"Error: Unable to get response from server. {str(e)}"
        chat_history.append({"role": "assistant", "content": error_message})
        return chat_history, "", "", ""

# Process function to handle the coin checkboxes and tool filters
def process_with_coins(prompt, model, mode, *args, uploaded_file=None):
    # Extract coin checkboxes from the args
    # The number of coin checkboxes is determined by len(crypto_options)
    num_crypto_options = len(crypto_options)
    checkbox_values = args[:num_crypto_options]
    
    # Extract tool filter checkboxes from the remaining args
    tool_filter_values = args[num_crypto_options:]
    
    # Process coin selections
    selected_coins = [crypto_options[i] for i, value in enumerate(checkbox_values) if value]
    
    # Process tool filters - Only include tools that are NOT checked
    # This means we're filtering OUT these tools
    filtered_tools = []
    
    # Check if we have the right number of tool values
    if len(tool_filter_values) > 0 and len(mcp_tool_options) > 0:
        # Include only tools that are unchecked (to be filtered out)
        for i, value in enumerate(tool_filter_values):
            if i < len(mcp_tool_options):  # Safety check
                if not value:  # If unchecked
                    filtered_tools.append(mcp_tool_options[i])
    
    print(f"Filtered tools (to be excluded): {filtered_tools}")
    
    # Call the main process function
    return process_query(prompt, model, mode, selected_coins, filtered_tools, uploaded_file)

# Handler for Select All button
def select_all_tools():
    return [True] * len(mcp_tool_options)

# Handler for Deselect All button
def deselect_all_tools():
    return [False] * len(mcp_tool_options)

# Main Gradio App
def create_app():
    # Get MCP information
    mcp_info = fetch_mcp_tools()
    is_mcp_initialized = mcp_info["initialized"]
    
    # Store available tools globally
    global mcp_tool_options
    mcp_tool_options = [tool.get("name") for tool in mcp_info.get("tools", [])]
    
    # Define mode options
    mode_dict = {
        # "Baseline": "baseline",
        # "Enhanced (with background knowledge)": "enhanced",
        # "Tool-based Search": "tool_search",
        "Simple Query": "direct",
        "MCP": "mcp"
    }
    
    # Crypto options
    global crypto_options
    crypto_options = ["Bitcoin", "Tron", "Web3", "Market", "Crypto", "Cardano"]
    
    # Model options
    model_options = ["3.5", "4o", "4o-mini"]
    
    # Theme configuration
    theme = gr.themes.Default().set(
        body_background_fill="#f7f7f7",
        block_background_fill="#ffffff",
        block_label_background_fill="#f0f0f0",
        input_background_fill="#ffffff"
    )
    
    with gr.Blocks(title="Web3 Assistant", theme=theme) as app:
        gr.Markdown("# Web3 Assistant")
        
        with gr.Row():
            # Main chat area
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    value=chat_history,
                    elem_id="chatbot",
                    height=500,
                    avatar_images=("👤", "🤖"),
                    type="messages"
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="What would you like to know?",
                        show_label=False,
                        container=False
                    )
                    send_btn = gr.Button("Send", variant="primary")
                
                # Graph visualization area (if provided)
                graph_display = gr.HTML(label="Knowledge Graph", visible=False)
                
                with gr.Accordion("Tool Execution Details", open=False):
                    intermediate_results_html = gr.HTML()
                    tools_used_html = gr.HTML(label="Tools Used")
            
            # Sidebar with controls
            with gr.Column(scale=1):
                gr.Markdown("### Settings")
                
                # Date range selection using dropdowns instead of Date component
                with gr.Group():
                    gr.Markdown("#### Select Date Range")
                    
                    # Generate date options for the last 30 days
                    current_date = datetime.now()
                    date_options = [(current_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(31)]
                    
                    # Create dropdown selectors for start and end dates
                    end_date = gr.Dropdown(
                        choices=date_options,
                        value=date_options[0],
                        label="End Date"
                    )
                    start_date = gr.Dropdown(
                        choices=date_options,
                        value=date_options[7],  # Default to a week ago
                        label="Start Date"
                    )
                
                # Cryptocurrency selection
                coin_checkboxes = []
                with gr.Accordion("Select Cryptocurrencies", open=False):
                    for coin in crypto_options:
                        coin_checkboxes.append(gr.Checkbox(label=coin, value=False))
                
                # Mode selection
                gr.Markdown("#### Select Mode")
                mode_dropdown = gr.Dropdown(
                    choices=list(mode_dict.keys()),
                    value="MCP" if is_mcp_initialized else "Baseline",
                    label="Select Framework"
                )
                
                # Model selection
                model_dropdown = gr.Dropdown(
                    choices=model_options,
                    value="3.5",
                    label="Choose a version"
                )
                
                # MCP Platform info and tool filtering
                gr.Markdown("#### MCP Platform")
                if is_mcp_initialized:
                    gr.Markdown(f"✅ MCP Platform is connected with {len(mcp_info['tools'])} tools")
                    
                    # Group tools by server for display
                    tools_by_server_html = ""
                    for server in mcp_info["servers"]:
                        tools_for_server = [tool for tool in mcp_info["tools"] if tool.get("server") == server]
                        if tools_for_server:
                            tools_by_server_html += f"<strong>Server: {server}</strong><ul>"
                            for tool in tools_for_server:
                                tools_by_server_html += f"<li>{tool.get('name')}</li>"
                            tools_by_server_html += "</ul><hr>"
                    
                    # Tool filtering UI
                    with gr.Accordion("Filter MCP Tools", open=False):
                        gr.Markdown("### Tool Selection")
                        gr.Markdown("✅ **Checked tools will be used** in processing your query")
                        gr.Markdown("❌ **Unchecked tools will be excluded**")
                        
                        tool_filter_checkboxes = []
                        
                        # Create two columns for better layout
                        with gr.Row():
                            # Left column
                            with gr.Column():
                                # First half of tools
                                half_point = len(mcp_tool_options) // 2
                                for tool in mcp_tool_options[:half_point]:
                                    tool_filter_checkboxes.append(gr.Checkbox(label=tool, value=True))
                            
                            # Right column
                            with gr.Column():
                                # Second half of tools
                                for tool in mcp_tool_options[half_point:]:
                                    tool_filter_checkboxes.append(gr.Checkbox(label=tool, value=True))
                        
                        # Select/Deselect All buttons
                        with gr.Row():
                            select_all_btn = gr.Button("Select All Tools", size="sm")
                            deselect_all_btn = gr.Button("Exclude All Tools", size="sm")
                    
                else:
                    gr.Markdown("❌ MCP Platform is not initialized")
                
                # File upload
                file_input = gr.File(label="Upload your input file", file_types=[".csv"])
                upload_btn = gr.Button("Upload File to Backend", variant="secondary")
                file_status = gr.Markdown("No file uploaded")
        
        # Handle form submission
        submit_event = send_btn.click(
            fn=process_with_coins,
            inputs=[
                msg,  # prompt
                model_dropdown,  # model
                mode_dropdown,  # mode
                *coin_checkboxes,  # each checkbox as a separate input
                *tool_filter_checkboxes,  # tool filter checkboxes
                file_input  # uploaded_file
            ],
            outputs=[
                chatbot,  # chat_history
                intermediate_results_html,  # formatted_results
                tools_used_html,  # tools_used_html
                graph_display  # graph_html
            ]
        )
        
        # Handle file upload button click
        upload_btn.click(
            fn=upload_file_to_backend,
            inputs=[file_input],
            outputs=[file_status]
        )
        
        # Handle Select All button click
        select_all_btn.click(
            fn=select_all_tools,
            outputs=tool_filter_checkboxes
        )
        
        # Handle Deselect All button click
        deselect_all_btn.click(
            fn=deselect_all_tools,
            outputs=tool_filter_checkboxes
        )
        
        # Clear the message box after sending
        submit_event.then(lambda: "", None, msg)
        
        # Also submit on Enter key
        msg.submit(
            fn=process_with_coins,
            inputs=[
                msg,
                model_dropdown,
                mode_dropdown,
                *coin_checkboxes,
                *tool_filter_checkboxes,
                file_input
            ],
            outputs=[
                chatbot,
                intermediate_results_html,
                tools_used_html,
                graph_display
            ]
        ).then(lambda: "", None, msg)
        
        # Update graph display visibility
        def update_graph_visibility(graph_html):
            return gr.update(visible=bool(graph_html))
        
        submit_event.then(
            fn=update_graph_visibility,
            inputs=[graph_display],
            outputs=[graph_display]
        )
    
    return app

# Handle file upload separately
def upload_file_to_backend(file):
    if file is None:
        return "No file selected. Please select a file first."
    
    try:
        # Upload file to backend
        files = {'file': (file.name, file)}
        response = requests.post(
            f"{BACKEND_URL}/api/upload",
            files=files
        )
        response.raise_for_status()
        
        # Store file info in session state
        global uploaded_file_info
        uploaded_file_info = response.json()
        
        return f"✅ File '{file.name}' uploaded successfully! File will be used for the next query."
    except Exception as e:
        return f"❌ Error uploading file: {str(e)}"

if __name__ == "__main__":
    app = create_app()
    app.launch(share=False) 