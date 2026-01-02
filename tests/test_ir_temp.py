# test_ir_temp.py - Simple MLX90614 IR Temperature Sensor Test
# Copy this file to your Pico W and run it to test IR temperature sensors

import machine
import time

# I2C Configuration - matches config.py defaults
# I2C Bus 0: GPIO 0 (SDA), GPIO 1 (SCL) - IR Sensor 1
# I2C Bus 1: GPIO 2 (SDA), GPIO 3 (SCL) - IR Sensor 2
I2C_CONFIGS = [
    {'bus': 0, 'sda': 0, 'scl': 1, 'name': 'IR Sensor 1'},
    {'bus': 1, 'sda': 2, 'scl': 3, 'name': 'IR Sensor 2'},
]

MLX90614_ADDR = 0x5A
MLX90614_TA_REG = 0x06    # Ambient temperature register
MLX90614_TOBJ1_REG = 0x07 # Object temperature register

print("=" * 50)
print("MLX90614 IR Temperature Sensor Test")
print("=" * 50)
print()

def read_temp(i2c, reg):
    """Read temperature from MLX90614 register"""
    try:
        data = i2c.readfrom_mem(MLX90614_ADDR, reg, 3)
        raw = data[0] | (data[1] << 8)
        temp_k = raw * 0.02  # Convert to Kelvin
        temp_c = temp_k - 273.15  # Convert to Celsius
        return temp_c
    except Exception as e:
        return None

# Initialize I2C buses and scan for sensors
sensors = []
for config in I2C_CONFIGS:
    print(f"Initializing {config['name']} on I2C{config['bus']} (SDA={config['sda']}, SCL={config['scl']})...")
    try:
        i2c = machine.I2C(config['bus'],
                         sda=machine.Pin(config['sda']),
                         scl=machine.Pin(config['scl']),
                         freq=100000)
        devices = i2c.scan()

        if MLX90614_ADDR in devices:
            print(f"  Found MLX90614 at address 0x{MLX90614_ADDR:02X}")
            sensors.append({'i2c': i2c, 'name': config['name'], 'bus': config['bus']})
        else:
            print(f"  No MLX90614 found (devices: {['0x{:02X}'.format(d) for d in devices]})")
    except Exception as e:
        print(f"  Error: {e}")

print()

if not sensors:
    print("No MLX90614 sensors found! Check wiring:")
    print("  IR Sensor 1:")
    print("    - SDA to GPIO 0")
    print("    - SCL to GPIO 1")
    print("    - VCC to 3.3V")
    print("    - GND to GND")
    print()
    print("  IR Sensor 2:")
    print("    - SDA to GPIO 2")
    print("    - SCL to GPIO 3")
    print("    - VCC to 3.3V")
    print("    - GND to GND")
else:
    print(f"Found {len(sensors)} sensor(s). Starting continuous readings...")
    print("Press Ctrl+C to stop")
    print()
    print("Ambient = sensor's internal temp")
    print("Object  = temperature of what sensor is pointed at")
    print()

    try:
        while True:
            print("-" * 50)
            print(f"Time: {time.localtime()[:6]}")
            print()

            for sensor in sensors:
                # Small delay before reading each sensor
                time.sleep_ms(50)

                ambient_c = read_temp(sensor['i2c'], MLX90614_TA_REG)
                time.sleep_ms(10)  # Brief pause between register reads
                object_c = read_temp(sensor['i2c'], MLX90614_TOBJ1_REG)

                if ambient_c is not None and object_c is not None:
                    ambient_f = ambient_c * 9/5 + 32
                    object_f = object_c * 9/5 + 32
                    print(f"  {sensor['name']} (I2C{sensor['bus']}):")
                    print(f"    Ambient: {ambient_c:.2f}°C / {ambient_f:.2f}°F")
                    print(f"    Object:  {object_c:.2f}°C / {object_f:.2f}°F")
                else:
                    print(f"  {sensor['name']} (I2C{sensor['bus']}): Read error")

            print()
            time.sleep(2)  # Increased from 1 to 2 seconds

    except KeyboardInterrupt:
        print("\nTest stopped by user")

