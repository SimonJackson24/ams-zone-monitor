#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import time
import logging
import threading
from queue import Queue
from collections import defaultdict

logger = logging.getLogger(__name__)

class Camera:
    """Class to handle a single camera stream."""
    
    def __init__(self, camera_id, name, rtsp_url, fps=10):
        """Initialize a camera instance.
        
        Args:
            camera_id: Unique identifier for the camera
            name: Human-readable name for the camera
            rtsp_url: RTSP URL for the camera stream
            fps: Target frames per second to process
        """
        self.camera_id = camera_id
        self.name = name
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.cap = None
        self.connected = False
        self.last_frame = None
        self.last_frame_time = 0
        self.frame_count = 0
        self.running = True
        self.lock = threading.Lock()
        self.frame_queue = Queue(maxsize=2)  # Only keep latest frames
        self.connection_attempts = 0
        self.connect()
        
    def connect(self):
        """Connect to the RTSP stream."""
        try:
            # OpenCV connection options for RTSP
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # Minimize buffer to reduce latency
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera stream: {self.rtsp_url}")
                self.connected = False
                self.connection_attempts += 1
                return False
                
            logger.info(f"Connected to camera: {self.name} ({self.rtsp_url})")
            self.connected = True
            self.connection_attempts = 0
            
            # Start capture thread
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to camera {self.name}: {e}")
            self.connected = False
            self.connection_attempts += 1
            return False
    
    def _capture_loop(self):
        """Continuously capture frames from the camera stream."""
        last_capture_time = 0
        interval = 1.0 / self.fps  # Time interval between frame captures
        
        while self.running:
            if not self.connected or not self.cap.isOpened():
                logger.warning(f"Camera {self.name} disconnected, attempting to reconnect...")
                self.connect()
                time.sleep(5)  # Wait before trying to reconnect
                continue
                
            # Control capture rate
            current_time = time.time()
            if current_time - last_capture_time < interval:
                time.sleep(0.001)  # Small sleep to prevent CPU hogging
                continue
                
            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.warning(f"Failed to read frame from camera {self.name}")
                    self.connected = False
                    continue
                    
                # Update frame
                with self.lock:
                    self.last_frame = frame
                    self.last_frame_time = current_time
                    self.frame_count += 1
                
                # Clear queue if full and put new frame
                while self.frame_queue.full():
                    self.frame_queue.get()
                self.frame_queue.put(frame)
                
                last_capture_time = current_time
            except Exception as e:
                logger.error(f"Error capturing frame from camera {self.name}: {e}")
                self.connected = False
        
        # Clean up
        if self.cap is not None:
            self.cap.release()
    
    def get_frame(self):
        """Get the latest frame from the camera.
        
        Returns:
            Latest frame or None if no frame available
        """
        with self.lock:
            return self.last_frame
    
    def get_frame_from_queue(self):
        """Get the latest frame from the queue (non-blocking).
        
        Returns:
            Latest frame or None if queue is empty
        """
        try:
            return self.frame_queue.get_nowait()
        except:
            return None
    
    def stop(self):
        """Stop the camera capture."""
        self.running = False
        if self.capture_thread is not None:
            self.capture_thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()

class CameraManager:
    """Manages multiple camera streams."""
    
    def __init__(self, camera_configs):
        """Initialize the camera manager.
        
        Args:
            camera_configs: List of camera configuration dictionaries
        """
        self.cameras = {}
        self.update_cameras(camera_configs)
    
    def update_cameras(self, camera_configs):
        """Update camera list from configuration.
        
        Args:
            camera_configs: List of camera configuration dictionaries
        """
        # Track cameras to add, update, or remove
        current_camera_ids = set(self.cameras.keys())
        new_camera_ids = set(camera['id'] for camera in camera_configs)
        
        # Remove cameras not in new config
        for camera_id in current_camera_ids - new_camera_ids:
            logger.info(f"Removing camera {camera_id}")
            self.cameras[camera_id].stop()
            del self.cameras[camera_id]
        
        # Add or update cameras
        for config in camera_configs:
            camera_id = config['id']
            # Update existing camera if URL changed
            if camera_id in self.cameras and self.cameras[camera_id].rtsp_url != config['rtsp_url']:
                logger.info(f"Updating camera {camera_id}")
                self.cameras[camera_id].stop()
                self.cameras[camera_id] = Camera(
                    camera_id,
                    config['name'],
                    config['rtsp_url'],
                    config.get('fps', 10)
                )
            # Add new camera
            elif camera_id not in self.cameras:
                logger.info(f"Adding camera {camera_id}")
                self.cameras[camera_id] = Camera(
                    camera_id,
                    config['name'],
                    config['rtsp_url'],
                    config.get('fps', 10)
                )
    
    def get_camera(self, camera_id):
        """Get a camera by its ID.
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            Camera object or None if not found
        """
        return self.cameras.get(camera_id)
    
    def get_all_cameras(self):
        """Get all camera objects.
        
        Returns:
            Dictionary of camera objects by ID
        """
        return self.cameras
    
    def get_camera_info(self):
        """Get information about all cameras.
        
        Returns:
            List of camera info dictionaries
        """
        camera_info = []
        for camera_id, camera in self.cameras.items():
            camera_info.append({
                'id': camera_id,
                'name': camera.name,
                'rtsp_url': camera.rtsp_url,
                'connected': camera.connected,
                'fps': camera.fps,
                'frame_count': camera.frame_count
            })
        return camera_info
    
    def get_camera_status(self):
        """Get status of all cameras for monitoring purposes.
        
        Returns:
            Dictionary with camera statuses
        """
        status = {}
        for camera_id, camera in self.cameras.items():
            status[camera_id] = {
                'connected': camera.connected,
                'frame_count': camera.frame_count,
                'last_frame_time': camera.last_frame_time,
                'connection_attempts': camera.connection_attempts
            }
        return status
    
    def stop_all(self):
        """Stop all camera captures."""
        for camera in self.cameras.values():
            camera.stop()
