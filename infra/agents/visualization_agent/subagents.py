from __future__ import annotations
import vertexai
import os
import json
import requests
import google.auth
from google.auth.transport.requests import Request as AuthRequest

# OpenTelemetry for distributed tracing across agents
from opentelemetry import trace
from opentelemetry.propagate import inject as otel_inject

tracer = trace.get_tracer('visualization_agent', '1.0.0')

# Initialize Vertex AI (must be done before using ReasoningEngine)
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
)
print(f"vi=====Vertex AI initialized with project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
print(f"vi=====Vertex AI initialized with location: {os.environ.get('GOOGLE_CLOUD_LOCATION')}")

###########################################
######### SUB-AGENTS VIA REASONING ENGINE ##
###########################################
# Sub-agents are deployed independently on Agent Engine
# Reference them via ReasoningEngine using their resource names
print("vi=====Setting up remote sub-agents via ReasoningEngine.")

# Get sub-agent resource names from environment variables
SQL_GENERATION_AGENT_RESOURCE = os.environ.get("SQL_GENERATION_AGENT_RESOURCE", "")
VALIDATION_AGENT_RESOURCE = os.environ.get("VALIDATION_AGENT_RESOURCE", "")
SQL_EXECUTION_AGENT_RESOURCE = os.environ.get("SQL_EXECUTION_AGENT_RESOURCE", "")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
print(f"vi=====SQL_GENERATION_AGENT_RESOURCE: {SQL_GENERATION_AGENT_RESOURCE}")
print(f"vi=====VALIDATION_AGENT_RESOURCE: {VALIDATION_AGENT_RESOURCE}")
print(f"vi=====SQL_EXECUTION_AGENT_RESOURCE: {SQL_EXECUTION_AGENT_RESOURCE}")
print(f"vi=====GOOGLE_CLOUD_PROJECT: {GOOGLE_CLOUD_PROJECT}")

# Helper to call remote agents using lower-level API
def _call_remote_agent(resource_name: str, query: str) -> str:
    """Call a remote agent via ReasoningEngine using direct HTTP/REST API to avoid SDK parsing issues."""
    agent_name = resource_name.split("/")[-1] if resource_name else "unknown"
    with tracer.start_as_current_span(
        f"call_remote_agent/{agent_name}",
        attributes={
            "agent.name": agent_name,
            "agent.resource": resource_name,
            "agent.query_length": len(query) if query else 0,
        },
    ) as span:
      try:
        print(f"vi=====Resource name0: {resource_name}")
        
        # 1. Get Authentication Credentials
        creds, project = google.auth.default()
        auth_req = AuthRequest()
        creds.refresh(auth_req)
        token = creds.token
        
        # 2. Construct API URL
        parts = resource_name.split("/")
        location = "us-central1"
        if "locations" in parts:
             idx = parts.index("locations")
             if idx + 1 < len(parts):
                 location = parts[idx+1]

        # Inject W3C trace context so child agent joins the same trace
        trace_ctx = trace.get_current_span().get_span_context()
        trace_id = format(trace_ctx.trace_id, '032x') if trace_ctx.trace_id else ''

        api_endpoint = f"https://{location}-aiplatform.googleapis.com/v1beta1/{resource_name}:streamQuery"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        otel_inject(headers)  # adds traceparent, tracestate
        
        payload = {
            "input": {
                "message": query,
                "user_id": "visualizer",
            }
        }
        
        print(f"vi=====Calling API: {api_endpoint} [trace={trace_id}]")
        
        # 3. Execute Request
        response = requests.post(api_endpoint, json=payload, headers=headers, stream=True)
        
        if response.status_code != 200:
            error_text = response.text
            print(f"vi=====HTTP Error {response.status_code}: {error_text}")
            return f"Error calling remote agent (HTTP {response.status_code}): {error_text}"
            
        # 4. Process Stream
        responses = []
        print("vi=====Stream started")
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8').strip()
                if not decoded_line:
                    continue
                
                # Remove possible SSE prefix
                if decoded_line.startswith("data:"):
                    decoded_line = decoded_line[5:].strip()
                
                # Handle JSON Array markers if present
                if decoded_line == "[" or decoded_line == "]":
                    continue
                if decoded_line.endswith(","):
                    decoded_line = decoded_line[:-1]
                
                try:
                    data = json.loads(decoded_line)
                    print(f"vi=====Parsed Chunk: {data}")
                    
                    # Extract text content based on observation of SDK behavior
                    # Expected structure: {"content": {"parts": [{"text": "..."}]}}
                    if isinstance(data, dict):
                         content = data.get("content", {})
                         if isinstance(content, dict):
                             parts = content.get("parts", [])
                             for part in parts:
                                 if isinstance(part, dict) and "text" in part:
                                     responses.append(part["text"])
                                     print(f"vi=====Added text: {part['text']}")
                                 elif isinstance(part, str):
                                     responses.append(part)
                         elif isinstance(content, str):
                             responses.append(content)
                             
                except json.JSONDecodeError:
                    print(f"vi=====Skipping non-JSON line: {decoded_line}")
                    
        result = "".join(responses) if responses else "No response from agent"
        span.set_attribute("agent.http_status", 200)
        span.set_attribute("agent.response_length", len(result))
        return result

      except Exception as e:
        span.set_attribute("agent.error", str(e))
        span.record_exception(e)
        print(f"vi=====Exception in _call_remote_agent: {e}")
        return f"Error calling remote agent: {e}"


def sql_generation_agent(query: str) -> str:
    """Query the SQL Generation agent to determine which BigQuery tables to use.

    Args:
        query: Natural language query asking which tables to use for a question.

    Returns:
        Response from the SQL Generation agent with table recommendations.
    """
    if not SQL_GENERATION_AGENT_RESOURCE:
        return "SQL Generation agent is not configured"
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{SQL_GENERATION_AGENT_RESOURCE}"
    return _call_remote_agent(resource, query)


def validation_agent(query: str) -> str:
    """Query the Validation agent to validate a SQL query before execution.

    Args:
        query: SQL query to validate.

    Returns:
        Response from the Validation agent with validation results.
    """
    if not VALIDATION_AGENT_RESOURCE:
        return "Validation agent is not configured"
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{VALIDATION_AGENT_RESOURCE}"
    return _call_remote_agent(resource, query)


def sql_execution_agent(query: str) -> str:
    """Query the SQL Execution agent to execute a validated SQL query.

    Args:
        query: Validated SQL query to execute.

    Returns:
        Response from the SQL Execution agent with query results.
    """
    if not SQL_EXECUTION_AGENT_RESOURCE:
        return "SQL Execution agent is not configured"
    resource = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_LOCATION}/reasoningEngines/{SQL_EXECUTION_AGENT_RESOURCE}"
    return _call_remote_agent(resource, query)


# Collect available remote agent tools
remote_agent_tools = []
if SQL_GENERATION_AGENT_RESOURCE:
    remote_agent_tools.append(sql_generation_agent)
    print("vi=====SQL Generation agent tool configured")
if VALIDATION_AGENT_RESOURCE:
    remote_agent_tools.append(validation_agent)
    print("vi=====Validation agent tool configured")
if SQL_EXECUTION_AGENT_RESOURCE:
    remote_agent_tools.append(sql_execution_agent)
    print("vi=====SQL Execution agent tool configured")
print(f"vi=====Total remote agent tools configured: {len(remote_agent_tools)}")
