#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import time
import logging
import numpy as np
import threading
import os
from collections import defaultdict
from datetime import datetime

# Import our improved Hailo wrapper
from modules.hailo_wrapper import HailoWrapper, is_hailo_available

logger = logging.getLogger(__name__)

class ZoneDetector:
    """Detects humans in predefined zones using Hailo8L AI accelerator."""
    
    def __init__(self, camera_manager, gpio_controller, config):
        """Initialize the zone detector.
        
        Args:
            camera_manager: CameraManager instance to get frames from
            gpio_controller: GPIOController instance to control GPIO
            config: Application configuration dictionary
        """
        self.camera_manager = camera_manager
        self.gpio_controller = gpio_controller
        self.config = config
        self.zones = {}
        
        # State variables
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.last_detection_time = {}
        self.frame_buffer = {}
        
        # Initialize Hailo for person detection
        self.hailo_available = is_hailo_available()
        if self.hailo_available:
            model_path = config.get('hailo', {}).get('model_path', '')
            if os.path.exists(model_path):
                self.hailo = HailoWrapper(model_path)
                logger.info(f"Hailo AI initialized with model: {model_path}")
            else:
                logger.error(f"Hailo model file not found: {model_path}")
                self.hailo_available = False
        else:
            logger.warning("Hailo AI SDK not available. Detection will be simulated.")
        
        # Initialize zones from config
        self._init_zones()
    def _init_zones(self):
        """Initialize zones from configuration file"""
        for camera in self.config.get('cameras', []):
            camera_id = camera.get('id')
            for zone_config in camera.get('zones', []):
                zone_id = zone_config.get('id')
                if zone_id and camera_id:
                    self.zones[zone_id] = {
                        'camera_id': camera_id,
                        'name': zone_config.get('name', f'Zone {zone_id}'),
                        'coordinates': zone_config.get('coordinates', []),
                        'confidence_threshold': zone_config.get('confidence_threshold', 0.5),
                        'active': False,
                        'person_detected': False,
                        'last_detection_time': None
                    }
                    logger.info(f"Zone initialized: {zone_id} for camera {camera_id}")
            
    def start(self):
        """Start the zone detector monitoring thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Zone detector started")
    
    def stop(self):
        """Stop the zone detector."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("Zone detector stopped")
    
    def get_zones(self):
        """Get all zones."""
        with self.lock:
            return self.zones.copy()
    
    def get_zone(self, zone_id):
        """Get a specific zone by ID."""
        with self.lock:
            return self.zones.get(zone_id, {})
    
    def set_zone_active(self, zone_id, active):
        """Activate or deactivate a zone."""
        with self.lock:
            if zone_id in self.zones:
                self.zones[zone_id]['active'] = active
                logger.info(f"Zone {zone_id} set to {'active' if active else 'inactive'}")
                return True
        return False
    
    def update_zone_coordinates(self, zone_id, coordinates):
        """Update zone coordinates."""
        with self.lock:
            if zone_id in self.zones:
                self.zones[zone_id]['coordinates'] = coordinates
                logger.info(f"Zone {zone_id} coordinates updated")
                return True
        return False
    
    def get_last_frame(self, camera_id):
        """Get the last processed frame for a camera."""
        return self.frame_buffer.get(camera_id)
    
    def _is_person_in_zone(self, person_bbox, zone_coordinates):
        """Check if a person is in a zone.
        
        Args:
            person_bbox: [x1, y1, x2, y2] bounding box
            zone_coordinates: List of [x, y] coordinates defining a polygon
            
        Returns:
            True if person is in zone, False otherwise
        """
        # Calculate center point of the bounding box
        center_x = (person_bbox[0] + person_bbox[2]) / 2
        center_y = (person_bbox[1] + person_bbox[3]) / 2
        
        # Convert zone coordinates to numpy array
        zone_polygon = np.array(zone_coordinates, np.int32)
        zone_polygon = zone_polygon.reshape((-1, 1, 2))
        
        # Check if center point is inside the polygon
        result = cv2.pointPolygonTest(zone_polygon, (center_x, center_y), False)
        return result >= 0
    
    def _detect_persons(self, frame):
        """Detect persons in a frame.
        
        Args:
            frame: The image to detect persons in
            
        Returns:
            List of [x1, y1, x2, y2] bounding boxes
        """
        if self.hailo_available and hasattr(self, 'hailo'):
            # Use Hailo for detection
            try:
                detections = self.hailo.infer(frame)
                # Format: [[x1, y1, x2, y2, confidence, class_id], ...]
                persons = []
                
                # Filter for person class (usually class_id 0 in YOLO models)
                for detection in detections:
                    if detection[5] == 0:  # Person class
                        if detection[4] > 0.3:  # Confidence threshold
                            persons.append(detection[:4])  # Get bounding box
                
                return persons
            except Exception as e:
                logger.error(f"Error in Hailo detection: {e}")
                # Fall back to OpenCV detection on error
                return self._opencv_person_detection(frame)
        else:
            # Use OpenCV for detection
            return self._opencv_person_detection(frame)
    
    def _opencv_person_detection(self, frame):
        """Fallback person detection using OpenCV.
        
        Args:
            frame: The image to detect persons in
            
        Returns:
            List of [x1, y1, x2, y2] bounding boxes
        """
        # Basic person detection using OpenCV
        # This is a simplified version for simulation
        height, width = frame.shape[:2]
        
        # For simulation, we'll just create a random detection 5% of the time
        if np.random.random() < 0.05:
            x1 = int(width * 0.4)
            y1 = int(height * 0.4)
            x2 = int(width * 0.6)
            y2 = int(height * 0.6)
            return [[x1, y1, x2, y2]]
        return []
    
    def _monitoring_loop(self):
        """Main monitoring loop that runs in a separate thread."""
        while self.running:
            try:
                for camera_id, camera in self.camera_manager.get_cameras().items():
                    # Get frame from camera
                    frame = camera.get_frame()
                    if frame is None:
                        continue
                    
                    # Store frame in buffer
                    self.frame_buffer[camera_id] = frame.copy()
                    
                    # Detect persons
                    persons = self._detect_persons(frame)
                    
                    # Process each zone for this camera
                    for zone_id, zone in self.zones.items():
                        if zone['camera_id'] == camera_id and zone['active']:
                            person_in_zone = False
                            
                            # Check if any person is in this zone
                            for person_bbox in persons:
                                if self._is_person_in_zone(person_bbox, zone['coordinates']):
                                    person_in_zone = True
                                    break
                            
                            # Update zone status
                            with self.lock:
                                previous_detection = self.zones[zone_id]['person_detected']
                                self.zones[zone_id]['person_detected'] = person_in_zone
                                
                                if person_in_zone:
                                    self.zones[zone_id]['last_detection_time'] = datetime.now()
                                    
                                    # Activate safety relay if person detected
                                    if not previous_detection:
                                        logger.warning(f"Person detected in zone {zone_id}")
                                        self.gpio_controller.set_relay(True)
                                elif previous_detection:
                                    # Deactivate safety relay if no person detected
                                    logger.info(f"No person detected in zone {zone_id}")
                                    self.gpio_controller.set_relay(False)
            except Exception as e:
                logger.error(f"Error in zone detector: {e}")
            
            # Sleep to reduce CPU usage
            time.sleep(0.1)
    
    def draw_zones(self, frame, camera_id):
        """Draw zones on a frame.
        
        Args:
            frame: The frame to draw on
            camera_id: The camera ID to draw zones for
            
        Returns:
            Frame with zones drawn on it
        """
        if frame is None:
            return frame
            
        result = frame.copy()
        
        for zone_id, zone in self.zones.items():
            if zone['camera_id'] == camera_id and zone['coordinates']:
                # Choose color based on zone status
                if zone['person_detected']:
                    color = (0, 0, 255)  # Red if person detected
                elif zone['active']:
                    color = (0, 255, 0)  # Green if active
                else:
                    color = (255, 255, 255)  # White if inactive
                
                thickness = 2
                
                # Convert coordinates to numpy array
                points = np.array(zone['coordinates'], np.int32)
                points = points.reshape((-1, 1, 2))
                
                # Draw filled polygon with transparency
                overlay = result.copy()
                cv2.fillPoly(overlay, [points], color)
                alpha = 0.3
                cv2.addWeighted(overlay, alpha, result, 1 - alpha, 0, result)
                
                # Draw polygon outline
                cv2.polylines(result, [points], True, color, thickness)
                
                # Draw zone name
                if len(zone['coordinates']) > 0:
                    text_point = (zone['coordinates'][0][0], zone['coordinates'][0][1] - 10)
                    cv2.putText(result, zone['name'], text_point, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return result
    
    def _process_detections(self, detections, frame_shape, camera_id, zone_id):
        """Process detections to determine if any person is in the zone.
        
        Args:
            detections: List of detection bounding boxes
            frame_shape: Shape of the video frame
            camera_id: ID of the camera being processed
            zone_id: ID of the zone being checked
            
        Returns:
            True if a person is detected in the zone, False otherwise
        """
        if zone_id not in self.zones:
            return False
            
        zone_coords = self.zones[zone_id]['coordinates']
        zone_polygon = np.array(zone_coords, np.int32).reshape((-1, 1, 2))
        
        # Check if any detection overlaps with the zone
        for detection in detections:
            # Each detection is [x1, y1, x2, y2, confidence, class_id]
            if detection[5] != 0:  # 0 is the class ID for person in COCO dataset
                continue
                
            confidence = detection[4]
            if confidence < 0.5:  # Confidence threshold
                continue
                
            # Calculate detection box coordinates (normalized to frame size)
            x1, y1, x2, y2 = detection[:4]
            x1 = int(x1 * frame_shape[1])
            y1 = int(y1 * frame_shape[0])
            x2 = int(x2 * frame_shape[1])
            y2 = int(y2 * frame_shape[0])
            
            # Check if bottom center point is in zone (person's feet)
            bottom_center_x = (x1 + x2) // 2
            bottom_center_y = y2
            bottom_center = (bottom_center_x, bottom_center_y)
            
            if cv2.pointPolygonTest(zone_polygon, bottom_center, False) >= 0:
                return True
                
        return False
    
    def _simulate_detection(self, frame, camera_id, zone_id):
        """Simulate person detection when Hailo is not available (for development only).
        
        Args:
            frame: Video frame to process
            camera_id: ID of the camera being processed
            zone_id: ID of the zone being checked
            
        Returns:
            True with 20% random chance (for simulation purposes)
        """
        import random
        # 20% chance of detecting a person (for simulation only)
        return random.random() < 0.2
    
    def _detect_with_hailo(self, frame, camera_id, zone_id):
        """Detect people in a frame using Hailo8L.
        
        Args:
            frame: Video frame to process
            camera_id: ID of the camera being processed
            zone_id: ID of the zone being checked
            
        Returns:
            True if a person is detected in the zone, False otherwise
        """
        if not HAILO_AVAILABLE or self.hailo_device is None:
            return self._simulate_detection(frame, camera_id, zone_id)
            
        try:
            # Preprocess image for Hailo
            input_shape = self.input_vstream_info.shape
            preprocessed_frame = cv2.resize(frame, (input_shape[2], input_shape[1]))
            preprocessed_frame = preprocessed_frame.astype(np.float32) / 255.0
            preprocessed_frame = np.expand_dims(preprocessed_frame, axis=0)  # Add batch dimension
            
            # Run inference
            outputs = self.infer_streams.infer(preprocessed_frame)
            
            # Post-process detections (example for YOLOv5 format)
            detections = self._postprocess_yolov5(outputs)
            
            # Check if any detection is in the zone
            return self._process_detections(detections, frame.shape, camera_id, zone_id)
        except Exception as e:
            logger.error(f"Error during Hailo detection: {e}")
            return False
    
    def _postprocess_yolov5(self, outputs):
        """Post-process YOLOv5 model outputs to get detection bounding boxes.
        
        Args:
            outputs: Raw output from Hailo inference
            
        Returns:
            List of detection bounding boxes [x1, y1, x2, y2, confidence, class_id]
        """
        # Note: This is a simplified implementation and should be adapted to the specific model used
        # Format depends on the exact model exported to Hailo
        
        # Example implementation for YOLOv5 with output shape [1, 25200, 85] (80 classes + 5 box params)
        try:
            # Get detection output tensor (varies based on model)
            detection_output = None
            for output_name, output_data in outputs.items():
                if len(output_data.shape) == 3 and output_data.shape[2] > 5:  # Detect output shape
                    detection_output = output_data
                    break
            
            if detection_output is None:
                logger.error("Could not find detection output tensor")
                return []
            
            # Process detections
            detections = []
            detection_data = detection_output[0]  # First batch
            
            for detection in detection_data:
                confidence = detection[4]  # Object confidence
                
                if confidence < 0.5:  # Confidence threshold
                    continue
                
                # Find class with highest confidence
                class_confidences = detection[5:]
                class_id = np.argmax(class_confidences)
                class_confidence = class_confidences[class_id]
                
                if class_confidence < 0.5:  # Class confidence threshold
                    continue
                
                # Only interested in people (class 0 in COCO)
                if class_id != 0:  # Not a person
                    continue
                
                # Extract bounding box
                x, y, w, h = detection[0:4]
                x1 = x - w/2
                y1 = y - h/2
                x2 = x + w/2
                y2 = y + h/2
                
                # Add detection
                detections.append([x1, y1, x2, y2, confidence * class_confidence, class_id])
            
            return detections
        except Exception as e:
            logger.error(f"Error in YOLOv5 post-processing: {e}")
            return []
    
    def run(self):
        """Run the zone detection loop."""
        self.running = True
        logger.info("Zone detector started")
        
        try:
            while self.running:
                # Process each camera
                for camera_id, camera in self.camera_manager.get_all_cameras().items():
                    # Skip if camera is not connected
                    if not camera.connected:
                        continue
                    
                    # Get the latest frame
                    frame = camera.get_frame()
                    if frame is None:
                        continue
                    
                    # Process each zone for this camera
                    for zone_id, zone_config in self.zones.items():
                        # Skip zones not associated with this camera
                        if zone_config.get('camera_id') != camera_id:
                            continue
                        
                        # Detect people in zone
                        has_person = self._detect_with_hailo(frame, camera_id, zone_id)
                        
                        # Update zone status
                        with self.lock:
                            self.zone_status[zone_id] = has_person
                            
                            # Annotate detection for UI
                            if 'coordinates' in zone_config:
                                zone_coords = zone_config['coordinates']
                                # Deep copy frame to avoid modifying original
                                annotated_frame = frame.copy()
                                zone_polygon = np.array(zone_coords, np.int32).reshape((-1, 1, 2))
                                color = (0, 255, 0) if not has_person else (0, 0, 255)  # Green if clear, Red if person detected
                                cv2.polylines(annotated_frame, [zone_polygon], True, color, 2)
                                
                                # Store annotated frame for UI
                                self.detection_results[zone_id] = {
                                    'frame': annotated_frame,
                                    'has_person': has_person,
                                    'timestamp': time.time()
                                }
                    
                # Update GPIO based on all zone statuses
                any_zone_active = any(self.zone_status.values())
                if any_zone_active:
                    self.gpio_controller.activate()
                else:
                    self.gpio_controller.deactivate()
                    
                self.last_process_time = time.time()
                
                # Prevent CPU overload
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in zone detector: {e}")
        finally:
            self.running = False
            logger.info("Zone detector stopped")
    
    def stop(self):
        """Stop the zone detector."""
        self.running = False
        
        # Cleanup Hailo resources
        if HAILO_AVAILABLE and self.hailo_device is not None:
            try:
                if self.infer_streams is not None:
                    self.infer_streams.stop()
                if self.hailo_network is not None:
                    self.hailo_device.release(self.hailo_network)
                self.hailo_device.close()
                logger.info("Hailo resources released")
            except Exception as e:
                logger.error(f"Error releasing Hailo resources: {e}")
    
    def update_zones(self, zones_config):
        """Update zone configurations.
        
        Args:
            zones_config: New zone configuration dictionary
        """
        with self.lock:
            self.zones = zones_config
            # Clear statuses for zones that no longer exist
            for zone_id in list(self.zone_status.keys()):
                if zone_id not in zones_config:
                    del self.zone_status[zone_id]
            logger.info(f"Zone configurations updated: {len(zones_config)} zones")
    
    def get_zones(self):
        """Get the current zone configurations.
        
        Returns:
            Dictionary of zone configurations
        """
        return self.zones
    
    def get_zone_status(self):
        """Get the current status of all zones.
        
        Returns:
            Dictionary with zone status information
        """
        with self.lock:
            status = {}
            for zone_id, is_active in self.zone_status.items():
                status[zone_id] = {
                    'has_person': is_active,
                    'last_updated': self.last_process_time
                }
            return status
