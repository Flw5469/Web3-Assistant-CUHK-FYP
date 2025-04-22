import requests
import time
import json

# Configuration
base_url = "http://localhost:8887"  # Replace with your actual API base URL
sessionId = 1
projectId = 1
instruction = "為何交易會有比特幣?" 
type_ = "NL"  # Natural Language query type
userId = 111111
# Step 1: Submit the query via POST request
payload = {
    "userId": userId,
    "sessionId": sessionId,
    "projectId": projectId,
    "instruction": instruction,
    "document": "",
    "type": type_
}

try:
    response = requests.post(
        f"{base_url}/v1/datas/asyncSubmit",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()  # Raise exception for bad status codes

    # Assuming the POST response contains the job ID in {"id": <job_id>} format
    response_data = response.json()
    # print(f"response_data: {response_data}")
    job_id = response_data["result"]["id"]
except Exception as e:
    ai_response = f"Error: Unable to submit query to server. {str(e)}"
    node_list = []
    print(f"AI Response: {ai_response}")
    print(f"Node List: {node_list}")
    exit(1)

# Step 2: Poll the query status via GET request until finished
while True:
    try:
        response = requests.get(
            f"{base_url}/v1/datas/query/{job_id}",
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()  # Raise exception for bad status codes

        # Check if the query processing is complete
        response_data = response.json()
        print(f"response_data: {response_data}")

        if response_data["success"] and response_data["result"]["status"] == "FINISH":
            break
        time.sleep(1)  # Wait 1 second before polling again

    except Exception as e:
        ai_response = f"Error: Unable to poll query status from server. {str(e)}"
        node_list = []
        print(f"AI Response: {ai_response}")
        print(f"Node List: {node_list}")
        exit(1)

# Step 3: Extract the answer and node list from the result
try:
    # Parse the resultMessage string into a JSON object
    result_message_str = response_data["result"]["resultMessage"]
    result_message = json.loads(result_message_str)
    
    # Print the result_message for debugging
    print("\nResult Message Structure:")
    print(json.dumps(result_message, indent=2, ensure_ascii=False)[:500] + "..." if len(json.dumps(result_message, ensure_ascii=False)) > 500 else json.dumps(result_message, indent=2, ensure_ascii=False))
    
    # Check if 'nodes' exists in the response
    if "nodes" in result_message:
        nodes = result_message["nodes"]
        
        # Extract ai_response from the node with id "0" (assumed to be the final answer node)
        ai_response_node = next((node for node in nodes if node["id"] == "0"), None)
        if ai_response_node:
            ai_response = ai_response_node["answer"].strip()  # Remove leading/trailing whitespace
            # If the answer is empty, provide a fallback message
            if not ai_response:
                ai_response = "No answer provided by the knowledge base."
        else:
            ai_response = "No final answer node found."

        # Extract the node list
        node_list = nodes

        # Print the results with better formatting
        print("\n" + "="*80)
        print("AI RESPONSE:")
        print("-"*80)
        print(ai_response)
        print("\n" + "="*80)
        print("DETAILED NODE LIST:")
        print("-"*80)
        for node in node_list:
            print(f"\nNode {node['id']}:")
            print(f"  Title: {node['title']}")
            print(f"  Question: {node['question']}")
            # print(f"  State: {node['state']}")
            print(f"  Answer: {node['answer'][:200]}..." if len(node['answer']) > 200 else f"  Answer: {node['answer']}")
        print("="*80 + "\n")
    else:
        # If no 'nodes' key exists, try to extract the answer directly from the result_message
        print("\n" + "="*80)
        print("AI RESPONSE (from resultMessage):")
        print("-"*80)
        
        # Based on the observed response format, extract the answer from the appropriate field
        # You may need to adjust this based on the actual structure of result_message
        if "think" in result_message:
            ai_response = result_message["think"]
        elif "answer" in result_message:
            ai_response = result_message["answer"]
        elif isinstance(result_message, str):
            ai_response = result_message
        else:
            ai_response = "Response structure doesn't contain a recognizable answer field."
            
        print(ai_response)
        node_list = []
        print("\nNo node list available in the response.")
        print("="*80 + "\n")

except Exception as e:
    ai_response = f"Error: Unable to parse response from server. {str(e)}"
    node_list = []
    print("\nERROR:")
    print("-"*80)
    print(ai_response)
    print("\nNode List: []")
    print("\nRaw resultMessage (if available):")
    try:
        print(result_message_str[:500] + "..." if len(result_message_str) > 500 else result_message_str)
    except:
        print("Raw resultMessage not available.")
