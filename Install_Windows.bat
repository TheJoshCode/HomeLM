@echo off
echo Installing HomeLM dependencies...

:: Create and activate virtual environment
python -m venv venv
call venv\Scripts\activate

:: Install Python dependencies
pip install flask flask-login werkzeug ollama zeroconf

:: Check if Ollama is installed
where ollama >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Ollama not found. Please download and install Ollama from https://ollama.ai/
) else (
    echo Pulling Gemma3:1b model...
    ollama pull gemma3:1b
)

echo Installation complete! Run the app with 'python app.py'
pause