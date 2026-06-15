# Python Environment Setup for Agent Engine

The Agent Engine integration requires Python with Google Cloud AI packages installed. The application now includes automatic Python discovery to make setup easier for developers.

## Quick Setup

Run the provided setup script:

```bash
# Make the script executable
chmod +x setup-python-env.sh

# Run the setup script
./setup-python-env.sh

# Activate the virtual environment (if created)
source venv/bin/activate

# Run the script again to install dependencies
./setup-python-env.sh
```

## Manual Setup

If you prefer to set up manually or use an existing Python environment:

### 1. Install Required Packages

```bash
pip install google-cloud-aiplatform>=1.38.0
pip install vertexai
pip install python-dotenv
```

### 2. Set Environment Variables

The application will automatically detect Python in the following order:

1. **Virtual Environment** (`$VIRTUAL_ENV/bin/python`)
2. **Conda Environment** (`$CONDA_PREFIX/bin/python`)
3. **System Python** (`python3` or `python`)
4. **Pyenv** (`~/.pyenv/shims/python3`)

## How Python Discovery Works

When you start the application in development mode, it will:

1. **Check for Python with vertexai installed** - Tries each candidate Python executable to see if it has the required packages
2. **Fall back to any available Python** - If no Python with packages is found, uses any available Python and warns you to install packages
3. **Provide helpful error messages** - If Python or packages are missing, you'll see clear instructions in the console

## Troubleshooting

### "No Python installation with vertexai package found"

This warning means Python was found but doesn't have the required packages. Install them:

```bash
pip install google-cloud-aiplatform vertexai python-dotenv
```

### "Failed to start Python process"

This means no Python executable was found. Install Python 3.8 or higher:

- **macOS**: `brew install python3` or download from [python.org](https://www.python.org)
- **Ubuntu/Debian**: `sudo apt-get install python3 python3-pip`
- **Windows**: Download from [python.org](https://www.python.org)

### Google Cloud Authentication Issues

Make sure you have:

1. **Service Account Credentials**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   ```

2. **Project Configuration**:
   ```bash
   export GOOGLE_CLOUD_PROJECT=your-project-id
   export GOOGLE_CLOUD_LOCATION=us-central1
   ```

## Using Different Python Environments

### With pyenv

```bash
pyenv install 3.11
pyenv local 3.11
pip install google-cloud-aiplatform vertexai python-dotenv
```

### With conda

```bash
conda create -n agent-engine python=3.11
conda activate agent-engine
pip install google-cloud-aiplatform vertexai python-dotenv
```

### With virtualenv

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install google-cloud-aiplatform vertexai python-dotenv
```

## Production Deployment

In production (Docker), the application expects Python packages to be pre-installed in the container. The Dockerfile should include:

```dockerfile
RUN pip install google-cloud-aiplatform vertexai python-dotenv
```

## Development Tips

1. **Check your Python path**: The console will show which Python executable is being used:
   ```
   DEBUG: Found Python with vertexai at: /path/to/python
   ```

2. **Verify packages are installed**:
   ```bash
   python3 -c "import vertexai; print('vertexai installed')"
   ```

3. **Use the same Python for testing**: Make sure to test your Agent Engine scripts with the same Python that the app discovers.

## Contributing

When contributing to the Agent Engine integration:

1. Don't hardcode Python paths
2. Test with different Python setups (venv, conda, system)
3. Ensure error messages are helpful
4. Update this documentation if you change the discovery logic