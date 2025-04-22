import asyncio
import json
import logging
import sys
import traceback
import warnings
from typing import Dict, Any, List

# Add the parent directory to the Python path
sys.path.append('.')
from ai_agent.mcp_platform import MCPPlatform

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress asyncio warnings
logging.getLogger('asyncio').setLevel(logging.ERROR)

# Suppress ResourceWarnings
warnings.filterwarnings("ignore", category=ResourceWarning)

async def process_query(platform: MCPPlatform, query: str):
    """Process a query using the MCP platform."""
    try:
        # Run the query through the platform
        result = await platform.process_query(query)
        
        # Print the result in a simplified format
        print("\nQuery Result:")
        
        # Display conversation steps
        if "conversation_steps" in result:
            print("\nConversation:")
            for step in result["conversation_steps"]:
                if step["role"] == "user":
                    print(f"\nUser: {step['content']}")
                elif step["role"] == "assistant":
                    print(f"\nAssistant: {step['content']}")
                elif step["role"] == "tool":
                    print(f"\n[Tool: {step['name']}]")
                elif step["role"] == "tool_result":
                    # Safely display tool result with error handling for various formats
                    try:
                        result_data = step.get('result', {})
                        
                        # Try different possible structures for the result
                        if isinstance(result_data, dict):
                            # Try to access content.text path
                            if 'content' in result_data and isinstance(result_data['content'], dict) and 'text' in result_data['content']:
                                print(f"Tool call result: {result_data['content']['text']}")
                            # Try to access text directly
                            elif 'text' in result_data:
                                print(f"Tool call result: {result_data['text']}")
                            # If it's a simple dict, show it as JSON
                            else:
                                result_str = json.dumps(result_data, indent=2)
                                print(f"Tool call result: {result_str[:500]}...")
                        # For non-dict results, display as is
                        else:
                            print(f"Tool call result: {str(result_data)[:500]}...")
                    except Exception as e:
                        print(f"Tool call result: [Complex data structure - {type(e).__name__}]")
                elif step["role"] == "error":
                    print(f"\nError: {step['content']}")
        
        # Display the final response
        if "final_response" in result:
            print("\nFinal Response:")
            print(result["final_response"])
            
        return result
    except Exception as e:
        print(f"\nError processing query: {type(e).__name__}")
        print(f"Details: {str(e)}")
        traceback.print_exc(file=sys.stderr)
        return None

async def safe_cleanup(platform):
    """Perform cleanup with error suppression."""
    print("\nPerforming cleanup...")
    try:
        # Cancel all pending tasks first
        for task in asyncio.all_tasks() - {asyncio.current_task()}:
            task.cancel()
            
        # Run the cleanup with a timeout
        await asyncio.wait_for(platform.cleanup(), timeout=5.0)
        print("Cleanup completed successfully")
    except asyncio.TimeoutError:
        print("Cleanup timed out, but continuing gracefully")
    except asyncio.CancelledError:
        print("Cleanup was cancelled, but continuing gracefully")
    except Exception as e:
        print(f"Non-critical error during cleanup: {type(e).__name__}")
    print("Example completed")

async def main():
    """Run the example queries."""
    platform = MCPPlatform()
    
    # Initialize the platform with necessary tools
    print("Initializing servers...")
    await platform.initialize_all_servers()
    
    # Example queries to demonstrate tool use
    example_queries = [
        # Basic Web3 Info Scraping
        "search and scrape some web3 news in both markdown and raw HTML formats",
        
        # Deep Search with Multiple Sources
        "deep search for recent developments in AI and blockchain, crawl multiple sources and compile a detailed report",
        
        # Generate LLM Text with Citations
        "search for information about quantum computing advances, then generate a technical summary with proper citations",
        
        # Targeted Deep Search with Format Options
        "perform a deep search about DeFi protocols, extract content in both markdown and HTML, focus on technical details",
        
        # Combined Search and Analysis
        "search and analyze the latest crypto market trends, generate an analytical report with data from multiple sources"
    ]
    
    try:
        # Process each query in sequence
        for i, query in enumerate(example_queries):
            print(f"\n===== Query {i+1}: {query} =====")
            await process_query(platform, query)
    finally:
        # Use a dedicated cleanup function that handles all errors
        await safe_cleanup(platform)

def run_example():
    """Run the example with proper error handling."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {type(e).__name__}")
        print(f"Details: {str(e)}")

if __name__ == "__main__":
    run_example()
    print("Program terminated")

# Example queries:
# - What's the weather in New York?
# - Create a file with investment strategies, cite sources
# - Search for recent news about artificial intelligence
# - get me some information about the stock market
# - crawl some stock market news and summarize them in a file, cite the source
