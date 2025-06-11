@echo off
echo Starting HomeLM...

:: Activate virtual environment
call venv\Scripts\activate

:: Check if Ollama is installed
where ollama >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Ollama not found. Please install Ollama from https://ollama.ai/ and try again.
    pause
    exit /b
)

:: Check if Ollama is already running on port 11434
netstat -a -n -o | find "11434" >nul
if %ERRORLEVEL% equ 0 (
    echo Ollama server is already running.
) else (
    echo Starting Ollama server...
    start /B ollama serve
    :: Wait briefly to ensure Ollama server starts
    timeout /t 2 /nobreak >nul
)

:: Run the Flask app
echo Launching HomeLM app...
python app.py

pause