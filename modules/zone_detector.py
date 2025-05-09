#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import time
import logging
import numpy as np
import threading
from collections import defaultdict

# Try to import Hailo AI SDK
try:
    import hailo
    from hailo_platform import HEF
    from hailo_platform import InferVStreams
    from hailo_platform import ConfigureParams
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False
    logging.warning("Hailo AI SDK not available. Detection will be simulated.")

logger = logging.getLogger(__name__)

class ZoneDetector:
    """Detects humans in predefined zones using Hailo8L AI accelerator."""
    
    def __init__(self, camera_manager, gpio_controller, zones_config, hailo_model_path=None):
        """Initialize the zone detector.
        
        Args:
            camera_manager: CameraManager instance to get frames from
            gpio_controller: GPIOController instance to control GPIO
            zones_config: Dictionary of zone configurations
            hailo_model_path: Path to Hailo model file (.hef)
        """
        self.camera_manager = camera_manager
        self.gpio_controller = gpio_controller
        self.zones = zones_config
        self.hailo_model_path = hailo_model_path or '/opt/hailo/models/yolov5s_persondetection.hef'
        
        # State variables
        self.running = False
        self.lock = threading.Lock()
        self.detection_results = {}
        self.zone_status = defaultdict(bool)  # Track if each zone has people
        self.last_process_time = 0
        self.hailo_device = None
        self.hailo_network = None
        
        # Initialize Hailo if available
        if HAILO_AVAILABLE:
            self._init_hailo()
    
    def _init_hailo(self):
        """Initialize Hailo AI accelerator."""
        try:
            # Create Hailo device
            self.hailo_device = hailo.Device()
            
            # Load model from HEF file
            hef = HEF(self.hailo_model_path)
            self.configure_params = ConfigureParams.create_from_hef(hef, interface=hailo.PCIE)
            self.hailo_network = self.hailo_device.configure(hef, self.configure_params)
            
            # Get input and output tensors info
            self.input_vstream_info = hef.get_input_vstream_infos()[0]
            self.output_vstream_info = hef.get_output_vstream_infos()
            
            # Create inference streams
            self.infer_streams = InferVStreams(self.hailo_device, self.hailo_network)
            self.infer_streams.start()
            
            logger.info(f"Hailo8L initialized with model: {self.hailo_model_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Hailo8L: {e}")
            self.hailo_device = None
            self.hailo_network = None
    
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
