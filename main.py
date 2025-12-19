# main.py - Agricultural Sensor Monitor
# Sensors: Rainfall, MLX90614 IR Temp, DS18B20 Soil Temp, Soil Moisture

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
from utils import NetworkLogger, SecurityManager, feed_watchdog
from memory_handler import MemoryHandler
from uploader import upload_data_to_server


def initialize_system():
    """Initialize all components"""
    for attempt in range(3):
        try:
            print(f"\n{'='*50}")
            print(f"[System] Initializing (attempt {attempt + 1}/3)...")
            print(f"{'='*50}")
            gc.collect()
            
            # Logger
            print("[System] Creating logger...")
            logger = NetworkLogger()
            
            # I2C bus for Rainfall and MLX90614
            print(f"[System] Setting up I2C (SCL={config.I2C_SCL_PIN}, SDA={config.I2C_SDA_PIN})...")
            i2c = I2C(0, scl=Pin(config.I2C_SCL_PIN), sda=Pin(config.I2C_SDA_PIN), freq=config.I2C_FREQUENCY)
            
            devices = i2c.scan()
            print(f"[System] I2C devices found: {[hex(d) for d in devices]}")
            
            # System monitor
            print("[System] Creating system monitor...")
            monitor = SystemMonitor(logger)
            
            # Sensors
            print("\n[System] Initializing sensors...")
            sensor_manager = SensorManager(i2c, monitor, logger)
            
            # Data logging
            print("\n[System] Setting up data logging...")
            data_logger = DataLogger(monitor, logger)
            
            # Memory handler
            memory_handler = MemoryHandler(logger)
            memory_handler.register_component('data_logger', data_logger)

            # Web server
            print("\n[System] Creating web server...")
            web_server = WebServer(monitor, sensor_manager, data_logger, logger)

            print(f"[System] Connecting to WiFi: {config.WIFI_SSID}")
            if not web_server.connect_wifi(config.WIFI_SSID, config.WIFI_PASSWORD):
                raise Exception("WiFi connection failed")
            
            if not web_server.initialize_server(config.WEB_SERVER_PORT):
                raise Exception("Web server failed to start")

            print(f"\n{'='*50}")
            print("[System] ✓ All systems ready!")
            print(f"[System] ✓ Dashboard: http://{web_server.ip_address}")
            print(f"{'='*50}\n")
            
            gc.collect()
            
            return {
                'led': Pin("LED", Pin.OUT),
                'web_server': web_server,
                'sensor_manager': sensor_manager,
                'data_logger': data_logger,
                'logger': logger,
                'security_manager': SecurityManager(logger),
                'memory_handler': memory_handler
            }
            
        except Exception as e:
            print(f"[System] ✗ Failed: {e}")
            if attempt < 2:
                print("[System] Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("[System] ✗ All attempts failed. Restarting...")
                time.sleep(10)
                reset()


def main():
    try:
        components = initialize_system()
        web_server = components['web_server']
        
        # Generate and cache HTML
        html_shell = create_html(config)
        web_server.set_html_shell(html_shell)
        html_shell = None
        gc.collect()

        print("Main loop started. Press Ctrl+C to stop.\n")

        last_log_time = time.time()
        last_blink_time = time.time()
        consecutive_errors = 0

        while True:
            try:
                if config.WATCHDOG_ENABLED:
                    feed_watchdog()

                # Handle web requests
                try:
                    r, _, _ = select.select([web_server.socket], [], [], 0.1)
                    
                    if r:
                        client, addr = web_server.socket.accept()
                        if components['security_manager'].validate_request(addr[0]):
                            web_server.handle_request(client)
                        else:
                            client.close()
                    
                    consecutive_errors = 0
                    
                except OSError as e:
                    consecutive_errors += 1
                    if "ECONNABORTED" in str(e) or "EBADF" in str(e):
                        web_server.recover_socket()
                    time.sleep(1)
                        
                except Exception as e:
                    consecutive_errors += 1
                    time.sleep(1)
                
                if consecutive_errors > 10:
                    print("[Main] Too many errors, restarting...")
                    reset()

            except Exception as e:
                print(f"[Main] Error: {e}")
                time.sleep(2)

            # Periodic tasks
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
                    rainfall_mm, rainfall_hourly, ir_obj_c, ir_obj_f, ir_amb_c, soil_temp_c, soil_temp_f, soil_moisture = readings
                    
                    # Get individual soil temperature readings
                    readings_dict = components['sensor_manager'].get_readings_dict()
                    soil_temp_1_c = readings_dict.get('soil_temp_1_c', soil_temp_c)
                    soil_temp_2_c = readings_dict.get('soil_temp_2_c', soil_temp_c)
                    soil_temp_3_c = readings_dict.get('soil_temp_3_c', soil_temp_c)
                    
                    # Log to file with individual sensor data
                    components['data_logger'].log_data(
                        soil_temp_c, soil_moisture, ir_obj_c, 
                        rainfall_mm, rainfall_hourly,
                        soil_temp_1_c, soil_temp_2_c, soil_temp_3_c
                    )
                    last_log_time = current_time

                    # Upload to server (using average temperature)
                    upload_data = {
                        "soil_temp_c": soil_temp_c,  # Average temperature
                        "soil_moisture": soil_moisture,
                        "ir_temp_c": ir_obj_c,
                        "rainfall_mm": rainfall_mm,
                        "rainfall_hourly": rainfall_hourly
                    }
                    upload_data_to_server(upload_data)
                    
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