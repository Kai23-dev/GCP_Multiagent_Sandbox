#!/usr/bin/env python3
"""
Python script to query ADK agents using the Vertex AI SDK
This script is called by the Node.js API to handle ADK agent communication
"""

import sys
import json
import os
from vertexai.preview import reasoning_engines
import vertexai

def query_agent(message, agent_id, user_id, session_id=None):
    """
    Query an ADK agent using the Python SDK
    """
    try:
        # Initialize Vertex AI
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'agentspace-prod-w89w')
        location = os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
        vertexai.init(project=project_id, location=location)

        # Load the agent
        agent_resource = f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_id}"
        agent = reasoning_engines.ReasoningEngine(agent_resource)

        # Check if agent has stream_query method (ADK agents)
        if hasattr(agent, 'operation_schemas'):
            schemas = agent.operation_schemas()
            has_stream_query = any(s['name'] == 'stream_query' for s in schemas)

            if has_stream_query:
                # This is an ADK agent with stream_query
                # However, stream_query requires actual streaming support
                # For now, return an informative message
                return {
                    "response": f"This is an ADK session management agent (ID: {agent_id}). ADK agents are designed for session management and require the Python SDK for full functionality. They expose operations like create_session, list_sessions, get_session, and delete_session, but do not support direct conversational queries through REST APIs.",
                    "sessionId": session_id or f"session-{user_id}",
                    "success": False,
                    "agentType": "ADK Session Manager",
                    "availableOperations": [s['name'] for s in schemas if 'async' not in s['api_mode']]
                }

        # Try standard query method for non-ADK agents
        if hasattr(agent, 'query'):
            result = agent.query(input=message)
            response_text = str(result) if result else "No response"
            return {
                "response": response_text,
                "sessionId": session_id or f"session-{user_id}",
                "success": True
            }

        # If no query method, try direct call
        if callable(agent):
            result = agent(message)
            response_text = str(result) if result else "No response"
            return {
                "response": response_text,
                "sessionId": session_id or f"session-{user_id}",
                "success": True
            }

        # Agent doesn't support standard query methods
        return {
            "response": f"Agent {agent_id} does not support standard query methods",
            "sessionId": session_id or f"session-{user_id}",
            "success": False,
            "error": "Unsupported agent type"
        }

    except Exception as e:
        return {
            "response": "",
            "sessionId": "",
            "success": False,
            "error": str(e)
        }

def main():
    """
    Main entry point - reads JSON from stdin and outputs JSON to stdout
    """
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        params = json.loads(input_data)

        # Extract parameters
        message = params.get('message')
        agent_id = params.get('agentId')
        user_id = params.get('userId')
        session_id = params.get('sessionId')

        # Query the agent
        result = query_agent(message, agent_id, user_id, session_id)

        # Output result as JSON
        print(json.dumps(result))

    except Exception as e:
        # Output error as JSON
        error_result = {
            "response": "",
            "sessionId": "",
            "success": False,
            "error": str(e)
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()