# data_logger.py - Data logging for 4 agricultural sensors
import time
import gc
import config
from utils import CircularBuffer, ensure_directory, feed_watchdog, format_datetime

class DataLogger:
    """Logs agricultural sensor data"""
    
    def __init__(self, monitor, logger, log_dir=config.LOG_DIRECTORY):
        self.monitor = monitor
        self.logger = logger
        self.log_dir = log_dir
        self.log_filename = f"{log_dir}/{config.SENSOR_LOG_FILE}"
        
        self.last_log_time = time.time()
        self.log_interval = config.LOG_INTERVAL
        self.data_history = CircularBuffer(config.CHART_HISTORY_POINTS)
        self.max_log_size = config.MAX_LOG_SIZE
        self.max_backup_files = config.MAX_LOG_FILES
        
        self._ensure_log_directory()
        self._ensure_log_file()
        self.load_history()
    
    def _ensure_log_directory(self):
        ensure_directory(self.log_dir)
    
    def _ensure_log_file(self):
        try:
            import os
            try:
                os.stat(self.log_filename)
            except OSError:
                with open(self.log_filename, 'w') as f:
                    f.write("DateTime,SoilTemp_C,SoilTemp1_C,SoilTemp2_C,SoilTemp3_C,SoilMoisture,IR_Temp_C,Rainfall_mm,Rainfall_hr\n")
                self.logger.log("LOGGER", f"Created log: {self.log_filename}", "INFO")
        except Exception as e:
            self.logger.log("LOGGER", f"Log file error: {e}", "ERROR")
    
    def _rotate_logs(self):
        try:
            import os
            try:
                size = os.stat(self.log_filename)[6]
                if size < self.max_log_size:
                    return False
            except:
                return False
            
            t = time.localtime()
            backup = f"{self.log_filename}.{t[0]}{t[1]:02d}{t[2]:02d}-{t[3]:02d}{t[4]:02d}"
            os.rename(self.log_filename, backup)
            self._ensure_log_file()
            return True
        except:
            return False
    
    def load_history(self):
        """Load recent history from log file"""
        feed_watchdog()
        gc.collect()
        
        try:
            import os
            try:
                os.stat(self.log_filename)
            except:
                return
            
            with open(self.log_filename, 'r') as f:
                f.readline()  # Skip header
                lines = []
                for line in f:
                    lines.append(line)
                    if len(lines) > config.CHART_HISTORY_POINTS:
                        lines.pop(0)
                
                for line in lines:
                    try:
                        if line.strip():
                            parts = line.strip().split(',')
                            if len(parts) >= 9:
                                # New format with individual sensors
                                self.data_history.append({
                                    'timestamp': parts[0],
                                    'soil_temp_c': float(parts[1]),  # Average
                                    'soil_temp_1_c': float(parts[2]),
                                    'soil_temp_2_c': float(parts[3]),
                                    'soil_temp_3_c': float(parts[4]),
                                    'soil_moisture': float(parts[5]),
                                    'ir_temp_c': float(parts[6]),
                                    'rainfall_mm': float(parts[7]),
                                    'rainfall_hourly': float(parts[8]),
                                })
                            elif len(parts) >= 6:
                                # Old format - use average for all sensors
                                avg_temp = float(parts[1])
                                self.data_history.append({
                                    'timestamp': parts[0],
                                    'soil_temp_c': avg_temp,
                                    'soil_temp_1_c': avg_temp,
                                    'soil_temp_2_c': avg_temp,
                                    'soil_temp_3_c': avg_temp,
                                    'soil_moisture': float(parts[2]),
                                    'ir_temp_c': float(parts[3]),
                                    'rainfall_mm': float(parts[4]),
                                    'rainfall_hourly': float(parts[5]),
                                })
                    except:
                        pass
            
            del lines
            gc.collect()
        except Exception as e:
            self.logger.log("LOGGER", f"Load history error: {e}", "ERROR")
    
    def log_data(self, soil_temp_c, soil_moisture, ir_temp_c, rainfall_mm, rainfall_hourly, 
                 soil_temp_1_c=None, soil_temp_2_c=None, soil_temp_3_c=None):
        """Log sensor data including individual soil temperature sensors"""
        current_time = time.time()
        
        if current_time - self.last_log_time < self.log_interval:
            return False
        
        gc.collect()
        
        try:
            self._rotate_logs()
            timestamp = format_datetime(time.localtime())
            
            # Use average for individual sensors if not provided (backward compatibility)
            if soil_temp_1_c is None:
                soil_temp_1_c = soil_temp_c
            if soil_temp_2_c is None:
                soil_temp_2_c = soil_temp_c
            if soil_temp_3_c is None:
                soil_temp_3_c = soil_temp_c
            
            data = {
                'timestamp': timestamp,
                'soil_temp_c': round(float(soil_temp_c or 0), 1),  # Average
                'soil_temp_1_c': round(float(soil_temp_1_c or 0), 1),
                'soil_temp_2_c': round(float(soil_temp_2_c or 0), 1),
                'soil_temp_3_c': round(float(soil_temp_3_c or 0), 1),
                'soil_moisture': round(float(soil_moisture or 0), 1),
                'ir_temp_c': round(float(ir_temp_c or 0), 1),
                'rainfall_mm': round(float(rainfall_mm or 0), 2),
                'rainfall_hourly': round(float(rainfall_hourly or 0), 2),
            }
            
            self.data_history.append(data)
            
            line = f"{timestamp},{data['soil_temp_c']},{data['soil_temp_1_c']},{data['soil_temp_2_c']},{data['soil_temp_3_c']},{data['soil_moisture']},{data['ir_temp_c']},{data['rainfall_mm']},{data['rainfall_hourly']}\n"
            with open(self.log_filename, 'a') as f:
                f.write(line)
            
            self.last_log_time = current_time
            gc.collect()
            
            self.logger.log("DATA", 
                f"Soil: {data['soil_temp_c']}°C/{data['soil_moisture']}%, Rain: {data['rainfall_hourly']}mm/hr", 
                "INFO")
            
            return True
        except Exception as e:
            self.logger.log("LOGGER", f"Log error: {e}", "ERROR")
            return False
    
    def get_history(self):
        return self.data_history.get_all()
    
    def emergency_memory_recovery(self):
        try:
            if len(self.data_history) > 10:
                temp = list(self.data_history)[-10:]
                self.data_history = CircularBuffer(10)
                for e in temp:
                    self.data_history.append(e)
                gc.collect()
                return True
            return False
        except:
            return False