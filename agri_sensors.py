# agri_sensors.py - Agricultural Sensor Drivers
# Sensors: Rainfall, MLX90614, DS18B20, Soil Moisture

import time
from machine import Pin, ADC, I2C
import config


class RainfallSensor:
    """Driver for DFRobot Rainfall Sensor SEN0575"""
    
    REG_PID = 0x00
    REG_VID = 0x02
    REG_TIME_RAINFALL = 0x0C
    REG_CUMULATIVE_RAINFALL = 0x10
    REG_RAW_DATA = 0x14
    REG_SYS_TIME = 0x18
    REG_RAW_RAIN_HOUR = 0x26
    
    def __init__(self, i2c, addr=None):
        self.i2c = i2c
        self.addr = addr or config.RAINFALL_I2C_ADDR
        self.available = False
        self._init_sensor()
    
    def _init_sensor(self):
        try:
            if self._verify_sensor():
                self.available = True
                print("[Rainfall] ✓ Sensor initialized")
                return True
            print("[Rainfall] ✗ Sensor verification failed")
            return False
        except Exception as e:
            print(f"[Rainfall] ✗ Init error: {e}")
            return False
    
    def _verify_sensor(self):
        try:
            data = self._read_register(self.REG_PID, 4)
            pid = data[0] | (data[1] << 8) | ((data[3] & 0xC0) << 10)
            vid = data[2] | ((data[3] & 0x3F) << 8)
            return vid == 0x3343 and pid == 0x100C0
        except:
            return False
    
    def _read_register(self, reg, length):
        try:
            return self.i2c.readfrom_mem(self.addr, reg, length)
        except:
            return bytearray(length)
    
    def _write_register(self, reg, data):
        try:
            if isinstance(data, int):
                data = bytes([data])
            self.i2c.writeto_mem(self.addr, reg, data)
            time.sleep(0.05)
            return True
        except:
            return False
    
    def get_cumulative_rainfall(self):
        """Get total rainfall since power on (mm)"""
        if not self.available:
            return 0.0
        try:
            data = self._read_register(self.REG_CUMULATIVE_RAINFALL, 4)
            raw = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
            return raw / 10000.0
        except:
            return 0.0
    
    def get_rainfall_hour(self, hours=1):
        """Get rainfall for specified hours (1-24)"""
        if not self.available or hours > 24:
            return 0.0
        try:
            self._write_register(self.REG_RAW_RAIN_HOUR, hours)
            data = self._read_register(self.REG_TIME_RAINFALL, 4)
            raw = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
            return raw / 10000.0
        except:
            return 0.0
    
    def is_available(self):
        return self.available


class MLX90614:
    """Driver for MLX90614 IR Temperature Sensor"""
    
    def __init__(self, i2c, addr=None):
        self.i2c = i2c
        self.addr = addr or config.MLX90614_I2C_ADDR
        self.available = False
        self._init_sensor()
    
    def _init_sensor(self):
        try:
            temp = self._read_temp(config.MLX90614_TA_REG)
            if temp is not None and -40 <= temp <= 125:
                self.available = True
                print(f"[MLX90614] ✓ Initialized (ambient: {temp:.1f}°C)")
                return True
            print("[MLX90614] ✗ Invalid reading")
            return False
        except Exception as e:
            print(f"[MLX90614] ✗ Init error: {e}")
            return False
    
    def _read_temp(self, register):
        try:
            data = self.i2c.readfrom_mem(self.addr, register, 3)
            temp_raw = (data[1] << 8) | data[0]
            return (temp_raw * 0.02) - 273.15
        except:
            return None
    
    @property
    def object_temp(self):
        """Get object/target temperature (°C)"""
        return self._read_temp(config.MLX90614_TOBJ1_REG)
    
    @property
    def ambient_temp(self):
        """Get ambient temperature (°C)"""
        return self._read_temp(config.MLX90614_TA_REG)
    
    def is_available(self):
        return self.available


