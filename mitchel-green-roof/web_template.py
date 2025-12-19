# web_template.py - Dashboard for 4 agricultural sensors
import gc
import config

HTML_HEADER = """<!DOCTYPE html><html><head><title>Agricultural Monitor v{version}</title>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{{font-family:Arial,sans-serif;background:linear-gradient(135deg,#e8f5e9,#f1f8e9);margin:0;padding:0}}
#main-container{{max-width:800px;margin:20px auto;background:#fff;padding:20px;box-shadow:0 0 15px rgba(0,0,0,.1);border-radius:12px}}
h1{{text-align:center;color:#2e7d32;margin-bottom:5px}}
.subtitle{{text-align:center;color:#666;margin-bottom:20px}}
h2{{color:#2c3e50;border-bottom:2px solid #4caf50;padding-bottom:8px;margin-top:30px}}
.readings-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:15px;margin-bottom:20px}}
.reading-card{{background:#f8f9fa;padding:15px;border-radius:10px;text-align:center;border-left:4px solid #4caf50;box-shadow:0 2px 5px rgba(0,0,0,.05)}}
.reading-card.rain{{border-left-color:#2196f3;background:linear-gradient(135deg,#e3f2fd,#fff)}}
.reading-card.temp{{border-left-color:#ff9800;background:linear-gradient(135deg,#fff3e0,#fff)}}
.reading-card.soil{{border-left-color:#795548;background:linear-gradient(135deg,#efebe9,#fff)}}
.reading-card.moisture{{border-left-color:#4caf50;background:linear-gradient(135deg,#e8f5e9,#fff)}}
.label{{font-size:.85em;color:#666;margin-bottom:5px}}
.value{{font-size:1.8em;font-weight:700;margin:8px 0}}
.unit{{font-size:.5em;font-weight:normal;color:#888}}
.status{{font-size:.75em;padding:3px 10px;border-radius:12px;display:inline-block;margin-top:5px}}
.status-ok{{background:#c8e6c9;color:#2e7d32}}
.status-warn{{background:#fff3cd;color:#856404}}
.status-error{{background:#ffcdd2;color:#c62828}}
.status-info{{background:#e3f2fd;color:#1565c0}}
.toggle-btn{{font-size:.7em;padding:4px 10px;margin-top:8px;cursor:pointer;border:none;background:#4caf50;color:#fff;border-radius:15px}}
.toggle-btn:hover{{background:#388e3c}}
.chart-container{{background:#fff;border:1px solid #e0e0e0;border-radius:10px;padding:15px;margin-bottom:15px}}
.chart-title{{margin:0 0 10px;font-size:1rem;color:#333}}
.system-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}}
.system-card{{background:#f5f5f5;border-radius:10px;padding:15px}}
.system-card h3{{margin:0 0 10px;font-size:.95rem;color:#333}}
.progress-bar{{width:100%;height:8px;background:#e0e0e0;border-radius:4px;overflow:hidden;margin:8px 0}}
.progress{{height:100%;transition:width .3s ease}}
.sensor-status{{display:flex;align-items:center;margin:5px 0;font-size:.85em}}
.sensor-status .dot{{width:10px;height:10px;border-radius:50%;margin-right:8px}}
.dot-green{{background:#4caf50}}
.dot-red{{background:#f44336}}
.footer{{text-align:center;margin-top:25px;padding-top:15px;border-top:1px solid #eee;font-size:.85em;color:#888}}
.footer a{{color:#4caf50}}
.sensor-unavailable{{opacity:0.5}}
.individual-temps{{font-size:.65em;color:#8d6e63;margin-top:8px;padding-top:8px;border-top:1px solid #e0e0e0}}
.individual-temps span{{margin:0 4px}}
</style></head><body><div id="main-container">"""

HTML_TITLE = """<h1>🌱 Agricultural Sensor Monitor</h1>
<p class="subtitle">Version {version} | Real-time soil and weather monitoring</p>"""

