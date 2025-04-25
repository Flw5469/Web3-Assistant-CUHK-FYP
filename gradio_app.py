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
import traceback

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
    try:
        # Escape any user input for security
        safe_input = html.escape(input)
        
        html_content = f"""
        <html>
        <head>
            <title>Neovis.js Simple Example</title>
            <style type="text/css">
                html, body {{
                    font: 16pt arial;
                    margin: 0;
                    padding: 0;
                }}

                #viz {{
                    width: 100%;
                    height: 300px;
                    border: 1px solid lightgray;
                    font: 22pt arial;
                    background-color: #f9f9f9;
                }}
                
                .viz-status {{
                    padding: 10px;
                    margin-top: 5px;
                    background-color: #f0f0f0;
                    border-radius: 5px;
                    font-size: 14px;
                    color: #666;
                }}
            </style>

            <!-- Load required libraries -->
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
                            label:"id",
                            caption: "id",
                            size: "size",
                            community: "community"
                          }},
                          "*":{{
                            label:"*",
                            caption: "id"          
                          }},
                        }},
                        relationships: {{
                            "*": {{
                                label:"description",
                                caption: "description",
                                value: "id",
                                thickness: "weight"
                            }}
                        }},
                        initialCypher: "{safe_input}",
                        visConfig: {{
                            nodes: {{
                                shape: 'circle',
                                physics: true,
                            }},
                            edges: {{
                                smooth: {{
                                    enabled: true,
                                    type: "dynamic"
                                }}
                            }}
                        }}
                    }};

                    try {{
                        viz = new NeoVis.default(config);
                        viz.render();
                        console.log(viz);
                        
                        // Add event listeners
                        viz.registerOnEvent("completed", (e) => {{
                            document.getElementById("viz-status").innerHTML = "Graph visualization completed";
                            // Check if we have any nodes
                            if (viz.nodes.length === 0) {{
                                document.getElementById("viz-status").innerHTML = "No nodes found in the graph. Try a different query.";
                            }}
                        }});
                        
                        viz.registerOnEvent("error", (e) => {{
                            document.getElementById("viz-status").innerHTML = "Error rendering graph: " + e.message;
                        }});
                    }} catch(err) {{
                        document.getElementById("viz-status").innerHTML = "Error initializing graph: " + err.message;
                        console.error(err);
                    }}
                }}
            </script>
        </head>
        <body onload="draw()">
            <div id="viz"></div>
            <div id="viz-status" class="viz-status">Loading graph visualization...</div>
            
            <div style="margin-top: 10px; padding: 10px; border-radius: 5px; background-color: #f0f0f0;">
                <p><strong>Knowledge Graph</strong> - Showing entities and relationships from the database.</p>
                <p>The graph is interactive - you can click and drag nodes, zoom in/out, and hover for more information.</p>
            </div>
        </body>
        </html>
        """
        return html_content
    except Exception as e:
        # Return a fallback HTML with error message
        error_message = str(e)
        return f"""
        <html>
        <head>
            <style>
                .error-container {{
                    padding: 15px;
                    background-color: #ffdddd;
                    border-left: 6px solid #f44336;
                    margin-bottom: 15px;
                }}
                .fallback-graph {{
                    width: 100%;
                    height: 300px;
                    border: 1px solid lightgray;
                    background-color: #f9f9f9;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-direction: column;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <p><strong>Error rendering graph:</strong> {html.escape(error_message)}</p>
            </div>
            <div class="fallback-graph">
                <p>Unable to render graph visualization</p>
                <p>Please try again with a different query</p>
            </div>
        </body>
        </html>
        """

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
            
            # Check content type for formatting with improved error handling
            try:
                # First check if content is a JSON string
                if isinstance(content, str) and (content.strip().startswith('{') or content.strip().startswith('[')):
                    try:
                        # Try to parse as JSON
                        parsed_json = json.loads(content)
                        formatted_json = json.dumps(parsed_json, indent=2)
                        html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(formatted_json)}</pre>'
                    except json.JSONDecodeError:
                        # Not valid JSON, display as is
                        html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(content)}</pre>'
                # Check if content is already a dict or list
                elif isinstance(content, (dict, list)):
                    # Handle nested structure similar to the provided code
                    if isinstance(content, dict):
                        # Try to access content.text path
                        if 'content' in content and isinstance(content['content'], dict) and 'text' in content['content']:
                            html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(content["content"]["text"])}</pre>'
                        # Try to access text directly
                        elif 'text' in content:
                            html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(content["text"])}</pre>'
                        else:
                            # Default to JSON
                            formatted_json = json.dumps(content, indent=2)
                            html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(formatted_json)}</pre>'
                    else:
                        # For lists
                        formatted_json = json.dumps(content, indent=2)
                        html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(formatted_json)}</pre>'
                else:
                    # Regular text
                    html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">{html.escape(str(content))}</pre>'
            except Exception as e:
                # Fallback for any display errors
                html_output += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto;">Error displaying result: {html.escape(str(e))}</pre>'
            
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
                graph_html = f"<div class='error-container' style='padding: 15px; background-color: #ffdddd; border-left: 6px solid #f44336; margin-bottom: 15px;'><p><strong>Error rendering graph:</strong> {str(e)}</p></div>"
        
        # Add assistant response to chat history
        chat_history.append({"role": "assistant", "content": ai_response})
        
        # Format the intermediate results for display
        formatted_results = format_intermediate_results(intermediate_results)
        
        # Format tools used for display
        tools_used_html = ""
        if tools_used:
            tools_used_html = "<ul>" + "".join([f"<li>{tool}</li>" for tool in tools_used]) + "</ul>"
        
        return chat_history, formatted_results, tools_used_html, graph_html
        
    except requests.exceptions.RequestException as e:
        error_message = f"Error: Unable to connect to server. {str(e)}"
        chat_history.append({"role": "assistant", "content": error_message})
        return chat_history, "", "", ""
    except Exception as e:
        error_message = f"Error: {type(e).__name__} - {str(e)}"
        print(f"Exception in process_query: {error_message}")
        traceback.print_exc()
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

