#!/usr/bin/env python3
"""
Auto Skedway — API Server

Serves the frontend and provides API endpoints for accounts, schedules, execution, and logs.
"""

import os
import sys
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import account_manager
from core.scheduler import (
    init_scheduler, trigger_run, get_active_runs,
    reload_jobs, get_scheduled_jobs, get_next_run_by_account, shutdown_scheduler,
)

# Configuration
LOGS_DIR = Path(__file__).parent.parent / "logs"
FRONTEND_DIR = Path(__file__).parent

# Initialize Flask app
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)

# Configure ProxyFix for nginx proxy with headers
# This tells Flask to trust the X-Forwarded-* headers from the proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # Trust X-Real-IP / X-Forwarded-For
    x_proto=1,    # Trust X-Forwarded-Proto (http/https)
    x_host=1,     # Trust X-Forwarded-Host
)

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
    if not LOGS_DIR.exists():
        return []
    folders = []
    for folder in LOGS_DIR.iterdir():
        if folder.is_dir():
            folders.append(folder)
    return sorted(folders, reverse=True)


def parse_execution_timestamp(folder_name):
    # Support both old format (2026-04-05_153113) and new (2026-04-05_153113_accountid)
    ts_part = folder_name[:19] if len(folder_name) >= 19 else folder_name
    try:
        return datetime.strptime(ts_part, "%Y-%m-%d_%H%M%S")
    except ValueError:
        return None


def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return None


def read_log_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading log file {file_path}: {e}")
        return None


def get_execution_data(folder_path):
    summary_path = folder_path / "summary.json"
    if not summary_path.exists():
        return None
    summary = read_json_file(summary_path)
    if not summary:
        return None
    timestamp = folder_path.name
    parsed_time = parse_execution_timestamp(timestamp)
    return {
        **summary,
        "timestamp": timestamp,
        "folder_name": folder_path.name,
        "parsed_time": parsed_time.isoformat() if parsed_time else timestamp,
    }


# ========================================
# Static Files
# ========================================

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


# ========================================
# Execution Log Routes
# ========================================

@app.route("/api/executions", methods=["GET"])
def get_executions():
    try:
        account_filter = request.args.get("account_id")
        executions = []
        for folder in get_execution_folders():
            data = get_execution_data(folder)
            if data:
                if account_filter and data.get("account_id") != account_filter:
                    continue
                executions.append(data)
        return jsonify(executions)
    except Exception as e:
        logger.error(f"Error getting executions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/executions/<timestamp>", methods=["GET"])
def get_execution_details(timestamp):
    try:
        execution_folder = LOGS_DIR / timestamp
        if not execution_folder.exists():
            return jsonify({"error": "Execution not found"}), 404
        summary_path = execution_folder / "summary.json"
        summary = read_json_file(summary_path) if summary_path.exists() else {}
        log_path = execution_folder / "execution.log"
        execution_log = read_log_file(log_path) if log_path.exists() else ""
        screenshot_files = sorted([
            f.name for f in execution_folder.iterdir()
            if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']
        ])
        return jsonify({**summary, "execution_log": execution_log, "screenshot_files": screenshot_files})
    except Exception as e:
        logger.error(f"Error getting execution details: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/executions/<timestamp>/screenshots/<filename>", methods=["GET"])
def get_screenshot(timestamp, filename):
    try:
        screenshot_path = LOGS_DIR / timestamp / filename
        if not screenshot_path.exists() or not screenshot_path.is_file():
            return jsonify({"error": "Screenshot not found"}), 404
        if screenshot_path.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            return jsonify({"error": "Invalid file type"}), 400
        return send_from_directory(LOGS_DIR / timestamp, filename)
    except Exception as e:
        logger.error(f"Error getting screenshot: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/executions/<timestamp>", methods=["DELETE"])
def delete_execution(timestamp):
    """Delete an execution log folder and all its contents (screenshots, logs)."""
    try:
        execution_folder = LOGS_DIR / timestamp
        if not execution_folder.exists():
            return jsonify({"error": "Execution not found"}), 404
        # Validate that the folder is actually inside LOGS_DIR (path traversal prevention)
        if not execution_folder.resolve().parent == LOGS_DIR.resolve():
            return jsonify({"error": "Invalid path"}), 400
        shutil.rmtree(execution_folder)
        logger.info(f"Deleted execution log: {timestamp}")
        return jsonify({"message": "Execution deleted", "timestamp": timestamp})
    except Exception as e:
        logger.error(f"Error deleting execution {timestamp}: {e}")
        return jsonify({"error": str(e)}), 500


# ========================================
# Account Routes
# ========================================

