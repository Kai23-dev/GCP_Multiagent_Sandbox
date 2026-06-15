# tests/test-connect-mcp.py
import requests
import subprocess

# Get auth token
token = subprocess.check_output(
    ["gcloud", "auth", "print-identity-token"], 
    text=True
).strip()

url = "https://ai-mcp-server-genai-toolbox-386427107883.us-central1.run.app"
headers = {"Authorization": f"Bearer {token}"}

# Test root endpoint
print("Testing MCP server connection...")
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}")