import json
import uuid
import os
from datetime import datetime, timedelta
from statistics import mean, stdev
import azure.functions as func
from azure.data.tables import TableServiceClient

app = func.FunctionApp()


def compute_analytics(entities):
    """Compute statistical analytics from sensor readings."""
    if not entities or len(entities) < 2:
        return None

    # Extract values
    soil_temps = [e.get("SoilTemp_C", 0) for e in entities if e.get("SoilTemp_C")]
    soil_moistures = [e.get("SoilMoisture_Percent", 0) for e in entities if e.get("SoilMoisture_Percent")]
    ir_temps = [e.get("IR_Temp_C", 0) for e in entities if e.get("IR_Temp_C")]
    rainfall = [e.get("Rainfall_Hourly_mm", 0) for e in entities if e.get("Rainfall_Hourly_mm") is not None]

    def safe_stats(values):
        if not values or len(values) < 2:
            return {"avg": 0, "min": 0, "max": 0, "std": 0, "trend": "stable"}
        avg = mean(values)
        std = stdev(values) if len(values) > 1 else 0
        # Calculate trend (compare first half vs second half)
        mid = len(values) // 2
        if mid > 0:
            first_half = mean(values[:mid])
            second_half = mean(values[mid:])
            diff = second_half - first_half
            if diff > std * 0.5:
                trend = "rising"
            elif diff < -std * 0.5:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"
        return {
            "avg": round(avg, 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "std": round(std, 2),
            "trend": trend
        }

    return {
        "soil_temp": safe_stats(soil_temps),
        "soil_moisture": safe_stats(soil_moistures),
        "ir_temp": safe_stats(ir_temps),
        "rainfall": {
            "total": round(sum(rainfall), 2),
            "avg": round(mean(rainfall), 2) if rainfall else 0,
            "max": round(max(rainfall), 2) if rainfall else 0,
            "rainy_readings": sum(1 for r in rainfall if r > 0)
        }
    }


def detect_anomalies(entities):
    """Detect anomalies in sensor readings using z-score method."""
    if not entities or len(entities) < 5:
        return []

    anomalies = []

    # Fields to check
    fields = [
        ("SoilTemp_C", "Soil Temperature", "°C", 2.5),
        ("SoilMoisture_Percent", "Soil Moisture", "%", 2.5),
        ("IR_Temp_C", "IR Temperature", "°C", 2.5)
    ]

    for field, name, unit, threshold in fields:
        values = [e.get(field, 0) for e in entities if e.get(field) is not None]
        if len(values) < 5:
            continue

        avg = mean(values)
        std = stdev(values) if len(values) > 1 else 1

        if std == 0:
            continue

        # Check latest reading for anomaly
        latest = entities[0].get(field, 0)
        z_score = abs(latest - avg) / std

        if z_score > threshold:
            direction = "high" if latest > avg else "low"
            anomalies.append({
                "sensor": name,
                "value": round(latest, 1),
                "unit": unit,
                "avg": round(avg, 1),
                "z_score": round(z_score, 2),
                "direction": direction,
                "severity": "warning" if z_score < 3 else "critical",
                "message": f"{name} is unusually {direction}: {latest:.1f}{unit} (avg: {avg:.1f}{unit})"
            })

    # Check for sudden changes (compare last 2 readings)
    if len(entities) >= 2:
        for field, name, unit, _ in fields:
            curr = entities[0].get(field, 0)
            prev = entities[1].get(field, 0)
            if prev != 0:
                pct_change = abs(curr - prev) / abs(prev) * 100
                if pct_change > 20:  # More than 20% change
                    anomalies.append({
                        "sensor": name,
                        "value": round(curr, 1),
                        "unit": unit,
                        "prev_value": round(prev, 1),
                        "pct_change": round(pct_change, 1),
                        "severity": "info",
                        "message": f"{name} changed {pct_change:.0f}% since last reading"
                    })

    return anomalies


def compute_insights(entities, analytics):
    """Generate human-readable insights from the data."""
    if not entities or not analytics:
        return []

    insights = []

    # Soil moisture insights
    moisture = analytics.get("soil_moisture", {})
    if moisture.get("avg", 0) < 30:
        insights.append({
            "type": "warning",
            "icon": "💧",
            "title": "Low Soil Moisture",
            "message": f"Average moisture is {moisture['avg']}%. Consider watering soon."
        })
    elif moisture.get("avg", 0) > 70:
        insights.append({
            "type": "info",
            "icon": "💦",
            "title": "High Soil Moisture",
            "message": f"Soil is well saturated at {moisture['avg']}% average."
        })

    # Temperature stress detection (leaf vs soil temp difference)
    soil_temp = analytics.get("soil_temp", {}).get("avg", 0)
    ir_temp = analytics.get("ir_temp", {}).get("avg", 0)
    temp_diff = ir_temp - soil_temp

    if temp_diff > 5:
        insights.append({
            "type": "warning",
            "icon": "🌡️",
            "title": "Possible Heat Stress",
            "message": f"Leaf temperature ({ir_temp:.1f}°C) is {temp_diff:.1f}°C warmer than soil. Plants may be heat-stressed."
        })
    elif temp_diff < -3:
        insights.append({
            "type": "info",
            "icon": "❄️",
            "title": "Cool Canopy",
            "message": f"Leaf temperature ({ir_temp:.1f}°C) is cooler than soil. Good transpiration occurring."
        })

    # Trend insights
    soil_temp_trend = analytics.get("soil_temp", {}).get("trend", "stable")
    if soil_temp_trend == "rising":
        insights.append({
            "type": "info",
            "icon": "📈",
            "title": "Temperature Rising",
            "message": "Soil temperature has been trending upward."
        })
    elif soil_temp_trend == "falling":
        insights.append({
            "type": "info",
            "icon": "📉",
            "title": "Temperature Falling",
            "message": "Soil temperature has been trending downward."
        })

    # Rainfall insights
    rainfall = analytics.get("rainfall", {})
    if rainfall.get("total", 0) > 10:
        insights.append({
            "type": "info",
            "icon": "🌧️",
            "title": "Significant Rainfall",
            "message": f"Total rainfall of {rainfall['total']}mm recorded in this period."
        })

    return insights


def compute_advanced_analytics(entities):
    """Compute advanced analytics including predictions and GDD."""
    if not entities or len(entities) < 3:
        return None

    # Extract data with timestamps
    data_points = []
    for e in entities:
        dt_str = e.get("DateTime", "")
        if dt_str:
            try:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except:
                dt = datetime.now()
            data_points.append({
                "datetime": dt,
                "soil_temp": e.get("SoilTemp_C", 0),
                "soil_moisture": e.get("SoilMoisture_Percent", 0),
                "ir_temp": e.get("IR_Temp_C", 0),
                "rainfall": e.get("Rainfall_Hourly_mm", 0)
            })

    if not data_points:
        return None

    # Sort by datetime
    data_points.sort(key=lambda x: x["datetime"])

    # --- Trend Analysis ---
    def calculate_hourly_stats(points, field):
        """Group by hour and calculate stats."""
        hourly = {}
        for p in points:
            hour_key = p["datetime"].strftime("%Y-%m-%d %H:00")
            if hour_key not in hourly:
                hourly[hour_key] = []
            hourly[hour_key].append(p[field])

        hourly_stats = []
        for hour, values in sorted(hourly.items()):
            hourly_stats.append({
                "hour": hour,
                "avg": round(mean(values), 2),
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "count": len(values)
            })
        return hourly_stats[-12:]  # Last 12 hours

    trend_analysis = {
        "soil_temp_hourly": calculate_hourly_stats(data_points, "soil_temp"),
        "moisture_hourly": calculate_hourly_stats(data_points, "soil_moisture"),
        "ir_temp_hourly": calculate_hourly_stats(data_points, "ir_temp")
    }

    # --- Predictive Watering ---
    moisture_values = [p["soil_moisture"] for p in data_points]
    current_moisture = moisture_values[-1] if moisture_values else 0

    # Calculate moisture depletion rate (% per hour)
    if len(moisture_values) >= 2 and len(data_points) >= 2:
        time_diff = (data_points[-1]["datetime"] - data_points[0]["datetime"]).total_seconds() / 3600
        if time_diff > 0:
            moisture_change = moisture_values[-1] - moisture_values[0]
            depletion_rate = moisture_change / time_diff
        else:
            depletion_rate = 0
    else:
        depletion_rate = 0

    # Predict when moisture will hit critical level (30%)
    critical_threshold = 30
    if depletion_rate < 0 and current_moisture > critical_threshold:
        hours_until_critical = (current_moisture - critical_threshold) / abs(depletion_rate)
        if hours_until_critical > 168:  # Cap at 1 week
            hours_until_critical = None
            watering_urgency = "low"
        elif hours_until_critical < 6:
            watering_urgency = "critical"
        elif hours_until_critical < 24:
            watering_urgency = "high"
        elif hours_until_critical < 48:
            watering_urgency = "medium"
        else:
            watering_urgency = "low"
    elif current_moisture <= critical_threshold:
        hours_until_critical = 0
        watering_urgency = "critical"
    else:
        hours_until_critical = None
        watering_urgency = "low"

    predictive_watering = {
        "current_moisture": round(current_moisture, 1),
        "depletion_rate": round(depletion_rate, 3),
        "hours_until_critical": round(hours_until_critical, 1) if hours_until_critical else None,
        "watering_urgency": watering_urgency,
        "recommendation": get_watering_recommendation(current_moisture, depletion_rate, hours_until_critical)
    }

    # --- Heat Stress Analysis ---
    heat_stress_events = []
    current_temp_diff = 0
    for i, p in enumerate(data_points):
        temp_diff = p["ir_temp"] - p["soil_temp"]
        if temp_diff > 5:
            severity = "severe" if temp_diff > 10 else "moderate" if temp_diff > 7 else "mild"
            heat_stress_events.append({
                "datetime": p["datetime"].isoformat(),
                "leaf_temp": round(p["ir_temp"], 1),
                "soil_temp": round(p["soil_temp"], 1),
                "difference": round(temp_diff, 1),
                "severity": severity
            })

    # Current heat stress status
    if data_points:
        latest = data_points[-1]
        current_temp_diff = latest["ir_temp"] - latest["soil_temp"]
        if current_temp_diff > 10:
            heat_stress_status = "severe"
        elif current_temp_diff > 7:
            heat_stress_status = "moderate"
        elif current_temp_diff > 5:
            heat_stress_status = "mild"
        elif current_temp_diff < -3:
            heat_stress_status = "cool_canopy"
        else:
            heat_stress_status = "normal"
    else:
        heat_stress_status = "unknown"

    heat_stress = {
        "current_status": heat_stress_status,
        "current_leaf_temp": round(data_points[-1]["ir_temp"], 1) if data_points else 0,
        "current_soil_temp": round(data_points[-1]["soil_temp"], 1) if data_points else 0,
        "current_difference": round(current_temp_diff, 1) if data_points else 0,
        "stress_events_count": len(heat_stress_events),
        "recent_events": heat_stress_events[-5:]  # Last 5 events
    }

    # --- Growing Degree Days (GDD) ---
    # Base temperature for most plants (10C / 50F)
    base_temp = 10.0

    # Calculate GDD from available data
    daily_gdd = {}
    for p in data_points:
        day_key = p["datetime"].strftime("%Y-%m-%d")
        if day_key not in daily_gdd:
            daily_gdd[day_key] = {"temps": [], "date": day_key}
        daily_gdd[day_key]["temps"].append(p["soil_temp"])

    gdd_by_day = []
    total_gdd = 0
    for day_key in sorted(daily_gdd.keys()):
        temps = daily_gdd[day_key]["temps"]
        if temps:
            avg_temp = mean(temps)
            daily_gdd_value = max(0, avg_temp - base_temp)
            total_gdd += daily_gdd_value
            gdd_by_day.append({
                "date": day_key,
                "avg_temp": round(avg_temp, 1),
                "gdd": round(daily_gdd_value, 1),
                "cumulative_gdd": round(total_gdd, 1)
            })

    growing_degree_days = {
        "base_temperature": base_temp,
        "total_gdd": round(total_gdd, 1),
        "daily_gdd": gdd_by_day[-7:],  # Last 7 days
        "growth_stage_estimate": estimate_growth_stage(total_gdd)
    }

    return {
        "trend_analysis": trend_analysis,
        "predictive_watering": predictive_watering,
        "heat_stress": heat_stress,
        "growing_degree_days": growing_degree_days
    }


def get_watering_recommendation(moisture, rate, hours_until_critical):
    """Generate watering recommendation based on moisture data."""
    if moisture <= 20:
        return "Water immediately - soil is critically dry"
    elif moisture <= 30:
        return "Water soon - soil moisture is low"
    elif hours_until_critical is not None and hours_until_critical < 12:
        return f"Plan to water within {int(hours_until_critical)} hours"
    elif hours_until_critical is not None and hours_until_critical < 24:
        return "Water within the next day"
    elif rate < -0.5:
        return "Monitor closely - moisture depleting quickly"
    elif moisture > 70:
        return "No watering needed - soil is well saturated"
    else:
        return "Moisture levels adequate - continue monitoring"


def estimate_growth_stage(gdd):
    """Estimate plant growth stage based on accumulated GDD."""
    if gdd < 50:
        return {"stage": "Dormant/Early", "description": "Seeds germinating or early growth", "progress": min(100, int(gdd/50*100))}
    elif gdd < 150:
        return {"stage": "Vegetative", "description": "Active leaf and stem growth", "progress": min(100, int((gdd-50)/100*100))}
    elif gdd < 300:
        return {"stage": "Development", "description": "Plant establishing structure", "progress": min(100, int((gdd-150)/150*100))}
    elif gdd < 500:
        return {"stage": "Mature", "description": "Full growth achieved", "progress": min(100, int((gdd-300)/200*100))}
    else:
        return {"stage": "Peak/Harvest", "description": "Optimal maturity", "progress": 100}


# POST endpoint - receives data from Pico (requires function key for security)
@app.route(route="sensor-data", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()

        if not req_body:
            return func.HttpResponse(
                "Invalid request: Expected JSON data",
                status_code=400
            )

        table_service = TableServiceClient.from_connection_string(
            os.environ["AzureWebJobsStorage"]
        )

        try:
            table_service.create_table_if_not_exists("SensorReadings")
        except Exception:
            pass

        table_client = table_service.get_table_client("SensorReadings")

        # Handle both old format and new format with individual sensors
        sensors = req_body.get("sensors", {})

        # Individual soil temperatures (or fallback to average)
        soil_temp_1 = float(sensors.get("soilTemperature1", req_body.get("Soil Temperature (C)", 0)))
        soil_temp_2 = float(sensors.get("soilTemperature2", 0))
        soil_temp_3 = float(sensors.get("soilTemperature3", 0))

        # Calculate average from available sensors
        valid_temps = [t for t in [soil_temp_1, soil_temp_2, soil_temp_3] if t != 0]
        soil_temp_avg = sum(valid_temps) / len(valid_temps) if valid_temps else soil_temp_1

        # Individual soil moisture sensors
        soil_moisture_1 = float(sensors.get("soilMoisture1", req_body.get("Soil Moisture (%)", 0)))
        soil_moisture_2 = float(sensors.get("soilMoisture2", 0))
        soil_moisture_3 = float(sensors.get("soilMoisture3", 0))

        # Calculate average from available sensors
        valid_moisture = [m for m in [soil_moisture_1, soil_moisture_2, soil_moisture_3] if m != 0]
        soil_moisture_avg = sum(valid_moisture) / len(valid_moisture) if valid_moisture else soil_moisture_1

        # Individual IR temperatures
        ir_temp_1 = float(sensors.get("irTemperature1", req_body.get("IR Temperature (C)", 0)))
        ir_temp_2 = float(sensors.get("irTemperature2", 0))

        # Calculate average IR temp
        valid_ir = [t for t in [ir_temp_1, ir_temp_2] if t != 0]
        ir_temp_avg = sum(valid_ir) / len(valid_ir) if valid_ir else ir_temp_1

        entity = {
            "PartitionKey": req_body.get("deviceId", req_body.get("ID", "unknown_device")),
            "RowKey": str(uuid.uuid4()),
            "DateTime": datetime.utcnow().isoformat(),
            # Averages (for backwards compatibility)
            "SoilTemp_C": round(soil_temp_avg, 1),
            "SoilMoisture_Percent": round(soil_moisture_avg, 1),
            "IR_Temp_C": round(ir_temp_avg, 1),
            # Individual soil temperatures
            "SoilTemp_1_C": round(soil_temp_1, 1),
            "SoilTemp_2_C": round(soil_temp_2, 1),
            "SoilTemp_3_C": round(soil_temp_3, 1),
            # Individual soil moisture
            "SoilMoisture_1_Percent": round(soil_moisture_1, 1),
            "SoilMoisture_2_Percent": round(soil_moisture_2, 1),
            "SoilMoisture_3_Percent": round(soil_moisture_3, 1),
            # Individual IR temps
            "IR_Temp_1_C": round(ir_temp_1, 1),
            "IR_Temp_2_C": round(ir_temp_2, 1),
            # Rainfall
            "Rainfall_Total_mm": float(sensors.get("rainfallTotal", req_body.get("Rainfall Total (mm)", 0))),
            "Rainfall_Hourly_mm": float(sensors.get("rainfallHourly", req_body.get("Rainfall Hourly (mm)", 0))),
            # Metadata
            "DeviceID": req_body.get("deviceId", req_body.get("ID", "unknown")),
            "SoftwareDate": req_body.get("softwareDate", req_body.get("software_date", "")),
            "Version": req_body.get("version", "")
        }

        table_client.create_entity(entity)

        return func.HttpResponse(
            json.dumps({"status": "success", "message": "Data ingested successfully"}),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"status": "error", "message": f"Invalid JSON data: {str(e)}"}),
            status_code=400,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"status": "error", "message": f"Server error: {str(e)}"}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


