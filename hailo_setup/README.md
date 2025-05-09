# Hailo AI SDK Setup for AMS Zone Monitor

This directory contains tools and instructions for setting up the Hailo AI SDK which is required for the AMS Zone Monitor application to perform human detection.

## Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS (64-bit recommended)
- Hailo8L AI accelerator connected via PCIe HAT
- Docker (will be installed by the setup script if not present)
- Internet connection during installation

## Installation Options

### Option 1: Using the Included Setup Script

If you have placed the Hailo SDK Docker package in this directory:

1. Copy the Hailo SDK Docker package (`hailo_ai_sw_suite_2025-04_docker.zip` or similar) to this directory
2. Rename it to `hailo_ai_sw_suite_docker.zip` 
3. Run the installation script:

```bash
chmod +x install_hailo.sh
./install_hailo.sh
```

### Option 2: Manual Installation

If you prefer to install the Hailo SDK manually:

1. Extract the Hailo SDK Docker package
2. Follow the instructions in the Hailo documentation to install the Docker image
3. Run the provided scripts to install the Hailo drivers and tools
4. Install the Python package: `pip install hailo-ai`

## Verification

After installation, verify that the Hailo SDK is properly installed and the Hailo8L device is detected:

```bash
# Check if the Hailo PCIe device is recognized
lspci | grep Hailo

# Test the Hailo PCIe connection
hailo_pcie_test

# Get device information
hailo_device_info
```

## Troubleshooting

### Common Issues

1. **"Device not found" errors**
   - Ensure the Hailo8L is properly seated in the PCIe slot
   - Check power requirements are met
   - Try rebooting the Raspberry Pi

2. **Docker-related issues**
   - Ensure your user is in the Docker group: `sudo usermod -aG docker $USER`
   - Logout and login again for group changes to take effect

3. **Permission issues**
   - Some Hailo tools require root privileges: try with `sudo`
   - If using a Python virtual environment, ensure it has access to the system libraries

### Advanced Troubleshooting

For more advanced troubleshooting, refer to the official Hailo documentation provided with the SDK package or contact Hailo support.

## Additional Resources

- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Hailo Documentation](https://hailo.ai/documentation/)
