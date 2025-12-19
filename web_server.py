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
        """Return all sensor data and recent history as JSON"""
        try:
            gc.collect()  # Clean memory before processing
            
            # Get basic data first
            readings = self.sensor_manager.get_readings()
            system_stats = self.monitor.check_system_health()
            sensor_status = self.sensor_manager.get_status()
            readings_dict = self.sensor_manager.get_readings_dict()
            
            if not readings:
                self.send_response(client_socket, '{"error":"No sensor data"}', status_code=500)
                return
                
            rainfall_mm, rainfall_hourly, ir_obj_c, ir_obj_f, ir_amb_c, soil_temp_c, soil_temp_f, soil_moisture = readings

            # Get limited history to prevent memory issues
            try:
                history = self.data_logger.get_history()
                recent_history = history[-12:] if len(history) > 12 else history  # Reduced from 24 to 12
            except:
                recent_history = []
            
            # Build minimal history payload
            history_payload = {
                "timestamps": [],
                "soil_temps": [],
                "soil_temp_1": [],
                "soil_temp_2": [],
                "soil_temp_3": [],
                "soil_moistures": [],
                "rainfall": [],
                "ir_temps": [],
            }
            
            for e in recent_history:
                try:
                    history_payload["timestamps"].append(e['timestamp'].split(' ')[1] if ' ' in e['timestamp'] else e['timestamp'])
                    history_payload["soil_temps"].append(round(e.get('soil_temp_c', 0), 1))
                    history_payload["soil_temp_1"].append(round(e.get('soil_temp_1_c', 0), 1))
                    history_payload["soil_temp_2"].append(round(e.get('soil_temp_2_c', 0), 1))
                    history_payload["soil_temp_3"].append(round(e.get('soil_temp_3_c', 0), 1))
                    history_payload["soil_moistures"].append(round(e.get('soil_moisture', 0), 1))
                    history_payload["rainfall"].append(round(e.get('rainfall_hourly', 0), 2))
                    history_payload["ir_temps"].append(round(e.get('ir_temp_c', 0), 1))
                except:
                    pass

            data = {
                "live": {
                    "rainfall_mm": round(rainfall_mm, 2),
                    "rainfall_hourly": round(rainfall_hourly, 2),
                    "ir_object_temp_c": round(ir_obj_c, 1),
                    "ir_object_temp_f": round(ir_obj_f, 1),
                    "ir_ambient_temp_c": round(ir_amb_c, 1),
                    "ir_object_temp_2_c": round(readings_dict.get('ir_object_temp_2_c', 0), 1),
                    "ir_object_temp_2_f": round(readings_dict.get('ir_object_temp_2_f', 32), 1),
                    "ir_ambient_temp_2_c": round(readings_dict.get('ir_ambient_temp_2_c', 0), 1),
                    "soil_temp_c": round(soil_temp_c, 1),
                    "soil_temp_f": round(soil_temp_f, 1),
                    "soil_temp_1_c": round(readings_dict.get('soil_temp_1_c', 0), 1),
                    "soil_temp_2_c": round(readings_dict.get('soil_temp_2_c', 0), 1),
                    "soil_temp_3_c": round(readings_dict.get('soil_temp_3_c', 0), 1),
                    "soil_moisture": round(soil_moisture, 1),
                    "soil_moisture_2": round(readings_dict.get('soil_moisture_2', 0), 1),
                    "soil_moisture_3": round(readings_dict.get('soil_moisture_3', 0), 1),
                },
                "status": sensor_status,
                "system": {
                    "uptime_str": format_uptime(system_stats.get('uptime', 0)),
                    "memory_percent": system_stats.get('memory_percent', 0),
                    "device_model": "Pico W",
                },
                "history": history_payload
            }
            
            json_str = json.dumps(data)
            self.send_response(client_socket, json_str, content_type='application/json')
            
        except Exception as e:
            self.logger.log("API", f"Error in handle_api_data: {e}", "ERROR")
            try:
                self.send_response(client_socket, '{"error":"API error"}', status_code=500)
            except:
                pass
        finally:
            gc.collect()

    def handle_request(self, client_socket):
        """Handle incoming HTTP requests"""
        path = '/'
        try:
            client_socket.settimeout(2.0)
            request_bytes = client_socket.recv(512)
            if not request_bytes:
                client_socket.close()
                return
            
            request = request_bytes.decode('utf-8')
            parts = request.split('\r\n')[0].split(' ')
            if len(parts) >= 2:
                path = parts[1]
            
            if path == '/favicon.ico':
                client_socket.send(b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n")
                return
            
            if path == '/':
                if self.html_shell:
                    send_chunked_html(client_socket, self.html_shell)
                else:
                    client_socket.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n<h1>Loading...</h1><p>HTML not ready</p>")
            elif path == '/simple':
                self.handle_simple_page(client_socket)
            elif path == '/sensors':
                self.handle_sensors_page(client_socket)
            elif path == '/debug':
                self.handle_debug_page(client_socket)
            elif path == '/api/data':
                self.handle_api_data(client_socket)
            elif path == '/api/stats':
                self.handle_api_stats(client_socket)
            elif path in ['/csv', '/json']:
                self.handle_file_download(client_socket, path)
            else:
                client_socket.send(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n<h1>404 Not Found</h1>")
        except Exception as e:
            self.logger.log("REQUEST", f"Error on '{path}': {e}", "WARNING")
        finally:
            try: 
                client_socket.close()
            except: 
                pass

    def handle_api_stats(self, client_socket):
        """Return statistical data for analytics"""
        try:
            history = self.data_logger.get_history()
            if not history:
                self.send_response(client_socket, '{"error":"No data available"}', status_code=404)
                return
            
            # Calculate statistics
            temps = [e.get('soil_temp_c', 0) for e in history[-24:]]  # Last 24 readings
            moistures = [e.get('soil_moisture', 0) for e in history[-24:]]
            rainfall = [e.get('rainfall_hourly', 0) for e in history[-24:]]
            
            stats = {
                "temperature": {
                    "avg": sum(temps) / len(temps) if temps else 0,
                    "min": min(temps) if temps else 0,
                    "max": max(temps) if temps else 0,
                    "trend": "stable" if len(temps) < 2 else ("up" if temps[-1] > temps[0] else "down")
                },
                "moisture": {
                    "avg": sum(moistures) / len(moistures) if moistures else 0,
                    "min": min(moistures) if moistures else 0,
                    "max": max(moistures) if moistures else 0,
                    "trend": "stable" if len(moistures) < 2 else ("up" if moistures[-1] > moistures[0] else "down")
                },
                "rainfall": {
                    "total_24h": sum(rainfall),
                    "max_hourly": max(rainfall) if rainfall else 0,
                    "events": len([r for r in rainfall if r > 0.1])
                },
                "data_points": len(history),
                "last_updated": history[-1]['timestamp'] if history else "Never"
            }
            
            self.send_response(client_socket, json.dumps(stats), content_type='application/json')
        except Exception as e:
            self.logger.log("API", f"Stats error: {e}", "ERROR")
            self.send_response(client_socket, '{"error":"Stats calculation failed"}', status_code=500)

    def stream_api_history(self, client_socket):
        """Stream history for charts with memory optimization"""
        try:
            headers = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n"
            client_socket.sendall(headers.encode())
            
            history = self.data_logger.get_history()
            if not history:
                client_socket.sendall('{"error":"No data","timestamps":[],"soil_temps":[],"soil_moistures":[],"rainfall":[]}'.encode())
                return
            
            # Limit to last 20 entries to prevent memory issues
            recent_history = history[-20:] if len(history) > 20 else history
            
            response = {
                "timestamps": [e['timestamp'].split(' ')[1] if ' ' in e['timestamp'] else e['timestamp'] for e in recent_history],
                "soil_temps": [round(e.get('soil_temp_c', 0), 1) for e in recent_history],
                "soil_temp_1": [round(e.get('soil_temp_1_c', e.get('soil_temp_c', 0)), 1) for e in recent_history],
                "soil_temp_2": [round(e.get('soil_temp_2_c', e.get('soil_temp_c', 0)), 1) for e in recent_history],
                "soil_temp_3": [round(e.get('soil_temp_3_c', e.get('soil_temp_c', 0)), 1) for e in recent_history],
                "soil_moistures": [round(e.get('soil_moisture', 0), 1) for e in recent_history],
                "rainfall": [round(e.get('rainfall_hourly', 0), 2) for e in recent_history],
                "ir_temps": [round(e.get('ir_temp_c', 0), 1) for e in recent_history],
            }
            
            json_str = json.dumps(response)
            client_socket.sendall(json_str.encode())
            
        except Exception as e:
            self.logger.log("API", f"History error: {e}", "ERROR")
            try:
                client_socket.sendall('{"error":"Server error","timestamps":[],"soil_temps":[],"soil_moistures":[],"rainfall":[]}'.encode())
            except:
                pass
        finally:
            try: 
                client_socket.close()
            except: 
                pass
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
            self.socket.listen(2)  # Increased backlog
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
        except Exception as e:
            self.logger.log("RESPONSE", f"Error: {e}", "ERROR")
        finally:
            if client_socket:
                client_socket.close()

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
        """Serve sensor page with loading screen"""
        try:
            html = """<!DOCTYPE html><html><head><title>Sensor Details</title>
            <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
            body{font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px}
            .container{max-width:1000px;margin:0 auto;background:white;padding:20px;border-radius:10px}
            h1{text-align:center;color:#2e7d32}
            .loading{text-align:center;padding:50px;font-size:1.2em;color:#666}
            .spinner{border:4px solid #f3f3f3;border-top:4px solid #4caf50;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin:20px auto}
            @keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
            .sensor-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin:20px 0}
            .sensor-card{background:#f9f9f9;padding:20px;border-radius:8px;border-left:4px solid #4caf50}
            .sensor-card.offline{border-left-color:#f44336;opacity:0.7}
            .sensor-name{font-size:1.2em;font-weight:bold;margin-bottom:10px}
            .sensor-value{font-size:2em;color:#2e7d32;margin:10px 0}
            .sensor-details{font-size:0.9em;color:#666}
            .status-online{color:#4caf50;font-weight:bold}
            .status-warn{color:#ff9800;font-weight:bold}
            .status-offline{color:#f44336;font-weight:bold}
            .refresh-btn{background:#4caf50;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;margin:10px 0}
            .refresh-btn:hover{background:#388e3c}
            #sensor-data{display:none}
            </style></head><body>
            <div class="container">
            <h1>🔧 Sensor Details</h1>
            
            <div id="loading" class="loading">
                <div class="spinner"></div>
                <p>Loading sensor data...</p>
            </div>
            
            <div id="sensor-data">
                <button class="refresh-btn" onclick="loadSensorData()">🔄 Refresh Data</button>
                <div id="sensor-grid" class="sensor-grid"></div>
                <div style="text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid #ddd">
                    <p id="system-info">Loading system info...</p>
                    <p><a href="/" style="color:#4caf50">← Back to Dashboard</a></p>
                </div>
            </div>
            </div>
            
            <script>
            function loadSensorData() {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('sensor-data').style.display = 'none';
                
                fetch('/api/data')
                .then(r => r.json())
                .then(data => {
                    const grid = document.getElementById('sensor-grid');
                    const live = data.live;
                    const status = data.status;
                    
                    grid.innerHTML = `
                        <div class="sensor-card ${!status.rainfall_available ? 'offline' : ''}">
                            <div class="sensor-name">🌧️ Rainfall Sensor (SEN0575)</div>
                            <div class="sensor-value">${live.rainfall_hourly.toFixed(2)} mm/hr</div>
                            <div class="sensor-details">
                                Status: <span class="${status.rainfall_available ? 'status-online' : 'status-offline'}">${status.rainfall_available ? 'Online' : 'Offline'}</span><br>
                                Total: ${live.rainfall_mm.toFixed(2)} mm<br>
                                I2C Address: 0x1D<br>
                                Bus: I2C0 (GP0/GP1)
                            </div>
                        </div>
                        
                        <div class="sensor-card ${!status.mlx90614_available ? 'offline' : ''}">
                            <div class="sensor-name">🍃 IR Temperature #1 (MLX90614)</div>
                            <div class="sensor-value">${live.ir_object_temp_c.toFixed(1)}°C</div>
                            <div class="sensor-details">
                                Status: <span class="${status.mlx90614_available ? 'status-online' : 'status-offline'}">${status.mlx90614_available ? 'Online' : 'Offline'}</span><br>
                                Ambient: ${live.ir_ambient_temp_c.toFixed(1)}°C<br>
                                I2C Address: 0x5A<br>
                                Bus: I2C0 (GP0/GP1)
                            </div>
                        </div>
                        
                        <div class="sensor-card ${!status.ds18b20_available ? 'offline' : ''}">
                            <div class="sensor-name">🌡️ Soil Temperature #1 (DS18B20)</div>
                            <div class="sensor-value">${live.soil_temp_1_c.toFixed(1)}°C</div>
                            <div class="sensor-details">
                                Status: <span class="${status.ds18b20_available ? 'status-online' : 'status-offline'}">${status.ds18b20_available ? 'Online' : 'Offline'}</span><br>
                                Pin: GP16<br>
                                Protocol: OneWire
                            </div>
                        </div>
                        
                        <div class="sensor-card ${!status.ds18b20_2_available && live.soil_temp_2_c === 0 ? 'offline' : ''}">
                            <div class="sensor-name">🌡️ Soil Temperature #2 (DS18B20)</div>
                            <div class="sensor-value">${live.soil_temp_2_c.toFixed(1)}°C</div>
                            <div class="sensor-details">
                                Status: <span class="${status.ds18b20_2_available ? 'status-online' : (live.soil_temp_2_c > 0 ? 'status-warn' : 'status-offline')}">${status.ds18b20_2_available ? 'Online' : (live.soil_temp_2_c > 0 ? 'Reading but Flagged Offline' : 'Offline')}</span><br>
                                Pin: GP17<br>
                                Protocol: OneWire
                            </div>
                        </div>
                        
                        <div class="sensor-card ${!status.ds18b20_3_available && live.soil_temp_3_c === 0 ? 'offline' : ''}">
                            <div class="sensor-name">🌡️ Soil Temperature #3 (DS18B20)</div>
                            <div class="sensor-value">${live.soil_temp_3_c.toFixed(1)}°C</div>
                            <div class="sensor-details">
                                Status: <span class="${status.ds18b20_3_available ? 'status-online' : (live.soil_temp_3_c > 0 ? 'status-warn' : 'status-offline')}">${status.ds18b20_3_available ? 'Online' : (live.soil_temp_3_c > 0 ? 'Reading but Flagged Offline' : 'Offline')}</span><br>
                                Pin: GP18<br>
                                Protocol: OneWire
                            </div>
                        </div>
                        
                        <div class="sensor-card ${!status.mlx90614_2_available ? 'offline' : ''}">
                            <div class="sensor-name">🍃 IR Temperature #2 (MLX90614)</div>
                            <div class="sensor-value">${live.ir_object_temp_2_c.toFixed(1)}°C</div>
                            <div class="sensor-details">
                                Status: <span class="${status.mlx90614_2_available ? 'status-online' : 'status-offline'}">${status.mlx90614_2_available ? 'Online' : 'Offline'}</span><br>
                                Ambient: ${live.ir_ambient_temp_2_c.toFixed(1)}°C<br>
                                I2C Address: 0x5A<br>
                                Bus: I2C1 (GP2/GP3)
                            </div>
                        </div>
                        
                        <div class="sensor-card ${!status.soil_moisture_available ? 'offline' : ''}">
                            <div class="sensor-name">💧 Soil Moisture #1</div>
                            <div class="sensor-value">${live.soil_moisture.toFixed(0)}%</div>
                            <div class="sensor-details">
                                Status: <span class="${status.soil_moisture_available ? 'status-online' : 'status-offline'}">${status.soil_moisture_available ? 'Online' : 'Offline'}</span><br>
                                Pin: GP26 (ADC0)<br>
                                Type: Capacitive
                            </div>
                        </div>
                        
                        <div class="sensor-card ${!status.soil_moisture_2_available ? 'offline' : ''}">
                            <div class="sensor-name">💧 Soil Moisture #2</div>
                            <div class="sensor-value">${live.soil_moisture_2.toFixed(0)}%</div>
                            <div class="sensor-details">
                                Status: <span class="${status.soil_moisture_2_available ? 'status-online' : 'status-offline'}">${status.soil_moisture_2_available ? 'Online' : 'Offline'}</span><br>
                                Pin: GP27 (ADC1)<br>
                                Type: Capacitive
                            </div>
                        </div>
                        
                        <div class="sensor-card ${!status.soil_moisture_3_available ? 'offline' : ''}">
                            <div class="sensor-name">💧 Soil Moisture #3</div>
                            <div class="sensor-value">${live.soil_moisture_3.toFixed(0)}%</div>
                            <div class="sensor-details">
                                Status: <span class="${status.soil_moisture_3_available ? 'status-online' : 'status-offline'}">${status.soil_moisture_3_available ? 'Online' : 'Offline'}</span><br>
                                Pin: GP28 (ADC2)<br>
                                Type: Capacitive
                            </div>
                        </div>
                    `;
                    
                    document.getElementById('system-info').innerHTML = `System Memory: ${data.system.memory_percent.toFixed(1)}% used | Uptime: ${data.system.uptime_str}`;
                    
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('sensor-data').style.display = 'block';
                })
                .catch(err => {
                    document.getElementById('loading').innerHTML = '<p style="color:red">Error loading sensor data</p>';
                });
            }
            
            // Load data when page loads
            loadSensorData();
            </script>
            </body></html>"""
            
            self.send_response(client_socket, html)
        except Exception as e:
            self.logger.log("SENSORS", f"Error: {e}", "ERROR")
            self.send_response(client_socket, "<h1>Sensors page error</h1>", status_code=500)
    def handle_simple_page(self, client_socket):
        """Serve the simple dashboard"""
        from web_template_simple import create_html as create_simple_html
        try:
            simple_html = create_simple_html(None)
            self.send_response(client_socket, simple_html)
        except Exception as e:
            self.logger.log("SIMPLE", f"Error: {e}", "ERROR")
            self.send_response(client_socket, "<h1>Simple page error</h1>", status_code=500)
    def handle_debug_page(self, client_socket):
        """Serve debug page with detailed sensor information"""
        try:
            import config
            if not getattr(config, 'SENSOR_DEBUG_MODE', False):
                self.send_response(client_socket, "<h1>Debug mode disabled</h1>", status_code=403)
                return
                
            status = self.sensor_manager.get_status()
            readings = self.sensor_manager.get_readings_dict()
            
            html = f"""<!DOCTYPE html><html><head><title>Sensor Debug</title>
            <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
            body{{font-family:monospace;background:#000;color:#0f0;margin:20px}}
            .debug-section{{margin:20px 0;padding:15px;border:1px solid #0f0;background:#001100}}
            .sensor-ok{{color:#0f0}}
            .sensor-error{{color:#f00}}
            .sensor-warn{{color:#ff0}}
            pre{{background:#111;padding:10px;border-left:3px solid #0f0}}
            </style></head><body>
            <h1>🐛 SENSOR DEBUG MODE</h1>
            
            <div class="debug-section">
                <h2>SENSOR STATUS OVERVIEW</h2>
                <pre>
Rainfall:           {'✓ ONLINE' if status.get('rainfall_available', False) else '✗ OFFLINE'}
IR Temp #1:         {'✓ ONLINE' if status.get('mlx90614_available', False) else '✗ OFFLINE'}
IR Temp #2:         {'✓ ONLINE' if status.get('mlx90614_2_available', False) else '✗ OFFLINE'}
Soil Temp #1:       {'✓ ONLINE' if status.get('ds18b20_available', False) else '✗ OFFLINE'}
Soil Temp #2:       {'✓ ONLINE' if status.get('ds18b20_2_available', False) else '✗ OFFLINE'}
Soil Temp #3:       {'✓ ONLINE' if status.get('ds18b20_3_available', False) else '✗ OFFLINE'}
Soil Moisture #1:   {'✓ ONLINE' if status.get('soil_moisture_available', False) else '✗ OFFLINE'}
Soil Moisture #2:   {'✓ ONLINE' if status.get('soil_moisture_2_available', False) else '✗ OFFLINE'}
Soil Moisture #3:   {'✓ ONLINE' if status.get('soil_moisture_3_available', False) else '✗ OFFLINE'}
                </pre>
            </div>
            
            <div class="debug-section">
                <h2>CURRENT READINGS</h2>
                <pre>
Rainfall:           {readings.get('rainfall_hourly', 0):.2f} mm/hr (Total: {readings.get('rainfall_mm', 0):.2f} mm)
IR Object #1:       {readings.get('ir_object_temp_c', 0):.1f}°C (Ambient: {readings.get('ir_ambient_temp_c', 0):.1f}°C)
IR Object #2:       {readings.get('ir_object_temp_2_c', 0):.1f}°C (Ambient: {readings.get('ir_ambient_temp_2_c', 0):.1f}°C)
Soil Temp #1:       {readings.get('soil_temp_1_c', 0):.1f}°C
Soil Temp #2:       {readings.get('soil_temp_2_c', 0):.1f}°C
Soil Temp #3:       {readings.get('soil_temp_3_c', 0):.1f}°C
Soil Moisture #1:   {readings.get('soil_moisture', 0):.1f}%
Soil Moisture #2:   {readings.get('soil_moisture_2', 0):.1f}%
Soil Moisture #3:   {readings.get('soil_moisture_3', 0):.1f}%
                </pre>
            </div>
            
            <div class="debug-section">
                <h2>HARDWARE CONFIGURATION</h2>
                <pre>
I2C Bus 0 (GP0/GP1):
  - Rainfall Sensor (0x1D)
  - MLX90614 #1 (0x5A)

I2C Bus 1 (GP2/GP3):
  - MLX90614 #2 (0x5A)

OneWire Sensors:
  - DS18B20 #1 (GP16)
  - DS18B20 #2 (GP17)
  - DS18B20 #3 (GP18)

ADC Sensors:
  - Soil Moisture #1 (GP26/ADC0)
  - Soil Moisture #2 (GP27/ADC1)
  - Soil Moisture #3 (GP28/ADC2)
                </pre>
            </div>
            
            <div class="debug-section">
                <h2>STATUS DETAILS</h2>
                <pre>
{status}
                </pre>
            </div>
            
            <div class="debug-section">
                <h2>READINGS DETAILS</h2>
                <pre>
{readings}
                </pre>
            </div>
            
            <p><a href="/sensors" style="color:#0f0">← Back to Sensors</a> | <a href="/" style="color:#0f0">← Dashboard</a></p>
            </body></html>"""
            
            self.send_response(client_socket, html)
        except Exception as e:
            self.logger.log("DEBUG", f"Error: {e}", "ERROR")
            self.send_response(client_socket, "<h1>Debug page error</h1>", status_code=500)