HTML_READINGS_GRID = """
<h2>📊 Live Sensor Readings</h2>
<div class="readings-grid">
    <div class="reading-card soil" id="soil-temp-card">
        <div class="label">🌡️ Average Soil Temperature</div>
        <div id="soil-temp-value" class="value" style="color:#795548" data-c="--" data-f="--">--.-<span class="unit">°C</span></div>
        <div id="soil-temp-status" class="status status-ok">Optimal</div>
        <button id="soil-temp-toggle" class="toggle-btn">Show °F</button>
        <div id="individual-temps" class="individual-temps"></div>
    </div>
    <div class="reading-card moisture" id="soil-moisture-card">
        <div class="label">💧 Soil Moisture</div>
        <div id="soil-moisture-value" class="value" style="color:#4caf50">--<span class="unit">%</span></div>
        <div id="soil-moisture-status" class="status status-ok">Optimal</div>
    </div>
    <div class="reading-card temp" id="ir-temp-card">
        <div class="label">🍃 Leaf/Surface Temp</div>
        <div id="ir-temp-value" class="value" style="color:#ff9800" data-c="--" data-f="--">--.-<span class="unit">°C</span></div>
        <div id="ir-temp-status" class="status status-ok">Normal</div>
        <button id="ir-temp-toggle" class="toggle-btn">Show °F</button>
    </div>
    <div class="reading-card rain" id="rainfall-card">
        <div class="label">🌧️ Rainfall (1 hour)</div>
        <div id="rainfall-value" class="value" style="color:#2196f3">--<span class="unit">mm</span></div>
        <div id="rainfall-status" class="status status-info">None</div>
    </div>
</div>
"""

HTML_CHART_SECTION = """
<h2>📈 Historical Trends</h2>
<div class="chart-container">
    <div class="chart-title">Soil Temperature & Moisture</div>
    <div id="chart-soil"></div>
</div>
<div class="chart-container">
    <div class="chart-title">Rainfall Over Time</div>
    <div id="chart-rainfall"></div>
</div>
"""

HTML_SYSTEM_SECTION = """
<h2>⚙️ System Status</h2>
<div class="system-grid">
    <div class="system-card">
        <h3>Memory Usage</h3>
        <div class="progress-bar"><div id="mem-progress" class="progress"></div></div>
        <div style="font-size:.8em;color:#666"><span id="mem-detail">--</span></div>
    </div>
    <div class="system-card">
        <h3>Device Info</h3>
        <div style="font-size:.85em;color:#555">
            <div>Device: <b id="device-model">--</b></div>
            <div>Uptime: <b id="uptime-value">--</b></div>
            <div>Version: v{version}</div>
        </div>
    </div>
    <div class="system-card">
        <h3>Sensor Status</h3>
        <div class="sensor-status"><div class="dot" id="dot-rainfall"></div>Rainfall Sensor</div>
        <div class="sensor-status"><div class="dot" id="dot-ir"></div>IR Temperature</div>
        <div class="sensor-status"><div class="dot" id="dot-soil-temp"></div>Soil Temperature</div>
        <div class="sensor-status"><div class="dot" id="dot-moisture"></div>Soil Moisture</div>
    </div>
</div>
"""