# GET endpoint - returns sensor data for dashboard
@app.route(route="sensor-data", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_sensor_data(req: func.HttpRequest) -> func.HttpResponse:
    try:
        table_service = TableServiceClient.from_connection_string(
            os.environ["AzureWebJobsStorage"]
        )
        table_client = table_service.get_table_client("SensorReadings")

        # Get query parameters
        device_id = req.params.get('device_id')
        limit = int(req.params.get('limit', 50))
        hours = req.params.get('hours')  # Time range filter: 24, 168 (week), 720 (month)

        # Calculate time filter if hours specified
        time_filter = None
        if hours:
            try:
                hours_int = int(hours)
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_int)
                time_filter = cutoff_time.isoformat() + "Z"
            except ValueError:
                pass

        # Query entities, ordered by timestamp descending
        if device_id:
            filter_query = f"PartitionKey eq '{device_id}'"
            entities = list(table_client.query_entities(filter_query))
        else:
            entities = list(table_client.list_entities())

        # Sort by DateTime descending
        entities.sort(key=lambda x: x.get('DateTime', ''), reverse=True)

        # Apply time filter if specified
        if time_filter:
            entities = [e for e in entities if e.get('DateTime', '') >= time_filter]

        # Apply limit
        entities = entities[:limit]

        # Get the latest reading for live display
        latest = entities[0] if entities else None

        # Compute analytics
        analytics = compute_analytics(entities)
        anomalies = detect_anomalies(entities)
        insights = compute_insights(entities, analytics)
        advanced = compute_advanced_analytics(entities)

        # Build response matching Pico dashboard format
        response = {
            "live": {
                # Averages
                "soil_temp_c": latest.get("SoilTemp_C", 0) if latest else 0,
                "soil_temp_f": (latest.get("SoilTemp_C", 0) * 9/5 + 32) if latest else 32,
                "soil_moisture": latest.get("SoilMoisture_Percent", 0) if latest else 0,
                "ir_object_temp_c": latest.get("IR_Temp_C", 0) if latest else 0,
                "ir_object_temp_f": (latest.get("IR_Temp_C", 0) * 9/5 + 32) if latest else 32,
                "rainfall_hourly": latest.get("Rainfall_Hourly_mm", 0) if latest else 0,
                "rainfall_total": latest.get("Rainfall_Total_mm", 0) if latest else 0,
                # Individual soil temperatures
                "soil_temp_1_c": latest.get("SoilTemp_1_C", 0) if latest else 0,
                "soil_temp_2_c": latest.get("SoilTemp_2_C", 0) if latest else 0,
                "soil_temp_3_c": latest.get("SoilTemp_3_C", 0) if latest else 0,
                # Individual soil moisture
                "soil_moisture_1": latest.get("SoilMoisture_1_Percent", 0) if latest else 0,
                "soil_moisture_2": latest.get("SoilMoisture_2_Percent", 0) if latest else 0,
                "soil_moisture_3": latest.get("SoilMoisture_3_Percent", 0) if latest else 0,
                # Individual IR temps
                "ir_temp_1_c": latest.get("IR_Temp_1_C", 0) if latest else 0,
                "ir_temp_2_c": latest.get("IR_Temp_2_C", 0) if latest else 0
            },
            "status": {
                "rainfall_available": True,
                "mlx90614_available": True,
                "mlx90614_2_available": latest.get("IR_Temp_2_C", 0) != 0 if latest else False,
                "ds18b20_available": True,
                "ds18b20_2_available": latest.get("SoilTemp_2_C", 0) != 0 if latest else False,
                "ds18b20_3_available": latest.get("SoilTemp_3_C", 0) != 0 if latest else False,
                "soil_moisture_available": True,
                "soil_moisture_2_available": latest.get("SoilMoisture_2_Percent", 0) != 0 if latest else False,
                "soil_moisture_3_available": latest.get("SoilMoisture_3_Percent", 0) != 0 if latest else False
            },
            "system": {
                "device_model": "Azure Cloud",
                "uptime_str": "Cloud Service",
                "memory_percent": 0,
                "device_id": latest.get("DeviceID", "unknown") if latest else "unknown",
                "version": latest.get("Version", "3.0") if latest else "3.0"
            },
            "history": {
                "timestamps": [e.get("DateTime", "")[11:16] for e in reversed(entities)],
                "soil_temps": [e.get("SoilTemp_C", 0) for e in reversed(entities)],
                "soil_temp_1": [e.get("SoilTemp_1_C", 0) for e in reversed(entities)],
                "soil_temp_2": [e.get("SoilTemp_2_C", 0) for e in reversed(entities)],
                "soil_temp_3": [e.get("SoilTemp_3_C", 0) for e in reversed(entities)],
                "soil_moistures": [e.get("SoilMoisture_Percent", 0) for e in reversed(entities)],
                "soil_moisture_1": [e.get("SoilMoisture_1_Percent", 0) for e in reversed(entities)],
                "soil_moisture_2": [e.get("SoilMoisture_2_Percent", 0) for e in reversed(entities)],
                "soil_moisture_3": [e.get("SoilMoisture_3_Percent", 0) for e in reversed(entities)],
                "ir_temps": [e.get("IR_Temp_C", 0) for e in reversed(entities)],
                "ir_temp_1": [e.get("IR_Temp_1_C", 0) for e in reversed(entities)],
                "ir_temp_2": [e.get("IR_Temp_2_C", 0) for e in reversed(entities)],
                "rainfall": [e.get("Rainfall_Hourly_mm", 0) for e in reversed(entities)],
                "datetimes": [e.get("DateTime", "") for e in reversed(entities)]
            },
            "analytics": analytics,
            "anomalies": anomalies,
            "insights": insights,
            "advanced_analytics": advanced,
            "readings_count": len(entities),
            "last_updated": latest.get("DateTime", "") if latest else "",
            "time_range": {
                "hours": int(hours) if hours else None,
                "from": time_filter if time_filter else None,
                "label": f"Last {hours} hours" if hours else "All data"
            }
        }

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            status_code=500,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        )


# OPTIONS endpoint for CORS preflight
@app.route(route="sensor-data", methods=["OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def options_sensor_data(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        "",
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )
