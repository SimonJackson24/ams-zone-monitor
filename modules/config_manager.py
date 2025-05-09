#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration for the AMS Zone Monitor application."""
    
    def __init__(self, config_path):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the JSON configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self):
        """Load configuration from the JSON file or create default if not exists."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()
    
    def _create_default_config(self):
        """Create a default configuration if none exists."""
        default_config = {
            'cameras': [],
            'zones': {},
            'gpio': {
                'output_pin': 17,  # Default GPIO pin for relay control
                'active_high': True,  # True if relay activates on HIGH
                'activation_delay': 0.5,  # Seconds to wait before deactivating after no detection
            },
            'hailo': {
                'model_path': '/opt/hailo/models/yolov5s_persondetection.hef',
                'confidence_threshold': 0.5,
            },
            'web': {
                'port': 5000,
                'debug': False,
            }
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Save default config
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        logger.info(f"Created default configuration at {self.config_path}")
        return default_config
    
    def get_config(self):
        """Get the current configuration."""
        return self.config
    
    def update_config(self, new_config):
        """Update the entire configuration.
        
        Args:
            new_config: New configuration dictionary
        """
        self.config = new_config
        self._save_config()
        
    def update_config_section(self, section, data):
        """Update a specific section of the configuration.
        
        Args:
            section: Section name to update
            data: New data for the section
        """
        self.config[section] = data
        self._save_config()
        
    def _save_config(self):
        """Save the current configuration to the JSON file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
