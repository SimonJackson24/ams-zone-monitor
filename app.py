#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
import signal
import json
from threading import Thread

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

from modules.camera_manager import CameraManager
from modules.zone_detector import ZoneDetector
from modules.gpio_controller import GPIOController
from modules.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log')
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)
os.makedirs('config', exist_ok=True)

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ams-zone-monitor-secret-key'
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# Initialize components
config_manager = ConfigManager('config/config.json')
config = config_manager.get_config()

gpio_controller = GPIOController(config.get('gpio', {}))
camera_manager = CameraManager(config.get('cameras', []))
zone_detector = ZoneDetector(
    camera_manager,
    gpio_controller,
    config.get('zones', {}),
    hailo_model_path=config.get('hailo', {}).get('model_path')
)

# Flag to control main loop
running = True

# Signal handlers
def signal_handler(sig, frame):
    global running
    logger.info("Shutdown signal received. Cleaning up...")
    running = False
    time.sleep(1)  # Allow time for threads to clean up
    gpio_controller.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(config_manager.get_config())

@app.route('/api/config', methods=['POST'])
def update_config():
    new_config = request.json
    config_manager.update_config(new_config)
    # Update components with new configuration
    gpio_controller.update_config(new_config.get('gpio', {}))
    camera_manager.update_cameras(new_config.get('cameras', []))
    zone_detector.update_zones(new_config.get('zones', {}))
    return jsonify({'status': 'success'})

@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    return jsonify(camera_manager.get_camera_info())

@app.route('/api/zones', methods=['GET'])
def get_zones():
    return jsonify(zone_detector.get_zones())

@app.route('/api/zones', methods=['POST'])
def update_zones():
    zones = request.json
    zone_detector.update_zones(zones)
    config_manager.update_config_section('zones', zones)
    return jsonify({'status': 'success'})

@app.route('/api/gpio', methods=['GET'])
def get_gpio_config():
    return jsonify(gpio_controller.get_config())

@app.route('/api/gpio', methods=['POST'])
def update_gpio_config():
    gpio_config = request.json
    gpio_controller.update_config(gpio_config)
    config_manager.update_config_section('gpio', gpio_config)
    return jsonify({'status': 'success'})

# WebSocket for streaming detection results and status
@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

def emit_status():
    """Emit status updates to connected clients."""
    while running:
        status_data = {
            'cameras': camera_manager.get_camera_status(),
            'zones': zone_detector.get_zone_status(),
            'gpio': gpio_controller.get_status()
        }
        socketio.emit('status_update', status_data)
        time.sleep(1)

# Main application entry point
def main():
    # Start status emission thread
    status_thread = Thread(target=emit_status)
    status_thread.daemon = True
    status_thread.start()
    
    # Start zone detector
    detector_thread = Thread(target=zone_detector.run)
    detector_thread.daemon = True
    detector_thread.start()
    
    # Start the web server
    logger.info("Starting AMS Zone Monitor")
    socketio.run(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
