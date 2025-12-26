# CLAUDE.md - GreenRoofingSENS Project Guide

This file provides guidance for AI assistants (Claude) working with this codebase.

## Project Overview

**GreenRoofingSENS v3.0** is a field-ready MicroPython firmware for Raspberry Pi Pico W that monitors green-roof agricultural sensors. It logs data locally, serves a real-time web dashboard, and uploads JSON data to Azure cloud.

## Technology Stack

- **Hardware:** Raspberry Pi Pico W (RP2040)
- **Firmware:** MicroPython v1.20+
- **Backend:** Azure Functions (Python 3.13), Azure Table Storage
- **Infrastructure:** Azure CLI
- **Frontend:** HTML5/CSS3, ApexCharts, vanilla JavaScript
- **External APIs:** OpenWeatherMap (weather correlation)

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
└── azure/               # Azure Function code
    ├── function_app.py  # Azure Function implementation
    ├── host.json        # Function host configuration
    ├── requirements.txt # Python dependencies
    └── index.html       # Cloud dashboard
```

## Azure Configuration

### Account & Subscription
- **Subscription:** Visual Studio Enterprise Subscription
- **Subscription ID:** 31c921e3-84cc-4c9d-bec3-603c35e6a7e7
- **User:** mario@mariocruz.net

### Function App
- **Name:** green-roof
- **Resource Group:** green-roof
- **Location:** Central US
- **SKU:** Consumption (Linux)
- **Runtime:** Python 3.11
- **Host:** `green-roof.azurewebsites.net`

### Endpoints
| Method | Route | Function | Auth |
|--------|-------|----------|------|
| GET | `/api/sensor-data` | get_sensor_data | Anonymous |
| POST | `/api/sensor-data` | http_trigger | Function Key |
| OPTIONS | `/api/sensor-data` | options_sensor_data | Anonymous |

### Storage
- **Account:** greenroof
- **Table:** SensorReadings
- **Table URL:** `https://greenroof.table.core.windows.net/SensorReadings`
- **Blob Container:** `app-package-green-roof-6ca898b` (deployment packages)
- **Static Website:** `$web` container for index.html hosting
- **Connection:** AzureWebJobsStorage app setting

### Table Storage Schema
| Column | Type | Description |
|--------|------|-------------|
| PartitionKey | string | Device ID |
| RowKey | string | UUID |
| DateTime | string | ISO timestamp |
| SoilTemp_C | float | Average soil temperature |
| SoilTemp_1_C | float | Soil temp sensor 1 |
| SoilTemp_2_C | float | Soil temp sensor 2 |
| SoilTemp_3_C | float | Soil temp sensor 3 |
| SoilMoisture_Percent | float | Average soil moisture |
| SoilMoisture_1_Percent | float | Moisture sensor 1 |
| SoilMoisture_2_Percent | float | Moisture sensor 2 |
| SoilMoisture_3_Percent | float | Moisture sensor 3 |
| IR_Temp_C | float | Average IR temperature |
| IR_Temp_1_C | float | IR sensor 1 (I2C0) |
| IR_Temp_2_C | float | IR sensor 2 (I2C1) |
| Rainfall_Total_mm | float | Cumulative rainfall |
| Rainfall_Hourly_mm | float | Last hour rainfall |
| DeviceID | string | Device identifier |
| Version | string | Firmware version |
| SoftwareDate | string | Firmware date |

### Deployment Commands
```bash
# Deploy function code
cd azure
zip -r /tmp/function-app.zip function_app.py host.json requirements.txt index.html
az functionapp deployment source config-zip \
  --resource-group green-roof \
  --name green-roof \
  --src /tmp/function-app.zip \
  --build-remote true

# Restart function app
az functionapp restart --name green-roof --resource-group green-roof

# Check function status
az functionapp show --name green-roof --resource-group green-roof --query "properties.state"

# Query table storage (last 5 readings)
az storage entity query --table-name SensorReadings --account-name greenroof --num-results 5

# Test API endpoint
curl "https://green-roof.azurewebsites.net/api/sensor-data"

# Test with time range filter (hours parameter)
curl "https://green-roof.azurewebsites.net/api/sensor-data?hours=24"

# Deploy static website (index.html to blob storage)
az storage blob upload --account-name greenroof --container-name '$web' \
  --name index.html --file azure/index.html --overwrite --content-type "text/html"
```

