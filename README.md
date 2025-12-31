# Honey Duo Gaming - N64 Emulation Web Control

Web-based control interface for RetroArch N64 emulation on Raspberry Pi 5.

## Features

- Remote game launching from mobile/desktop
- Save state management
- Cheat code support
- 4 Bluetooth N64 controllers
- Accessible via Cloudflare tunnel at pi.honey-duo.com

## Hardware

- **System:** Raspberry Pi 5 (8GB RAM, 2.8GHz overclock)
- **Display:** 70-inch Samsung 4K TV (forced 1080p)
- **Controllers:** 4x Aftermarket Bluetooth N64 controllers
- **Cooling:** Active cooling with PWM fan

## Installation

**Requirements:**
- Python 3.x
- RetroArch with mupen64plus-next core
- Flask and dependencies

**Setup:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask

# Place ROMs in N64/ directory
mkdir -p N64

# Run app
python app.py
```

## Systemd Service

Service runs as: `honeyduo-gaming.service`
```bash
# Status
systemctl status honeyduo-gaming

# Restart
sudo systemctl restart honeyduo-gaming

# Logs
journalctl -u honeyduo-gaming -f
```

## Configuration

- **Port:** 5000
- **External Access:** https://pi.honey-duo.com (Cloudflare tunnel)
- **ROM Directory:** `/home/honeyduopi/Desktop/HoneyDuoGaming/N64`
- **RetroArch:** Optimized with dynamic recompiler

## Integration

This app is monitored by Honey Duo Infrastructure:
- Repository: https://github.com/HoneyDuoDevelopments/honey-duo-infrastructure
- Uptime monitoring via Uptime Kuma
- Logs shipped to Loki
- Metrics collected by Prometheus

## License

Private - Personal Use Only
