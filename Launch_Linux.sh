#!/bin/bash
echo "Starting HomeLM..."

# Activate virtual environment
source venv/bin/activate

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Please install Ollama from https://ollama.ai/ and try again."
    read -p "Press Enter to continue..."
    exit 1
fi

# Check if Ollama is already running on port 11434
if lsof -i :11434 &> /dev/null; then
    echo "Ollama server is already running."
else
    echo "Starting Ollama server..."
    ollama serve &
    # Wait briefly to ensure Ollama server starts
    sleep 2
fi

# Run the Flask app
echo "Launching HomeLM app..."
python3 app.py