### Azure Function Analytics Features
The function provides advanced analytics in GET responses:

- **Basic Analytics:** Min/max/avg/std for soil temp, moisture, IR temp
- **Trend Analysis:** Hourly statistics for last 12 hours
- **Anomaly Detection:** Z-score based detection with severity levels
- **Predictive Watering:** Moisture depletion rate, hours until critical
- **Heat Stress Analysis:** Leaf vs soil temperature differential
- **Growing Degree Days (GDD):** Accumulated heat units for growth tracking
- **Insights:** Human-readable recommendations based on sensor data
- **Time Range Filter:** `?hours=N` parameter to filter data (6, 24, 168, 720)

### GET Query Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| hours | int | Filter data to last N hours (e.g., 24, 168 for week, 720 for month) |
| limit | int | Maximum number of readings to return (default 500) |

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

### Deploy Azure Function
```bash
cd azure
zip -r /tmp/function-app.zip function_app.py host.json requirements.txt index.html
az functionapp deployment source config-zip \
  --resource-group green-roof \
  --name green-roof \
  --src /tmp/function-app.zip \
  --build-remote true
```

## Configuration (`config.py`)

### Key Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `WIFI_SSID` / `WIFI_PASSWORD` | -- | Network credentials (2.4GHz only) |
| `UPLOAD_URL` | -- | Azure Function POST endpoint with function key |
| `VERSION` / `SOFTWARE_DATE` | 3.0 / 2025-01-01 | Firmware version info |
| `LOG_INTERVAL` | 30 | Seconds between sensor readings |
| `UPLOAD_INTERVAL` | 300 | Seconds between cloud uploads (5 min) |

### Sensor Enable Flags
| Flag | Default | Sensor |
|------|---------|--------|
| `ENABLE_RAINFALL` | True | DFRobot SEN0575 tipping bucket |
| `ENABLE_MLX90614` | True | IR temperature (×2 on separate I2C buses) |
| `ENABLE_DS18B20` | True | Soil temperature (×3 on separate GPIO pins) |
| `ENABLE_SOIL_MOISTURE` | True | Capacitive moisture (×3 on ADC pins) |

### I2C Bus Configuration
| Bus | SCL Pin | SDA Pin | Devices |
|-----|---------|---------|---------|
| I2C0 | GPIO 1 | GPIO 0 | Rainfall (0x1D), MLX90614 #1 (0x5A) |
| I2C1 | GPIO 3 | GPIO 2 | MLX90614 #2 (0x5A) |

### Sensor Pin Assignments
| Sensor | Pin(s) | Interface |
|--------|--------|-----------|
| DS18B20 #1 | GPIO 16 | OneWire |
| DS18B20 #2 | GPIO 17 | OneWire |
| DS18B20 #3 | GPIO 18 | OneWire |
| Soil Moisture #1 | GPIO 26 (ADC0) | Analog |
| Soil Moisture #2 | GPIO 27 (ADC1) | Analog |
| Soil Moisture #3 | GPIO 28 (ADC2) | Analog |

### Soil Moisture Calibration
```python
SOIL_MOISTURE_DRY = 65535   # ADC value in air (dry)
SOIL_MOISTURE_WET = 20000   # ADC value in water (wet)
```
To calibrate: measure raw ADC value with sensor in air and in water, update these values.

### Static IP (Optional)
```python
USE_STATIC_IP = True
STATIC_IP = "192.168.1.97"
SUBNET_MASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS_SERVER = "8.8.8.8"
```

### Debug Modes
- `SENSOR_DEBUG_MODE = True` - Print sensor readings to serial console
- `UPLOAD_DEBUG_MODE = True` - Print upload payloads and responses