@app.route("/api/accounts", methods=["GET"])
def list_accounts():
    try:
        accounts = account_manager.load_accounts()
        # Strip credentials from response
        safe = []
        for acc in accounts:
            a = dict(acc)
            a.pop("credentials", None)
            a["has_credentials"] = bool(
                acc.get("credentials", {}).get("user")
                and acc.get("credentials", {}).get("passwd")
            )
            a["next_run"] = get_next_run_by_account(acc["id"])
            safe.append(a)
        return jsonify(safe)
    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/<account_id>", methods=["GET"])
def get_account_endpoint(account_id):
    try:
        account = account_manager.get_account(account_id)
        if not account:
            return jsonify({"error": "Account not found"}), 404
        a = dict(account)
        a.pop("credentials", None)
        a["has_credentials"] = bool(
            account.get("credentials", {}).get("user")
            and account.get("credentials", {}).get("passwd")
        )
        return jsonify(a)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts", methods=["POST"])
def create_account():
    try:
        data = request.get_json()
        if not data or not data.get("label"):
            return jsonify({"error": "label is required"}), 400

        account = account_manager.add_account(
            label=data["label"],
            desks=data.get("desks", []),
            days_ahead=data.get("days_ahead", 7),
            start_time=data.get("start_time", "08:30"),
            end_time=data.get("end_time", "17:00"),
            site_params=data.get("site_params"),
            enabled=data.get("enabled", True),
        )

        # Set credentials if provided
        if data.get("user") and data.get("passwd"):
            account_manager.set_credentials(account["id"], data["user"], data["passwd"])

        reload_jobs()
        return jsonify(account), 201
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/<account_id>", methods=["PUT"])
def update_account_endpoint(account_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        updates = {}
        if "label" in data:
            updates["label"] = data["label"]
        if "enabled" in data:
            updates["enabled"] = data["enabled"]

        prefs = {}
        for key in ("desks", "days_ahead", "start_time", "end_time", "site_params"):
            if key in data:
                prefs[key] = data[key]
        if prefs:
            updates["preferences"] = prefs

        result = account_manager.update_account(account_id, updates)
        if not result:
            return jsonify({"error": "Account not found"}), 404

        # Update credentials if provided
        if data.get("user") and data.get("passwd"):
            account_manager.set_credentials(account_id, data["user"], data["passwd"])

        reload_jobs()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error updating account: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/<account_id>", methods=["DELETE"])
def delete_account_endpoint(account_id):
    try:
        success = account_manager.delete_account(account_id)
        if not success:
            return jsonify({"error": "Account not found"}), 404
        account_manager.remove_credentials(account_id)
        reload_jobs()
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================================
# Schedule Routes
# ========================================

@app.route("/api/accounts/<account_id>/schedules", methods=["GET"])
def list_schedules(account_id):
    try:
        account = account_manager.get_account(account_id)
        if not account:
            return jsonify({"error": "Account not found"}), 404
        return jsonify(account.get("schedules", []))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/<account_id>/schedules", methods=["POST"])
def create_schedule(account_id):
    try:
        data = request.get_json()
        if not data or not data.get("cron"):
            return jsonify({"error": "cron is required"}), 400

        schedule = account_manager.add_schedule(
            account_id,
            cron=data["cron"],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
        )
        if not schedule:
            return jsonify({"error": "Account not found"}), 404

        reload_jobs()
        return jsonify(schedule), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/<account_id>/schedules/<schedule_id>", methods=["PUT"])
def update_schedule_endpoint(account_id, schedule_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        result = account_manager.update_schedule(account_id, schedule_id, data)
        if not result:
            return jsonify({"error": "Schedule not found"}), 404

        reload_jobs()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/<account_id>/schedules/<schedule_id>", methods=["DELETE"])
def delete_schedule_endpoint(account_id, schedule_id):
    try:
        success = account_manager.delete_schedule(account_id, schedule_id)
        if not success:
            return jsonify({"error": "Schedule not found"}), 404
        reload_jobs()
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================================
# Execution Control Routes
# ========================================

@app.route("/api/accounts/<account_id>/run", methods=["POST"])
def run_account(account_id):
    try:
        result = trigger_run(account_id)
        if "error" in result:
            return jsonify(result), 409
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def get_status():
    try:
        return jsonify({
            "active_runs": get_active_runs(),
            "scheduled_jobs": get_scheduled_jobs(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
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
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ========================================
# Main
# ========================================

def create_app():
    """Create and configure the Flask app (for use by main.py)."""
    return app


if __name__ == "__main__":
    logger.info("Starting Auto Skedway")
    logger.info(f"Logs directory: {LOGS_DIR}")

    if not LOGS_DIR.exists():
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    init_scheduler()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False,
    )
