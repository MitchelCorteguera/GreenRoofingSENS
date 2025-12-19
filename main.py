import time
import gc
import select
from machine import I2C, Pin, reset

from web_server import WebServer
from system_monitor import SystemMonitor
from sensor_manager import SensorManager
from data_logger import DataLogger
import config
from web_template import create_html
from utils import NetworkLogger, feed_watchdog
from memory_handler import MemoryHandler
from uploader import upload_data_to_server


def initialize_system():
    """Initialize all components"""
    for attempt in range(3):
        try:
            print(f"[System] Initializing (attempt {attempt + 1}/3)...")
            gc.collect()
            
            logger = NetworkLogger()
            i2c = I2C(0, scl=Pin(config.I2C_SCL_PIN), sda=Pin(config.I2C_SDA_PIN), freq=config.I2C_FREQUENCY)
            i2c1 = I2C(1, scl=Pin(config.I2C1_SCL_PIN), sda=Pin(config.I2C1_SDA_PIN), freq=config.I2C1_FREQUENCY)
            print(f"[System] I2C0 devices: {[hex(d) for d in i2c.scan()]}")
            print(f"[System] I2C1 devices: {[hex(d) for d in i2c1.scan()]}")
            
            monitor = SystemMonitor(logger)
            sensor_manager = SensorManager(i2c, i2c1, monitor, logger)
            data_logger = DataLogger(monitor, logger)
            
            memory_handler = MemoryHandler(logger)
            memory_handler.register_component('data_logger', data_logger)

            web_server = WebServer(monitor, sensor_manager, data_logger, logger)

            if not web_server.connect_wifi(config.WIFI_SSID, config.WIFI_PASSWORD):
                raise Exception("WiFi connection failed")
            
            if not web_server.initialize_server(config.WEB_SERVER_PORT):
                raise Exception("Web server failed to start")

            print(f"[System] ✓ Ready! Dashboard: http://{web_server.ip_address}")
            gc.collect()
            
            return {
                'led': Pin("LED", Pin.OUT),
                'web_server': web_server,
                'sensor_manager': sensor_manager,
                'data_logger': data_logger,
                'logger': logger,
                'memory_handler': memory_handler
            }
            
        except Exception as e:
            print(f"[System] ✗ Failed: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                print("[System] ✗ Restarting...")
                time.sleep(10)
                reset()


def main():
    try:
        components = initialize_system()
        web_server = components['web_server']
        
        web_server.set_html_shell(create_html(config))
        print(f"[Main] HTML template loaded, size: {len(web_server.html_shell)} chars")
        gc.collect()

        print("Main loop started. Press Ctrl+C to stop.")

        last_log_time = time.time()
        last_blink_time = time.time()
        last_upload_time = time.time()
        consecutive_errors = 0

        while True:
            if config.WATCHDOG_ENABLED:
                feed_watchdog()

            # Handle web requests
            try:
                r, _, _ = select.select([web_server.socket], [], [], 0.05)  # Shorter timeout
                
                if r:
                    client, addr = web_server.socket.accept()
                    web_server.handle_request(client)
                    gc.collect()  # Free memory after handling a request
                
                consecutive_errors = 0
                
            except OSError as e:
                consecutive_errors += 1
                if "ECONNABORTED" in str(e) or "EBADF" in str(e):
                    web_server.recover_socket()
                time.sleep(1)
                    
            except Exception:
                consecutive_errors += 1
                time.sleep(1)
            
            if consecutive_errors > 10:
                print("[Main] Too many errors, restarting...")
                reset()

            current_time = time.time()

            # LED heartbeat
            if current_time - last_blink_time > 1:
                components['led'].toggle()
                last_blink_time = current_time
                web_server.check_network_connection()

            # Data logging
            if current_time - last_log_time >= config.LOG_INTERVAL:
                try:
                    readings = components['sensor_manager'].get_readings()
                    rainfall_mm, rainfall_hourly, ir_obj_c, _, _, soil_temp_c, _, soil_moisture = readings
                    
                    readings_dict = components['sensor_manager'].get_readings_dict()
                    sensor_status = components['sensor_manager'].get_status()
                    
                    # Debug output if enabled
                    if getattr(config, 'SENSOR_DEBUG_MODE', False):
                        print("\n[DEBUG] ===== SENSOR READINGS =====")
                        print(f"[DEBUG] Rainfall: {rainfall_hourly:.2f} mm/hr (Total: {rainfall_mm:.2f} mm) - {'ONLINE' if sensor_status.get('rainfall_available', False) else 'OFFLINE'}")
                        print(f"[DEBUG] IR Temp #1: {ir_obj_c:.1f}°C - {'ONLINE' if sensor_status.get('mlx90614_available', False) else 'OFFLINE'}")
                        print(f"[DEBUG] IR Temp #2: {readings_dict.get('ir_object_temp_2_c', 0):.1f}°C - {'ONLINE' if sensor_status.get('mlx90614_2_available', False) else 'OFFLINE'}")
                        print(f"[DEBUG] Soil Temp #1: {readings_dict.get('soil_temp_1_c', 0):.1f}°C - {'ONLINE' if sensor_status.get('ds18b20_available', False) else 'OFFLINE'}")
                        print(f"[DEBUG] Soil Temp #2: {readings_dict.get('soil_temp_2_c', 0):.1f}°C - {'ONLINE' if sensor_status.get('ds18b20_2_available', False) else 'OFFLINE'}")
                        print(f"[DEBUG] Soil Temp #3: {readings_dict.get('soil_temp_3_c', 0):.1f}°C - {'ONLINE' if sensor_status.get('ds18b20_3_available', False) else 'OFFLINE'}")
                        print(f"[DEBUG] Soil Moisture #1: {soil_moisture:.1f}% - {'ONLINE' if sensor_status.get('soil_moisture_available', False) else 'OFFLINE'}")
                        print(f"[DEBUG] Soil Moisture #2: {readings_dict.get('soil_moisture_2', 0):.1f}% - {'ONLINE' if sensor_status.get('soil_moisture_2_available', False) else 'OFFLINE'}")
                        print(f"[DEBUG] Soil Moisture #3: {readings_dict.get('soil_moisture_3', 0):.1f}% - {'ONLINE' if sensor_status.get('soil_moisture_3_available', False) else 'OFFLINE'}")
                        print("[DEBUG] ==============================\n")
                    
                    soil_temp_1_c = readings_dict.get('soil_temp_1_c', soil_temp_c)
                    soil_temp_2_c = readings_dict.get('soil_temp_2_c', soil_temp_c)
                    soil_temp_3_c = readings_dict.get('soil_temp_3_c', soil_temp_c)
                    soil_moisture_2 = readings_dict.get('soil_moisture_2', soil_moisture)
                    soil_moisture_3 = readings_dict.get('soil_moisture_3', soil_moisture)
                    ir_temp_2_c = readings_dict.get('ir_object_temp_2_c', ir_obj_c)
                    
                    components['data_logger'].log_data(
                        soil_temp_c, soil_moisture, ir_obj_c, 
                        rainfall_mm, rainfall_hourly,
                        soil_temp_1_c, soil_temp_2_c, soil_temp_3_c,
                        soil_moisture_2, soil_moisture_3, ir_temp_2_c
                    )
                    last_log_time = current_time

                    # Upload data periodically
                    if current_time - last_upload_time >= 300: # 5 minutes
                        upload_data_to_server({
                            "soil_temp_c": soil_temp_c,
                            "soil_moisture": soil_moisture,
                            "ir_temp_c": ir_obj_c,
                            "rainfall_mm": rainfall_mm,
                            "rainfall_hourly": rainfall_hourly
                        })
                        last_upload_time = current_time
                    
                except Exception as e:
                    components['logger'].log('DATA', str(e), 'ERROR')

    except KeyboardInterrupt:
        print("\nShutdown requested.")
    except Exception as e:
        print(f"Fatal error: {e}")
        time.sleep(10)
        reset()
    finally:
        if 'components' in locals():
            if 'web_server' in components:
                components['web_server'].shutdown()
            if 'led' in components:
                components['led'].off()
        print("Server stopped.")


if __name__ == "__main__":
    main()