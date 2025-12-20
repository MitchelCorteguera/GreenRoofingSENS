# GreenRoofingSENS

Field-ready, battery/solar-friendly MicroPython firmware for tracking green-roof performance: rainfall vs. drainage, moisture at three points, and surface temperatures of pavement vs. green roof. It logs locally, serves a real-time web dashboard, and can uplink JSON to a cloud endpoint.

## What it does
- Reads **DFRobot tipping-bucket rainfall** (SEN0575), **three capacitive soil moisture probes**, **three DS18B20 soil temperature probes**, and **two MLX90614 IR temperature** sensors.
- Serves a lightweight dashboard with live values, history charts, CSV/JSON downloads, and status indicators at `http://<pico-ip>/`.
- Logs to `/logs/sensor_log.txt` with auto-rotation and exposes an upload hook to `UPLOAD_URL` for remote collection.
- Protects the RP2040 with watchdog hooks, memory/health monitoring, and Wi‑Fi reconnection/recovery.

## Hardware at a glance
- Board: Raspberry Pi Pico W (MicroPython)
- Rainfall: DFRobot SEN0575 (I²C, addr `0x1D`)
- IR temp: MLX90614 (two devices, default addr `0x5A`)
- Soil temp: 3× DS18B20 (OneWire)
- Soil moisture: 3× capacitive analog probes

### Default pin map (see `config.py`)
| Sensor | Pins |
| --- | --- |
| Rainfall (I²C0) + MLX90614 #1 | SCL `GP1`, SDA `GP0`, 100 kHz |
| MLX90614 #2 (I²C1) | SCL `GP3`, SDA `GP2`, 100 kHz |
| DS18B20 soil temps | `GP16`, `GP17`, `GP18` |
| Soil moisture probes | ADC `GP26`, `GP27`, `GP28` |
| Status LED | Onboard `LED` |

## Repo layout
- `main.py` – boots services, loops on logging/upload/LED heartbeat
- `sensor_manager.py` + `agri_sensors.py` – drivers and orchestration for rain, IR, soil temp, moisture
- `data_logger.py` – CSV log + in-memory history buffer for charts/downloads
- `web_server.py` + `web_template.py` – Wi‑Fi setup, HTTP endpoints, interactive dashboard (ApexCharts)
- `uploader.py` – optional JSON POST to `UPLOAD_URL`
- `system_monitor.py` / `memory_handler.py` / `utils.py` – watchdog, health checks, rotation, helpers
- `boot.py` – optional boot-time Wi‑Fi/time sync/WebREPL setup when run as `boot.py`

## Quick start (Pico W + MicroPython)
1) Flash MicroPython to the Pico W (v1.20+ recommended).  
2) Clone this repo locally.  
3) Edit `config.py`:
   - `WIFI_SSID` / `WIFI_PASSWORD` (or enable static IP)
   - `UPLOAD_URL` if you want cloud ingest; keep `UPLOAD_DEBUG_MODE=True` for serial feedback
   - Calibrate `SOIL_MOISTURE_DRY` / `SOIL_MOISTURE_WET` with your probes (dry in air, wet in water)
   - Adjust `LOG_INTERVAL` (seconds) and alert thresholds as needed
4) Copy the project files to the Pico (`boot.py` + `main.py` + modules) via Thonny or VS Code + PyMakr/mpremote.  
5) Reboot the board. Watch the serial console for Wi‑Fi IP; open the dashboard in your browser: `http://<that-ip>/`.

## Using the dashboard & API
- Dashboard: `/` – live cards for temperature/moisture/rainfall, per-sensor details, memory/uptime, and charts.
- Live data API: `/api/data` – JSON payload with latest readings, sensor availability, system stats, and recent history for charts.
- Downloads: `/csv` (sensor log with timestamps) and `/json` (same data as JSON file).
- Uplink: `uploader.py` posts a JSON body with IDs/version to `UPLOAD_URL` when Wi‑Fi is up (default every 5 minutes inside `main.py`).

## Configuration notes (`config.py`)
- Networking: retries, optional static IP, NTP host, and timezone offset.
- Sensors: enable/disable flags per sensor family and validation ranges to guard bogus readings.
- Thresholds: moisture (dry/wet), soil temp (cold/optimal/hot), rainfall intensity buckets, IR temp bands.
- Logging: log directory/name, max size, rotation count, and chart history depth (`CHART_HISTORY_POINTS`).
- Power/robustness: optional watchdog (`WATCHDOG_ENABLED`), GC intervals, and simple low-power toggles.

## Operating tips
- Moisture calibration matters: set `SOIL_MOISTURE_DRY`/`SOIL_MOISTURE_WET` per probe batch for accurate % values.
- If battery swaps are frequent, add a small solar panel + charge controller; firmware is already conservative on memory/CPU.
- Sensor placement: 3 moisture + 3 soil temp probes across the roof profile; rainfall bucket on pavement; IR sensors aimed at roof vs. green roof surface.
- If the dashboard stops responding after many client hits, rate limiting and socket recovery in `web_server.py` will attempt to self-heal; a power cycle remains the fastest reset.

## Roadmap ideas
- Decide and document maintenance cadence (cleaning debris from tipping bucket, seasonal recalibration).
- Optional OTA updates and MQTT/LoRa backhaul for off-grid deployments.

## License
Open source; choose a license in this repository to formalize reuse and contributions. In the meantime, credit the project if you fork or extend it.
