import os
import sys
import importlib.util
import json
import logging
from typing import Dict, Any, AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("local_agent_server")

# Make sure infra is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
infra_dir = os.path.dirname(current_dir)
if infra_dir not in sys.path:
    sys.path.insert(0, infra_dir)
agents_dir = os.path.join(infra_dir, "agents")
if agents_dir not in sys.path:
    sys.path.insert(0, agents_dir)

app = FastAPI(title="Local Agent Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registry of loaded agents
agents: Dict[str, Any] = {}

def load_agents():
    """Dynamically load all agents from infra/agents."""
    agent_folders = [f for f in os.listdir(agents_dir) if os.path.isdir(os.path.join(agents_dir, f))]
    
    for agent_key in agent_folders:
        agent_path = os.path.join(agents_dir, agent_key, "agent.py")
        if not os.path.exists(agent_path):
            continue
            
        try:
            logger.info(f"Loading agent: {agent_key}")
            # Mock the dependencies
            os.environ["GOOGLE_CLOUD_PROJECT"] = os.environ.get("GOOGLE_CLOUD_PROJECT", "local-test-project")
            os.environ["GOOGLE_CLOUD_LOCATION"] = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
            # Route Gemini inference through Vertex AI using ADC (not an API key).
            os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
            
            os.environ["AUDITOR_AGENT_RESOURCE"] = "auditor_agent"
            os.environ["BUYER_AGENT_RESOURCE"] = "buyer_agent"
            os.environ["TREND_AGENT_RESOURCE"] = "trend_agent"
            os.environ["SUPPLIER_CLASSIFICATION_AGENT_RESOURCE"] = "supplier_classification_agent"
            os.environ["CONTRACT_INTELLIGENCE_AGENT_RESOURCE"] = "contract_intelligence_agent"
            os.environ["FINANCIAL_LEAKAGE_AGENT_RESOURCE"] = "financial_leakage_agent"
            # Shared SQL sub-agents — so domain agents build their SQL tools and
            # delegate to them over the loopback instead of real Reasoning Engines.
            os.environ["SQL_GENERATION_AGENT_RESOURCE"] = "sql_generation_agent"
            os.environ["VALIDATION_AGENT_RESOURCE"] = "validation_agent"
            os.environ["SQL_EXECUTION_AGENT_RESOURCE"] = "sql_execution_agent"
            os.environ["VERTEX_API_BASE"] = "http://127.0.0.1:8000"
            
            spec = importlib.util.spec_from_file_location(agent_key, agent_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # AdkApp (adk_app) exposes .stream_query/.create_session/.query used by
            # the mock endpoints; fall back to root_agent only if it's missing.
            agent_obj = getattr(module, "adk_app", None) or getattr(module, "root_agent", None)
            if agent_obj:
                agents[agent_key] = agent_obj
                logger.info(f"Successfully loaded agent: {agent_key}")
            else:
                logger.warning(f"Could not find agent object in {agent_key}")
        except Exception as e:
            logger.error(f"Failed to load agent {agent_key}: {e}", exc_info=True)

@app.on_event("startup")
async def startup_event():
    load_agents()

@app.get("/v1beta1/{resource_name:path}")
async def get_agent(resource_name: str):
    """Mock the Reasoning Engine GET endpoint so the frontend thinks it's an ADK agent."""
    agent_key = resource_name.split("/")[-1]
    if agent_key not in agents:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_key}")
    return {
        "name": resource_name,
        "displayName": agent_key,
        "spec": {
            "agentFramework": "google-adk"
        }
    }

@app.post("/v1beta1/{resource_name:path}:query")
async def query_agent(resource_name: str, request: Request):
    """Handle standard query and create_session requests."""
    agent_key = resource_name.split("/")[-1]
    
    if agent_key not in agents:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_key}")
        
    agent = agents[agent_key]
    data = await request.json()
    
    class_method = data.get("class_method", "query")
    input_kwargs = data.get("input", {})
    
    # Simple query format fallback
    if "query" in data and not input_kwargs:
        class_method = "query"
        input_kwargs = {"message": data["query"]}
        
    try:
        # Fallbacks for class methods
        if class_method == "async_create_session": class_method = "create_session"
        
        method = getattr(agent, class_method)
        result = method(**input_kwargs)
        
        # Format the response nicely
        return {"output": result}
    except Exception as e:
        logger.error(f"Error executing {class_method} on {agent_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1beta1/{resource_name:path}:streamQuery")
async def stream_query_agent(resource_name: str, request: Request):
    """Handle streaming queries."""
    agent_key = resource_name.split("/")[-1]
    
    if agent_key not in agents:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_key}")
        
    agent = agents[agent_key]
    data = await request.json()
    
    class_method = data.get("class_method", "stream_query")
    input_kwargs = data.get("input", {})
    
    # Handle async aliases
    if class_method == "async_stream_query": class_method = "stream_query"
    
    try:
        method = getattr(agent, class_method)
        result_stream = method(**input_kwargs)
        
        async def event_generator() -> AsyncGenerator[str, None]:
            # Convert sync generator to async generator for FastAPI
            try:
                for chunk in result_stream:
                    # Format as JSON string for each SSE chunk
                    if isinstance(chunk, str):
                        data_chunk = {"text": chunk}
                    else:
                        data_chunk = chunk
                        
                    yield f"data: {json.dumps(data_chunk)}\n\n"
            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error executing {class_method} on {agent_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
