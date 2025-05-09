# Raspberry Pi 5 Installation Guide for AMS Zone Monitor

This guide provides step-by-step instructions for installing the AMS Zone Monitor application on your Raspberry Pi 5 with Hailo8L.

## Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS installed
- Hailo8L AI accelerator connected via PCIe HAT
- Internet connection on your Pi
- SSH or direct terminal access to your Pi
- Camera with RTSP stream capability
- Relay connected to GPIO for safety device control

## Installation Steps

### 1. Update Raspberry Pi OS

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install System Dependencies

```bash
sudo apt install -y python3-pip python3-opencv libhdf5-dev libatlas-base-dev \
                    python3-numpy git python3-venv libopenblas-dev \
                    python3-websockets libilmbase-dev libopenexr-dev libgstreamer1.0-dev
```

### 3. Install Hailo SDK

Follow the official Hailo installation instructions for Raspberry Pi 5:

1. Download the Hailo AI Software Suite from the [Hailo Developer Zone](https://hailo.ai/developer-zone/)
2. Install the Hailo driver packages according to their documentation
3. Verify Hailo installation with their test utilities

### 4. Clone the AMS Zone Monitor Repository

```bash
cd /home/pi
git clone https://github.com/SimonJackson24/ams-zone-monitor.git
cd ams-zone-monitor
```

### 5. Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Configure the Application

```bash
# Create config directory if it doesn't exist
mkdir -p config

# Copy the example config and customize it
cp config/config.example.json config/config.json
nano config/config.json
```

Edit the configuration file:
- Update RTSP camera URLs
- Adjust GPIO pin settings for your relay
- Verify Hailo model path is correct
- The port is already set to 7800 to avoid conflict with your existing service

### 7. Create Required Directories

```bash
mkdir -p logs
mkdir -p static/img
```

### 8. Test the Hailo Integration

```bash
python test_hailo.py
```

This will verify that your Hailo8L is properly connected and the model can be loaded.

### 9. Run the Application Manually (Testing)

```bash
python app.py
```

Access the web interface by opening a browser and navigating to:
```
http://<raspberry-pi-ip>:7800
```

### 10. Set Up as a System Service

```bash
# Edit the service file path to match your installation
nano systemd/ams-zone-monitor.service
```

Update the paths in the service file to match your installation:
```ini
[Unit]
Description=AMS Zone Monitor Service
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/ams-zone-monitor
ExecStart=/home/pi/ams-zone-monitor/venv/bin/python app.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Install and enable the service:
```bash
sudo cp systemd/ams-zone-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ams-zone-monitor
sudo systemctl start ams-zone-monitor
```

Check the service status:
```bash
sudo systemctl status ams-zone-monitor
```

## Troubleshooting

### View Application Logs

```bash
# View service logs
sudo journalctl -u ams-zone-monitor -f

# View application logs
tail -f /home/pi/ams-zone-monitor/logs/app.log
```

### Common Issues

1. **Connection refused to web interface**
   - Check if the service is running: `sudo systemctl status ams-zone-monitor`
   - Verify port 7800 is not blocked by firewall: `sudo ufw status`

2. **Cannot connect to camera stream**
   - Verify RTSP URL is correct in configuration
   - Ensure camera is accessible from the Raspberry Pi's network
   - Try accessing the RTSP stream with VLC or similar tool

3. **Hailo8L not detected**
   - Run `lspci` to verify the Hailo device is recognized
   - Check the Hailo driver installation: `hailo_pcie_test`

4. **GPIO control not working**
   - Verify GPIO pin number in config matches your wiring
   - Ensure the user running the service has GPIO access permissions

## Updating the Application

To update to the latest version from GitHub:

```bash
cd /home/pi/ams-zone-monitor
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ams-zone-monitor
```

## Reference Documentation

- [Hailo Developer Zone](https://hailo.ai/developer-zone/)
- [Raspberry Pi GPIO Documentation](https://www.raspberrypi.com/documentation/computers/os.html#gpio-and-the-40-pin-header)
- [RTSP Camera Streaming](https://en.wikipedia.org/wiki/Real_Time_Streaming_Protocol)