### Alert Thresholds
| Category | Setting | Value | Description |
|----------|---------|-------|-------------|
| Soil Moisture | `SOIL_DRY` | 30% | Below = needs watering |
| Soil Moisture | `SOIL_WET` | 70% | Above = saturated |
| Soil Temp | `SOIL_TEMP_COLD` | 10°C | Too cold for plants |
| Soil Temp | `SOIL_TEMP_OPTIMAL_LOW/HIGH` | 18-24°C | Optimal range |
| Soil Temp | `SOIL_TEMP_HOT` | 30°C | Too hot |
| Rainfall | `RAINFALL_LIGHT` | 2.5 mm/hr | Light rain |
| Rainfall | `RAINFALL_MODERATE` | 7.5 mm/hr | Moderate rain |
| Rainfall | `RAINFALL_HEAVY` | 15 mm/hr | Heavy rain |

## Main Loop Behavior (`main.py`)

The Pico runs a continuous loop with these intervals:
- **50ms** - Check for incoming web requests (select timeout)
- **1 second** - LED heartbeat toggle, network health check
- **30 seconds** (LOG_INTERVAL) - Read all sensors, log to CSV
- **5 minutes** (300s) - Upload data to Azure cloud

### Automatic Recovery
- 3 initialization attempts on startup, then hard reset
- Socket recovery on connection errors (ECONNABORTED, EBADF)
- Hard reset after 10 consecutive main loop errors
- Watchdog timer optional (8 second timeout)

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

### POST Request (from Pico)
```json
{
  "deviceId": "pico-001",
  "timestamp": 1703423400,
  "version": "3.0",
  "softwareDate": "2025-01-15",
  "sensors": {
    "soilTemperature1": 22.3,
    "soilTemperature2": 22.6,
    "soilTemperature3": 22.6,
    "soilMoisture1": 45.2,
    "soilMoisture2": 48.1,
    "soilMoisture3": 43.7,
    "irTemperature1": 24.1,
    "irTemperature2": 23.8,
    "rainfallTotal": 12.5,
    "rainfallHourly": 0.5
  }
}
```

### GET Response (from Azure)
```json
{
  "live": {
    "soil_temp_c": 22.5,
    "soil_temp_1_c": 22.3,
    "soil_temp_2_c": 22.6,
    "soil_temp_3_c": 22.6,
    "soil_moisture": 45.7,
    "soil_moisture_1": 45.2,
    "soil_moisture_2": 48.1,
    "soil_moisture_3": 43.7,
    "ir_object_temp_c": 24.0,
    "ir_temp_1_c": 24.1,
    "ir_temp_2_c": 23.8,
    "rainfall_total": 12.5,
    "rainfall_hourly": 0.5
  },
  "status": {
    "rainfall_available": true,
    "mlx90614_available": true,
    "mlx90614_2_available": false,
    "ds18b20_available": true,
    "ds18b20_2_available": false,
    "ds18b20_3_available": false,
    "soil_moisture_available": true,
    "soil_moisture_2_available": false,
    "soil_moisture_3_available": false
  },
  "analytics": {
    "soil_temp": { "avg": 23.9, "min": 23.7, "max": 24.2, "std": 0.11, "trend": "rising" },
    "soil_moisture": { "avg": 24.5, "min": 24.2, "max": 25.1, "std": 0.19, "trend": "stable" },
    "ir_temp": { "avg": 24.6, "min": 24.3, "max": 25.0, "std": 0.18, "trend": "rising" },
    "rainfall": { "total": 0.0, "avg": 0.0, "max": 0.0, "rainy_readings": 0 }
  },
  "advanced_analytics": {
    "predictive_watering": {
      "current_moisture": 24.6,
      "depletion_rate": -0.024,
      "hours_until_critical": 72.5,
      "watering_urgency": "low",
      "recommendation": "Moisture levels adequate - continue monitoring"
    },
    "heat_stress": {
      "current_status": "normal",
      "current_difference": 0.5,
      "stress_events_count": 0
    },
    "growing_degree_days": {
      "base_temperature": 10.0,
      "total_gdd": 13.9,
      "growth_stage_estimate": { "stage": "Dormant/Early", "progress": 27 }
    }
  },
  "insights": [
    { "type": "warning", "icon": "💧", "title": "Low Soil Moisture", "message": "..." }
  ],
  "anomalies": [],
  "history": { "timestamps": [...], "soil_temps": [...], "soil_moistures": [...] },
  "readings_count": 50,
  "last_updated": "2025-12-24T11:01:41.872766"
}
```

