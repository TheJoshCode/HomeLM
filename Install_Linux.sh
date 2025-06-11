#!/bin/bash
echo "Installing HomeLM dependencies..."

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install flask flask-login werkzeug ollama zeroconf

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Please download and install Ollama from https://ollama.ai/"
else
    echo "Pulling Gemma3:1b model..."
    ollama pull gemma3:1b
fi

echo "Installation complete! Run the app with 'python3 app.py'"