# Installation Guide for AMS Zone Monitor

## Prerequisites

### Hardware Setup
1. Raspberry Pi 5 with Raspberry Pi OS installed
2. Hailo8L AI accelerator connected via PCIe HAT
3. Camera with RTSP stream capability
4. Relay for safety device connection

### Software Prerequisites

1. Install system dependencies:
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-opencv python3-pil libhdf5-dev libatlas-base-dev python3-numpy python3-websockets
   ```

2. Install Hailo AI SDK by following the official Hailo documentation:
   ```bash
   # Visit https://hailo.ai/developer-zone/
   # Follow Hailo's instructions for installing the Hailo AI Software Suite on Raspberry Pi
   ```

## Application Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ams-zone-monitor.git
   cd ams-zone-monitor
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create configuration file:
   ```bash
   cp config/config.example.json config/config.json
   nano config/config.json  # Edit with your settings
   ```

5. Create required directories:
   ```bash
   mkdir -p logs
   mkdir -p static/img
   ```

## Running the Application

### Manual Start
```bash
python app.py
```

### Running as a Service
1. Copy the service file to the systemd directory:
   ```bash
   sudo cp systemd/ams-zone-monitor.service /etc/systemd/system/
   ```

2. Edit the service file if necessary to match your installation path:
   ```bash
   sudo nano /etc/systemd/system/ams-zone-monitor.service
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable ams-zone-monitor
   sudo systemctl start ams-zone-monitor
   ```

4. Check the service status:
   ```bash
   sudo systemctl status ams-zone-monitor
   ```

## Accessing the Web Interface

Once the application is running, you can access the web interface by opening a browser and navigating to:

```
http://<raspberry-pi-ip>:5000
```

Replace `<raspberry-pi-ip>` with the actual IP address of your Raspberry Pi.

## GPIO Configuration

The default GPIO pin for relay control is GPIO 17 (BCM numbering). You can change this in the web interface or by editing the config file.

Connect your relay to:
- GPIO pin (default: GPIO 17)
- Ground (GND)

Note: The relay will be activated when a person is detected in any of the configured zones.
