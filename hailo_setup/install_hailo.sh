#!/bin/bash

# Hailo AI SDK Installation Script
set -e

echo "==== AMS Zone Monitor - Hailo SDK Installation ===="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is required but not installed. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker installed. You may need to log out and back in for group changes to take effect."
fi

# Extract the Hailo SDK if it exists in the current directory
HAILO_ZIP="hailo_ai_sw_suite_docker.zip"
if [ -f "$HAILO_ZIP" ]; then
    echo "Found Hailo SDK package. Extracting..."
    unzip -o "$HAILO_ZIP"
    
    # Find the extracted directory
    HAILO_DIR=$(find . -type d -name "hailo_ai_sw_suite*" -maxdepth 1 | head -n 1)
    
    if [ -n "$HAILO_DIR" ]; then
        echo "Extracted Hailo SDK to $HAILO_DIR"
        cd "$HAILO_DIR"
        
        # Run the Hailo installation script if it exists
        if [ -f "./install.sh" ]; then
            echo "Running Hailo installation script..."
            sudo ./install.sh
        else
            echo "Loading Docker image..."
            # Look for Docker installation files
            DOCKER_SCRIPT=$(find . -name "*docker*.sh" | head -n 1)
            if [ -n "$DOCKER_SCRIPT" ]; then
                echo "Running Docker setup script: $DOCKER_SCRIPT"
                sudo bash "$DOCKER_SCRIPT"
            else
                echo "No Docker setup script found. Trying to load Docker image directly."
                # Look for Docker tar files
                DOCKER_TAR=$(find . -name "*.tar" | head -n 1)
                if [ -n "$DOCKER_TAR" ]; then
                    echo "Loading Docker image from $DOCKER_TAR"
                    sudo docker load -i "$DOCKER_TAR"
                else
                    echo "ERROR: Could not find Hailo Docker image or installation script."
                    exit 1
                fi
            fi
        fi
    else
        echo "ERROR: Could not find extracted Hailo directory."
        exit 1
    fi
else
    echo "ERROR: Hailo SDK package not found. Please place $HAILO_ZIP in this directory."
    exit 1
fi

# Install Python package for Hailo
echo "Installing Hailo Python package..."
pip install -U hailo-ai

# Test Hailo installation
echo "Testing Hailo installation..."
if command -v hailo_pcie_test &> /dev/null; then
    echo "Running Hailo PCIe test..."
    hailo_pcie_test
else
    echo "Hailo PCIe test tool not found. Installation may not be complete."
fi

echo "==== Hailo SDK installation completed ===="
echo "You can now use the AMS Zone Monitor application."
