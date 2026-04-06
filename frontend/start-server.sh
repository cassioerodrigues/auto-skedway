#!/bin/bash

# Start Frontend Dashboard Server
# This script starts the Flask API server for the Execution Dashboard

echo ""
echo "╔════════════════════════════════════════╗"
echo "║   Execution Dashboard - Frontend API   ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ Python is not installed"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Check if Flask is installed
$PYTHON_CMD -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  Flask is not installed. Installing dependencies..."
    pip install -r ../requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

echo "✅ All dependencies are installed"
echo ""
echo "🚀 Starting Frontend Dashboard..."
echo ""
echo "📍 Server will be available at: http://localhost:5000"
echo ""
echo "🛑 Press Ctrl+C to stop the server"
echo ""

$PYTHON_CMD api.py