class DS18B20:
    """Driver for DS18B20 OneWire Temperature Sensor"""
    
    def __init__(self, pin=None):
        self.pin = pin or config.DS18B20_PIN
        self.available = False
        self.ds = None
        self.roms = []
        self._init_sensor()
    
    def _init_sensor(self):
        try:
            import onewire
            import ds18x20
            
            ow = onewire.OneWire(Pin(self.pin))
            self.ds = ds18x20.DS18X20(ow)
            self.roms = self.ds.scan()
            
            if self.roms:
                self.available = True
                print(f"[DS18B20] ✓ Found {len(self.roms)} sensor(s) on pin {self.pin}")
                return True
            else:
                print(f"[DS18B20] ✗ No sensors found on pin {self.pin}")
                return False
        except Exception as e:
            print(f"[DS18B20] ✗ Init error on pin {self.pin}: {e}")
            return False
    
    def get_temperature(self, index=0):
        """Get temperature (°C) from sensor"""
        if not self.available or index >= len(self.roms):
            return None
        try:
            self.ds.convert_temp()
            time.sleep_ms(config.DS18B20_CONVERSION_DELAY)
            return self.ds.read_temp(self.roms[index])
        except:
            return None
    
    def is_available(self):
        return self.available


class MultiDS18B20:
    """Manager for multiple DS18B20 sensors on different pins"""
    
    def __init__(self):
        self.sensors = []
        self.available = False
        self._init_sensors()
    
    def _init_sensors(self):
        """Initialize all three DS18B20 sensors"""
        pins = [config.DS18B20_PIN, config.DS18B20_PIN_2, config.DS18B20_PIN_3]
        
        print("\n[MultiDS18B20] Initializing soil temperature sensors...")
        for i, pin in enumerate(pins, 1):
            try:
                sensor = DS18B20(pin)
                self.sensors.append(sensor)
                if sensor.is_available():
                    print(f"  Sensor {i} (GPIO {pin}): ✓ Online")
                else:
                    print(f"  Sensor {i} (GPIO {pin}): ✗ Offline")
            except Exception as e:
                print(f"  Sensor {i} (GPIO {pin}): ✗ Error: {e}")
                self.sensors.append(None)
        
        # Check if at least one sensor is available
        self.available = any(s and s.is_available() for s in self.sensors)
        print(f"[MultiDS18B20] Overall status: {'✓ Ready' if self.available else '✗ No sensors available'}")
    
    def get_temperatures(self):
        """Get temperatures from all sensors
        
        Returns:
            tuple: (temp1, temp2, temp3, average) in Celsius
        """
        temps = []
        valid_temps = []
        
        for sensor in self.sensors:
            if sensor and sensor.is_available():
                temp = sensor.get_temperature()
                temps.append(temp)
                if temp is not None:
                    valid_temps.append(temp)
            else:
                temps.append(None)
        
        # Calculate average from valid readings
        if valid_temps:
            average = sum(valid_temps) / len(valid_temps)
        else:
            average = None
        
        return temps[0], temps[1], temps[2], average
    
    def get_sensor_status(self):
        """Get status of each sensor"""
        return [
            sensor.is_available() if sensor else False 
            for sensor in self.sensors
        ]
    
    def is_available(self):
        """Check if at least one sensor is available"""
        return self.available


class SoilMoisture:
    """Driver for analog soil moisture sensor"""
    
    def __init__(self, pin=None):
        self.pin = pin or config.SOIL_MOISTURE_PIN
        self.adc = None
        self.available = False
        self._init_sensor()
    
    def _init_sensor(self):
        try:
            self.adc = ADC(Pin(self.pin))
            # Test read
            val = self.adc.read_u16()
            self.available = True
            print(f"[SoilMoisture] ✓ Initialized (raw: {val})")
            return True
        except Exception as e:
            print(f"[SoilMoisture] ✗ Init error: {e}")
            return False
    
    def get_raw_value(self):
        """Get raw ADC value (0-65535)"""
        if not self.available:
            return 0
        try:
            return self.adc.read_u16()
        except:
            return 0
    
    def get_percentage(self):
        """Get moisture as percentage (0-100%)"""
        raw = self.get_raw_value()
        dry = config.SOIL_MOISTURE_DRY
        wet = config.SOIL_MOISTURE_WET
        
        if raw >= dry:
            return 0.0
        if raw <= wet:
            return 100.0
        
        percentage = ((dry - raw) / (dry - wet)) * 100
        return round(max(0, min(100, percentage)), 1)
    
    def is_available(self):
        return self.available