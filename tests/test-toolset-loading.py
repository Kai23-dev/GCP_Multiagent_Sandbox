"""Test toolset loading from MCP server locally.

This script tests if the sql_generation agent can load all toolsets
from the MCP server when running locally.
"""

import os
import sys
import subprocess

# Set required environment variables
os.environ["GOOGLE_CLOUD_PROJECT"] = "sco-agents-dev-1a9n"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GENAI_MCP_URL"] = "https://ai-mcp-server-genai-toolbox-386427107883.us-central1.run.app"
os.environ["SCO_KB_PROJECT_ID"] = "sco-kb-dev-1a9n"

# Import after setting env vars
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "infra", "agents", "sql_generation_agent"))

from toolbox_core import ToolboxSyncClient

def get_id_token(url: str) -> str:
    """Get ID token for authentication."""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"],
            text=True
        ).strip()
        return token
    except Exception as e:
        print(f"Error getting token: {e}")
        return ""

def test_toolset_loading():
    """Test loading all toolsets."""
    GENAI_MCP_URL = os.environ["GENAI_MCP_URL"]
    TOOLBOX_BQ_PROJECT_ID = os.environ["SCO_KB_PROJECT_ID"]
    
    print("=" * 60)
    print("Testing Toolset Loading")
    print("=" * 60)
    print(f"MCP URL: {GENAI_MCP_URL}")
    print(f"BQ Project: {TOOLBOX_BQ_PROJECT_ID}")
    print()
    
    # Create toolbox client
    def _genai_toolbox_auth_header() -> str:
        token = get_id_token(GENAI_MCP_URL)
        return f"Bearer {token}" if token else ""
    
    toolbox_client = ToolboxSyncClient(
        GENAI_MCP_URL,
        client_headers={"Authorization": _genai_toolbox_auth_header},
    )
    print("✓ Toolbox client created")
    print()
    
    # Test loading each toolset
    _USER_IDS = ["auditor", "buyer", "ssi", "supplier_classification"]
    
    for _uid in _USER_IDS:
        _ts_name = f"{_uid}-toolset"
        print(f"Loading toolset: {_ts_name}")
        try:
            loaded = toolbox_client.load_toolset(_ts_name)
            tools = loaded if isinstance(loaded, list) else [loaded]
            
            if TOOLBOX_BQ_PROJECT_ID:
                try:
                    tools = [t.bind_params({"project_id": TOOLBOX_BQ_PROJECT_ID}) for t in tools]
                except Exception as e:
                    print(f"  Warning: bind_params failed: {e}")
            
            print(f"  ✓ Loaded {len(tools)} tools:")
            for tool in tools:
                print(f"    - {tool.__name__}")
            print()
            
        except Exception as e:
            print(f"  ✗ Failed to load toolset '{_ts_name}': {e}")
            print()

if __name__ == "__main__":
    test_toolset_loading()
