# Web3 Assistant (CUHK FYP)

An intelligent Web3 assistant that provides comprehensive answers to cryptocurrency and blockchain queries by combining multiple data sources, knowledge graphs, and AI models. The system uses a hybrid approach combining vector similarity search, graph database queries, and large language models to deliver accurate and contextual responses.

## Key Features

- **Multi-Source Information Integration**
  - Real-time cryptocurrency market data
  - Historical news and events
  - Technical domain knowledge
  - Community insights
  
- **Intelligent Query Processing**
  - Query breakdown into specialized subtasks
  - Context-aware response generation
  - Source attribution for transparency
  
- **Multiple Query Frameworks**
  - Baseline: Direct LLM responses with context
  - Enhanced: Background knowledge enriched responses
  - Tool-based: Specialized tools for different query types
  - Simple Query: Basic question-answering

- **Interactive Visualization**
  - Knowledge graph visualization using Neovis.js
  - Dynamic relationship exploration
  - Source tracking and verification

## Technical Architecture

### Backend (server.py)
- FastAPI server with CORS support
- Integration with:
  - OpenAI API / Ollama for LLM capabilities
  - Neo4j graph database for knowledge storage
  - FAISS for vector similarity search
  - LangChain for embeddings and document processing

### Frontend (app.py)
- Streamlit-based user interface
- Features:
  - Date range selection
  - Cryptocurrency filtering (Bitcoin, Tron, Web3, Market, Crypto, Cardano)
  - Model selection (GPT-3.5/4o)
  - Client selection (Ollama/OpenRouter)
  - Interactive chat interface
  - Graph visualization using Neovis.js

## Setup Instructions

### Prerequisites
- Python 3.8+
- Neo4j Database
- OpenAI API key or Ollama setup
- Required Python packages:
  - fastapi
  - uvicorn
  - openai
  - langchain
  - streamlit
  - python-dotenv
  - neo4j
  - faiss-cpu
  - pydantic
  - pandas

### Environment Variables
Create a `.env` file with the following:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=your_base_url
OPENROUTER_API_KEY=your_router_key
OPENROUTER_BASE_URL=your_router_url
OLLAMA_BASE_URL=your_ollama_url
```

### Installation
1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the Application
1. Start the FastAPI backend:

```bash
python server.py
```
or
```bash
uvicorn server:app --reload
```

2. Start the Streamlit frontend:

```bash
streamlit run app.py
```

## API Endpoints

- `/api/chat1`: Baseline framework with context retrieval
- `/api/chat2`: Enhanced framework with tool integration
- `/api/chat3`: Pure tool-based processing
- `/api/chat4`: Simple query processing without context

## Query Processing Pipeline

1. **Query Breakdown**
   - Analyzes user input
   - Classifies into subtasks:
     - news: requires recent news/events data
     - domain_knowledge: requires technical definitions/concepts
     - structured_data: requires current market data/statistics
     - general: other types of queries

2. **Context Retrieval**
   - Vector similarity search using FAISS
   - Neo4j graph database queries
   - Background knowledge integration
   - Source tracking

3. **Response Generation**
   - Context-aware LLM processing
   - Source attribution
   - Graph visualization generation

## Data Sources

- Neo4j knowledge graph for entity relationships
- FAISS vector store for document similarity
- External APIs for real-time data
- Curated background knowledge base (context_qa2.csv)
- Cryptocurrency price data (coins_name.json)

## Contributing
Contributions are welcome! Please feel free to submit pull requests.

## License
This project is part of a Final Year Project at The Chinese University of Hong Kong.
