# uploader.py - Upload agricultural sensor data to Azure Functions
import urequests
import json
import network
import time
import config

def upload_data_to_server(sensor_data):
    """Upload sensor data to Azure Functions if URL is configured"""
    if not config.UPLOAD_URL:
        return False
        
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        if config.UPLOAD_DEBUG_MODE:
            print("[Upload] ✗ WiFi not connected.")
        return False

    payload = {
        "deviceId": config.DEVICE_ID,
        "timestamp": time.time(),
        "version": config.VERSION,
        "softwareDate": config.SOFTWARE_DATE,
        "sensors": {
            "soilTemperature1": round(sensor_data.get('soil_temp_1_c', 0), 1),
            "soilTemperature2": round(sensor_data.get('soil_temp_2_c', 0), 1),
            "soilTemperature3": round(sensor_data.get('soil_temp_3_c', 0), 1),
            "soilMoisture1": round(sensor_data.get('soil_moisture', 0), 1),
            "soilMoisture2": round(sensor_data.get('soil_moisture_2', 0), 1),
            "soilMoisture3": round(sensor_data.get('soil_moisture_3', 0), 1),
            "irTemperature1": round(sensor_data.get('ir_object_temp_c', 0), 1),
            "irTemperature2": round(sensor_data.get('ir_object_temp_2_c', 0), 1),
            "rainfallTotal": round(sensor_data.get('rainfall_mm', 0), 2),
            "rainfallHourly": round(sensor_data.get('rainfall_hourly', 0), 2)
        }
    }

    if config.UPLOAD_DEBUG_MODE:
        print("[Upload] === Sensor Data Received ===")
        for key, value in sensor_data.items():
            print(f"  {key}: {value}")
        print("[Upload] === Payload Being Sent ===")
        print(f"  deviceId: {payload['deviceId']}")
        for key, value in payload['sensors'].items():
            print(f"  {key}: {value}")

    try:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'GreenRoofingSENS/{config.VERSION}'
        }
        
        response = urequests.post(
            config.UPLOAD_URL, 
            data=json.dumps(payload), 
            headers=headers,
            timeout=config.UPLOAD_RESPONSE_TIMEOUT
        )
        
        success = 200 <= response.status_code < 300
        if config.UPLOAD_DEBUG_MODE:
            print(f"[Upload] Response [{response.status_code}]: {'✓ Success' if success else '✗ Failed'}")
        
        response.close()
        return success
        
    except Exception as e:
        if config.UPLOAD_DEBUG_MODE:
            print(f"[Upload] ✗ Error: {e}")
        return False