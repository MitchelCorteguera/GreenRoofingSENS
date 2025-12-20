# config.py - Configuration for Agricultural Sensor Monitor
# Sensors: Rainfall, MLX90614 IR Temp, DS18B20 Soil Temp, Soil Moisture

import machine
import binascii

# Unique Device ID
unique_id_bytes = machine.unique_id()
unique_id_hex = binascii.hexlify(unique_id_bytes).decode('utf-8').upper()
DEVICE_ID = f"{unique_id_hex}"

print(f"[Config] Device ID: {DEVICE_ID}")

# ============== WiFi Settings ==============
WIFI_SSID = 'SSID'
WIFI_PASSWORD = 'password'

WIFI_MAX_ATTEMPTS = 10
WIFI_CONNECT_TIMEOUT = 30
WIFI_RETRY_DELAY = 5
WIFI_INIT_DELAY = 2
NTP_MAX_ATTEMPTS = 7
NETWORK_CHECK_INTERVAL = 60
RECONNECT_DELAY_BASE = 5

# Static IP (set USE_STATIC_IP = True to enable)
USE_STATIC_IP = False
STATIC_IP = "192.168.1.97"
SUBNET_MASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS_SERVER = "8.8.8.8"

# ============== Data Upload Settings ==============
UPLOAD_URL = "https://your-function-app.azurewebsites.net/api/sensor-data"
UPLOAD_DEBUG_MODE = True
UPLOAD_RESPONSE_TIMEOUT = 10

# Software version
VERSION = "3.0"
SOFTWARE_DATE = "2025-01-01"

# ============== I2C Configuration ==============
# I2C Bus 0 - Rainfall sensor + MLX90614 #1
I2C_SCL_PIN = 1
I2C_SDA_PIN = 0
I2C_FREQUENCY = 100000

# I2C Bus 1 - MLX90614 #2 (solo)
I2C1_SCL_PIN = 3
I2C1_SDA_PIN = 2
I2C1_FREQUENCY = 100000

# ============== Sensor Enable Flags ==============
ENABLE_RAINFALL = True        # DFRobot rainfall sensor
ENABLE_MLX90614 = True        # Infrared temperature sensor
ENABLE_DS18B20 = True         # Soil temperature sensor (OneWire)
ENABLE_SOIL_MOISTURE = True   # Soil moisture sensor (Analog)

# ============== Rainfall Sensor Settings (SEN0575) ==============
RAINFALL_I2C_ADDR = 0x1D
RAINFALL_HOURS_TO_TRACK = 1   # Hours for cumulative rainfall reading

# ============== IR Temperature Sensor Settings (MLX90614) ==============
MLX90614_I2C_ADDR = 0x5A
MLX90614_TA_REG = 0x06        # Ambient temperature register
MLX90614_TOBJ1_REG = 0x07     # Object temperature register

# ============== Soil Temperature Sensor Settings (DS18B20) ==============
DS18B20_PIN = 16              # OneWire data pin for sensor 1
DS18B20_PIN_2 = 17            # OneWire data pin for sensor 2
DS18B20_PIN_3 = 18            # OneWire data pin for sensor 3
DS18B20_CONVERSION_DELAY = 750  # ms to wait for temperature conversion

# ============== Soil Moisture Sensor Settings ==============
SOIL_MOISTURE_PIN = 26        # ADC pin (ADC0 = GP26) - Sensor 1
SOIL_MOISTURE_PIN_2 = 27      # ADC pin (ADC1 = GP27) - Sensor 2
SOIL_MOISTURE_PIN_3 = 28      # ADC pin (ADC2 = GP28) - Sensor 3
# Calibration values - adjust based on your sensor!
# Measure raw value when dry and when in water, then set these:
SOIL_MOISTURE_DRY = 65535     # ADC value when completely dry (air)
SOIL_MOISTURE_WET = 20000     # ADC value when in water

# ============== Alert Thresholds ==============
# Soil moisture thresholds (percentage)
SOIL_DRY = 30                 # Below this = needs watering
SOIL_WET = 70                 # Above this = saturated

# Soil temperature thresholds (Celsius)
SOIL_TEMP_COLD = 10           # Too cold for most plants
SOIL_TEMP_OPTIMAL_LOW = 18    # Optimal range start
SOIL_TEMP_OPTIMAL_HIGH = 24   # Optimal range end
SOIL_TEMP_HOT = 30            # Too hot

# IR temperature thresholds
IR_TEMP_LOW = 15              # Low leaf temperature
IR_TEMP_HIGH = 35             # High leaf temperature (stress)

# Rainfall thresholds (mm per hour)
RAINFALL_LIGHT = 2.5          # Light rain
RAINFALL_MODERATE = 7.5       # Moderate rain
RAINFALL_HEAVY = 15           # Heavy rain

# ============== Sensor Validation Ranges ==============
VALID_SOIL_MOISTURE_RANGE = (0, 100)    # Percentage
VALID_SOIL_TEMP_RANGE = (-20, 60)       # Celsius
VALID_RAINFALL_RANGE = (0, 500)         # mm
VALID_IR_TEMP_RANGE = (-40, 125)        # MLX90614 range

# ============== Error Handling ==============
MAX_CONSECUTIVE_ERRORS = 3
SENSOR_RETRY_DELAY = 1
SENSOR_RESET_DELAY = 2
MAX_RECOVERY_ATTEMPTS = 3

# ============== Memory Management ==============
MEMORY_WARNING_THRESHOLD = 75
MEMORY_CRITICAL_THRESHOLD = 85
GC_COLLECT_INTERVAL = 60

STORAGE_WARNING_THRESHOLD = 80
STORAGE_CRITICAL_THRESHOLD = 90

# ============== Logging Settings ==============
LOG_INTERVAL = 30             # 30 seconds between logs
LOG_DIRECTORY = '/logs'
SENSOR_LOG_FILE = 'sensor_log.txt'
NETWORK_LOG_FILE = 'network.log'
ERROR_LOG_FILE = 'error.log'
MAX_LOG_SIZE = 1024 * 50      # 50KB max log size
MAX_LOG_FILES = 3

CHART_HISTORY_POINTS = 24     # Reduced for memory conservation

# ============== Time Settings ==============
NTP_SERVER = 'time.google.com'
TIMEZONE_OFFSET = -5          # EST = -5, adjust for your location
NTP_SYNC_INTERVAL = 6 * 3600  # Sync every 6 hours

# ============== Web Server Settings ==============
WEB_SERVER_PORT = 80
ALLOWED_ENDPOINTS = ['/', '/csv', '/json', '/api/data', '/api/history', '/test.html', '/sensors']

MAX_REQUESTS_PER_MINUTE = 60
BLOCKED_IPS_TIMEOUT = 300
WEBREPL_ENABLED = True
WEBREPL_PASSWORD = "webrepl"

LOW_POWER_MODE_ENABLED = False
SLEEP_WHEN_IDLE = False
SLEEP_DURATION = 1000

WATCHDOG_ENABLED = False
WATCHDOG_TIMEOUT = 8000

# ============== Debug Settings ==============
SENSOR_DEBUG_MODE = False      # Enable detailed sensor debugging
