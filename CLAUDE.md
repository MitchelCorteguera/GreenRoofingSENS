# CLAUDE.md - GreenRoofingSENS Project Guide

This file provides guidance for AI assistants (Claude) working with this codebase.

## Project Overview

**GreenRoofingSENS v3.0** is a field-ready MicroPython firmware for Raspberry Pi Pico W that monitors green-roof agricultural sensors. It logs data locally, serves a real-time web dashboard, and uploads JSON data to Azure cloud.

## Technology Stack

- **Hardware:** Raspberry Pi Pico W (RP2040)
- **Firmware:** MicroPython v1.20+
- **Backend:** Azure Functions (Python 3.9), Cosmos DB
- **Infrastructure:** Terraform
- **Frontend:** HTML5/CSS3, ApexCharts, vanilla JavaScript

## Repository Structure

```
/
├── boot.py              # Minimal boot initialization
├── config.py            # All configuration parameters (WiFi, sensors, thresholds)
├── main.py              # Application entry point and main loop
├── sensor_manager.py    # Sensor orchestration layer
├── agri_sensors.py      # Hardware drivers (rainfall, IR temp, soil temp, moisture)
├── data_logger.py       # CSV logging with auto-rotation
├── web_server.py        # HTTP server and API endpoints
├── web_template.py      # Dashboard HTML/CSS/JS template
├── utils.py             # Utility functions (logging, time, buffers)
├── memory_handler.py    # Memory management for constrained environments
├── system_monitor.py    # System health metrics
├── uploader.py          # Azure cloud data posting
├── README.md            # Project documentation
└── terraform/           # Azure infrastructure as code
    ├── main.tf          # Terraform resources
    ├── function_app/    # Azure Function implementation
    ├── deploy.sh        # Bash deployment script
    └── deploy.ps1       # PowerShell deployment script
```

## Hardware Sensors

| Sensor | Type | Interface | Notes |
|--------|------|-----------|-------|
| DFRobot SEN0575 | Rainfall (tipping bucket) | I2C (0x1D) | Cumulative + hourly |
| MLX90614 × 2 | IR Temperature | I2C (separate buses) | Leaf/surface temp |
| DS18B20 × 3 | Soil Temperature | OneWire (GPIO 16,17,18) | Individual + average |
| Capacitive × 3 | Soil Moisture | ADC (GPIO 26,27,28) | Calibrated 0-100% |

## Key Architecture Patterns

### Data Flow
```
Sensors → agri_sensors.py → sensor_manager.py → [data_logger / web_server / uploader] → main.py loop
```

### Memory Management
- Uses circular buffers (24 points) to limit RAM usage
- Three-tier warning system: 75% warning, 85% critical, 90% emergency
- Emergency recovery reduces history buffer when RAM critical

### Web Server Endpoints
- `/` - Main dashboard (HTML)
- `/api/data` - Current sensor data + history (JSON)
- `/api/history` - Historical data for charts
- `/csv` - Download logs as CSV
- `/json` - Download logs as JSON
- `/sensors` - Sensor status

## Build & Deploy Commands

### Flash to Pico W
```bash
# Use Thonny, PyMakr, or mpremote to copy all .py files to Pico
mpremote cp *.py :
mpremote reset
```

### Deploy Azure Infrastructure
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Deploy Azure Function
```bash
cd terraform
./deploy.sh  # Linux/macOS
# or
./deploy.ps1  # Windows PowerShell
```

## Configuration (`config.py`)

Key settings to modify:
- `WIFI_SSID` / `WIFI_PASSWORD` - Network credentials
- `UPLOAD_URL` - Azure Function endpoint
- `SENSOR_ENABLE_*` - Toggle individual sensors
- `SOIL_MOISTURE_DRY` / `SOIL_MOISTURE_WET` - Calibration values (ADC)
- `LOG_INTERVAL` - Data logging frequency (default 30s)
- `UPLOAD_INTERVAL` - Cloud upload frequency (default 300s)

## Common Development Tasks

### Adding a New Sensor
1. Create driver class in `agri_sensors.py`
2. Add initialization in `sensor_manager.py`
3. Update `get_readings()` to include new data
4. Add display card in `web_template.py`
5. Add enable flag in `config.py`

### Modifying Dashboard
- Edit `web_template.py` - contains all HTML/CSS/JS
- Use ApexCharts for new charts
- Cards use CSS grid layout (responsive)

### Debugging
- Set `SENSOR_DEBUG_MODE = True` in config for serial output
- Set `UPLOAD_DEBUG_MODE = True` for upload diagnostics
- Check `/logs/sensor_log.txt` for historical data

### Testing Sensors
```python
# In REPL (via Thonny or mpremote repl)
from sensor_manager import SensorManager
sm = SensorManager()
print(sm.get_readings(as_dict=True))
```

## Code Style Notes

- MicroPython compatible (no f-strings in some contexts, memory conscious)
- Error handling with fallback to last-good-values
- Rate limiting on sensor reads (2-second minimum)
- Watchdog timer optional (8-second timeout)

## Azure Function Payload Format

```json
{
  "deviceId": "pico-001",
  "timestamp": "2025-01-15T14:30:00Z",
  "version": "3.0",
  "softwareDate": "2025-01-15",
  "sensors": {
    "soil_temp_avg": 22.5,
    "soil_temp_1": 22.3,
    "soil_temp_2": 22.6,
    "soil_temp_3": 22.6,
    "soil_moisture_1": 45.2,
    "soil_moisture_2": 48.1,
    "soil_moisture_3": 43.7,
    "ir_temp_1": 24.1,
    "ir_temp_2": 23.8,
    "rainfall_cumulative": 12.5,
    "rainfall_hourly": 0.5
  }
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| WiFi not connecting | Check credentials in config.py, verify network is 2.4GHz |
| Sensor reading "None" | Check wiring, verify I2C/OneWire addresses, check enable flags |
| Dashboard not loading | Verify Pico IP, check for memory issues in serial output |
| Cloud upload failing | Verify UPLOAD_URL, check Azure Function logs, test endpoint |
| Memory errors | Reduce LOG_HISTORY_SIZE, enable WATCHDOG, check for sensor failures |

## Important Files for Common Changes

- **WiFi/Network:** `config.py`, `web_server.py`
- **Sensor readings:** `agri_sensors.py`, `sensor_manager.py`
- **Dashboard UI:** `web_template.py`
- **Data storage:** `data_logger.py`
- **Cloud integration:** `uploader.py`, `terraform/function_app/function_app.py`
- **System health:** `system_monitor.py`, `memory_handler.py`
