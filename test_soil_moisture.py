# test_soil_moisture.py - Simple Capacitive Soil Moisture Sensor Test
# Copy this file to your Pico W and run it to test soil moisture sensors

import machine
import time

# Pin configuration - matches config.py defaults
MOISTURE_PINS = [26, 27, 28]  # ADC pins for sensors 1, 2, 3

# Calibration values - adjust these based on your sensors!
# Measure raw ADC value with sensor in air (dry) and in water (wet)
DRY_VALUE = 65535   # ADC reading when sensor is dry (in air)
WET_VALUE = 20000   # ADC reading when sensor is in water

print("=" * 50)
print("Capacitive Soil Moisture Sensor Test")
print("=" * 50)
print()
print(f"Calibration: DRY={DRY_VALUE}, WET={WET_VALUE}")
print("Adjust these values based on your sensor readings")
print()

# Initialize ADC for each sensor
sensors = []
for i, pin_num in enumerate(MOISTURE_PINS):
    print(f"Initializing sensor {i+1} on ADC pin GPIO {pin_num}...")
    try:
        adc = machine.ADC(machine.Pin(pin_num))
        sensors.append({'pin': pin_num, 'adc': adc, 'num': i+1})
        print(f"  Sensor {i+1} ready")
    except Exception as e:
        print(f"  Error on GPIO {pin_num}: {e}")

print()

def raw_to_percent(raw_value):
    """Convert raw ADC value to moisture percentage"""
    # Clamp to calibration range
    if raw_value >= DRY_VALUE:
        return 0.0
    if raw_value <= WET_VALUE:
        return 100.0
    # Linear interpolation
    percent = (DRY_VALUE - raw_value) / (DRY_VALUE - WET_VALUE) * 100
    return round(percent, 1)

if not sensors:
    print("No sensors initialized! Check wiring:")
    print("  - Signal wire to GPIO 26, 27, or 28")
    print("  - VCC to 3.3V")
    print("  - GND to GND")
else:
    print(f"Initialized {len(sensors)} sensor(s). Starting continuous readings...")
    print("Press Ctrl+C to stop")
    print()
    print("TIP: Note the RAW values when sensor is:")
    print("  - In air (dry) -> use as DRY_VALUE")
    print("  - In water (wet) -> use as WET_VALUE")
    print()

    try:
        while True:
            print("-" * 50)
            print(f"Time: {time.localtime()[:6]}")
            print()

            for sensor in sensors:
                try:
                    raw = sensor['adc'].read_u16()
                    percent = raw_to_percent(raw)

                    # Status indicator
                    if percent < 30:
                        status = "DRY"
                    elif percent > 70:
                        status = "WET"
                    else:
                        status = "OK"

                    print(f"  Sensor {sensor['num']} (GPIO {sensor['pin']}): {percent:5.1f}%  [RAW: {raw:5d}]  ({status})")
                except Exception as e:
                    print(f"  Sensor {sensor['num']} (GPIO {sensor['pin']}): Error - {e}")

            print()
            time.sleep(1)  # Read every second

    except KeyboardInterrupt:
        print("\nTest stopped by user")
p