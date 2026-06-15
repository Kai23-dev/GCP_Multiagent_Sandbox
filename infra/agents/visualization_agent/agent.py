from __future__ import annotations

import pathlib

from google.adk.agents import Agent
from google.genai import types
from vertexai.agent_engines import AdkApp

try:
    from .tools import (
        generate_subplot_visualization_code,
        generate_visualization_code,
        save_visualization,
        validate_visualization_code,
    )
    from .subagents import remote_agent_tools
except ImportError:
    from tools import (
        generate_subplot_visualization_code,
        generate_visualization_code,
        save_visualization,
        validate_visualization_code,
    )
    from subagents import remote_agent_tools

print("vi======== VISUALIZATION AGENT ===")

_INSTRUCTION_PATH = pathlib.Path(__file__).parent / "instruction" / "system.md"
_INSTRUCTION = _INSTRUCTION_PATH.read_text(encoding="utf-8")

root_agent = Agent(
    model="gemini-2.5-flash",
    name="visualization_agent",
    instruction=_INSTRUCTION,
    tools=[
        generate_visualization_code,
        generate_subplot_visualization_code,
        validate_visualization_code,
        save_visualization,
        *remote_agent_tools
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        http_options=types.HttpOptions(
            headers={
                "X-Vertex-AI-LLM-Request-Type": "shared",
                "X-Vertex-AI-LLM-Shared-Request-Type": "priority",
            }
        ),
    ),
)
print("vi=====Visualization agent defined")

# Wrap the agent with AdkApp for Agent Engine deployment
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)
print("vi=====Visualization Agent initialization complete")
