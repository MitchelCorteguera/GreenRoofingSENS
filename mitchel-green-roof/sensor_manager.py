# sensor_manager.py - Manages the 4 agricultural sensors
# Sensors: Rainfall, MLX90614, DS18B20, Soil Moisture

import time
from machine import I2C, Pin
import config
from agri_sensors import RainfallSensor, MLX90614, DS18B20, MultiDS18B20, SoilMoisture

class SensorManager:
    """Manages all agricultural sensors"""
    
    def __init__(self, i2c, monitor, logger):
        """Initialize sensor manager
        
        Args:
            i2c: I2C bus for Rainfall and MLX90614 sensors
            monitor: System monitor for tracking
            logger: Logger for events
        """
        self.i2c = i2c
        self.monitor = monitor
        self.logger = logger
        
        # Sensor instances
        self.rainfall = None
        self.mlx90614 = None
        self.ds18b20 = None  # Now will be MultiDS18B20
        self.soil_moisture = None
        
        # Error tracking
        self.consecutive_errors = 0
        self.last_successful_read = 0
        self.min_read_interval = 2  # Minimum seconds between reads
        
        # Last good readings (defaults)
        self.last_good_reading = {
            'rainfall_mm': 0.0,
            'rainfall_hourly': 0.0,
            'ir_object_temp_c': 20.0,
            'ir_object_temp_f': 68.0,
            'ir_ambient_temp_c': 20.0,
            'soil_temp_c': 18.0,  # Average
            'soil_temp_f': 64.4,  # Average
            'soil_temp_1_c': 18.0,
            'soil_temp_2_c': 18.0,
            'soil_temp_3_c': 18.0,
            'soil_moisture': 50.0
        }
        
        # Initialize all sensors
        self._initialize_sensors()
    
    def _initialize_sensors(self):
        """Initialize all 4 sensors"""
        print("\n[Sensors] Initializing agricultural sensors...")
        print("-" * 40)
        
        # Rainfall Sensor (I2C)
        if config.ENABLE_RAINFALL:
            try:
                self.rainfall = RainfallSensor(self.i2c)
            except Exception as e:
                self.logger.log("SENSOR", f"Rainfall init failed: {e}", "ERROR")
        
        # MLX90614 IR Temperature (I2C)
        if config.ENABLE_MLX90614:
            try:
                self.mlx90614 = MLX90614(self.i2c)
            except Exception as e:
                self.logger.log("SENSOR", f"MLX90614 init failed: {e}", "ERROR")
        
        # DS18B20 Soil Temperature (OneWire) - now multiple sensors
        if config.ENABLE_DS18B20:
            try:
                self.ds18b20 = MultiDS18B20()
            except Exception as e:
                self.logger.log("SENSOR", f"MultiDS18B20 init failed: {e}", "ERROR")
        
        # Soil Moisture (Analog)
        if config.ENABLE_SOIL_MOISTURE:
            try:
                self.soil_moisture = SoilMoisture()
            except Exception as e:
                self.logger.log("SENSOR", f"Soil moisture init failed: {e}", "ERROR")
        
        print("-" * 40)
        self._print_status()
    
    def _print_status(self):
        """Print sensor status summary"""
        print("[Sensors] Status:")
        print(f"  Rainfall:      {'✓' if self.rainfall and self.rainfall.is_available() else '✗'}")
        print(f"  IR Temp:       {'✓' if self.mlx90614 and self.mlx90614.is_available() else '✗'}")
        print(f"  Soil Temp:     {'✓' if self.ds18b20 and self.ds18b20.is_available() else '✗'}")
        print(f"  Soil Moisture: {'✓' if self.soil_moisture and self.soil_moisture.is_available() else '✗'}")
    
    def get_readings(self):
        """Get readings from all sensors
        
        Returns:
            tuple: (rainfall_mm, rainfall_hourly, ir_obj_c, ir_obj_f, 
                    ir_amb_c, soil_temp_c, soil_temp_f, soil_moisture)
        """
        current_time = time.time()
        
        # Rate limiting
        if current_time - self.last_successful_read < self.min_read_interval:
            return self._format_readings(self.last_good_reading)
        
        readings = dict(self.last_good_reading)
        
        # Rainfall sensor
        if self.rainfall and self.rainfall.is_available():
            try:
                readings['rainfall_mm'] = self.rainfall.get_cumulative_rainfall()
                readings['rainfall_hourly'] = self.rainfall.get_rainfall_hour(config.RAINFALL_HOURS_TO_TRACK)
            except Exception as e:
                self.logger.log("SENSOR", f"Rainfall read error: {e}", "WARNING")
        
        # IR Temperature sensor
        if self.mlx90614 and self.mlx90614.is_available():
            try:
                obj_c = self.mlx90614.object_temp
                amb_c = self.mlx90614.ambient_temp
                if obj_c is not None:
                    readings['ir_object_temp_c'] = round(obj_c, 1)
                    readings['ir_object_temp_f'] = round((obj_c * 9/5) + 32, 1)
                if amb_c is not None:
                    readings['ir_ambient_temp_c'] = round(amb_c, 1)
            except Exception as e:
                self.logger.log("SENSOR", f"MLX90614 read error: {e}", "WARNING")
        
        # Soil Temperature sensors (multiple)
        if self.ds18b20 and self.ds18b20.is_available():
            try:
                temp1, temp2, temp3, avg_temp = self.ds18b20.get_temperatures()
                
                # Store individual readings
                if temp1 is not None:
                    readings['soil_temp_1_c'] = round(temp1, 1)
                if temp2 is not None:
                    readings['soil_temp_2_c'] = round(temp2, 1)
                if temp3 is not None:
                    readings['soil_temp_3_c'] = round(temp3, 1)
                
                # Store average
                if avg_temp is not None:
                    readings['soil_temp_c'] = round(avg_temp, 1)
                    readings['soil_temp_f'] = round((avg_temp * 9/5) + 32, 1)
            except Exception as e:
                self.logger.log("SENSOR", f"MultiDS18B20 read error: {e}", "WARNING")
        
        # Soil Moisture sensor
        if self.soil_moisture and self.soil_moisture.is_available():
            try:
                readings['soil_moisture'] = self.soil_moisture.get_percentage()
            except Exception as e:
                self.logger.log("SENSOR", f"Soil moisture read error: {e}", "WARNING")
        
        # Update tracking
        self.last_good_reading.update(readings)
        self.last_successful_read = current_time
        self.consecutive_errors = 0
        
        return self._format_readings(readings)
    
    def _format_readings(self, readings):
        """Format readings as tuple"""
        return (
            readings.get('rainfall_mm', 0.0),
            readings.get('rainfall_hourly', 0.0),
            readings.get('ir_object_temp_c', 0.0),
            readings.get('ir_object_temp_f', 32.0),
            readings.get('ir_ambient_temp_c', 0.0),
            readings.get('soil_temp_c', 0.0),
            readings.get('soil_temp_f', 32.0),
            readings.get('soil_moisture', 0.0)
        )
    
    def get_readings_dict(self):
        """Get readings as dictionary"""
        r = self.get_readings()
        return {
            'rainfall_mm': r[0],
            'rainfall_hourly': r[1],
            'ir_object_temp_c': r[2],
            'ir_object_temp_f': r[3],
            'ir_ambient_temp_c': r[4],
            'soil_temp_c': r[5],  # Average
            'soil_temp_f': r[6],  # Average
            'soil_moisture': r[7],
            'soil_temp_1_c': self.last_good_reading.get('soil_temp_1_c', 0.0),
            'soil_temp_2_c': self.last_good_reading.get('soil_temp_2_c', 0.0),
            'soil_temp_3_c': self.last_good_reading.get('soil_temp_3_c', 0.0)
        }
    
    def get_status(self):
        """Get sensor status"""
        return {
            'rainfall_available': self.rainfall.is_available() if self.rainfall else False,
            'mlx90614_available': self.mlx90614.is_available() if self.mlx90614 else False,
            'ds18b20_available': self.ds18b20.is_available() if self.ds18b20 else False,
            'soil_moisture_available': self.soil_moisture.is_available() if self.soil_moisture else False,
            'consecutive_errors': self.consecutive_errors,
            'last_reading': self.last_good_reading,
            'last_success': self.last_successful_read
        }
    
    def clear_caches(self):
        """Clear caches for memory recovery"""
        return True