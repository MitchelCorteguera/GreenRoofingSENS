# web_template.py - Dashboard for 4 agricultural sensors
import gc
import config

def create_html(config_obj):
    return """<!DOCTYPE html><html><head><title>Agricultural Monitor v3.0</title>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<style>
body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);margin:0;padding:0;min-height:100vh}
#main-container{max-width:1200px;margin:20px auto;background:rgba(255,255,255,0.95);padding:30px;box-shadow:0 20px 40px rgba(0,0,0,.15);border-radius:20px;backdrop-filter:blur(10px)}
h1{text-align:center;color:#2e7d32;margin-bottom:5px;font-size:2.5em;text-shadow:2px 2px 4px rgba(0,0,0,0.1)}
.subtitle{text-align:center;color:#666;margin-bottom:30px;font-size:1.1em}
h2{color:#2c3e50;border-bottom:3px solid #4caf50;padding-bottom:10px;margin-top:40px;font-size:1.8em}
.readings-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin-bottom:30px}
.reading-card{background:linear-gradient(145deg,#ffffff,#f0f0f0);padding:25px;border-radius:15px;text-align:center;border-left:6px solid #4caf50;box-shadow:0 8px 25px rgba(0,0,0,.1);transition:transform 0.3s ease,box-shadow 0.3s ease;position:relative;overflow:hidden}
.reading-card:hover{transform:translateY(-5px);box-shadow:0 15px 35px rgba(0,0,0,.2)}
.reading-card.rain{border-left-color:#2196f3;background:linear-gradient(145deg,#e3f2fd,#ffffff)}
.reading-card.temp{border-left-color:#ff9800;background:linear-gradient(145deg,#fff3e0,#ffffff)}
.reading-card.soil{border-left-color:#795548;background:linear-gradient(145deg,#efebe9,#ffffff)}
.reading-card.moisture{border-left-color:#4caf50;background:linear-gradient(145deg,#e8f5e9,#ffffff)}
.label{font-size:1em;color:#555;margin-bottom:8px;font-weight:600}
.value{font-size:2.2em;font-weight:700;margin:12px 0;text-shadow:1px 1px 2px rgba(0,0,0,0.1)}
.unit{font-size:0.4em;font-weight:normal;color:#888;margin-left:2px}
.status{font-size:.75em;padding:3px 10px;border-radius:12px;display:inline-block;margin-top:5px}
.status-ok{background:#c8e6c9;color:#2e7d32}
.status-warn{background:#fff3cd;color:#856404}
.status-error{background:#ffcdd2;color:#c62828}
.status-info{background:#e3f2fd;color:#1565c0}
.toggle-btn{font-size:.7em;padding:4px 10px;margin-top:8px;cursor:pointer;border:none;background:#4caf50;color:#fff;border-radius:15px}
.toggle-btn:hover{background:#388e3c}
.chart-container{background:linear-gradient(145deg,#ffffff,#f8f9fa);border:2px solid #e0e0e0;border-radius:15px;padding:25px;margin-bottom:25px;box-shadow:0 8px 20px rgba(0,0,0,.08)}
.chart-title{margin:0 0 15px;font-size:1.3rem;color:#333;font-weight:600;display:flex;align-items:center;gap:10px}
.chart-controls{display:flex;gap:10px;margin-bottom:15px;flex-wrap:wrap}
.chart-btn{padding:8px 16px;border:2px solid #4caf50;background:transparent;color:#4caf50;border-radius:20px;cursor:pointer;transition:all 0.3s ease;font-size:0.9em}
.chart-btn.active,.chart-btn:hover{background:#4caf50;color:white}
.system-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}
.system-card{background:#f5f5f5;border-radius:10px;padding:15px}
.system-card h3{margin:0 0 10px;font-size:.95rem;color:#333}
.progress-bar{width:100%;height:8px;background:#e0e0e0;border-radius:4px;overflow:hidden;margin:8px 0}
.progress{height:100%;transition:width .3s ease}
.sensor-status{display:flex;align-items:center;margin:5px 0;font-size:.85em}
.sensor-status .dot{width:10px;height:10px;border-radius:50%;margin-right:8px}
.dot-green{background:#4caf50}
.dot-red{background:#f44336}
.footer{text-align:center;margin-top:25px;padding-top:15px;border-top:1px solid #eee;font-size:.85em;color:#888}
.footer a{color:#4caf50}
.sensor-unavailable{opacity:0.5}
.individual-temps{font-size:.65em;color:#8d6e63;margin-top:8px;padding-top:8px;border-top:1px solid #e0e0e0}
.individual-temps span{margin:0 4px}
</style></head><body><div id="main-container">

<h1>🌱 Agricultural Sensor Monitor</h1>
<p class="subtitle">Version 3.0 | Real-time soil and weather monitoring</p>

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

<h2>📈 Real-time Analytics</h2>
<div class="chart-container">
    <div class="chart-title">🌡️ Temperature & Moisture Trends</div>
    <div class="chart-controls">
        <button class="chart-btn active" onclick="setTimeRange('1h')">1 Hour</button>
        <button class="chart-btn" onclick="setTimeRange('6h')">6 Hours</button>
        <button class="chart-btn" onclick="setTimeRange('24h')">24 Hours</button>
        <button class="chart-btn" onclick="toggleSensorView()">Toggle Individual Sensors</button>
    </div>
    <div id="chart-soil"></div>
</div>
<div class="chart-container">
    <div class="chart-title">🌧️ Precipitation Analysis</div>
    <div class="chart-controls">
        <button class="chart-btn active" onclick="setRainView('hourly')">Hourly</button>
        <button class="chart-btn" onclick="setRainView('cumulative')">Cumulative</button>
    </div>
    <div id="chart-rainfall"></div>
</div>
<div class="chart-container">
    <div class="chart-title">🍃 IR Temperature Monitoring</div>
    <div id="chart-ir"></div>
</div>

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
            <div>Version: v3.0</div>
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

<div class="footer">
    <p>Last Updated: <span id="last-updated">Never</span></p>
    <p>Download: <a href="/csv">CSV</a> | <a href="/json">JSON</a> | <a href="/sensors">Sensors</a> | <a href="/debug">Debug</a></p>
</div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    let soilTempCelsius = true;
    let irTempCelsius = true;
    let showIndividualSensors = false;
    let currentRainView = 'hourly';
    
    // Load placeholder data immediately
    loadPlaceholderData();
    
    function loadPlaceholderData() {
        // Set realistic placeholder values
        document.getElementById('soil-temp-value').setAttribute('data-c', '22.3');
        document.getElementById('soil-temp-value').setAttribute('data-f', '72.1');
        document.getElementById('soil-temp-value').innerHTML = '22.3<span class="unit">°C</span>';
        document.getElementById('individual-temps').innerHTML = 'S1: 21.8°C<span>|</span>S2: 22.1°C<span>|</span>S3: 23.0°C';
        
        document.getElementById('soil-moisture-value').innerHTML = '45<span class="unit">%</span>';
        document.getElementById('ir-temp-value').setAttribute('data-c', '24.7');
        document.getElementById('ir-temp-value').setAttribute('data-f', '76.5');
        document.getElementById('ir-temp-value').innerHTML = '24.7<span class="unit">°C</span>';
        document.getElementById('rainfall-value').innerHTML = '0.0<span class="unit">mm</span>';
        
        // Set status indicators
        document.getElementById('soil-temp-status').innerText = 'Loading...';
        document.getElementById('soil-moisture-status').innerText = 'Loading...';
        document.getElementById('ir-temp-status').innerText = 'Loading...';
        document.getElementById('rainfall-status').innerText = 'Loading...';
        
        // System info placeholders
        document.getElementById('device-model').innerText = 'Pico W';
        document.getElementById('uptime-value').innerText = '2h 15m';
        document.getElementById('mem-progress').style.width = '35%';
        document.getElementById('mem-progress').style.backgroundColor = '#4caf50';
        document.getElementById('mem-detail').innerText = '35% used';
        
        // All sensors online initially
        document.getElementById('dot-rainfall').className = 'dot dot-green';
        document.getElementById('dot-ir').className = 'dot dot-green';
        document.getElementById('dot-soil-temp').className = 'dot dot-green';
        document.getElementById('dot-moisture').className = 'dot dot-green';
        
        document.getElementById('last-updated').innerText = 'Loading...';
    }
    
    // Enhanced Soil Chart
    const soilChart = new ApexCharts(document.querySelector("#chart-soil"), {
        series: [], 
        chart: { 
            height: 350, 
            type: 'line', 
            toolbar: { show: true },
            animations: { enabled: true }
        },
        stroke: { 
            curve: 'smooth',
            width: [4, 4]
        },
        xaxis: { 
            type: 'datetime',
            labels: { 
                style: { colors: '#666' },
                format: 'HH:mm'
            }
        },
        yaxis: [
            { 
                title: { text: "Temperature (°C)", style: { color: '#795548' } }, 
                labels: { style: { colors: '#795548' } }
            },
            { 
                opposite: true, 
                min: 0, 
                max: 100, 
                title: { text: "Moisture (%)", style: { color: '#4caf50' } }, 
                labels: { style: { colors: '#4caf50' } }
            }
        ],
        colors: showIndividualSensors ? ['#795548', '#ff5722', '#e91e63', '#9c27b0', '#4caf50'] : ['#795548', '#4caf50'],
        legend: { position: 'top' },
        grid: { borderColor: '#e0e0e0' },
        tooltip: { 
            shared: true,
            intersect: false
        },
        noData: { text: 'Loading sensor data...' }
    });
    soilChart.render();
    
    // Rainfall Chart
    const rainChart = new ApexCharts(document.querySelector("#chart-rainfall"), {
        series: [], 
        chart: { 
            height: 280, 
            type: 'bar', 
            toolbar: { show: true }
        },
        plotOptions: {
            bar: {
                borderRadius: 4,
                columnWidth: '60%'
            }
        },
        xaxis: { 
            type: 'datetime',
            labels: { 
                style: { colors: '#666' },
                format: 'HH:mm'
            }
        },
        yaxis: { 
            title: { text: 'Rainfall (mm)', style: { color: '#2196f3' } }, 
            min: 0,
            labels: { style: { colors: '#2196f3' } }
        },
        colors: ['#2196f3'],
        dataLabels: { enabled: false },
        grid: { borderColor: '#e0e0e0' },
        tooltip: { 
            y: { formatter: function(val) { return val.toFixed(2) + ' mm'; } }
        },
        noData: { text: 'Loading rainfall data...' }
    });
    rainChart.render();
    
    // IR Temperature Chart
    const irChart = new ApexCharts(document.querySelector("#chart-ir"), {
        series: [], 
        chart: { 
            height: 280, 
            type: 'line', 
            toolbar: { show: true }
        },
        stroke: { 
            curve: 'smooth',
            width: 3
        },
        xaxis: { 
            type: 'datetime',
            labels: { 
                style: { colors: '#666' },
                format: 'HH:mm'
            }
        },
        yaxis: { 
            title: { text: 'Temperature (°C)', style: { color: '#ff9800' } }, 
            labels: { style: { colors: '#ff9800' } }
        },
        colors: ['#ff9800', '#ff5722'],
        legend: { position: 'top' },
        grid: { borderColor: '#e0e0e0' },
        tooltip: { 
            shared: true,
            intersect: false
        },
        noData: { text: 'Loading IR temperature data...' }
    });
    irChart.render();

    window.setTimeRange = function(range) {
        document.querySelectorAll('.chart-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        updateCharts();
    };
    
    window.toggleSensorView = function() {
        showIndividualSensors = !showIndividualSensors;
        updateCharts();
    };
    
    window.setRainView = function(view) {
        currentRainView = view;
        document.querySelectorAll('.chart-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        updateCharts();
    };
    
    function updateCharts() {
        if (!window.lastApiData || !window.lastApiData.history) {
            return;
        }
        
        const data = window.lastApiData.history;
        if (!data.timestamps) return;
        
        const timestamps = data.timestamps.map(t => new Date().toISOString().split('T')[0] + 'T' + t);
        
        let series = [
            { 
                name: 'Avg Soil Temp', 
                data: timestamps.map((t, i) => [new Date(t).getTime(), data.soil_temps[i] || 0]),
                yAxisIndex: 0
            }
        ];
        
        if (showIndividualSensors && data.soil_temp_1) {
            series.push(
                { name: 'Sensor 1', data: timestamps.map((t, i) => [new Date(t).getTime(), data.soil_temp_1[i] || 0]), yAxisIndex: 0 },
                { name: 'Sensor 2', data: timestamps.map((t, i) => [new Date(t).getTime(), data.soil_temp_2[i] || 0]), yAxisIndex: 0 },
                { name: 'Sensor 3', data: timestamps.map((t, i) => [new Date(t).getTime(), data.soil_temp_3[i] || 0]), yAxisIndex: 0 }
            );
        }
        
        series.push({
            name: 'Moisture',
            data: timestamps.map((t, i) => [new Date(t).getTime(), data.soil_moistures[i] || 0]),
            yAxisIndex: 1
        });
        
        soilChart.updateOptions({
            colors: showIndividualSensors ? ['#795548', '#ff5722', '#e91e63', '#9c27b0', '#4caf50'] : ['#795548', '#4caf50']
        });
        soilChart.updateSeries(series);
        
        // Update rainfall chart
        let rainData = timestamps.map((t, i) => [new Date(t).getTime(), data.rainfall[i] || 0]);
        if (currentRainView === 'cumulative') {
            let cumulative = 0;
            rainData = rainData.map(([t, val]) => [t, cumulative += val]);
        }
        rainChart.updateSeries([{ name: currentRainView === 'cumulative' ? 'Cumulative Rainfall' : 'Hourly Rainfall', data: rainData }]);
        
        // Update IR temperature chart
        const irSeries = [
            { name: 'Object Temp', data: timestamps.map((t, i) => [new Date(t).getTime(), data.ir_temps ? data.ir_temps[i] || 0 : 0]) }
        ];
        irChart.updateSeries(irSeries);
    }

    // Temperature toggle buttons
    document.getElementById('soil-temp-toggle').addEventListener('click', function() {
        soilTempCelsius = !soilTempCelsius;
        updateSoilTempDisplay();
    });
    document.getElementById('ir-temp-toggle').addEventListener('click', function() {
        irTempCelsius = !irTempCelsius;
        updateIrTempDisplay();
    });
    
    function updateSoilTempDisplay() {
        const el = document.getElementById('soil-temp-value');
        const c = el.getAttribute('data-c');
        const f = el.getAttribute('data-f');
        el.innerHTML = soilTempCelsius ? c + '<span class="unit">°C</span>' : f + '<span class="unit">°F</span>';
        document.getElementById('soil-temp-toggle').innerText = soilTempCelsius ? 'Show °F' : 'Show °C';
    }
    
    function updateIrTempDisplay() {
        const el = document.getElementById('ir-temp-value');
        const c = el.getAttribute('data-c');
        const f = el.getAttribute('data-f');
        el.innerHTML = irTempCelsius ? c + '<span class="unit">°C</span>' : f + '<span class="unit">°F</span>';
        document.getElementById('ir-temp-toggle').innerText = irTempCelsius ? 'Show °F' : 'Show °C';
    }
    
    function updateLiveData() {
        fetch('/api/data', {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
            signal: AbortSignal.timeout(5000)
        }).then(r => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        }).then(d => {
            window.lastSensorData = d.live;
            window.lastApiData = d;
            updateCharts();
            
            // Soil Temperature
            const stEl = document.getElementById('soil-temp-value');
            const stCard = document.getElementById('soil-temp-card');
            const stStatus = document.getElementById('soil-temp-status');
            const individualEl = document.getElementById('individual-temps');
            
            if (d.status.ds18b20_available) {
                stCard.classList.remove('sensor-unavailable');
                stEl.setAttribute('data-c', d.live.soil_temp_c.toFixed(1));
                stEl.setAttribute('data-f', d.live.soil_temp_f.toFixed(1));
                updateSoilTempDisplay();
                
                const temp1 = d.live.soil_temp_1_c ? d.live.soil_temp_1_c.toFixed(1) : '--';
                const temp2 = d.live.soil_temp_2_c ? d.live.soil_temp_2_c.toFixed(1) : '--';
                const temp3 = d.live.soil_temp_3_c ? d.live.soil_temp_3_c.toFixed(1) : '--';
                
                if (soilTempCelsius) {
                    individualEl.innerHTML = 'S1: ' + temp1 + '°C<span>|</span>S2: ' + temp2 + '°C<span>|</span>S3: ' + temp3 + '°C';
                } else {
                    const temp1f = d.live.soil_temp_1_c ? ((d.live.soil_temp_1_c * 9/5) + 32).toFixed(1) : '--';
                    const temp2f = d.live.soil_temp_2_c ? ((d.live.soil_temp_2_c * 9/5) + 32).toFixed(1) : '--';
                    const temp3f = d.live.soil_temp_3_c ? ((d.live.soil_temp_3_c * 9/5) + 32).toFixed(1) : '--';
                    individualEl.innerHTML = 'S1: ' + temp1f + '°F<span>|</span>S2: ' + temp2f + '°F<span>|</span>S3: ' + temp3f + '°F';
                }
                
                stStatus.className = 'status status-ok';
                stStatus.innerText = 'Optimal';
            } else { 
                stCard.classList.add('sensor-unavailable'); 
                stEl.innerHTML = 'N/A'; 
                stStatus.innerText = 'Offline';
                individualEl.innerHTML = '';
            }
            
            // Soil Moisture
            const smEl = document.getElementById('soil-moisture-value');
            const smCard = document.getElementById('soil-moisture-card');
            const smStatus = document.getElementById('soil-moisture-status');
            if (d.status.soil_moisture_available) {
                smCard.classList.remove('sensor-unavailable');
                smEl.innerHTML = d.live.soil_moisture.toFixed(0) + '<span class="unit">%</span>';
                smStatus.className = 'status status-ok';
                smStatus.innerText = 'Optimal';
            } else { 
                smCard.classList.add('sensor-unavailable'); 
                smEl.innerHTML = 'N/A'; 
                smStatus.innerText = 'Offline'; 
            }
            
            // IR Temperature
            const irEl = document.getElementById('ir-temp-value');
            const irCard = document.getElementById('ir-temp-card');
            const irStatus = document.getElementById('ir-temp-status');
            if (d.status.mlx90614_available) {
                irCard.classList.remove('sensor-unavailable');
                irEl.setAttribute('data-c', d.live.ir_object_temp_c.toFixed(1));
                irEl.setAttribute('data-f', d.live.ir_object_temp_f.toFixed(1));
                updateIrTempDisplay();
                irStatus.className = 'status status-ok'; 
                irStatus.innerText = 'Active';
            } else { 
                irCard.classList.add('sensor-unavailable'); 
                irEl.innerHTML = 'N/A'; 
                irStatus.innerText = 'Offline'; 
            }
            
            // Rainfall
            const rfEl = document.getElementById('rainfall-value');
            const rfCard = document.getElementById('rainfall-card');
            const rfStatus = document.getElementById('rainfall-status');
            if (d.status.rainfall_available) {
                rfCard.classList.remove('sensor-unavailable');
                rfEl.innerHTML = d.live.rainfall_hourly.toFixed(1) + '<span class="unit">mm</span>';
                rfStatus.className = 'status status-info'; 
                rfStatus.innerText = 'None';
            } else { 
                rfCard.classList.add('sensor-unavailable'); 
                rfEl.innerHTML = 'N/A'; 
                rfStatus.innerText = 'Offline'; 
            }
            
            // System info
            document.getElementById('device-model').innerText = d.system.device_model || '--';
            document.getElementById('uptime-value').innerText = d.system.uptime_str || '--';
            
            const mp = document.getElementById('mem-progress');
            mp.style.width = d.system.memory_percent.toFixed(1) + '%';
            mp.style.backgroundColor = d.system.memory_percent > 85 ? '#f44336' : d.system.memory_percent > 70 ? '#ff9800' : '#4caf50';
            document.getElementById('mem-detail').innerText = d.system.memory_percent.toFixed(1) + '% used';
            
            // Sensor status dots
            document.getElementById('dot-rainfall').className = 'dot ' + (d.status.rainfall_available ? 'dot-green' : 'dot-red');
            document.getElementById('dot-ir').className = 'dot ' + (d.status.mlx90614_available ? 'dot-green' : 'dot-red');
            document.getElementById('dot-soil-temp').className = 'dot ' + (d.status.ds18b20_available ? 'dot-green' : 'dot-red');
            document.getElementById('dot-moisture').className = 'dot ' + (d.status.soil_moisture_available ? 'dot-green' : 'dot-red');
            
            document.getElementById('last-updated').innerText = new Date().toLocaleTimeString();
        }).catch(err => {
            console.error("Data fetch failed:", err.message);
            document.getElementById('last-updated').innerText = 'Connection Error';
        });
    }
    
    updateLiveData();
    setInterval(updateLiveData, 15000);
});
</script>
</body></html>
"""

def send_chunked_html(client_socket, html_content):
    try:
        headers = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n"
        client_socket.sendall(headers + html_content.encode())
    except Exception as e:
        print(f"Error sending HTML: {e}")
    finally:
        client_socket.close()