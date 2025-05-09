#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import logging
from threading import Lock

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO module not available. GPIO control will be simulated.")

logger = logging.getLogger(__name__)

class GPIOController:
    """Controls Raspberry Pi GPIO pins for relay activation."""
    
    def __init__(self, gpio_config):
        """Initialize the GPIO controller.
        
        Args:
            gpio_config: GPIO configuration dictionary
        """
        self.config = gpio_config
        self.output_pin = gpio_config.get('output_pin', 17)  # Default to GPIO 17
        self.active_high = gpio_config.get('active_high', True)
        self.activation_delay = gpio_config.get('activation_delay', 0.5)
        
        self.is_active = False
        self.last_deactivation_time = 0
        self.lock = Lock()
        
        # Initialize GPIO if available
        if GPIO_AVAILABLE:
            try:
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.output_pin, GPIO.OUT)
                # Initialize pin to inactive state
                initial_state = GPIO.HIGH if self.active_high else GPIO.LOW
                GPIO.output(self.output_pin, not initial_state)
                logger.info(f"GPIO initialized. Output pin: {self.output_pin}, Active high: {self.active_high}")
            except Exception as e:
                logger.error(f"Failed to initialize GPIO: {e}")
        else:
            logger.info("Running in GPIO simulation mode")
    
    def update_config(self, gpio_config):
        """Update GPIO configuration.
        
        Args:
            gpio_config: New GPIO configuration
        """
        with self.lock:
            # If pin changed, cleanup old pin first
            if 'output_pin' in gpio_config and gpio_config['output_pin'] != self.output_pin:
                if GPIO_AVAILABLE:
                    # Set old pin to inactive state before changing
                    initial_state = GPIO.HIGH if self.active_high else GPIO.LOW
                    GPIO.output(self.output_pin, not initial_state)
                    GPIO.cleanup(self.output_pin)
                
                self.output_pin = gpio_config['output_pin']
                
                # Setup new pin
                if GPIO_AVAILABLE:
                    GPIO.setup(self.output_pin, GPIO.OUT)
                    # Initialize pin to inactive state
                    GPIO.output(self.output_pin, not initial_state)
            
            # Update other config options
            if 'active_high' in gpio_config:
                self.active_high = gpio_config['active_high']
            
            if 'activation_delay' in gpio_config:
                self.activation_delay = gpio_config['activation_delay']
            
            self.config = gpio_config
            logger.info(f"GPIO configuration updated: {gpio_config}")
    
    def activate(self):
        """Activate the GPIO pin (for relay control)."""
        with self.lock:
            if not self.is_active:
                if GPIO_AVAILABLE:
                    active_state = GPIO.HIGH if self.active_high else GPIO.LOW
                    GPIO.output(self.output_pin, active_state)
                self.is_active = True
                logger.info(f"GPIO pin {self.output_pin} activated")
    
    def deactivate(self):
        """Deactivate the GPIO pin (for relay control)."""
        with self.lock:
            # Only deactivate if enough time has passed since last deactivation
            current_time = time.time()
            if current_time - self.last_deactivation_time < self.activation_delay:
                return
            
            if self.is_active:
                if GPIO_AVAILABLE:
                    inactive_state = GPIO.LOW if self.active_high else GPIO.HIGH
                    GPIO.output(self.output_pin, inactive_state)
                self.is_active = False
                self.last_deactivation_time = current_time
                logger.info(f"GPIO pin {self.output_pin} deactivated")
    
    def is_activated(self):
        """Check if the GPIO pin is currently activated.
        
        Returns:
            True if activated, False otherwise
        """
        return self.is_active
    
    def get_config(self):
        """Get the current GPIO configuration.
        
        Returns:
            GPIO configuration dictionary
        """
        return self.config
    
    def get_status(self):
        """Get the current GPIO status.
        
        Returns:
            Dictionary with GPIO status information
        """
        return {
            'pin': self.output_pin,
            'active': self.is_active,
            'active_high': self.active_high,
            'delay': self.activation_delay
        }
    
    def cleanup(self):
        """Clean up GPIO resources."""
        if GPIO_AVAILABLE:
            try:
                # Set pin to inactive state before cleanup
                inactive_state = GPIO.LOW if self.active_high else GPIO.HIGH
                GPIO.output(self.output_pin, inactive_state)
                GPIO.cleanup(self.output_pin)
                logger.info(f"GPIO pin {self.output_pin} cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up GPIO: {e}")
