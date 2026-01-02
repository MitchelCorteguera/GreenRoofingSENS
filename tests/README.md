# Sensor Test Scripts

Simple test scripts for debugging and verifying individual sensors on the Raspberry Pi Pico W. Use these to test each sensor independently before running the full GreenRoofingSENS firmware.

**Important:** Do NOT copy this `tests/` folder to the Pico or rename it to `utils/` - the firmware has a `utils.py` module that would be shadowed.

## Available Tests

| Script | Sensor | Interface | Description |
|--------|--------|-----------|-------------|
| `test_soil_temp.py` | DS18B20 | OneWire | Soil temperature probes (3x) |
| `test_soil_moisture.py` | Capacitive | ADC | Soil moisture sensors (3x) |
| `test_ir_temp.py` | MLX90614 | I2C | Infrared temperature sensors (2x) |
| `test_rainfall.py` | DFRobot SEN0575 | I2C | Tipping bucket rainfall sensor |

## How to Use

### 1. Copy test file to Pico W
```bash
# Using mpremote
mpremote cp tests/test_soil_temp.py :

# Or copy all tests
mpremote cp tests/test_*.py :
```

### 2. Run the test
```bash
mpremote run test_soil_temp.py
```

Or use Thonny: Open the file and click Run.

### 3. Press Ctrl+C to stop

---

## Test Details

### test_soil_temp.py - DS18B20 Soil Temperature

**Pins:** GPIO 16, 17, 18 (OneWire)

**What it does:**
- Scans each GPIO pin for DS18B20 sensors
- Displays ROM addresses of found sensors
- Reads temperature every 2 seconds in °C and °F
- Includes retry logic for CRC errors

**Wiring:**
```
DS18B20          Pico W
-------          ------
VCC (red)   -->  3.3V
GND (black) -->  GND
Data (yellow) -> GPIO 16/17/18
                 + 4.7k pull-up to 3.3V
```

**Troubleshooting CRC errors:**
- Add/check 4.7k ohm pull-up resistor between Data and 3.3V
- Use shorter wires or stronger pull-up (2.2k-3.3k)
- Check for loose connections

---

### test_soil_moisture.py - Capacitive Soil Moisture

**Pins:** GPIO 26, 27, 28 (ADC)

**What it does:**
- Reads raw ADC values from each sensor
- Converts to percentage using calibration values
- Shows status: DRY (<30%), OK (30-70%), WET (>70%)
- Updates every second

**Wiring:**
```
Moisture Sensor   Pico W
---------------   ------
VCC          -->  3.3V
GND          -->  GND
Signal       -->  GPIO 26/27/28
```

**Calibration:**
1. Note the RAW value when sensor is in air (dry)
2. Note the RAW value when sensor is in water (wet)
3. Update `DRY_VALUE` and `WET_VALUE` in the script
4. Copy calibrated values to `config.py`:
   ```python
   SOIL_MOISTURE_DRY = <your dry value>
   SOIL_MOISTURE_WET = <your wet value>
   ```

---

### test_ir_temp.py - MLX90614 IR Temperature

**Pins:**
- IR Sensor 1: I2C0 (SDA=GPIO 0, SCL=GPIO 1)
- IR Sensor 2: I2C1 (SDA=GPIO 2, SCL=GPIO 3)

**What it does:**
- Scans both I2C buses for MLX90614 sensors (address 0x5A)
- Reads ambient temperature (sensor's internal temp)
- Reads object temperature (what the sensor is pointed at)
- Displays in both °C and °F
- Updates every 2 seconds with delays to prevent read errors

**Wiring:**
```
MLX90614 #1       Pico W
-----------       ------
VCC          -->  3.3V
GND          -->  GND
SDA          -->  GPIO 0
SCL          -->  GPIO 1

MLX90614 #2       Pico W
-----------       ------
VCC          -->  3.3V
GND          -->  GND
SDA          -->  GPIO 2
SCL          -->  GPIO 3
```

---

### test_rainfall.py - DFRobot SEN0575 Rainfall Sensor

**Pins:** I2C0 (SDA=GPIO 0, SCL=GPIO 1)

**What it does:**
- Scans I2C bus for sensor at address 0x1D
- Reads product/version ID
- Displays rainfall in last hour (mm)
- Displays rainfall today (mm)
- Shows raw tip count (useful for debugging)
- Shows sensor uptime
- Updates every 2 seconds

**Wiring:**
```
SEN0575           Pico W
-------           ------
VCC          -->  3.3V (or 5V)
GND          -->  GND
SDA          -->  GPIO 0
SCL          -->  GPIO 1
```

**Note:** The SEN0575 may require 5V power but uses 3.3V logic levels for I2C.

---

## Pin Reference Summary

| Sensor | Pin(s) | Interface |
|--------|--------|-----------|
| DS18B20 #1 | GPIO 16 | OneWire |
| DS18B20 #2 | GPIO 17 | OneWire |
| DS18B20 #3 | GPIO 18 | OneWire |
| Soil Moisture #1 | GPIO 26 (ADC0) | Analog |
| Soil Moisture #2 | GPIO 27 (ADC1) | Analog |
| Soil Moisture #3 | GPIO 28 (ADC2) | Analog |
| MLX90614 #1 | GPIO 0 (SDA), GPIO 1 (SCL) | I2C0 |
| MLX90614 #2 | GPIO 2 (SDA), GPIO 3 (SCL) | I2C1 |
| Rainfall SEN0575 | GPIO 0 (SDA), GPIO 1 (SCL) | I2C0 |

---

## Common Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| "No sensor found" | Wiring issue | Check VCC, GND, data connections |
| CRC errors (DS18B20) | Missing pull-up | Add 4.7k resistor between Data and 3.3V |
| Read errors (I2C) | Reading too fast | Tests include delays; check wiring |
| Wrong moisture % | Needs calibration | Measure dry/wet RAW values, update config |
| Rainfall always 0 | Sensor not triggered | Manually tip the bucket to test |
