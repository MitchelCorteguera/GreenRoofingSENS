# test_rainfall.py - Simple DFRobot SEN0575 Rainfall Sensor Test
# Copy this file to your Pico W and run it to test the rainfall sensor

import machine
import time
import struct

# I2C Configuration - matches config.py defaults
# Rainfall sensor on I2C Bus 0: GPIO 0 (SDA), GPIO 1 (SCL)
I2C_SDA = 0
I2C_SCL = 1
RAINFALL_ADDR = 0x1D

# Register addresses for SEN0575
REG_PID = 0x00           # Product ID
REG_VID = 0x02           # Version ID
REG_RAIN_HOUR = 0x0A     # Rainfall in last hour (mm)
REG_RAIN_DAY = 0x0C      # Rainfall today (mm)
REG_RAW_DATA = 0x10      # Raw tip count
REG_SYS_TIME = 0x04      # System time

print("=" * 50)
print("DFRobot SEN0575 Rainfall Sensor Test")
print("=" * 50)
print()

def read_register(i2c, reg, length=2):
    """Read data from sensor register"""
    try:
        data = i2c.readfrom_mem(RAINFALL_ADDR, reg, length)
        return data
    except Exception as e:
        return None

def read_float(i2c, reg):
    """Read 4-byte float from register"""
    try:
        data = i2c.readfrom_mem(RAINFALL_ADDR, reg, 4)
        return struct.unpack('<f', data)[0]
    except Exception as e:
        return None

def read_uint32(i2c, reg):
    """Read 4-byte unsigned int from register"""
    try:
        data = i2c.readfrom_mem(RAINFALL_ADDR, reg, 4)
        return struct.unpack('<I', data)[0]
    except Exception as e:
        return None

# Initialize I2C
print(f"Initializing I2C on SDA=GPIO{I2C_SDA}, SCL=GPIO{I2C_SCL}...")
try:
    i2c = machine.I2C(0,
                     sda=machine.Pin(I2C_SDA),
                     scl=machine.Pin(I2C_SCL),
                     freq=100000)
    devices = i2c.scan()
    print(f"  Found devices: {['0x{:02X}'.format(d) for d in devices]}")
except Exception as e:
    print(f"  I2C Error: {e}")
    devices = []

print()

sensor_found = RAINFALL_ADDR in devices

if not sensor_found:
    print("No rainfall sensor found at address 0x1D!")
    print()
    print("Check wiring:")
    print("  - SDA to GPIO 0")
    print("  - SCL to GPIO 1")
    print("  - VCC to 3.3V (or 5V if sensor supports it)")
    print("  - GND to GND")
    print()
    print("Note: The SEN0575 may need 5V power but 3.3V I2C logic")
else:
    # Read sensor info
    print("Sensor found! Reading sensor info...")
    pid = read_register(i2c, REG_PID, 2)
    vid = read_register(i2c, REG_VID, 2)
    if pid:
        print(f"  Product ID: 0x{pid[0]:02X}{pid[1]:02X}")
    if vid:
        print(f"  Version ID: 0x{vid[0]:02X}{vid[1]:02X}")

    print()
    print("Starting continuous readings...")
    print("Press Ctrl+C to stop")
    print()
    print("Tip: Trigger the tipping bucket to see values change")
    print()

    try:
        while True:
            print("-" * 50)
            print(f"Time: {time.localtime()[:6]}")
            print()

            # Read rainfall values
            rain_hour = read_float(i2c, REG_RAIN_HOUR)
            rain_day = read_float(i2c, REG_RAIN_DAY)
            raw_tips = read_uint32(i2c, REG_RAW_DATA)
            sys_time = read_uint32(i2c, REG_SYS_TIME)

            if rain_hour is not None:
                print(f"  Rainfall (1 hour):  {rain_hour:.2f} mm")
            else:
                print(f"  Rainfall (1 hour):  Read error")

            if rain_day is not None:
                print(f"  Rainfall (today):   {rain_day:.2f} mm")
            else:
                print(f"  Rainfall (today):   Read error")

            if raw_tips is not None:
                print(f"  Raw tip count:      {raw_tips}")
            else:
                print(f"  Raw tip count:      Read error")

            if sys_time is not None:
                print(f"  Sensor uptime:      {sys_time} seconds")

            print()
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nTest stopped by user")
