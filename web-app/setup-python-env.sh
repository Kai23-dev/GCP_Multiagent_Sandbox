#!/bin/bash

# Setup script for Python environment with Google Cloud AI dependencies
# This script helps developers set up their local Python environment for the Agent Engine integration

echo "🚀 Setting up Python environment for DaVita Agent Marketplace..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    echo "   Visit: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Found Python: $PYTHON_VERSION"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo ""
    echo "📦 Creating virtual environment..."

    # Create venv if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Virtual environment created at ./venv"
    else
        echo "✅ Virtual environment already exists at ./venv"
    fi

    echo ""
    echo "📝 To activate the virtual environment, run:"
    echo "   source venv/bin/activate"
    echo ""
    echo "Then run this script again to install dependencies."
    exit 0
else
    echo "✅ Virtual environment is active: $VIRTUAL_ENV"
fi

# Install required packages
echo ""
echo "📦 Installing required Python packages..."
echo ""

pip install --upgrade pip

# Install Google Cloud AI packages
pip install google-cloud-aiplatform>=1.38.0
pip install vertexai
pip install python-dotenv

# Check if installation was successful
echo ""
echo "🔍 Verifying installation..."

python3 -c "import vertexai; print('✅ vertexai package installed successfully')" 2>/dev/null || {
    echo "❌ Failed to install vertexai package"
    exit 1
}

python3 -c "import google.cloud.aiplatform; print('✅ google-cloud-aiplatform package installed successfully')" 2>/dev/null || {
    echo "❌ Failed to install google-cloud-aiplatform package"
    exit 1
}

echo ""
echo "🎉 Python environment setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Make sure you have Google Cloud credentials configured:"
echo "   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json"
echo ""
echo "2. Set your Google Cloud project:"
echo "   export GOOGLE_CLOUD_PROJECT=your-project-id"
echo "   export GOOGLE_CLOUD_LOCATION=us-central1"
echo ""
echo "3. Start the Next.js development server:"
echo "   npm run dev"
echo ""
echo "The Agent Engine API will now autodiscover this Python environment!"