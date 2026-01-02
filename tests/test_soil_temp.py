# test_soil_temp.py - Simple DS18B20 Soil Temperature Sensor Test
# Copy this file to your Pico W and run it to test soil temperature sensors

import machine
import onewire
import ds18x20
import time

# Pin configuration - matches config.py defaults
DS18B20_PINS = [16, 17, 18]  # GPIO pins for sensors 1, 2, 3

print("=" * 50)
print("DS18B20 Soil Temperature Sensor Test")
print("=" * 50)
print()

# Store sensor objects
sensors = []

# Initialize each sensor on its own pin
for i, pin_num in enumerate(DS18B20_PINS):
    print(f"Initializing sensor {i+1} on GPIO {pin_num}...")
    try:
        pin = machine.Pin(pin_num)
        ow = onewire.OneWire(pin)
        ds = ds18x20.DS18X20(ow)
        roms = ds.scan()

        if roms:
            print(f"  Found {len(roms)} device(s): {[rom.hex() for rom in roms]}")
            sensors.append({'pin': pin_num, 'ds': ds, 'roms': roms, 'num': i+1, 'ow': ow})
        else:
            print(f"  No sensor found on GPIO {pin_num}")
    except Exception as e:
        print(f"  Error on GPIO {pin_num}: {e}")

print()

if not sensors:
    print("No sensors found! Check wiring:")
    print("  - Data wire to GPIO 16, 17, or 18")
    print("  - VCC to 3.3V")
    print("  - GND to GND")
    print("  - 4.7k ohm pull-up resistor between Data and VCC")
else:
    print(f"Found {len(sensors)} sensor(s). Starting continuous readings...")
    print("Press Ctrl+C to stop")
    print()
    print("If you see CRC errors, check:")
    print("  1. Pull-up resistor (4.7k between Data and 3.3V)")
    print("  2. Wire connections (loose wires cause CRC errors)")
    print("  3. Wire length (try shorter wires or stronger pull-up)")
    print()

    def read_temp_with_retry(ds, rom, retries=3):
        """Try to read temperature with retries on CRC error"""
        for attempt in range(retries):
            try:
                ds.convert_temp()
                time.sleep_ms(750)
                temp = ds.read_temp(rom)
                return temp, None
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep_ms(100)  # Brief pause before retry
                else:
                    return None, str(e)
        return None, "Max retries"

    try:
        while True:
            print("-" * 40)
            print(f"Time: {time.localtime()[:6]}")

            for sensor in sensors:
                for rom in sensor['roms']:
                    temp_c, error = read_temp_with_retry(sensor['ds'], rom)
                    if temp_c is not None:
                        temp_f = temp_c * 9/5 + 32
                        print(f"  Sensor {sensor['num']} (GPIO {sensor['pin']}): {temp_c:.2f}°C / {temp_f:.2f}°F")
                    else:
                        print(f"  Sensor {sensor['num']} (GPIO {sensor['pin']}): Error - {error}")

            print()
            time.sleep(2)  # Wait 2 seconds between readings

    except KeyboardInterrupt:
        print("\nTest stopped by user")