HTML_FOOTER = """
<div class="footer">
    <p>Last Updated: <span id="last-updated">Never</span></p>
    <p>Download: <a href="/csv">CSV</a> | <a href="/json">JSON</a> | <a href="/sensors">Details</a> | <a href="/test.html">Test</a></p>
</div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
    let soilTempCelsius = true;
    let irTempCelsius = true;
    
    // Soil Chart with multiple temperature sensors
    const soilChart = new ApexCharts(document.querySelector("#chart-soil"), {{
        series: [], 
        chart: {{ height: 280, type: 'line', toolbar: {{ show: false }} }},
        stroke: {{ 
            curve: 'smooth',
            width: [3, 2, 2, 2, 3],  // Average thick, individuals thin, moisture thick
            dashArray: [0, 5, 5, 5, 0]  // Solid for average and moisture, dotted for individual sensors
        }},
        xaxis: {{ type: 'category', categories: [] }},
        yaxis: [
            {{ 
                title: {{ text: "Temperature (°C)" }}, 
                labels: {{ style: {{ colors: '#795548' }} }}
            }},
            {{ 
                opposite: true, 
                min: 0, 
                max: 100, 
                title: {{ text: "Moisture (%)" }}, 
                labels: {{ style: {{ colors: '#4caf50' }} }}
            }}
        ],
        colors: ['#795548', '#a0826d', '#b08d78', '#c09883', '#4caf50'],  // Main temp, 3 sensor variations, moisture
        legend: {{ position: 'top', horizontalAlign: 'left' }},
        noData: {{ text: 'Loading...' }}
    }});
    soilChart.render();
    
    // Rainfall Chart
    const rainChart = new ApexCharts(document.querySelector("#chart-rainfall"), {{
        series: [], chart: {{ height: 200, type: 'bar', toolbar: {{ show: false }} }},
        xaxis: {{ type: 'category', categories: [] }},
        yaxis: {{ title: {{ text: 'Rainfall (mm)' }}, min: 0 }},
        colors: ['#2196f3'],
        dataLabels: {{ enabled: false }},
        noData: {{ text: 'Loading...' }}
    }});
    rainChart.render();

    function updateCharts() {{
        fetch('/api/history').then(r => r.json()).then(data => {{
            // Prepare series with proper y-axis assignment
            const series = [
                {{ 
                    name: 'Avg Soil Temp', 
                    data: data.soil_temps || [],
                    type: 'line'
                }},
                {{ 
                    name: 'Sensor 1', 
                    data: data.soil_temp_1 || [],
                    type: 'line'
                }},
                {{ 
                    name: 'Sensor 2', 
                    data: data.soil_temp_2 || [],
                    type: 'line'
                }},
                {{ 
                    name: 'Sensor 3', 
                    data: data.soil_temp_3 || [],
                    type: 'line'
                }},
                {{ 
                    name: 'Moisture', 
                    data: data.soil_moistures || [],
                    type: 'line'
                }}
            ];
            
            soilChart.updateSeries(series);
            soilChart.updateOptions({{ 
                xaxis: {{ categories: data.timestamps || [] }},
                yaxis: [
                    {{
                        title: {{ text: "Temperature (°C)" }},
                        seriesName: 'Avg Soil Temp'
                    }},
                    {{
                        opposite: true,
                        min: 0,
                        max: 100,
                        title: {{ text: "Moisture (%)" }},
                        seriesName: 'Moisture'
                    }}
                ]
            }});
            
            rainChart.updateSeries([{{ name: 'Rainfall', data: data.rainfall }}]);
            rainChart.updateOptions({{ xaxis: {{ categories: data.timestamps }} }});
        }}).catch(err => console.error("History error:", err));
    }}

    // Temperature toggle buttons
    document.getElementById('soil-temp-toggle').addEventListener('click', function() {{
        soilTempCelsius = !soilTempCelsius;
        updateSoilTempDisplay();
    }});
    document.getElementById('ir-temp-toggle').addEventListener('click', function() {{
        irTempCelsius = !irTempCelsius;
        updateIrTempDisplay();
    }});
    
    function updateSoilTempDisplay() {{
        const el = document.getElementById('soil-temp-value');
        const c = el.getAttribute('data-c');
        const f = el.getAttribute('data-f');
        el.innerHTML = soilTempCelsius ? `${{c}}<span class="unit">°C</span>` : `${{f}}<span class="unit">°F</span>`;
        document.getElementById('soil-temp-toggle').innerText = soilTempCelsius ? 'Show °F' : 'Show °C';
        
        // Also update individual temps if they exist (will be updated properly in updateLiveData)
        const individualEl = document.getElementById('individual-temps');
        if (individualEl && window.lastSensorData) {{
            const d = window.lastSensorData;
            const temp1 = d.soil_temp_1_c ? d.soil_temp_1_c.toFixed(1) : '--';
            const temp2 = d.soil_temp_2_c ? d.soil_temp_2_c.toFixed(1) : '--';
            const temp3 = d.soil_temp_3_c ? d.soil_temp_3_c.toFixed(1) : '--';
            
            if (soilTempCelsius) {{
                individualEl.innerHTML = `S1: ${{temp1}}°C<span>|</span>S2: ${{temp2}}°C<span>|</span>S3: ${{temp3}}°C`;
            }} else {{
                const temp1f = d.soil_temp_1_c ? ((d.soil_temp_1_c * 9/5) + 32).toFixed(1) : '--';
                const temp2f = d.soil_temp_2_c ? ((d.soil_temp_2_c * 9/5) + 32).toFixed(1) : '--';
                const temp3f = d.soil_temp_3_c ? ((d.soil_temp_3_c * 9/5) + 32).toFixed(1) : '--';
                individualEl.innerHTML = `S1: ${{temp1f}}°F<span>|</span>S2: ${{temp2f}}°F<span>|</span>S3: ${{temp3f}}°F`;
            }}
        }}
    }}
    
    function updateIrTempDisplay() {{
        const el = document.getElementById('ir-temp-value');
        const c = el.getAttribute('data-c');
        const f = el.getAttribute('data-f');
        el.innerHTML = irTempCelsius ? `${{c}}<span class="unit">°C</span>` : `${{f}}<span class="unit">°F</span>`;
        document.getElementById('ir-temp-toggle').innerText = irTempCelsius ? 'Show °F' : 'Show °C';
    }}

    function updateLiveData() {{
        fetch('/api/data').then(r => r.json()).then(d => {{
            // Store for toggle updates
            window.lastSensorData = d;
            // Soil Temperature
            const stEl = document.getElementById('soil-temp-value');
            const stCard = document.getElementById('soil-temp-card');
            const stStatus = document.getElementById('soil-temp-status');
            const individualEl = document.getElementById('individual-temps');
            
            if (d.ds18b20_available) {{
                stCard.classList.remove('sensor-unavailable');
                stEl.setAttribute('data-c', d.soil_temp_c.toFixed(1));
                stEl.setAttribute('data-f', d.soil_temp_f.toFixed(1));
                updateSoilTempDisplay();
                
                // Update individual sensor readings
                const temp1 = d.soil_temp_1_c ? d.soil_temp_1_c.toFixed(1) : '--';
                const temp2 = d.soil_temp_2_c ? d.soil_temp_2_c.toFixed(1) : '--';
                const temp3 = d.soil_temp_3_c ? d.soil_temp_3_c.toFixed(1) : '--';
                
                if (soilTempCelsius) {{
                    individualEl.innerHTML = `S1: ${{temp1}}°C<span>|</span>S2: ${{temp2}}°C<span>|</span>S3: ${{temp3}}°C`;
                }} else {{
                    const temp1f = d.soil_temp_1_c ? ((d.soil_temp_1_c * 9/5) + 32).toFixed(1) : '--';
                    const temp2f = d.soil_temp_2_c ? ((d.soil_temp_2_c * 9/5) + 32).toFixed(1) : '--';
                    const temp3f = d.soil_temp_3_c ? ((d.soil_temp_3_c * 9/5) + 32).toFixed(1) : '--';
                    individualEl.innerHTML = `S1: ${{temp1f}}°F<span>|</span>S2: ${{temp2f}}°F<span>|</span>S3: ${{temp3f}}°F`;
                }}
                
                if (d.soil_temp_c < {soil_cold}) {{ stStatus.className = 'status status-warn'; stStatus.innerText = 'Cold'; }}
                else if (d.soil_temp_c > {soil_hot}) {{ stStatus.className = 'status status-error'; stStatus.innerText = 'Hot'; }}
                else {{ stStatus.className = 'status status-ok'; stStatus.innerText = 'Optimal'; }}
            }} else {{ 
                stCard.classList.add('sensor-unavailable'); 
                stEl.innerHTML = 'N/A'; 
                stStatus.innerText = 'Offline';
                individualEl.innerHTML = '';
            }}
            
            // Soil Moisture
            const smEl = document.getElementById('soil-moisture-value');
            const smCard = document.getElementById('soil-moisture-card');
            const smStatus = document.getElementById('soil-moisture-status');
            if (d.soil_moisture_available) {{
                smCard.classList.remove('sensor-unavailable');
                smEl.innerHTML = `${{d.soil_moisture.toFixed(0)}}<span class="unit">%</span>`;
                if (d.soil_moisture < {soil_dry}) {{ smStatus.className = 'status status-error'; smStatus.innerText = 'Needs Water!'; }}
                else if (d.soil_moisture > {soil_wet}) {{ smStatus.className = 'status status-warn'; smStatus.innerText = 'Very Wet'; }}
                else {{ smStatus.className = 'status status-ok'; smStatus.innerText = 'Optimal'; }}
            }} else {{ smCard.classList.add('sensor-unavailable'); smEl.innerHTML = 'N/A'; smStatus.innerText = 'Offline'; }}
            
            // IR Temperature
            const irEl = document.getElementById('ir-temp-value');
            const irCard = document.getElementById('ir-temp-card');
            const irStatus = document.getElementById('ir-temp-status');
            if (d.mlx90614_available) {{
                irCard.classList.remove('sensor-unavailable');
                irEl.setAttribute('data-c', d.ir_object_temp_c.toFixed(1));
                irEl.setAttribute('data-f', d.ir_object_temp_f.toFixed(1));
                updateIrTempDisplay();
                irStatus.className = 'status status-ok'; irStatus.innerText = 'Active';
            }} else {{ irCard.classList.add('sensor-unavailable'); irEl.innerHTML = 'N/A'; irStatus.innerText = 'Offline'; }}
            
            // Rainfall
            const rfEl = document.getElementById('rainfall-value');
            const rfCard = document.getElementById('rainfall-card');
            const rfStatus = document.getElementById('rainfall-status');
            if (d.rainfall_available) {{
                rfCard.classList.remove('sensor-unavailable');
                rfEl.innerHTML = `${{d.rainfall_hourly.toFixed(1)}}<span class="unit">mm</span>`;
                if (d.rainfall_hourly >= {rain_heavy}) {{ rfStatus.className = 'status status-error'; rfStatus.innerText = 'Heavy Rain'; }}
                else if (d.rainfall_hourly >= {rain_mod}) {{ rfStatus.className = 'status status-warn'; rfStatus.innerText = 'Moderate'; }}
                else if (d.rainfall_hourly >= {rain_light}) {{ rfStatus.className = 'status status-ok'; rfStatus.innerText = 'Light Rain'; }}
                else {{ rfStatus.className = 'status status-info'; rfStatus.innerText = 'None'; }}
            }} else {{ rfCard.classList.add('sensor-unavailable'); rfEl.innerHTML = 'N/A'; rfStatus.innerText = 'Offline'; }}
            
            // System info
            document.getElementById('device-model').innerText = d.device_model || '--';
            document.getElementById('uptime-value').innerText = d.uptime_str || '--';
            
            const mp = document.getElementById('mem-progress');
            mp.style.width = d.memory_percent.toFixed(1) + '%';
            mp.style.backgroundColor = d.memory_percent > 85 ? '#f44336' : d.memory_percent > 70 ? '#ff9800' : '#4caf50';
            document.getElementById('mem-detail').innerText = `${{d.memory_percent.toFixed(1)}}% used`;
            
            // Sensor status dots
            document.getElementById('dot-rainfall').className = 'dot ' + (d.rainfall_available ? 'dot-green' : 'dot-red');
            document.getElementById('dot-ir').className = 'dot ' + (d.mlx90614_available ? 'dot-green' : 'dot-red');
            document.getElementById('dot-soil-temp').className = 'dot ' + (d.ds18b20_available ? 'dot-green' : 'dot-red');
            document.getElementById('dot-moisture').className = 'dot ' + (d.soil_moisture_available ? 'dot-green' : 'dot-red');
            
            document.getElementById('last-updated').innerText = new Date().toLocaleTimeString();
        }}).catch(err => console.error("Data error:", err));
    }}
    
    updateLiveData(); updateCharts();
    setInterval(updateLiveData, 5000);
    setInterval(updateCharts, 60000);
}});
</script>
</body></html>
"""

def create_html(config_obj):
    gc.collect()
    v = config_obj.VERSION
    return ''.join([
        HTML_HEADER.format(version=v),
        HTML_TITLE.format(version=v),
        HTML_READINGS_GRID,
        HTML_CHART_SECTION,
        HTML_SYSTEM_SECTION.format(version=v),
        HTML_FOOTER.format(
            soil_dry=config_obj.SOIL_DRY, soil_wet=config_obj.SOIL_WET,
            soil_cold=config_obj.SOIL_TEMP_COLD, soil_hot=config_obj.SOIL_TEMP_HOT,
            rain_light=config_obj.RAINFALL_LIGHT, rain_mod=config_obj.RAINFALL_MODERATE,
            rain_heavy=config_obj.RAINFALL_HEAVY
        )
    ])

def send_chunked_html(client_socket, html_content):
    try:
        headers = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n"
        client_socket.sendall(headers + html_content.encode())
    except Exception as e:
        print(f"Error sending HTML: {e}")
    finally:
        client_socket.close()