## Troubleshooting

### Pico W Issues
| Issue | Solution |
|-------|----------|
| WiFi not connecting | Check credentials in config.py, verify network is 2.4GHz |
| Sensor reading "None" | Check wiring, verify I2C/OneWire addresses, check enable flags |
| Dashboard not loading | Verify Pico IP, check for memory issues in serial output |
| Cloud upload failing | Verify UPLOAD_URL includes function key, check Azure Function logs |
| Memory errors | Reduce CHART_HISTORY_POINTS, enable WATCHDOG, check for sensor failures |
| Sensors 2/3 showing 0 | Physical sensors not connected to GPIO pins (16,17,18 for DS18B20; 26,27,28 for moisture) |
| No I2C devices found | Check wiring (SDA/SCL), verify pull-up resistors, check I2C address |
| Pico keeps resetting | Reduce upload frequency, check power supply, enable WATCHDOG debug |
| Static IP not working | Verify USE_STATIC_IP = True, check gateway/subnet match your network |
| WebREPL not connecting | Set WEBREPL_ENABLED = True, check WEBREPL_PASSWORD in config |

### Device ID
The Pico generates a unique device ID from its hardware ID on boot:
```python
unique_id_bytes = machine.unique_id()
DEVICE_ID = binascii.hexlify(unique_id_bytes).decode('utf-8').upper()
# Example: E6614103E72B5C2E
```
This ID is used as the PartitionKey in Azure Table Storage.

### Azure Function Issues
| Issue | Solution |
|-------|----------|
| "Function host is not running" (503) | Redeploy the function zip with `--build-remote true`, wait for cold start |
| No data in Table Storage | Check POST endpoint, verify AzureWebJobsStorage connection string |
| CORS errors | OPTIONS endpoint handles preflight, check Access-Control headers |
| Analytics returning null | Need at least 3-5 readings in table for analytics to compute |
| Linux Consumption cold start | First request after idle may take 10-30s, subsequent requests are fast |
| Weather widget shows error | Replace `YOUR_OPENWEATHERMAP_API_KEY` with valid API key in index.html |
| Time range not updating charts | Check browser console for JS errors, verify `hours` param in API response |

## Cloud Dashboard Features (azure/index.html)

### OpenWeatherMap Integration
The dashboard integrates with OpenWeatherMap API for weather correlation:

- **Location:** Zip code 02115 (Boston area)
- **API Key:** Set `WEATHER_API_KEY` constant in index.html (line ~558)
- **Data Shown:** Temperature, feels like, humidity, wind, pressure, visibility
- **Refresh Rate:** Every 10 minutes

### Weather API Configuration
```javascript
const WEATHER_API_KEY = 'your_api_key_here'; // Get from openweathermap.org
const WEATHER_ZIP = '02115';
const WEATHER_COUNTRY = 'US';
```

### Sensor vs Weather Correlation
The dashboard shows real-time comparisons:
- **Surface vs Air:** IR sensor temp vs ambient weather temp
- **Soil vs Air:** Soil temp vs ambient weather temp
- **Soil vs Air Humidity:** Soil moisture vs atmospheric humidity
- **Recent Rain:** Weather station rainfall data

### Dashboard UI Features
- **Time Range Selector:** 6 Hours, 24 Hours, Week, Month, All Data
- **CSV Export:** Download all sensor history as CSV file
- **Offline Indicator:** Banner shows when device hasn't reported in 10+ minutes
- **About Modal:** Project info, creator credits, tech stack details
- **Tabbed Interface:** Dashboard and Analytics & Intelligence tabs
- **Chart Toggle:** Switch between average and individual sensor views

## Important Files for Common Changes

- **WiFi/Network:** `config.py`, `web_server.py`
- **Sensor readings:** `agri_sensors.py`, `sensor_manager.py`
- **Dashboard UI:** `web_template.py` (Pico local), `azure/index.html` (cloud)
- **Data storage:** `data_logger.py`
- **Cloud integration:** `uploader.py`, `azure/function_app.py`
- **System health:** `system_monitor.py`, `memory_handler.py`
