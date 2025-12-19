# uploader.py - Upload agricultural sensor data to server
import urequests
import json
import network
import config

def upload_data_to_server(sensor_data):
    """Upload sensor data to server"""
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        return False

    payload = {
        "Soil Temperature (C)": round(sensor_data.get('soil_temp_c', 0), 1),
        "Soil Moisture (%)": round(sensor_data.get('soil_moisture', 0), 1),
        "IR Temperature (C)": round(sensor_data.get('ir_temp_c', 0), 1),
        "Rainfall Total (mm)": round(sensor_data.get('rainfall_mm', 0), 2),
        "Rainfall Hourly (mm)": round(sensor_data.get('rainfall_hourly', 0), 2),
        "ID": config.DEVICE_ID,
        "software_date": config.SOFTWARE_DATE,
        "version": config.VERSION
    }

    try:
        headers = {'Content-Type': 'application/json'}
        response = urequests.post(config.UPLOAD_URL, data=json.dumps(payload), headers=headers)
        
        success = 200 <= response.status_code < 300
        if config.UPLOAD_DEBUG_MODE:
            print(f"[Upload] {'✓ Success' if success else '✗ Failed'}")
        response.close()
        return success
        
    except Exception as e:
        if config.UPLOAD_DEBUG_MODE:
            print(f"[Upload] Error: {e}")
        return False