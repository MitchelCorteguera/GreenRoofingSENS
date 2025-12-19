# web_server.py - Web server for 4 agricultural sensors
import network
import socket
import time
from machine import Pin, unique_id
import config
import gc
import os
import json
from web_template import send_chunked_html

def format_uptime(seconds):
    try:
        if seconds < 0: return "0m 0s"
        days, r = divmod(seconds, 86400)
        hours, r = divmod(r, 3600)
        minutes, seconds = divmod(r, 60)
        if days > 0: return f"{int(days)}d {int(hours)}h"
        elif hours > 0: return f"{int(hours)}h {int(minutes)}m"
        else: return f"{int(minutes)}m {int(seconds)}s"
    except: return "Error"

class WebServer:
    def __init__(self, monitor, sensor_manager, data_logger, logger):
        self.monitor = monitor
        self.sensor_manager = sensor_manager
        self.data_logger = data_logger
        self.logger = logger
        self.socket = None
        self.wlan = None
        self.ip_address = None
        self.html_shell = None
        self.last_network_check = 0
        self.reconnect_attempts = 0
        self.last_reconnect_time = 0
        self.port = 80

    def set_html_shell(self, html):
        self.html_shell = html

    def handle_api_data(self, client_socket):
        """Return all sensor data as JSON"""
        try:
            readings = self.sensor_manager.get_readings()
            system_stats = self.monitor.check_system_health()
            sensor_status = self.sensor_manager.get_status()
            readings_dict = self.sensor_manager.get_readings_dict()
            
            rainfall_mm, rainfall_hourly, ir_obj_c, ir_obj_f, ir_amb_c, soil_temp_c, soil_temp_f, soil_moisture = readings
            
            data = {
                # Sensor readings
                "rainfall_mm": round(rainfall_mm, 2),
                "rainfall_hourly": round(rainfall_hourly, 2),
                "ir_object_temp_c": round(ir_obj_c, 1),
                "ir_object_temp_f": round(ir_obj_f, 1),
                "ir_ambient_temp_c": round(ir_amb_c, 1),
                "soil_temp_c": round(soil_temp_c, 1),  # Average
                "soil_temp_f": round(soil_temp_f, 1),  # Average
                "soil_temp_1_c": round(readings_dict.get('soil_temp_1_c', 0), 1),
                "soil_temp_2_c": round(readings_dict.get('soil_temp_2_c', 0), 1),
                "soil_temp_3_c": round(readings_dict.get('soil_temp_3_c', 0), 1),
                "soil_moisture": round(soil_moisture, 1),
                
                # Sensor availability
                "rainfall_available": sensor_status.get('rainfall_available', False),
                "mlx90614_available": sensor_status.get('mlx90614_available', False),
                "ds18b20_available": sensor_status.get('ds18b20_available', False),
                "soil_moisture_available": sensor_status.get('soil_moisture_available', False),
                
                # System info
                "uptime_str": format_uptime(system_stats.get('uptime', 0)),
                "memory_percent": system_stats.get('memory_percent', 0),
                "memory_used_kb": system_stats.get('memory_used', 0) / 1024,
                "storage_percent": system_stats.get('storage_percent', 0),
                "device_id": config.DEVICE_ID,
                "device_model": os.uname().machine.split(' with')[0],
            }
            self.send_response(client_socket, json.dumps(data), content_type='application/json')
        except Exception as e:
            self.logger.log("API", f"Error: {e}", "ERROR")
            self.send_response(client_socket, '{"error":"API error"}', status_code=500)

    def handle_request(self, client_socket):
        """Handle incoming HTTP requests"""
        path = '/'
        try:
            client_socket.settimeout(5.0)
            request_bytes = client_socket.recv(1024)
            if not request_bytes:
                client_socket.close()
                return
            
            request = request_bytes.decode('utf-8')
            parts = request.split('\r\n')[0].split(' ')
            if len(parts) >= 2:
                path = parts[1]
            
            if path == '/':
                send_chunked_html(client_socket, self.html_shell)
            elif path == '/api/history':
                self.stream_api_history(client_socket)
            elif path == '/api/data':
                self.handle_api_data(client_socket)
            elif path in ['/csv', '/json']:
                self.handle_file_download(client_socket, path)
            elif path == '/test.html':
                self.handle_test_page(client_socket)
            elif path == '/sensors':
                self.handle_sensors_page(client_socket)
            else:
                self.send_response(client_socket, "<h1>404 Not Found</h1>", status_code=404)
        except Exception as e:
            self.logger.log("REQUEST", f"Error on '{path}': {e}", "WARNING")
        finally:
            try: client_socket.close()
            except: pass

    def stream_api_history(self, client_socket):
        """Stream history for charts"""
        gc.collect()
        try:
            history = self.data_logger.get_history()
            headers = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n"
            client_socket.sendall(headers.encode())
            
            response = {
                "timestamps": [e['timestamp'].split(' ')[1] if ' ' in e['timestamp'] else e['timestamp'] for e in history],
                "soil_temps": [round(e.get('soil_temp_c', 0), 1) for e in history],  # Average for backward compatibility
                "soil_temp_1": [round(e.get('soil_temp_1_c', e.get('soil_temp_c', 0)), 1) for e in history],
                "soil_temp_2": [round(e.get('soil_temp_2_c', e.get('soil_temp_c', 0)), 1) for e in history],
                "soil_temp_3": [round(e.get('soil_temp_3_c', e.get('soil_temp_c', 0)), 1) for e in history],
                "soil_moistures": [round(e.get('soil_moisture', 0), 1) for e in history],
                "rainfall": [round(e.get('rainfall_hourly', 0), 2) for e in history],
                "ir_temps": [round(e.get('ir_temp_c', 0), 1) for e in history],
            }
            client_socket.sendall(json.dumps(response).encode())
        except Exception as e:
            self.logger.log("API", f"History error: {e}", "ERROR")
        finally:
            try: client_socket.close()
            except: pass
            gc.collect()

    def connect_wifi(self, ssid, password, max_wait=30):
        """Connect to WiFi"""
        print(f"[WiFi] Connecting to '{ssid}'...")
        try:
            self.wlan = network.WLAN(network.STA_IF)
            self.wlan.active(True)
            time.sleep(1)
            
            if self.wlan.isconnected():
                self.ip_address = self.wlan.ifconfig()[0]
                print(f"[WiFi] ✓ Already connected: {self.ip_address}")
                return True
            
            self.wlan.connect(ssid, password)
            start = time.time()
            while time.time() - start < max_wait:
                if self.wlan.isconnected():
                    self.ip_address = self.wlan.ifconfig()[0]
                    print(f"\n[WiFi] ✓ Connected: {self.ip_address}")
                    return True
                print(".", end="")
                time.sleep(1)
            
            raise Exception("Connection timeout")
        except Exception as e:
            print(f"\n[WiFi] ✗ Failed: {e}")
            return False

    def initialize_server(self, port=80):
        """Start web server"""
        self.port = port
        if not self.wlan or not self.wlan.isconnected():
            return False
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', port))
            self.socket.listen(1)
            self.socket.setblocking(False)
            self.logger.log("SERVER", f"Started on port {port}", "INFO")
            return True
        except Exception as e:
            self.logger.log("SERVER", f"Init failed: {e}", "CRITICAL")
            return False

    def send_response(self, client_socket, content, status_code=200, content_type="text/html", headers=None):
        try:
            status = {200: "OK", 404: "Not Found", 500: "Error"}.get(status_code, "OK")
            h = [f"HTTP/1.1 {status_code} {status}", f"Content-Type: {content_type}", "Connection: close"]
            if headers:
                h.extend([f"{k}: {v}" for k, v in headers.items()])
            if not isinstance(content, bytes):
                content = content.encode()
            client_socket.sendall(("\r\n".join(h) + "\r\n\r\n").encode() + content)
        except: pass
        finally:
            if client_socket: client_socket.close()

    def handle_file_download(self, client_socket, path):
        gc.collect()
        try:
            history = self.data_logger.get_history()
            if path == '/csv':
                h = "HTTP/1.1 200 OK\r\nContent-Type: text/csv\r\nContent-Disposition: attachment; filename=\"data.csv\"\r\nConnection: close\r\n\r\n"
                client_socket.sendall(h.encode())
                client_socket.sendall("DateTime,SoilTemp_C,SoilMoisture,IR_Temp_C,Rainfall_mm,Rainfall_hr\n".encode())
                for e in history:
                    line = f"{e['timestamp']},{e.get('soil_temp_c',0)},{e.get('soil_moisture',0)},{e.get('ir_temp_c',0)},{e.get('rainfall_mm',0)},{e.get('rainfall_hourly',0)}\n"
                    client_socket.sendall(line.encode())
            elif path == '/json':
                self.send_response(client_socket, json.dumps(history), content_type="application/json",
                                   headers={'Content-Disposition': 'attachment; filename="data.json"'})
                return
        except Exception as e:
            self.logger.log("DOWNLOAD", f"Error: {e}", "ERROR")
        finally:
            if client_socket: client_socket.close()
            gc.collect()

    def check_network_connection(self):
        if time.time() - self.last_network_check < 30:
            return self.wlan and self.wlan.isconnected()
        self.last_network_check = time.time()
        if not self.wlan or not self.wlan.isconnected():
            return self.reconnect_wifi()
        return True

    def reconnect_wifi(self):
        try:
            if self.wlan: self.wlan.disconnect()
            time.sleep(1)
            return self.connect_wifi(config.WIFI_SSID, config.WIFI_PASSWORD, 15)
        except:
            return False

    def recover_socket(self):
        try:
            if self.socket: self.socket.close()
            time.sleep(1)
            return self.initialize_server(self.port)
        except:
            return False

    def shutdown(self):
        if self.socket: self.socket.close()

    def handle_test_page(self, client_socket):
        t = time.localtime()
        html = f"""<!DOCTYPE html><html><head><title>Test</title></head>
        <body><h1>✓ Server Running</h1>
        <p>Time: {t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}</p>
        <p><a href="/">Dashboard</a></p></body></html>"""
        self.send_response(client_socket, html)

    def handle_sensors_page(self, client_socket):
        status = self.sensor_manager.get_status()
        readings = self.sensor_manager.get_readings_dict()
        html = f"""<!DOCTYPE html><html><head><title>Sensors</title>
        <style>body{{font-family:Arial;padding:20px}}table{{border-collapse:collapse;width:100%}}
        th,td{{border:1px solid #ddd;padding:10px;text-align:left}}.ok{{color:green}}.err{{color:red}}</style></head>
        <body><h1>Sensor Details</h1>
        <table><tr><th>Sensor</th><th>Status</th><th>Reading</th></tr>
        <tr><td>Rainfall</td><td class="{'ok' if status['rainfall_available'] else 'err'}">{'✓ Online' if status['rainfall_available'] else '✗ Offline'}</td>
        <td>{readings['rainfall_hourly']:.2f} mm/hr</td></tr>
        <tr><td>IR Temperature (MLX90614)</td><td class="{'ok' if status['mlx90614_available'] else 'err'}">{'✓ Online' if status['mlx90614_available'] else '✗ Offline'}</td>
        <td>{readings['ir_object_temp_c']:.1f}°C</td></tr>
        <tr><td>Soil Temperature (DS18B20)</td><td class="{'ok' if status['ds18b20_available'] else 'err'}">{'✓ Online' if status['ds18b20_available'] else '✗ Offline'}</td>
        <td>{readings['soil_temp_c']:.1f}°C</td></tr>
        <tr><td>Soil Moisture</td><td class="{'ok' if status['soil_moisture_available'] else 'err'}">{'✓ Online' if status['soil_moisture_available'] else '✗ Offline'}</td>
        <td>{readings['soil_moisture']:.1f}%</td></tr>
        </table><p><a href="/">← Back to Dashboard</a></p></body></html>"""
        self.send_response(client_socket, html)