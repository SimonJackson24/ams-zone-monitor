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

1. Clone this repository to your Raspberry Pi
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure the application:
   ```
   cp config/config.example.json config/config.json
   ```
   Edit `config.json` with your specific settings.

4. Start the application:
   ```
   python app.py
   ```

5. To run as a service:
   ```
   sudo cp systemd/ams-zone-monitor.service /etc/systemd/system/
   sudo systemctl enable ams-zone-monitor
   sudo systemctl start ams-zone-monitor
   ```

6. Access the web interface at `http://<raspberry-pi-ip>:5000`

## Configuration

Use the web interface to:
- Add RTSP camera streams
- Configure GPIO pins
- Define monitoring zones

## License

MIT
