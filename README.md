# AMS Zone Monitor

A Raspberry Pi 5 application that monitors camera feeds for human presence in predefined zones using Hailo8L AI accelerator, with relay control via GPIO pins.

## Features

- Continuous monitoring of RTSP camera streams
- AI-powered human detection using Hailo8L
- Customizable monitoring zones
- GPIO control for relay activation when humans detected
- Web-based configuration interface
- Runs as a system service

## Hardware Requirements

- Raspberry Pi 5
- Hailo8L AI accelerator on PCIe HAT
- Camera with RTSP stream capability
- Relay for safety device connection

## Installation

### 1. Clone this repository to your Raspberry Pi
```bash
git clone https://github.com/SimonJackson24/ams-zone-monitor.git
cd ams-zone-monitor
```

### 2. Install Hailo SDK and dependencies
```bash
# Install Hailo SDK first
cd hailo_setup
chmod +x install_hailo.sh
./install_hailo.sh
cd ..

# Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure the application
```bash
cp config/config.example.json config/config.json
```
Edit `config.json` with your specific settings (camera streams, GPIO pins, etc).

### 4. Start the application
```bash
python app.py
```

### 5. Run as a service (optional)
```bash
sudo cp systemd/ams-zone-monitor.service /etc/systemd/system/
sudo systemctl enable ams-zone-monitor
sudo systemctl start ams-zone-monitor
```

### 6. Access the web interface
Open a browser and navigate to:
```
http://<raspberry-pi-ip>:7800
```

## Configuration

Use the web interface to:
- Add RTSP camera streams
- Configure GPIO pins
- Define monitoring zones

## License

MIT
