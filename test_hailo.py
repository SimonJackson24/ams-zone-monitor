#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hailo8L Test Script for AMS Zone Monitor

This script tests if the Hailo8L device is properly connected and can run inferences.
Run this before setting up the full application to verify your hardware setup.
"""

import os
import sys
import time
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_hailo_installation():
    """Test if Hailo SDK is properly installed"""
    try:
        import hailo
        logger.info("✓ Hailo SDK is installed")
        return True
    except ImportError as e:
        logger.error(f"✗ Hailo SDK is not installed: {e}")
        logger.error("Please install the Hailo AI Software Suite")
        return False

def test_hailo_device():
    """Test if Hailo device is connected and accessible"""
    try:
        import hailo
        device = hailo.Device()
        device_id = device.device_id
        logger.info(f"✓ Hailo device found. Device ID: {device_id}")
        device.close()
        return True
    except Exception as e:
        logger.error(f"✗ Could not connect to Hailo device: {e}")
        return False

def test_model_inference(model_path):
    """Test running inference with a specified model"""
    try:
        import hailo
        import numpy as np
        from hailo_platform import HEF
        from hailo_platform import InferVStreams
        from hailo_platform import ConfigureParams

        if not os.path.exists(model_path):
            logger.error(f"✗ Model file not found: {model_path}")
            return False
            
        logger.info(f"Loading model: {model_path}")
        
        # Create device and load model
        device = hailo.Device()
        hef = HEF(model_path)
        configure_params = ConfigureParams.create_from_hef(hef, interface=hailo.PCIE)
        network = device.configure(hef, configure_params)
        
        # Get input shape and prepare dummy input
        input_vstream_info = hef.get_input_vstream_infos()[0]
        input_shape = input_vstream_info.shape
        logger.info(f"Model input shape: {input_shape}")
        
        # Create dummy input (1x3x640x640 example - adjust based on your model)
        dummy_input = np.random.rand(*input_shape).astype(np.float32)
        
        # Run inference
        infer_streams = InferVStreams(device, network)
        infer_streams.start()
        
        # Time the inference
        start_time = time.time()
        outputs = infer_streams.infer(dummy_input)
        inference_time = time.time() - start_time
        
        # Clean up
        infer_streams.stop()
        device.release(network)
        device.close()
        
        logger.info(f"✓ Inference successful! Time: {inference_time:.2f} seconds")
        logger.info(f"✓ Output shapes: {[out.shape for out in outputs.values()]}")
        return True
    except Exception as e:
        logger.error(f"✗ Error during inference test: {e}")
        return False

def test_gpio():
    """Test GPIO functionality"""
    try:
        import RPi.GPIO as GPIO
        
        # Test pin - default for our application
        test_pin = 17
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(test_pin, GPIO.OUT)
        
        logger.info(f"Setting GPIO {test_pin} HIGH")
        GPIO.output(test_pin, GPIO.HIGH)
        time.sleep(1)
        
        logger.info(f"Setting GPIO {test_pin} LOW")
        GPIO.output(test_pin, GPIO.LOW)
        time.sleep(1)
        
        GPIO.cleanup(test_pin)
        logger.info(f"✓ GPIO test successful on pin {test_pin}")
        return True
    except Exception as e:
        logger.error(f"✗ Error during GPIO test: {e}")
        logger.error("This test requires running on a Raspberry Pi")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test Hailo8L setup for AMS Zone Monitor')
    parser.add_argument('--model', type=str, 
                        default='/opt/hailo/models/yolov5s_persondetection.hef',
                        help='Path to Hailo model file (.hef)')
    parser.add_argument('--gpio', action='store_true', 
                        help='Test GPIO functionality (Raspberry Pi only)')
    args = parser.parse_args()
    
    logger.info("===== AMS Zone Monitor - Hailo8L Test =====")
    
    # Run tests
    sdk_installed = test_hailo_installation()
    if sdk_installed:
        device_connected = test_hailo_device()
        if device_connected:
            inference_ok = test_model_inference(args.model)
    
    # Test GPIO if requested
    if args.gpio:
        gpio_ok = test_gpio()
    
    logger.info("===== Test Complete =====")

if __name__ == '__main__':
    main()
