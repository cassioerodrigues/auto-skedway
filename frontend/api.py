#!/usr/bin/env python3
"""
Execution Dashboard API Server

Serves the frontend and provides API endpoints to access execution logs.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Configuration
LOGS_DIR = Path(__file__).parent.parent / "logs"
FRONTEND_DIR = Path(__file__).parent

# Initialize Flask app
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-8s] [%(name)-12s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# ========================================
# Helper Functions
# ========================================

def get_execution_folders():
    """Get all execution folders sorted by timestamp."""
    if not LOGS_DIR.exists():
        return []
    
    folders = []
    for folder in LOGS_DIR.iterdir():
        if folder.is_dir() and folder.name.replace("-", "").replace("_", "").isdigit():
            folders.append(folder)
    
    return sorted(folders, reverse=True)


def parse_execution_timestamp(folder_name):
    """Parse timestamp from folder name (e.g., 2026-04-05_153113)."""
    try:
        return datetime.strptime(folder_name, "%Y-%m-%d_%H%M%S")
    except ValueError:
        return None


def read_json_file(file_path):
    """Safely read a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return None


def read_log_file(file_path):
    """Safely read a log file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading log file {file_path}: {e}")
        return None


def get_execution_data(folder_path):
    """Extract execution data from a folder."""
    summary_path = folder_path / "summary.json"
    
    if not summary_path.exists():
        return None
    
    summary = read_json_file(summary_path)
    if not summary:
        return None
    
    # Add timestamp to the data
    timestamp = folder_path.name
    parsed_time = parse_execution_timestamp(timestamp)
    
    return {
        **summary,
        "timestamp": timestamp,
        "folder_name": folder_path.name,
        "parsed_time": parsed_time.isoformat() if parsed_time else timestamp,
    }


# ========================================
# API Routes
# ========================================

@app.route("/")
def index():
    """Serve the main frontend."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    """Serve static files (CSS, JS)."""
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/executions", methods=["GET"])
def get_executions():
    """Get list of all executions."""
    try:
        executions = []
        
        for folder in get_execution_folders():
            data = get_execution_data(folder)
            if data:
                executions.append(data)
        
        logger.info(f"Loaded {len(executions)} executions")
        return jsonify(executions)
    
    except Exception as e:
        logger.error(f"Error getting executions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/executions/<timestamp>", methods=["GET"])
def get_execution_details(timestamp):
    """Get details for a specific execution."""
    try:
        execution_folder = LOGS_DIR / timestamp
        
        if not execution_folder.exists():
            return jsonify({"error": "Execution not found"}), 404
        
        # Read summary
        summary_path = execution_folder / "summary.json"
        summary = read_json_file(summary_path) if summary_path.exists() else {}
        
        # Read execution log
        log_path = execution_folder / "execution.log"
        execution_log = read_log_file(log_path) if log_path.exists() else ""
        
        # Get list of screenshots
        screenshot_files = []
        for file in execution_folder.iterdir():
            if file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
                screenshot_files.append(file.name)
        
        screenshot_files.sort()
        
        return jsonify({
            **summary,
            "execution_log": execution_log,
            "screenshot_files": screenshot_files,
        })
    
    except Exception as e:
        logger.error(f"Error getting execution details: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/executions/<timestamp>/screenshots/<filename>", methods=["GET"])
def get_screenshot(timestamp, filename):
    """Get a specific screenshot."""
    try:
        screenshot_path = LOGS_DIR / timestamp / filename
        
        # Validate file exists and is in the correct directory
        if not screenshot_path.exists() or not screenshot_path.is_file():
            return jsonify({"error": "Screenshot not found"}), 404
        
        # Validate it's an image file
        if screenshot_path.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            return jsonify({"error": "Invalid file type"}), 400
        
        # Serve the file
        return send_from_directory(LOGS_DIR / timestamp, filename)
    
    except Exception as e:
        logger.error(f"Error getting screenshot: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "logs_dir": str(LOGS_DIR),
        "logs_dir_exists": LOGS_DIR.exists(),
    })


# ========================================
# Error Handlers
# ========================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ========================================
# Main
# ========================================

if __name__ == "__main__":
    logger.info(f"Starting Execution Dashboard")
    logger.info(f"Logs directory: {LOGS_DIR}")
    logger.info(f"Frontend directory: {FRONTEND_DIR}")
    
    if not LOGS_DIR.exists():
        logger.warning(f"Logs directory does not exist: {LOGS_DIR}")
    
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False,
    )