# Function to render an example knowledge graph
def render_example_graph():
    """Helper function to render an example knowledge graph with static HTML"""
    try:
        print("Rendering example knowledge graph")
        
        # Create a static HTML visualization that doesn't require Neo4j connection
        html_content = """
        <html>
        <head>
            <title>Example Knowledge Graph</title>
            <style type="text/css">
                html, body {
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                }
                
                #exampleGraph {
                    width: 100%;
                    height: 300px;
                    border: 1px solid lightgray;
                    font: 16pt arial;
                    position: relative;
                    background-color: #f9f9f9;
                    overflow: hidden;
                }
                
                .node {
                    position: absolute;
                    border-radius: 50%;
                    width: 60px;
                    height: 60px;
                    line-height: 60px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    transition: transform 0.2s ease;
                    cursor: pointer;
                }
                
                .node:hover {
                    transform: scale(1.1);
                    z-index: 10;
                }
                
                .entity {
                    background-color: #4285f4;
                }
                
                .document {
                    background-color: #34a853;
                }
                
                .relationship {
                    position: absolute;
                    border-top: 2px solid #999;
                    transform-origin: 0 0;
                    z-index: -1;
                }
                
                .relationship-label {
                    position: absolute;
                    background-color: #ffffff;
                    padding: 2px 5px;
                    border-radius: 3px;
                    font-size: 12px;
                    color: #666;
                    text-align: center;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                
                .graph-info {
                    margin-top: 10px;
                    padding: 10px;
                    background-color: #f0f0f0;
                    border-radius: 5px;
                    font-size: 14px;
                }
            </style>
            
            <script>
                // Simple JavaScript to draw lines between nodes after they're positioned
                window.onload = function() {
                    const nodes = document.querySelectorAll('.node');
                    const relationships = [
                        {from: 'doc1', to: 'entity1', label: 'MENTIONS'},
                        {from: 'doc1', to: 'entity2', label: 'MENTIONS'},
                        {from: 'doc1', to: 'entity3', label: 'MENTIONS'},
                        {from: 'doc2', to: 'entity1', label: 'MENTIONS'},
                        {from: 'doc2', to: 'entity4', label: 'MENTIONS'},
                        {from: 'entity2', to: 'entity3', label: 'RELATED_TO'},
                    ];
                    
                    try {
                        // Draw relationships
                        relationships.forEach(rel => {
                            drawRelationship(
                                document.getElementById(rel.from), 
                                document.getElementById(rel.to), 
                                rel.label
                            );
                        });
                        
                        // Add interactivity
                        nodes.forEach(node => {
                            node.addEventListener('click', function() {
                                // Highlight connected relationships
                                const nodeId = this.id;
                                const connectedRels = relationships.filter(
                                    rel => rel.from === nodeId || rel.to === nodeId
                                );
                                
                                // Reset all nodes and relationships
                                document.querySelectorAll('.relationship').forEach(
                                    el => el.style.borderTop = '2px solid #999'
                                );
                                nodes.forEach(n => n.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)');
                                
                                // Highlight this node
                                this.style.boxShadow = '0 0 10px rgba(255,215,0,1)';
                                
                                // Highlight connected relationships
                                connectedRels.forEach(rel => {
                                    const selector = `[data-from="${rel.from}"][data-to="${rel.to}"]`;
                                    const relElement = document.querySelector(selector);
                                    if (relElement) {
                                        relElement.style.borderTop = '3px solid #ff9900';
                                    }
                                    
                                    // Also highlight connected nodes
                                    const connectedNode = (rel.from === nodeId) ? 
                                        document.getElementById(rel.to) : 
                                        document.getElementById(rel.from);
                                    if (connectedNode) {
                                        connectedNode.style.boxShadow = '0 0 8px rgba(66,133,244,0.8)';
                                    }
                                });
                            });
                        });
                    } catch (err) {
                        console.error('Error initializing example graph:', err);
                        document.getElementById('graphStatus').innerHTML = 
                            'Error initializing example graph: ' + err.message;
                    }
                };
                
                function drawRelationship(node1, node2, label) {
                    if (!node1 || !node2) {
                        console.error('Cannot draw relationship: node not found');
                        return;
                    }
                    
                    const container = document.getElementById('exampleGraph');
                    
                    // Get centers of each node
                    const rect1 = node1.getBoundingClientRect();
                    const rect2 = node2.getBoundingClientRect();
                    const containerRect = container.getBoundingClientRect();
                    
                    const x1 = rect1.left + rect1.width/2 - containerRect.left;
                    const y1 = rect1.top + rect1.height/2 - containerRect.top;
                    const x2 = rect2.left + rect2.width/2 - containerRect.left;
                    const y2 = rect2.top + rect2.height/2 - containerRect.top;
                    
                    // Create line
                    const line = document.createElement('div');
                    line.className = 'relationship';
                    line.setAttribute('data-from', node1.id);
                    line.setAttribute('data-to', node2.id);
                    
                    // Calculate line length and angle
                    const length = Math.sqrt((x2-x1)*(x2-x1) + (y2-y1)*(y2-y1));
                    const angle = Math.atan2(y2-y1, x2-x1) * 180 / Math.PI;
                    
                    // Position and rotate line
                    line.style.width = length + 'px';
                    line.style.left = x1 + 'px';
                    line.style.top = y1 + 'px';
                    line.style.transform = 'rotate(' + angle + 'deg)';
                    
                    // Create and position label
                    const labelElem = document.createElement('div');
                    labelElem.className = 'relationship-label';
                    labelElem.textContent = label;
                    labelElem.style.left = (x1 + x2) / 2 - 30 + 'px';
                    labelElem.style.top = (y1 + y2) / 2 - 10 + 'px';
                    
                    container.appendChild(line);
                    container.appendChild(labelElem);
                }
            </script>
        </head>
        <body>
            <div id="exampleGraph">
                <!-- Document Nodes -->
                <div id="doc1" class="node document" style="left: 50px; top: 50px;">Doc 1</div>
                <div id="doc2" class="node document" style="left: 50px; top: 180px;">Doc 2</div>
                
                <!-- Entity Nodes -->
                <div id="entity1" class="node entity" style="left: 200px; top: 120px;">Bitcoin</div>
                <div id="entity2" class="node entity" style="left: 320px; top: 50px;">Crypto</div>
                <div id="entity3" class="node entity" style="left: 320px; top: 180px;">Market</div>
                <div id="entity4" class="node entity" style="left: 200px; top: 230px;">Tron</div>
            </div>
            
            <div id="graphStatus" style="text-align: center; padding: 5px; font-style: italic;"></div>
            
            <div class="graph-info">
                <p><strong>Example Knowledge Graph</strong> - This visualization shows how documents connect to entities within the Neo4j database.</p>
                <p>In a real query, you would see actual documents and entities extracted from your data, visualized with interactive features.</p>
                <p><small>Try clicking on nodes to see connections highlighted.</small></p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        # Return a fallback HTML with error message
        error_message = str(e)
        print(f"Error rendering example graph: {error_message}")
        return f"""
        <html>
        <head>
            <style>
                .error-container {{
                    padding: 15px;
                    background-color: #ffdddd;
                    border-left: 6px solid #f44336;
                    margin-bottom: 15px;
                }}
                .fallback-graph {{
                    width: 100%;
                    height: 300px;
                    border: 1px solid lightgray;
                    background-color: #f9f9f9;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-direction: column;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <p><strong>Error rendering example graph:</strong> {html.escape(error_message)}</p>
            </div>
            <div class="fallback-graph">
                <p>Unable to render example graph visualization</p>
                <p>Please try refreshing the page</p>
            </div>
        </body>
        </html>
        """

# Function to toggle the example graph display
def toggle_example_graph(button_text, graph_html):
    """Toggle the example graph display on/off"""
    if "Show" in button_text:
        # Currently showing "Show Example Knowledge Graph" button - so show the graph
        return "Hide Example Knowledge Graph", render_example_graph()
    else:
        # Currently showing "Hide Example Knowledge Graph" button - so hide the graph
        return "Show Example Knowledge Graph", ""

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
                    # avatar_images=("👤", "🤖"),
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
                gr.Markdown("### Knowledge Graph")
                graph_display = gr.HTML(visible=True, elem_id="graph-display")
                
                # Tool execution details
                with gr.Accordion("Tool Execution Details", open=False):
                    intermediate_results_html = gr.HTML()
                    tools_used_html = gr.HTML(label="Tools Used")
            
                # Example graph button
                with gr.Row():
                    example_graph_btn = gr.Button("Show Example Knowledge Graph", variant="secondary")
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
    
    # Example graph button click
        example_graph_btn.click(
            fn=toggle_example_graph,
            inputs=[example_graph_btn, graph_display],
            outputs=[example_graph_btn, graph_display]
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